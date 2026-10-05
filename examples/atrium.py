"""A three-zone arena with a lower loop and an elevated armor bridge."""

import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

# Runnable directly from a checkout; no pip installation required.
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bspharness import Map, Palette, box, ramp
from bspharness.wad import make_blockout, read_wad


def generate(output, stock_wad=None):
    root = Path(__file__).resolve().parents[1]
    utility = make_blockout(root/"assets/wads/blockout.wad")
    palette = Palette()
    wads = [utility]
    if stock_wad:
        textures = read_wad(stock_wad)
        required = {"bricka2_2","woodflr1_4","wood1_1","metal1_1","sky1"}
        missing = required-set(textures)
        if missing:
            raise ValueError(f"Stock WAD lacks expected textures: {sorted(missing)}")
        palette = Palette(wall="bricka2_2",floor="woodflr1_4",ceiling="wood1_1",trim="metal1_1",sky="sky1")
        wads.insert(0,stock_wad)
    arena = Map("BSP Harness: Atrium",_bounce="1",_bouncecolorscale="1",_dirt="1",
                _dirtscale="0.7",_dirtdepth="192",_minlight="16",
                _sunlight="220",_sun_mangle="40 -50 0",_sunlight_color="255 215 175",
                _sunlight2="140",_sunlight2_color="165 190 235")
    west = replace(palette,wall="bh_accent") if not stock_wad else palette
    arena.room("atrium",(-384,-384,0),(384,384,448),palette)
    arena.room("sky-well",(-384,-384,448),(384,384,512),palette,kind="sky")
    arena.room("west",(-1216,-320,0),(-768,320,320),west)
    arena.room("west-link",(-768,-128,0),(-384,128,192),palette)
    arena.room("east",(768,-320,128),(1216,320,448),palette)
    arena.room("east-link",(384,-128,0),(768,128,320),palette)
    arena.room("lower-loop",(-992,-640,0),(992,-384,224),palette)
    arena.room("west-return",(-992,-640,0),(-800,-320,224),palette)
    arena.room("east-return",(800,-640,0),(992,-320,320),palette)
    arena.structural(ramp(384,-128,768,128,-8,8,136,texture=palette.trim,top=palette.floor),
                 ramp(800,-640,992,-320,-8,8,136,along="y",texture=palette.trim,top=palette.floor),
                 ramp(-336,-320,-208,64,-8,8,200,along="y",texture=palette.trim,top=palette.floor),
                 box(-384,64,184,384,192,200,texture=palette.trim,top=palette.floor))
    # Repeating architectural kit pieces can be parameterized independently
    # of the room graph. Visible fullbright strips get nearby point lights.
    for x in (-256,256):
        arena.detail(box(x-8,376,0,x+8,384,384,texture=palette.trim),
                     box(x-48,372,288,x+48,380,296,texture="bh_light"))
        arena.light((x,340,272),250,delay="2")
    arena.light((-1000,0,256),340,(255,190,125),delay="2")
    arena.light((1000,0,376),340,(145,195,255),delay="2")
    for x in (-768,-256,256,768):
        arena.light((x,-512,176),180,delay="2")
    spawns = [((-1000,-192,24),90),((0,-256,24),90),((1000,-192,152),90),
              ((-640,-512,24),0),((640,-512,24),180),((192,256,24),225)]
    arena.entity("info_player_start",spawns[0][0],angle=str(spawns[0][1]))
    for origin,angle in spawns:
        arena.entity("info_player_deathmatch",origin,angle=str(angle))
    arena.entity("weapon_rocketlauncher",(-1000,128,24))
    arena.entity("weapon_rocketlauncher",(1000,128,152))
    arena.entity("weapon_lightning",(-64,-512,24))
    arena.entity("item_armorInv",(0,128,224))
    arena.entity("item_armor2",(1088,-64,152))
    arena.entity("item_health",(160,-128,24),spawnflags="2")
    arena.entity("item_health",(-1088,0,24))
    arena.entity("item_health",(896,0,152))
    arena.entity("item_shells",(-512,-512,24))
    arena.entity("item_rockets",(512,-512,24))
    arena.camera("atrium",(320,-300,352),(24,140,0))
    arena.camera("west",(-1152,-256,240),(22,40,0))
    arena.camera("east",(1152,-256,368),(22,140,0))
    arena.camera("lower-loop",(-880,-560,152),(10,0,0))
    path = arena.write(output,wads)
    path.with_suffix(".cameras.json").write_text(json.dumps(arena.cameras,indent=2)+"\n")
    print(path)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=Path("src/atrium.map"))
    parser.add_argument("--stock-wad",type=Path)
    args = parser.parse_args()
    generate(args.output,args.stock_wad)
