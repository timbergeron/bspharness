"""Build the original video-reference materials as a local Quake WAD2.

FFmpeg decodes/resamples the generated PNG sources. Palette conversion,
periodic masonry, relief panels and pad markings are deterministic Python.
The harness core remains dependency-free.
"""

import argparse
import json
from math import cos, hypot, pi, sin
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from bspharness.pipeline import digest, write_json
from bspharness.wad import miptex, write_wad


def indexed(rgba, palette, gray=False, masked=False):
    if len(palette) != 768 or len(rgba) % 4:
        raise ValueError("Expected a Quake palette and RGBA pixels")
    colors = [tuple(palette[i:i+3]) for i in range(0, 768, 3)]
    candidates = range(16) if gray else range(224)  # Never bake fullbright speckles.
    cache, output = {}, bytearray()
    for offset in range(0, len(rgba), 4):
        r, g, b, alpha = rgba[offset:offset+4]
        if masked and alpha < 96:
            output.append(255)
            continue
        if gray:
            value = round((r*0.25+g*0.6+b*0.15)*0.88)
            key = (value, value, value)
        else:
            key = (r, g, b)
        if key not in cache:
            # Quake has few olive colors. Preserve leaf identity using its
            # muted green ramp, while woody strands retain their brown ramp.
            choices = range(176,192) if masked and g >= r*0.92 and g > b*1.2 else candidates
            cache[key] = min(choices, key=lambda i: sum((a-b)**2 for a, b in zip(key, colors[i])))
        output.append(cache[key])
    return output


def source_pixels(path):
    result = subprocess.run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-vf", "scale=128:128:flags=area", "-frames:v", "1", "-pix_fmt", "rgba",
        "-f", "rawvideo", "pipe:1"], check=True, stdout=subprocess.PIPE)
    if len(result.stdout) != 128*128*4:
        raise ValueError("Texture decoder did not produce 128x128 RGBA")
    return result.stdout


def make_materials(output=ROOT/"assets/wads/awoken.wad", palette=ROOT/"assets/palette.lmp",
                   sources=ROOT/"assets/awoken"):
    metadata = json.loads((ROOT/"maps/awoken/art.json").read_text())
    paths = {name: Path(sources)/data["file"] for name, data in metadata["sources"].items()}
    for name, path in paths.items():
        if digest(path) != metadata["sources"][name]["sha256"]:
            raise ValueError(f"Original art source changed: {path}")
    palette = Path(palette)
    colors = palette.read_bytes()
    stone = indexed(source_pixels(paths["stone"]), colors, gray=True)
    slab = indexed(source_pixels(paths["slab"]), colors, gray=True)
    vines = indexed(source_pixels(paths["vines"]), colors, masked=True)
    # Lay out periodic courses explicitly: generated art supplies the grain,
    # while these joints have exact phase and edge continuity on both axes.
    wall, paving, panel, pad = bytearray(), bytearray(), bytearray(), bytearray()
    for y in range(128):
        for x in range(128):
            grain = slab[y*128+x]
            row, v = divmod(y, 32)
            u = (x+(row%2)*32) % 64
            if u == 0 or v == 0:
                value = 6
            elif u == 1 or v == 1:
                value = min(14, grain+1)
            elif u >= 62 or v >= 30:
                value = max(7, grain-2)
            else:
                value = min(13, max(8, grain+(stone[y*128+x] < 8)*-1))
            wall.append(value)
            # Quiet large flagstones, with moss restricted to the seams.
            u, v = x%64, y%64
            paving.append(180 if u == 0 or v == 0 else
                          min(13, grain+1) if u == 1 or v == 1 else max(8, grain-1))
            # Original geometric carving; restrained relief, no copied emblem.
            border = x in (8, 9, 118, 119) or y in (8, 9, 118, 119)
            maze = ((x//12+y//24)%2 == 0 and x%24 in (6, 7) and 24<y<104 or
                    y%24 in (6, 7) and 24<x<104 and (x//24)%2 == (y//24)%2)
            panel.append(7 if border or maze else min(12, grain))
            radius = hypot(x-63.5, y-63.5)
            ring = 40<radius<43 or 49<radius<51
            arrow = 40<y<80 and abs(x-63.5) < (80-y)*0.4
            pad.append(213 if ring or arrow else 7 if radius<52 else min(12, grain))
    textures = {name:miptex(name,128,128,pixels) for name,pixels in {
        "aw_stone":wall,"aw_trim":slab,"aw_pave":paving,
        "aw_panel":panel,"aw_pad":pad,"{aw_vine":vines}.items()}
    water = bytes(183+round((0.8*sin((x+2*cos(y*pi/16))*pi/8)+
                            0.7*cos((y+3*sin(x*pi/16))*pi/8))*0.6)
                  for y in range(64) for x in range(64))
    textures["*aw_water"] = miptex("*aw_water",64,64,water)
    sky = bytearray()
    for y in range(128):
        for x in range(256):
            wave = (sin((x%128)*pi/32)+cos(y*pi/32)+sin((x%128+y)*pi/64))/3
            sky.append((14 if wave>0.25 else 13 if wave>0.05 else 0)
                       if x<128 else 12+(wave>0.4))
    textures["sky_aw"] = miptex("sky_aw",256,128,sky)
    output = write_wad(output, textures)
    write_json(output.with_suffix(".json"), {
        "schema":1,"wad_sha256":digest(output),"palette_sha256":digest(palette),
        "generator_sha256":digest(__file__),"source_sha256":{n:digest(p) for n,p in paths.items()},
        "textures":list(textures),"transparency":"{aw_vine uses palette index 255; all opaque colors stay below 224"})
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=ROOT/"assets/wads/awoken.wad")
    parser.add_argument("--palette",type=Path,default=ROOT/"assets/palette.lmp")
    parser.add_argument("--sources",type=Path,default=ROOT/"assets/awoken")
    print(make_materials(**vars(parser.parse_args())))
