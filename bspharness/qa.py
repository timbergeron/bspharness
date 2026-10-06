"""Isolated QSS-M screenshot passes and runtime entity audits."""

import json
from math import isfinite
from pathlib import Path
import re
import shutil
import subprocess
import time

from .bsp import BSP
from .geometry import number
from .pipeline import digest, verified_build, write_json
from .routes import BUTTONS, WalkRoute

RENDER = {"width":1280,"height":720,"fov":90,"fov_adapt":1,
          "gamma":1,"contrast":1,"gl_texturemode":"GL_LINEAR_MIPMAP_LINEAR",
          "viewsize":120,"crosshair":0,"r_drawviewmodel":0,
          "r_fullbright":0,"r_drawflat":0,"r_lightmap":0,"gl_overbright":1}
RENDER.update(gl_load24bit=1, gl_max_size=0, gl_picmip=0, r_fastturb=0, r_fastsky=0, r_norefresh=0)
PHYSICS = {"sv_gravity":800,"sv_maxspeed":320,"sv_accelerate":10,
           "sv_friction":4,"sv_stopspeed":100,"edgefriction":2}


def waits(frames):
    groups,remainder = divmod(frames,50)
    return ["bh_ww"]*groups+["wait"]*remainder


def dump(marker):
    return [f"echo {marker}_BEGIN","edict 1",f"echo {marker}_END"]


def camera_config(cameras, routes=(), mode="sp"):
    if mode not in ("sp","dm"):
        raise ValueError("QA mode must be sp or dm")
    if mode=="dm" and (cameras or routes):
        raise ValueError("QSS-M disables test positioning in deathmatch; use DM for spawn/item audit and a separate SP pass for routes/cameras")
    if not cameras and not routes and mode!="dm":
        raise ValueError("Supply at least one camera or movement route")
    if any(not isinstance(r,WalkRoute) for r in routes) or len({r.name for r in routes})!=len(routes):
        raise ValueError("Supply distinct WalkRoute objects")
    names = set()
    for camera in cameras:
        name = camera["name"]
        if not isinstance(name,str) or not name.strip() or name in names:
            raise ValueError("Camera names must be nonempty and unique")
        names.add(name)
        if len(camera["origin"])!=3 or len(camera["angles"])!=3:
            raise ValueError("Camera requires XYZ and pitch/yaw/roll")
        for value in (*camera["origin"],*camera["angles"]):
            number(value)
        settle = camera.get("settle_frames",10)
        if type(settle) is not int or not 1 <= settle <= 7200:
            raise ValueError("Camera settle_frames must be an integer from 1 to 7200")
    lines = ["host_maxfps 72","host_framerate 0.013888889","host_timescale 0","cl_alwaysrun 0",
             *(f"{key} {value}" for key,value in PHYSICS.items()),
             *(f"{key} {value}" for key,value in RENDER.items() if key not in ("width","height")),
             "con_notifytime 0","con_notifylines 0",'alias bh_w "wait;wait;wait;wait;wait;wait;wait;wait;wait;wait"',
             'alias bh_ww "bh_w;bh_w;bh_w;bh_w;bh_w"',
             # Physics/entity settling does not need expensive scene drawing.
             # Restore drawing before cameras; their render settings stay fixed.
             "r_norefresh 1",
             "bh_ww;bh_ww;bh_ww;bh_ww",
             "echo BSPHARNESS_AUDIT_BEGIN","edicts","echo BSPHARNESS_AUDIT_END"]
    lines.extend(["echo BSPHARNESS_IMAGES_BEGIN", "imagelist", "echo BSPHARNESS_IMAGES_END"])
    releases = ["-"+button for button in BUTTONS]
    lines.extend(releases)
    for index,route in enumerate(routes):
        prefix = f"BSPHARNESS_ROUTE_{index}"
        lines.extend([f"cl_forwardspeed {number(route.speed)}",f"cl_backspeed {number(route.speed)}",
                      f"cl_sidespeed {number(route.speed)}","cl_movespeedkey 1",
                      "setpos "+" ".join(map(number,route.origin+route.angles)),
                      # QSS-M's numeric setpos enables noclip. Turn it off
                      # explicitly and verify the settled start before input.
                      "noclip 0",*waits(route.settle),*dump(prefix+"_START")])
        for step,action in enumerate(route.actions):
            lines.extend([*("+"+button for button in action.buttons),*waits(action.frames),
                          *releases,*dump(prefix+f"_STEP_{step}")])
        lines.extend([*waits(route.settle),*dump(prefix+"_FINISH")])
    if cameras:
        lines.extend(["god 1","noclip 1","r_norefresh 0"])
    for camera in cameras:
        values = (*camera["origin"],*camera["angles"])
        settling = ["bh_w"] if camera.get("settle_frames",10)==10 else waits(camera["settle_frames"])
        lines.extend(["setpos "+" ".join(map(number,values)),*settling,"screenshot png"])
    lines.extend(["bh_w","echo BSPHARNESS_QA_COMPLETE","quit"])
    return "\n".join(lines)+"\n"


