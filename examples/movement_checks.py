"""A jumpable ledge and an intentionally blocked version for engine QA."""

import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from bspharness import Bounds, Map, Move, WalkRoute, box
from bspharness.wad import make_blockout


def generate(output=Path("src")):
    wad = make_blockout(Path("assets/wads/blockout.wad"))
    route = WalkRoute("jump-ledge",(0,-128,24),(0,90,0),(
        Move(20),
        Move(18,("forward","jump"),Bounds((-16,-48,64),(16,-16,80))),
        Move(40),
    ),Bounds((-16,80,20),(16,160,32)))
    for name,height in (("movement_open",40),("movement_blocked",128)):
        arena = Map(name,_minlight="16")
        arena.room("test",(-256,-256,0),(256,256,192))
        arena.structural(box(-128,-16,0,128,16,height))
        arena.entity("info_player_start",route.origin,angle="90")
        arena.light((128,128,160),300)
        source = arena.write(output/(name+".map"),[wad])
        source.with_suffix(".routes.json").write_text(json.dumps([route.metadata()],indent=2)+"\n")
        print(source)


if __name__=="__main__":
    generate()
