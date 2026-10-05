"""Ember Cloister: a stock-textured, two-level architectural reference area."""

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bspharness import (Bounds, Map, Material, Move, Palette, WalkRoute,
                        arch, beam, box, column, fixture, lighting_recipe, stairs, trim_profile)
from bspharness.wad import read_wad


def generate(output, stock_wad):
    textures = read_wad(stock_wad)
    required = {"stone1_7","stone1_5","afloor1_4","wood1_1","metal1_1","tlight01","tlight02","sky1"}
    if required-set(textures):
        raise ValueError(f"Extract the stock WAD first; missing {sorted(required-set(textures))}")
    stone = Material("stone1_7",repeat=(128,128))
    gold = Material("stone1_5",repeat=(128,128))
    floor = Material("afloor1_4",repeat=(128,128))
    bronze = Material("metal1_1",repeat=(64,64))
    wood = Material("wood1_1",repeat=(128,128))
    palette = Palette(wall=stone,floor=floor,ceiling=wood,trim=bronze,sky="sky1")
    carved = replace(palette,trim=gold)
    arena = Map("Ember Cloister",**lighting_recipe(sun=190,sky=150,minlight=10,bounce=2,dirt=0.45))
    arena.room("nave",(-512,-384,0),(512,384,448),palette)
    arena.room("entry",(-128,-704,0),(128,-384,288),palette)
    arena.room("apse",(512,-192,0),(768,192,320),palette)
    arena.room("lantern",(-224,-160,448),(224,160,512),palette,kind="sky")
    # Walking surfaces remain structural. The mezzanine has generous
    # clearance below, and the stairs use 12u risers and 16u treads.
    arena.structural(box(-512,224,176,512,384,192,texture=bronze,top=floor),
                     box(-176,64,176,-80,224,192,texture=bronze,top=floor),
                     *stairs((-432,64,0),width=160,rise=12,run=16,steps=16,palette=palette))
    # Arcade below the gallery, including an open route from the stair landing.
    for x in (-448,-224,0,224,448):
        arena.detail(*column((x,224,0),height=176,radius=24,palette=palette),
                     mode="detail",_phong="1",_phong_angle="40")
    for x in (-336,-112,112,336):
        arena.detail(*arch((x,224,0),width=176,spring=104,rise=56,thickness=16,depth=24,
                           segments=8,palette=carved,jambs=False),mode="detail")
    # Two massive transverse arches break up the nave silhouette. Their
    # spandrels meet the roof; the gallery passes through the arch openings.
    for x in (-288,288):
        arena.detail(*arch((x,0,0),width=704,spring=240,rise=160,thickness=32,depth=32,
                           segments=16,axis="x",palette=carved,wall_height=448),mode="detail")
    arena.detail(*arch((0,-384,0),width=256,spring=128,rise=112,thickness=24,depth=32,
                       palette=carved,wall_height=288),
                 *arch((512,0,0),width=336,spring=128,rise=128,thickness=24,depth=32,
                       axis="x",palette=carved,wall_height=320),mode="detail")
    # Molding, coffer beams, and balcony rails provide a consistent secondary scale.
    for y in (-376,376):
        arena.detail(*trim_profile((-512,y,320),(512,y,320),palette=carved),mode="wall")
    for x in (-448,-160,160,448):
        arena.detail(*beam((x,-376,440),(x,376,440),width=24,height=16,palette=palette),mode="wall")
    for y in (-160,160):
        arena.detail(*beam((-224,y,440),(224,y,440),width=24,height=16,palette=palette),mode="wall")
    for x0,x1 in ((-512,-208),(-80,512)):
        arena.structural(box(x0,208,192,x1,224,232,texture=bronze,top=gold))
        arena.detail(*trim_profile((x0,216,232),(x1,216,232),widths=(20,24),heights=(4,4),palette=carved),mode="wall")
    for x in (-448,-288,0,288,448):
        arena.detail(box(x-8,208,192,x+8,224,232,texture=gold),mode="wall")
    # A small dais gives the apse a focal point and a second stepped traversal.
    arena.structural(box(624,-96,0,736,96,32,texture=bronze,top=floor),
                     *stairs((592,-64,0),width=128,rise=16,run=16,steps=2,palette=palette))
    for x in (-400,-144,144,400):
        emitter = Material("tlight01",repeat=(24,40),anchor=(x-12,372,324))
        fixture(arena,(x-16,372,280),(x+16,380,328),face="south",housing=bronze,
                emitter=emitter,intensity=340,color=(255,204,140),offset=20)
    for x in (-400,400):
        emitter = Material("tlight01",repeat=(24,56),anchor=(x-12,-372,204))
        fixture(arena,(x-16,-380,144),(x+16,-372,208),face="north",housing=bronze,
                emitter=emitter,intensity=380,color=(255,210,155),offset=20)
    for y in (-96,96):
        emitter = Material("tlight02",repeat=(56,24),anchor=(752,y-28,232))
        fixture(arena,(752,y-32,204),(760,y+32,236),face="west",housing=bronze,
                emitter=emitter,intensity=260,color=(175,205,255),offset=20)
    # Entrance lights are visible recessed panels, facing inward.
    for x,face in ((-120,"east"),(112,"west")):
        fixture(arena,(x,-612,144),(x+8,-564,184),face=face,housing=bronze,
                emitter=Material("tlight01",repeat=(40,32),anchor=(x,-608,180)),
                intensity=220,color=(255,210,155),offset=16)
    for x in (-352,0,352):
        arena.detail(*beam((x,-96,344),(x,-96,440),width=8,height=8,
                           palette=replace(palette,ceiling=bronze)),mode="illusionary",_shadow="1")
        fixture(arena,(x-64,-120,332),(x+64,-72,344),face="bottom",housing=bronze,
                emitter=Material("tlight02",repeat=(120,40),anchor=(x-60,-116,332)),
                intensity=520,color=(255,225,175),offset=24)
    for x in (-336,112,336):
        fixture(arena,(x-24,284,160),(x+24,316,172),face="bottom",housing=bronze,
                emitter=Material("tlight01",repeat=(40,24),anchor=(x-20,288,160)),
                intensity=220,color=(255,208,150),offset=12)
    arena.entity("info_player_start",(0,-640,24),angle="90")
    arena.entity("item_armor2",(176,288,216))
    arena.entity("weapon_rocketlauncher",(672,0,56))
    arena.entity("item_health",(-384,-288,24))
    arena.entity("item_shells",(336,288,216))
    arena.camera("entry-arch",(80,-600,128),(0,90,0))
    arena.camera("nave",(-432,-288,176),(8,32,0))
    arena.camera("gallery",(-160,328,288),(10,-12,0))
    arena.camera("arcade",(336,128,96),(3,155,0))
    arena.camera("apse",(448,-128,176),(8,35,0))
    routes = [
        WalkRoute("entry-arch",(0,-640,24),(0,90,0),(Move(144),),
                  Bounds((-16,-272,20),(16,-176,32))),
        WalkRoute("gallery-stairs",(-480,144,24),(0,0,0),(Move(120),),
                  Bounds((-160,128,210),(-96,160,224))),
        WalkRoute("stair-landing",(-128,144,216),(0,90,0),(Move(60),),
                  Bounds((-144,284,210),(-112,352,224))),
        WalkRoute("upper-gallery",(-112,304,216),(0,0,0),(Move(180),),
                  Bounds((380,288,210),(448,320,224))),
        WalkRoute("arcade-opening",(112,144,24),(0,90,0),(Move(72),),
                  Bounds((96,320,20),(128,369,32))),
        WalkRoute("apse-dais",(536,0,24),(0,0,0),(Move(42),),
                  Bounds((626,-16,50),(704,16,64))),
    ]
    output = arena.write(output,[stock_wad])
    output.with_suffix(".cameras.json").write_text(json.dumps(arena.cameras,indent=2)+"\n")
    output.with_suffix(".routes.json").write_text(json.dumps([r.metadata() for r in routes],indent=2)+"\n")
    print(output)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=Path("src/reference_hall.map"))
    parser.add_argument("--stock-wad",type=Path,default=Path("assets/wads/id1.wad"))
    args = parser.parse_args()
    generate(args.output,args.stock_wad)