def prepare(bsp, cameras, basedir, gamedir="bspharness_qa", routes=(), mode="sp"):
    bsp = Path(bsp).resolve()
    manifest = verified_build(bsp)
    if not re.fullmatch(r"[A-Za-z0-9_-]+",gamedir) or gamedir.casefold()=="id1":
        raise ValueError("Use a separate QA gamedir, not id1")
    basedir = Path(basedir).resolve()
    if not (basedir/"id1").is_dir():
        raise ValueError("basedir must contain your id1 directory")
    game = basedir/gamedir
    # Each pass gets its own folder: existing map installs and screenshots
    # are preserved, and old artifacts cannot count towards this QA pass.
    if game.exists():
        raise ValueError(f"QA gamedir already exists: {game}; choose a fresh --gamedir")
    config = camera_config(cameras,routes,mode)
    (game/"maps").mkdir(parents=True)
    (game/"configs").mkdir()
    if manifest.get("runtime_assets"):
        from .assets import stage
        stage(bsp.parent/"runtime", manifest["runtime_assets"], game)
    for suffix in (".bsp",".lit"):
        source = bsp.with_suffix(suffix)
        if source.exists():
            shutil.copy2(source,game/"maps"/source.name)
    (game/"shots.cfg").write_text(config,encoding="ascii")
    # QSS-M executes this after client signon. Startup +exec with wait chains
    # can block the command buffer used for the connection handshake.
    (game/"configs/connect.cfg").write_text("exec shots.cfg\n",encoding="ascii")
    return game


def edicts(text, marker="BSPHARNESS_AUDIT"):
    section = re.search(re.escape(marker)+r"_BEGIN\s*\n(.*?)"+re.escape(marker)+"_END",text,re.S)
    if not section:
        return []
    # Fields follow each EDICT header; classify the whole block before
    # reading origin/health/flags (not only lines before classname).
    live = []
    for block in re.split(r"\bEDICT\s+\d+:",section[1])[1:]:
        fields = {}
        for line in block.splitlines():
            match = re.match(r"\s*(\w+)\s+(.*?)\s*$",line)
            if match:
                fields[match[1]] = match[2].strip(" '")
        live.append(fields)
    return live


def position(entity):
    result = tuple(map(float,entity["origin"].split()))
    if len(result)!=3 or not all(isfinite(x) for x in result):
        raise ValueError("Invalid runtime origin")
    return result


