"""Mixed-resolution floor joins, wrapped walls, and automatic portal trim."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bspharness import Map, Material, Palette, TransitionRule
from bspharness.wad import make_blockout, miptex, write_wad


def diagnostic_wad(path):
    textures = {}
    for name,size in (("tile64",64),("tile128",128)):
        # The 128px variant is the same original pattern at twice the pixel
        # resolution. Shared 128u repeats give identical physical joints.
        factor = size//64
        pixels = bytes(3 if x%(16*factor)<factor or y%(16*factor)<factor else
                       9 if ((x//(16*factor)+y//(16*factor))%2)==0 else 6
                       for y in range(size) for x in range(size))
        textures[name] = miptex(name,size,size,pixels)
    for name,size,dark,light in (("warmbrick",64,96,103),("coolbrick",128,160,165)):
        pixels = bytes(dark if y%16<2 or (x+(16 if y//16%2 else 0))%32<2 else light
                       for y in range(size) for x in range(size))
        textures[name] = miptex(name,size,size,pixels)
    return write_wad(path,textures)


def generate(output):
    root = Path(__file__).resolve().parents[1]
    utility = make_blockout(root/"assets/wads/blockout.wad")
    diagnostic = diagnostic_wad(root/"assets/wads/materials_demo.wad")
    small = Material("tile64",repeat=(128,128),anchor=(64,32,0),family="floor_tiles")
    large = Material("tile128",repeat=(128,128),anchor=(64,32,0),family="floor_tiles")
    warm = Material("warmbrick",density=0.5)
    cool = Material("coolbrick",density=0.5)
    trim = Material("bh_trim",repeat=(64,64))
    arena = Map("BSP Harness: Material joins",_minlight="24",_bounce="1")
    arena.room("west-south",(-384,-256,0),(0,0,256),Palette(wall=warm,floor=small))
    arena.room("west-north",(-384,0,0),(0,256,256),Palette(wall=warm,floor=large))
    arena.room("east",(0,-256,0),(384,256,256),Palette(wall=cool,floor=large))
    arena.transition_rule(TransitionRule((warm,cool),trim,width=16,depth=8))
    arena.wall_run(warm,[(-384,-256),(0,-256),(0,256),(-384,256),(-384,-256)])
    arena.wall_run(cool,[(0,-256),(384,-256),(384,256),(0,256),(0,-256)])
    arena.entity("info_player_start",(-256,-128,24),angle="45")
    arena.entity("item_armor2",(-256,128,24))
    arena.entity("weapon_rocketlauncher",(256,-128,24))
    arena.light((-192,0,208),450,(255,220,185),delay="2")
    arena.light((192,0,208),450,(170,215,255),delay="2")
    arena.camera("mixed-resolution-floor",(-300,-128,200),(35,40,0))
    arena.camera("trim-doorways",(-160,-128,160),(10,0,0))
    arena.camera("wrapped-east-corner",(224,-96,176),(15,-45,0))
    output = arena.write(output,[diagnostic,utility])
    output.with_suffix(".cameras.json").write_text(json.dumps(arena.cameras,indent=2)+"\n")
    print(output)


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=Path("src/materials_demo.map"))
    generate(parser.parse_args().output)
