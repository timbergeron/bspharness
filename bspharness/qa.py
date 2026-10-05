"""Isolated QSS-M screenshot passes and runtime entity audits."""

import json
from pathlib import Path
import re
import shutil
import subprocess
import time

from .bsp import BSP
from .geometry import number
from .pipeline import digest, verified_build, write_json


def camera_config(cameras):
    if not cameras:
        raise ValueError("Supply at least one camera")
    lines = ["host_maxfps 72","viewsize 120","crosshair 0","r_drawviewmodel 0",
             "con_notifytime 0",'alias bh_w "wait;wait;wait;wait;wait;wait;wait;wait;wait;wait"',
             'alias bh_ww "bh_w;bh_w;bh_w;bh_w;bh_w"',
             "bh_ww;bh_ww;bh_ww;bh_ww",
             "echo BSPHARNESS_AUDIT_BEGIN","edicts","echo BSPHARNESS_AUDIT_END",
             "god","noclip"]
    for camera in cameras:
        values = camera["origin"]+camera["angles"]
        if len(values) != 6:
            raise ValueError("Camera requires XYZ and pitch/yaw/roll")
        lines.extend(["setpos "+" ".join(map(number,values)),"bh_ww;bh_ww","screenshot png"])
    lines.extend(["bh_ww;bh_ww","echo BSPHARNESS_QA_COMPLETE","quit"])
    return "\n".join(lines)+"\n"


def prepare(bsp, cameras, basedir, gamedir="bspharness_qa"):
    bsp = Path(bsp).resolve()
    verified_build(bsp)
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
    (game/"maps").mkdir(parents=True)
    (game/"configs").mkdir()
    for suffix in (".bsp",".lit"):
        source = bsp.with_suffix(suffix)
        if source.exists():
            shutil.copy2(source,game/"maps"/source.name)
    (game/"shots.cfg").write_text(camera_config(cameras),encoding="ascii")
    # QSS-M executes this after client signon. Startup +exec with wait chains
    # can block the command buffer used for the connection handshake.
    (game/"configs/connect.cfg").write_text("exec shots.cfg\n",encoding="ascii")
    return game


def audit_log(text, entities):
    errors = []
    if "BSPHARNESS_QA_COMPLETE" not in text:
        errors.append("Engine did not complete the camera script")
    section = re.search(r"BSPHARNESS_AUDIT_BEGIN\s*\n(.*?)BSPHARNESS_AUDIT_END",text,re.S)
    if not section:
        return errors+["Runtime entity dump is missing"]
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
    players = [e for e in live if e.get("classname")=="player"]
    if not players:
        errors.append("No live player in spawn audit")
    for player in players:
        if float(player.get("health","0")) < 100:
            errors.append("Player lost health during spawn smoke test")
        if "FL_ONGROUND" not in player.get("flags",""):
            errors.append("Player is not on the ground before camera noclip")
    for expected in entities:
        name = expected.get("classname","")
        # SP QA intentionally does not audit DM-only spawns/items. Stock
        # spawnflags 2048 excludes an entity from single-player.
        if not name.startswith(("item_","weapon_")) or int(expected.get("spawnflags","0"))&2048:
            continue
        try:
            x,y,_ = map(float,expected["origin"].split())
        except (KeyError,ValueError):
            errors.append(f"Item has invalid origin: {name}")
            continue
        found = False
        for actual in live:
            if actual.get("classname") != name or "origin" not in actual:
                continue
            try:
                ax,ay,_ = map(float,actual["origin"].split())
            except ValueError:
                continue
            # Some stock item spawn functions shift corner origins by 16u.
            if abs(ax-x)<=24 and abs(ay-y)<=24:
                found = True
                break
        if not found:
            errors.append(f"Item absent at runtime: {name} at {expected['origin']}")
    return errors


def run(bsp, cameras, basedir, engine, gamedir="bspharness_qa", timeout=90):
    game = prepare(bsp,cameras,basedir,gamedir)
    engine = Path(engine).resolve()
    command = [str(engine),"-basedir",str(Path(basedir).resolve()),"-game",gamedir,
               "-window","-width","1280","-height","720","-condebug","-developer",
               "-nosound","+deathmatch","0","+skill","1","+map",Path(bsp).stem]
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
    errors.extend(audit_log(text,BSP(bsp).entities()))
    shots = sorted((game/"screenshots").glob("*.png"))
    if len(shots) != len(cameras):
        errors.append(f"Expected {len(cameras)} screenshots, found {len(shots)}")
    report = {"schema":1,"passed":not errors,"errors":errors,"bsp_sha256":digest(bsp),
              "engine_sha256":digest(engine),"command":command,"exit_code":code,
              "seconds":round(time.monotonic()-start,3),"gamedir":str(game),
              "screenshots":[{"camera":c["name"],"file":str(s),"sha256":digest(s)} for c,s in zip(cameras,shots)],
              "visual_review":"pending; open the screenshots to review lighting and geometry"}
    write_json(game/"qa.json",report)
    return game/"qa.json",report