def audit_log(text, entities, skill=1, deathmatch=False):
    errors = []
    # A rejected setting/command invalidates the claimed QA configuration,
    # even when the rest of the script reaches its completion marker.
    for command in sorted(set(re.findall(r'Unknown command\s+"([^"\n]+)"',text,re.I))):
        errors.append("Engine rejected QA command: "+command)
    for marker in ("Unknown particle command", "Too many duplicate names",
                   "assoc on particle chain", "uses unknown spawn type", "uses unknown render type"):
        if marker.casefold() in text.casefold():
            errors.append("Engine rejected particle configuration: "+marker)
    if "BSPHARNESS_QA_COMPLETE" not in text:
        errors.append("Engine did not complete the QA script")
    live = edicts(text)
    if not live:
        return errors+["Runtime entity dump is missing"]
    players = [e for e in live if e.get("classname")=="player"]
    if not players:
        errors.append("No live player in spawn audit")
    for player in players:
        try:
            health = float(player.get("health","0"))
        except ValueError:
            health = float("nan")
        if not isfinite(health) or health < 100:
            errors.append("Player lost health during spawn smoke test")
        if "FL_ONGROUND" not in player.get("flags",""):
            errors.append("Player is not on the ground before camera noclip")
    candidates,expected_items = [],[]
    for expected in entities:
        name = expected.get("classname","")
        # Stock 2048 means NOT_DEATHMATCH. Skill exclusions apply only in SP.
        excluded = 2048 if deathmatch else (256,512,1024)[min(2,skill)]
        if not name.startswith(("item_","weapon_")) or int(expected.get("spawnflags","0"))&excluded:
            continue
        try:
            point = position(expected)
        except (KeyError,ValueError):
            errors.append(f"Item has invalid origin: {name}")
            continue
        matches = []
        for index,actual in enumerate(live):
            if actual.get("classname") != name or "origin" not in actual:
                continue
            try:
                actual_point = position(actual)
            except ValueError:
                continue
            # Stock items fall from the authored +24 origin and may shift
            # corner origins by 16u. Match all three axes, once per edict.
            if all(abs(a-b)<=24.01 for a,b in zip(point,actual_point)):
                matches.append(index)
        candidates.append(matches)
        expected_items.append(expected)
    assigned = {}
    def match(item,seen):
        for index in candidates[item]:
            if index in seen:
                continue
            seen.add(index)
            if index not in assigned or match(assigned[index],seen):
                assigned[index] = item
                return True
        return False
    for item,expected in enumerate(expected_items):
        if not match(item,set()):
            errors.append(f"Item absent at runtime: {expected['classname']} at {expected['origin']}")
    return errors


def audit_routes(text, routes):
    results = []
    for index,route in enumerate(routes):
        errors,observations = [],{}
        def inspect(label, bounds=None, ground=False):
            players = [e for e in edicts(text,f"BSPHARNESS_ROUTE_{index}_{label}")
                       if e.get("classname")=="player"]
            if len(players)!=1:
                errors.append(f"{label}: expected one runtime player dump")
                return
            player = players[0]
            observations[label] = player
            if player.get("movetype") not in ("MOVETYPE_WALK","3","3.0"):
                errors.append(f"{label}: player is not using walking collision")
            if "FL_GODMODE" in player.get("flags",""):
                errors.append(f"{label}: god mode invalidates health verification")
            try:
                point = position(player)
                health = float(player.get("health","0"))
                if not isfinite(health) or health<route.min_health:
                    errors.append(f"{label}: player health is below {route.min_health}")
                if bounds is not None and not bounds.contains(point):
                    errors.append(f"{label}: origin {point} is outside expected bounds")
            except (KeyError,ValueError):
                errors.append(f"{label}: invalid runtime position/health")
            if ground and "FL_ONGROUND" not in player.get("flags",""):
                errors.append(f"{label}: player is not grounded")
        from .geometry import Bounds
        tolerance = route.start_tolerance
        start = Bounds(tuple(x-tolerance for x in route.origin),tuple(x+tolerance for x in route.origin))
        inspect("START",start,True)
        for step,action in enumerate(route.actions):
            inspect(f"STEP_{step}",action.expect)
        inspect("FINISH",route.finish,True)
        results.append({"name":route.name,"passed":not errors,"errors":errors,
                        "specification":route.metadata(),"observations":observations})
    return results


