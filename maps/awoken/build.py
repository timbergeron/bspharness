"""Adapt 4Bidden's recovered Q2 Awoken brushwork to stock Quake 1."""

import argparse
from collections import Counter
from math import sqrt
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from bspharness import Bounds, Map, Material, Move, WalkRoute, box, lighting_recipe
from bspharness.geometry import normalize, dot, vector
from bspharness.pipeline import digest, resolve_tool, run_stage, write_json
from bspharness.source import read
from bspharness.wad import make_blockout
from maps.awoken.materials import make_materials
from maps.awoken.polish import carvings

SOURCE_SHA256 = "17451ce49877375e4e0efdc4ba306be1044275fc7ec3c909c7cf76730f9bf251"


def generate(reference, stock_wad, output, style="video"):
    if digest(reference)!=SOURCE_SHA256:
        raise ValueError("This Awoken recipe expects the recorded 4Bidden Q2 reference BSP")
    work = ROOT/"out/references/awoken/conversion"
    work.mkdir(parents=True,exist_ok=True)
    original = work/"reference.bsp"
    shutil.copy2(reference,original)
    run_stage([resolve_tool(ROOT/"tools/ericw/modern","bsputil"),"-decompile",original],
              work,work/"decompile.log",180)
    entities = read(original.with_suffix(".decompile.map"))
    video = style == "video"
    art_wad = make_materials() if video else None
    arena = Map("Awoken — Quake 1",shell="explicit",
                **lighting_recipe(sun=120 if video else 300,sky=80 if video else 180,minlight=20 if video else 38,
                                  bounce=1 if video else 2,dirt=0.35 if video else 0.25,
                                  sun_color=(235,245,220) if video else (255,222,185),
                                  sky_color=(190,215,235) if video else (165,195,235)))
    # ASCII engine metadata; original brushwork and gameplay positions remain.
    arena.worldspawn["message"] = "Awoken - Quake 1"
    wall = Material("aw_stone",repeat=(256,256)) if video else Material("city4_2",repeat=(128,128))
    stone = Material("aw_trim",repeat=(128,128)) if video else Material("stone1_7",repeat=(128,128))
    rock = stone if video else Material("rock3_7",repeat=(128,128))
    floor = Material("aw_pave",repeat=(128,128)) if video else Material("ground1_6",repeat=(128,128))
    trim = Material("aw_trim",repeat=(128,128)) if video else Material("metalt2_3",repeat=(64,64))
    light = Material("tlight02",repeat=(64,64))
    materials = {
        "1und/grudbr1a":wall,"1und/rtnick2d":stone,"1und/rtbrockbm":rock,
        "1und/flo3":floor,"1und/flo4b":floor,"stark/brickfloor2":floor,
        "1und/hrudgb":trim,"1und/grudsign2":Material("aw_panel",repeat=(64,128)) if video else Material("rune2_3",repeat=(64,64)),
        "1und/grud1ctr":stone,"1und/gnotiley31":Material("afloor1_4",repeat=(128,128)),
        "1und/rtgnobr":stone,"1und/grud1atr":wall,"1und/pieaseds":trim,
        "1und/grud-br1":wall,"1und/rtgnobotd":stone,"1und/flo2a":floor,
        "mosswall/mossfloor02":floor,"1und/rtgriff":stone,"1und/ttzutilgr":light,
        "1und/contilec":stone,"e3u3/bluelite":light,"e1u1/grnx2_1":light,
        "e2u3/lead1_2":trim}
    def material(f):
        if f.texture=="e1u1/clip":return "clip"
        if f.texture=="e1u1/trigger":return "trigger"
        if f.flags&4 or f.texture=="e1u1/sky1":return "sky_aw" if video else "sky1"
        if f.contents&32:return Material("*aw_water" if video else "*water0",repeat=(128,128))
        if f.texture not in materials:raise ValueError(f"Unmapped source texture: {f.texture}")
        return materials[f.texture]
    changes = Counter()
    emitters, solids = [], []
    for entity in entities:
        name = entity.keys["classname"]
        brushes = []
        for source in entity.brushes:
            if all(f.contents&16777216 for f in source.faces):
                changes["origin brushes removed"]+=1
                continue
            if all(f.contents&268435456 and not f.contents&32 for f in source.faces):
                if video and any(f.texture in ("stark/vine06","stark/dk_vines") for f in source.faces):
                    vine = source.mapped(lambda f:Material("{aw_vine",repeat=(256,256),anchor=(0,0,-192))
                                         if f.texture in ("stark/vine06","stark/dk_vines") else "skip")
                    arena.detail(vine,mode="illusionary",_shadow="1")
                    changes["nonblocking vine brushes restored"]+=1
                    continue
                changes["Q2 alpha foliage/decal brushes removed"]+=1
                continue
            brush = source.mapped(material)
            if name=="worldspawn":
                contents = source.faces[0].contents
                if not contents&(64|65536|32):solids.append(brush)
                if any(f.flags&4 for f in source.faces) or contents&65536:
                    arena.structural(brush)
                elif contents&64:
                    arena.detail(brush,mode="illusionary",_shadow="1")
                elif contents&134217728 and not contents&32:
                    arena.detail(brush)
                else:
                    arena.structural(brush)
                changes["world brushes retained"]+=1
                # Q2 uses surface emission instead of point-light entities.
                # Recover its low-power trim glow and stronger blue fixtures.
                for raw,face in zip(source.faces,brush.faces):
                    if raw.flags&1 and not raw.flags&4 and not raw.contents&32:
                        vertices = brush.face_vertices(face)
                        if vertices:
                            center = tuple(sum(p[i] for p in vertices)/len(vertices) for i in range(3))
                            n = normalize(face.normal)
                            emitters.append((tuple(center[i]+n[i]*20 for i in range(3)),
                                             min(360,70+sqrt(max(0,raw.value))*10),
                                             (110,170,255) if video and raw.texture=="e3u3/bluelite" else
                                             (175,205,255) if raw.texture=="e3u3/bluelite" else
                                             (205,235,215) if video else (255,220,175)))
            else:
                brushes.append(brush)
        if name=="worldspawn":continue
        keys = {k:v for k,v in entity.keys.items() if k not in ("classname","model")}
        if name=="func_rotating":
            # Vanilla id1 has no Q2 func_rotating. Preserve the five floor-pad
            # ornaments as nonblocking static compiler detail.
            arena.detail(*brushes,mode="illusionary",_shadow="1")
            changes["rotating ornaments made static"]+=1
        elif name in ("trigger_push","trigger_hurt"):
            if name=="trigger_push" and keys.get("angle")=="-1":
                # id1 replaces horizontal velocity on contact, and Quake's
                # air acceleration cannot carry a vertical launch off these
                # broad pads. Give each lift its required landing direction.
                pitch,yaw,speed={"57":(-70,90,60),"55":(-75,270,57),
                                 "60":(-75,180,62)}[keys["speed"]]
                keys.pop("angle")
                keys.update(angles=f"{pitch} {yaw} 0",speed=str(speed))
                changes["vertical pads angled toward Q1 landing ledges"]+=1
            arena.entity(name,brushes=brushes,**keys)
        elif name=="misc_teleporter_dest":
            p=tuple(map(float,keys.pop("origin").split())); p=(p[0],p[1],p[2]+9)
            arena.entity("info_teleport_destination",p,**keys)
        elif name=="misc_teleporter":
            x,y,z=map(float,keys.pop("origin").split())
            arena.entity("trigger_teleport",brushes=(box(x-24,y-24,z-24,x+24,y+24,z+40,texture="trigger"),),
                         target=keys["target"])
            arena.detail(box(x-28,y-28,z-24,x+28,y+28,z-20,texture=trim,top=light),mode="wall")
        elif name=="item_armor_shard":
            changes["armor shards removed"]+=1
        else:
            mapping={"weapon_machinegun":"weapon_nailgun","weapon_chaingun":"weapon_supernailgun",
                "weapon_hyperblaster":"weapon_supernailgun","weapon_railgun":"weapon_lightning",
                "weapon_supershotgun":"weapon_supershotgun","weapon_rocketlauncher":"weapon_rocketlauncher",
                "weapon_grenadelauncher":"weapon_grenadelauncher","ammo_shells":"item_shells",
                "ammo_bullets":"item_spikes","ammo_slugs":"item_cells","ammo_grenades":"item_rockets",
                "ammo_rockets":"item_rockets","ammo_cells":"item_spikes","item_health_large":"item_health",
                "item_health_mega":"item_health","item_armor_combat":"item_armor2",
                "item_armor_jacket":"item_armor1","item_quad":"item_artifact_super_damage",
                "info_player_start":"info_player_start","info_player_deathmatch":"info_player_deathmatch"}
            if name not in mapping:raise ValueError(f"Unmapped source entity: {name}")
            p=tuple(map(float,keys.pop("origin").split()))
            if not name.startswith("info_player"):
                p=(p[0],p[1],p[2]+8)
            if name=="item_health_mega":keys["spawnflags"]="2"
            if name=="ammo_slugs":keys["spawnflags"]="1" # large cells supply the rail -> lightning replacement
            if name=="item_quad":keys["spawnflags"]="1792" # absent on every SP skill; retained in DM
            mapped=mapping[name]
            if mapped in ("item_health","item_shells","item_spikes","item_rockets","item_cells"):
                # Q2 authored item centers; id1 ammo/health use a 0..32 box.
                p=(p[0]-16,p[1]-16,p[2])
            if name=="item_armor_combat" and p[0]<1000:mapped="item_armorInv"
            arena.entity(mapped,p,**keys)
            changes[name+" -> "+mapped]+=1
            if name=="info_player_deathmatch":
                arena.light((p[0],p[1],p[2]+104),180,(195,215,240))
    # Discard emitters buried behind another recovered solid, rather than
    # nudging lights through walls and lighting the wrong room.
    solid_planes=[(Bounds(tuple(min(p[i] for p in b.vertices) for i in range(3)),
                         tuple(max(p[i] for p in b.vertices) for i in range(3))),
                   [(normalize(f.normal),f.points[1]) for f in b.faces]) for b in solids]
    seen=set()
    for p,intensity,color in emitters:
        if p in seen or any(bounds.contains(p) and all(dot(n,vector(p,o))<0 for n,o in planes)
                            for bounds,planes in solid_planes):continue
        seen.add(p);arena.light(p,intensity,color)
    changes["recovered exposed surface lights"]=len(seen)
    # Broad fill within the covered courts keeps paths readable under the
    # retained roofs while preserving the warmer fixture/cooler sky contrast.
    for p in ((1408,1664,-580),(768,1120,-580),(1000,1120,-580),(1600,1152,-570),
              (1968,1552,-330),(1408,2048,-420),(768,1456,-340),(1312,736,-440),
              (1792,544,-440),(2500,1000,-420),(2400,1700,-450)):
        arena.light(p,350,(210,235,225) if video else (210,225,255),delay="2",wait="0.7")
    ornaments = []
    if video:
        ornaments = carvings(arena,solids)
        changes["beveled carved wall reliefs added"] = len(ornaments)
        # Cool cues at the four lifts and teleporter, restrained against the
        # neutral stone instead of making every doorway blue metal.
        for x,y,z in ((1408,1908,-720),(768,844,-720),(684,1696,-720),(1904,1008,-700)):
            arena.detail(box(x-40,y-40,z-16,x+40,y+40,z-15.5,texture=trim,
                             top=Material("aw_pad",repeat=(128,128),anchor=(x-64,y+64,z))),
                         mode="illusionary")
            arena.light((x,y,z+88),200,(105,155,255),delay="2",wait="0.8")
        arena.light((1652,1152,-652),250,(90,150,255),delay="2",wait="0.6")
        arena.light((1408,1920,-652),200,(100,170,255),delay="2",wait="0.7")
    # Initial viewpoints are fixed in source coordinates for visual iteration.
    arena.camera("central-courtyard",(1744,1088,-320),(16,160,0))
    arena.camera("rocket-terrace",(1248,736,-536),(8,155,0))
    arena.camera("lower-arena",(1408,1696,-650),(8,180,0))
    arena.camera("mega-balcony",(1552,2048,-400),(18,230,0))
    arena.camera("bridge",(2312,1320,-552),(14,205,0))
    routes=[]
    for i,(keys,_) in enumerate(arena.entities):
        if keys["classname"]=="info_player_deathmatch":
            p=tuple(map(float,keys["origin"].split()))
            routes.append(WalkRoute(f"dm-spawn-{len(routes)+1:02d}",p,(0,float(keys.get("angle",0)),0),
                                   (Move(1,()),),Bounds(tuple(x-8 for x in p),tuple(x+8 for x in p))))
    routes.extend([
        WalkRoute("lower-crossing",(1456,1664,-712),(0,180,0),(Move(190),),
                  Bounds((860,1640,-720),(1000,1688,-704))),
        WalkRoute("rocket-terrace-walk",(720,736,-584),(0,0,0),(Move(205),),
                  Bounds((1240,712,-592),(1360,760,-576))),
        WalkRoute("grenade-bridge-walk",(1952,1632,-456),(0,270,0),(Move(115),),
                  Bounds((1920,1240,-464),(1984,1360,-448))),
        WalkRoute("mega-jump-pad",(1408,1808,-712),(0,90,0),
                  (Move(70,expect=Bounds((1370,1880,-610),(1450,2090,-460))),Move(90,())),
                  Bounds((1370,1960,-560),(1450,2136,-544))),
        WalkRoute("rocket-jump-pad",(768,944,-712),(0,270,0),
                  (Move(65,expect=Bounds((730,740,-600),(810,900,-480))),Move(90,())),
                  Bounds((730,680,-592),(810,800,-576))),
        WalkRoute("quad-jump-pad",(800,1696,-712),(0,180,0),
                  (Move(70,expect=Bounds((540,1656,-560),(740,1736,-420))),Move(100,())),
                  Bounds((520,1656,-528),(650,1736,-512))),
        WalkRoute("grenade-jump-pad",(1904,1136,-712),(0,90,0),
                  (Move(30,("back",)),Move(75,expect=Bounds((1872,1200,-440),(1936,1280,-380))),Move(100,())),
                  Bounds((1872,1230,-464),(1936,1450,-448))),
        WalkRoute("lower-teleporter",(1620,1152,-712),(0,0,0),
                  (Move(30),Move(40,())),Bounds((1410,424,-592),(1470,600,-576))),
        WalkRoute("quad-to-lightning-stairs",(576,1456,-520),(0,0,0),(Move(112),),
                  Bounds((860,1432,-464),(980,1480,-448))),
        WalkRoute("lightning-to-quad-stairs",(960,1456,-456),(0,180,0),(Move(130),),
                  Bounds((520,1432,-528),(630,1480,-496))),
        WalkRoute("rocket-to-center-stairs",(1440,768,-584),(0,45,0),(Move(123),),
                  Bounds((1660,988,-528),(1740,1068,-496))),
        WalkRoute("grenade-to-nailgun-jump",(1952,1280,-456),(0,0,0),
                  (Move(16),Move(24,("forward","jump"),
                                 Bounds((2020,1256,-440),(2080,1304,-388))),Move(50)),
                  Bounds((2160,1256,-624),(2290,1304,-608))),
    ])
    if video:
        # Pale stone needs substantially less light than the first dark stock
        # palette. Scale every recovered/fill/landmark light consistently.
        for keys,_ in arena.entities:
            if keys["classname"]=="light":
                keys["light"] = str(round(float(keys["light"])*0.45))
    output=arena.write(output,[stock_wad,make_blockout(ROOT/"assets/wads/blockout.wad"),
                               *([art_wad] if art_wad else [])])
    write_json(output.with_suffix(".cameras.json"),arena.cameras)
    write_json(output.with_suffix(".routes.json"),[r.metadata() for r in routes])
    write_json(output.with_suffix(".conversion.json"),{
        "reference_sha256":SOURCE_SHA256,"reference_author":"4Bidden","changes":dict(changes),
        "source_brushes":sum(len(e.brushes) for e in entities),"world_brushes":len(arena.details),
        "entity_brushes":sum(len(b) for _,b in arena.entities),"generator_sha256":digest(__file__),
        "style":style,"carved_reliefs":ornaments,
        "art_wad_sha256":digest(art_wad) if art_wad else None,
        "polish_sha256":digest(ROOT/"maps/awoken/polish.py") if video else None})
    print(output)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference",type=Path,default=ROOT/"out/references/awoken/q2-awoken-original.bsp")
    p.add_argument("--stock-wad",type=Path,default=ROOT/"assets/wads/id1.wad")
    p.add_argument("--output",type=Path,default=ROOT/"src/awoken.map")
    p.add_argument("--style",choices=("stock","video"),default="stock")
    a=p.parse_args();generate(a.reference,a.stock_wad,a.output,a.style)