def run(bsp, cameras, basedir, engine, gamedir="bspharness_qa", timeout=90, routes=(), mode="sp"):
    if mode not in ("sp","dm"):
        raise ValueError("QA mode must be sp or dm")
    manifest = verified_build(bsp)
    game = prepare(bsp,cameras,basedir,gamedir,routes,mode)
    tested_bsp = game/"maps"/Path(bsp).name
    if any(digest(game/"maps"/name)!=sha for name,sha in manifest["artifacts"].items()):
        raise ValueError("Build artifacts changed while staging engine QA")
    engine = Path(engine).resolve()
    # Collision/entity passes do not need publication-size rendering. Fixed
    # physics timing is unchanged; camera passes retain the pinned resolution.
    width,height = (RENDER["width"],RENDER["height"]) if cameras else (320,200)
    command = [str(engine),"-basedir",str(Path(basedir).resolve()),"-game",gamedir,
               "-window","-width",str(width),"-height",str(height),"-condebug","-nomouse",
               "-nosound",*(arg for key in ("gl_load24bit", "gl_max_size", "gl_picmip", "r_fastturb", "r_fastsky")
                            for arg in ("+"+key, str(RENDER[key]))),
               "+deathmatch","1" if mode=="dm" else "0","+skill","1","+map",Path(bsp).stem]
    errors,code = [],None
    start = time.monotonic()
    with (game/"engine.log").open("w") as log:
        try:
            result = subprocess.run(command,cwd=game,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
            code = result.returncode
            if code != 0:
                errors.append(f"Engine exited {code}")
        except subprocess.TimeoutExpired:
            errors.append("Engine QA timed out")
    text = (game/"engine.log").read_text(errors="replace")
    console = game/"qconsole.log"
    if console.exists():
        text += "\n"+console.read_text(errors="replace")
    for marker in ("Mod_LoadNodes","invalid leaf","not 16 aligned","fell out of level","Host_Error","Sys_Error"):
        if marker.casefold() in text.casefold():
            errors.append("Engine reported "+marker)
    errors.extend(audit_log(text,BSP(tested_bsp).entities(),deathmatch=mode=="dm"))
    from .assets import audit_images, files
    records = manifest.get("runtime_assets", {})
    image_errors, loaded_images = audit_images(text, records)
    errors.extend(image_errors)
    try:
        files(game, records)
    except ValueError as exc:
        errors.append(str(exc))
    route_results = audit_routes(text,routes)
    errors.extend(f"Route {r['name']}: {error}" for r in route_results for error in r["errors"])
    # Timestamped filenames with same-second suffixes need not sort in the
    # order they were captured. Preserve the engine's file write sequence.
    shots = sorted((game/"screenshots").glob("*.png"),key=lambda p:(p.stat().st_mtime_ns,p.name))
    if len(shots) != len(cameras):
        errors.append(f"Expected {len(cameras)} screenshots, found {len(shots)}")
    report = {"schema":1,"passed":not errors,"errors":errors,"bsp_sha256":digest(tested_bsp),
              "artifacts":manifest["artifacts"],"routes":route_results,
              "runtime_assets":records,"loaded_images":loaded_images,
              "physics":{"fps":72,"fixed_frame_seconds":1/72,**PHYSICS,
                         "mode":"stock deathmatch" if mode=="dm" else "stock single-player"},
              "game_paks":{p.name:digest(p) for p in sorted((Path(basedir)/"id1").glob("*.pak"))},
              "engine_sha256":digest(engine),"command":command,"exit_code":code,
              "seconds":round(time.monotonic()-start,3),"gamedir":str(game),
              "render":{**RENDER,"width":width,"height":height,"r_norefresh":0 if cameras else 1},
              "screenshots":[{"camera":c["name"],"view":c,"file":str(s),"sha256":digest(s)} for c,s in zip(cameras,shots)],
              "visual_review":"pending; open the screenshots to review lighting and geometry",
              "scope":("Initial stock deathmatch spawn/item audit; use a separate SP pass for movement and cameras" if mode=="dm" else
                       "Authored movement probes and spawn/item audit; full gameplay and unsampled routes require playtesting")}
    write_json(game/"qa.json",report)
    return game/"qa.json",report
