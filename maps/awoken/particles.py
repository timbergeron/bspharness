"""Build an isolated Awoken variant with original FTE jump-pad vapor."""

import argparse
import json
from math import cos, exp, pi, sin
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from bspharness.assets import stage
from bspharness.pipeline import digest, write_json
from bspharness.source import read

# Retained ornaments are 96 units across, with tops at -728. The grenade
# pad has a higher 80-unit marking. Emit four units above the visible tops,
# not from the buried marking or the player's launch origin.
PADS = {
    "mega": (1408, 1904, -724),
    "rocket": (768, 848, -724),
    "quad": (688, 1696, -724),
    "grenade": (1904, 1008, -711.5),
}
SECTORS = 24
# Rates describe new paths per sector per second. Chained steps continue a path
# once, rather than multiplying it. Clockwise is viewed from above (+Z).
LAYERS = (
    dict(name="haze", radius=44, tangent=32, inward=12, rise=1,
         rate=2.5, life=.70, minimum=.45, scale=(18, 30), alpha=.055,
         alpha_random=.025, jitter=(4, 4, 1), velocity_random=(5, 5, 1),
         rotation=(-180, 180, -60, -25), rgb=(35, 100, 255), grow=2),
    dict(name="core", radius=39, tangent=0, inward=0, rise=.8,
         rate=3, life=.10, minimum=.10, scale=(8, 12), alpha=.78,
         alpha_random=.12, jitter=(.6, .6, .3), velocity_random=(1, 1, .3),
         rotation=(0, 0, 0, 0), rgb=(60, 155, 255), grow=0,
         render="texturedspark", stretch=-13, steps=6, step_time=.075),
    dict(name="streak", radius=43, tangent=85, inward=23, rise=2,
         rate=2.8, life=.45, minimum=.28, scale=(14, 22), alpha=.36,
         alpha_random=.14, jitter=(2, 2, .8), velocity_random=(8, 8, 1),
         rotation=(0, 0, 0, 0), rgb=(30, 110, 255), grow=-6,
         render="texturedspark", stretch=-18),
    dict(name="wisp", radius=43, tangent=0, inward=0, rise=22,
         rate=.18, life=.145, minimum=.145, scale=(12, 18), alpha=.40,
         alpha_random=.06, jitter=(1, 1, .4), velocity_random=(1, 1, 1),
         rotation=(0, 0, 0, 0), rgb=(45, 140, 255), grow=0,
         render="texturedspark", stretch=-8, steps=8, step_time=.12),
    dict(name="hot", radius=40, tangent=0, inward=0, rise=.4,
         rate=.27, life=.125, minimum=.125, scale=(22, 30), alpha=.85,
         alpha_random=.05, jitter=(1, 1, .3), velocity_random=(1, 1, .3),
         rotation=(0, 0, 0, 0), rgb=(220, 245, 255), grow=0,
         render="normal", steps=10, step_time=.10),
    dict(name="snap", radius=24, tangent=14, inward=-3, rise=7,
         rate=.40, life=.30, minimum=.30, scale=(14, 20), alpha=.7,
         alpha_random=0, jitter=(3, 3, 1), velocity_random=(5, 5, 3),
         rotation=(-180, 180, -30, 30), rgb=(100, 210, 255), grow=0,
         render="normal"),
    dict(name="orb", radius=48, tangent=20, inward=5, rise=20,
         rate=.20, life=.60, minimum=.45, scale=(7, 10), alpha=.65,
         alpha_random=.12, jitter=(6, 6, 2), velocity_random=(4, 4, 5),
         rotation=(-180, 180, -20, 20), rgb=(40, 135, 255), grow=-2),
    dict(name="center", radius=0, tangent=0, inward=0, rise=0,
         rate=.08, life=.8, minimum=.6, scale=(28, 34), alpha=.014,
         alpha_random=.006, jitter=(1, 1, .2), velocity_random=(0, 0, 0),
         rotation=(-180, 180, -20, 20), rgb=(30, 100, 255), grow=0),
    dict(name="feed", radius=10, tangent=28, inward=-55, rise=1,
         rate=.08, life=.55, minimum=.40, scale=(2, 3), alpha=.16,
         alpha_random=.06, jitter=(1, 1, .5), velocity_random=(3, 3, 1),
         rotation=(0, 0, 0, 0), rgb=(60, 155, 255), grow=-1,
         render="texturedspark", stretch=-1.5),
)


STAGGERED = {"wisp", "hot", "snap", "orb", "center", "feed"}

def effect_nodes():
    """Roots are model emissions; finite children continue individual orbits."""
    roots = [(layer, sector, -1 if layer["name"] in STAGGERED else 0)
             for layer in LAYERS for sector in range(SECTORS)]
    children = [(layer, sector, hop) for layer in LAYERS
                for sector in range(SECTORS)
                for hop in range(0 if layer["name"] in STAGGERED else 1, layer.get("steps", 1))]
    return roots + children


def node_name(layer, sector, hop):
    if layer["name"] == "haze" and sector == 0 and hop == 0:
        return "vortex"
    return f"v_{layer['name']}_{sector:02d}_{hop:02d}"


def path_velocity(layer, sector, hop=0):
    direction = -1 if (sector*7 + sum(map(ord,layer["name"]))) % 24 < 17 else 1
    angle = (sector + direction*hop)*2*pi/SECTORS
    c, s = cos(angle), sin(angle)
    if "steps" in layer:
        next_angle = angle + direction*2*pi/SECTORS
        dt = layer["step_time"]
        return ((cos(next_angle)-c)*layer["radius"]/dt,
                (sin(next_angle)-s)*layer["radius"]/dt, layer["rise"])
    return (-s*layer["tangent"]*direction-c*layer["inward"],
            c*layer["tangent"]*direction-s*layer["inward"], layer["rise"])


def png(path, name, size=512):
    """Original soft alpha sprites, analytically drawn with no dependencies."""
    pixels = bytearray()
    for y in range(size):
        pixels.append(0)  # PNG filter: none
        for x in range(size):
            u, v = (x + .5) / size * 2 - 1, (y + .5) / size * 2 - 1
            if name in ("core", "streak", "wisp", "snap", "feed"):
                # Long, irregular electric filaments with a sharp spine and a
                # broad, faint sheath. No whole-ring billboard or decal.
                if name == "snap":
                    # Faceted branching bolt, with a second offshoot.
                    bend = .18*sin(round(u*10)/10*13) + .06*sin(u*35)
                    branch = bend + .38*(u+.15)
                elif name == "wisp":
                    bend = .17*sin(u*7) + .05*sin(u*23)
                    branch = bend + .35*(u-.3)
                else:
                    bend = .23*(u*u-.4) + .045*sin(u*11)
                    branch = bend + .24*(u+.1)
                d = v-bend
                spine = exp(-d*d*(700 if name=="core" else 450))
                sheath = .20*exp(-d*d*25)
                secondary = .26*exp(-(v-branch)**2*650)*exp(-(u-.2)**2*5)
                a = (spine+sheath+secondary)*exp(-u*u*.9)
            elif name == "hot":
                r2=u*u+v*v
                a = exp(-r2*180)+.32*exp(-r2*12)
                a += .65*exp(-v*v*1900-u*u*8)
                a += .65*exp(-u*u*1900-v*v*8)
                a += .25*exp(-(u-v)**2*1600-r2*13)
            elif name == "orb":
                a = exp(-(u*u+v*v)*150)+.22*exp(-(u*u+v*v)*18)
            else:
                bend = v + .16*sin(u*5)
                a = exp(-u*u*4 - bend*bend*5)
                a *= .65 + .17*sin(11*u+5*v) + .12*cos(7*v-4*u)
                a += .18*exp(-(u+.25)**2*12 - (v-.20)**2*15)
            # Fully transparent border prevents square edges under filtering.
            edge = max(0, 1-max(abs(u), abs(v))**4)**2
            alpha = round(255*min(1, max(0, a*edge)))
            # Hot spots have a white center and blue halo within one sprite.
            if name == "hot":
                white = exp(-(u*u+v*v)*120)
                pixels.extend((round(65+190*white), round(160+95*white), 255, alpha))
            else:
                pixels.extend((255, 255, 255, alpha))
    def chunk(kind, data):
        return struct.pack(">I", len(data))+kind+data+struct.pack(">I", zlib.crc32(kind+data))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n"+
                    chunk(b"IHDR", struct.pack(">IIBBBBB",size,size,8,6,0,0,0))+
                    chunk(b"IDAT", zlib.compress(pixels))+chunk(b"IEND", b""))


def config(namespace):
    lines = ["// Original Awoken miniature blue cyclone. Generated by particles.py.",
             "// Silent light_globe anchors; finite orbits, no custom progs.dat.",
             f"r_effect progs/s_light.spr {namespace}.vortex replace"]
    nodes = effect_nodes()
    root_count = SECTORS*len(LAYERS)
    for i, (layer, sector, hop) in enumerate(nodes):
        name = node_name(layer, sector, hop)
        angle = sector*2*pi/SECTORS
        child = hop+1 < layer.get("steps", 1)
        alpha = layer["alpha"]
        if layer["name"] == "hot":
            # Each travelling patch blooms then fades over its finite orbit.
            alpha *= (.35 + .65*sin(pi*(hop+.5)/layer["steps"]))
        if layer["name"] == "wisp":
            alpha *= 1-hop/layer["steps"]
        lines += [f"// {layer['name']} sector {sector:02d}, path step {hop}",
                  "r_part "+name, "{"]
        if i+1 < root_count:
            lines.append("    assoc "+node_name(*nodes[i+1]))
        if hop == -1:
            # Native fractional model emission otherwise starts all sparse
            # sectors together. Delay each invisible seed by its own phase.
            phase = ((sector*7+sum(map(ord,layer["name"]))) % SECTORS+.5)/SECTORS
            delay = phase/layer["rate"]
            lines += ["    type normal", "    texture particles/awoken_pad/haze",
                      "    blend adda", "    scalefactor 1", "    spawnmode box",
                      f"    count {layer['rate']}", f"    die {delay+.04:.5f}",
                      "    scale 1", "    alpha 0", "    alphadelta 0",
                      "    orgbias 0 0 0", "    velbias 0 0 0",
                      "    emit "+node_name(layer,sector,0),
                      f"    emitstart {delay:.5f}", f"    emitinterval {delay+1:.5f}", "}"]
            continue
        lines += ["    type "+layer.get("render", "normal"),
                  f"    texture particles/awoken_pad/{layer['name']}",
                  "    blend adda", "    scalefactor 1", "    spawnmode box"]
        if "stretch" in layer:
            lines.append(f"    stretchfactor {layer['stretch']}")
        if i >= root_count:
            # The third count argument is the unconditional extra count in
            # native FTE. Standalone countextra belongs to DP effectinfo.
            lines += ["    count 0 0 1"]
        else:
            lines.append(f"    count {layer['rate']*.78:.5f} {layer['rate']*.44:.5f}")
        if hop:
            lines.append("    orgbias 0 0 0")
        else:
            lines += [f"    orgbias {cos(angle)*layer['radius']:.5f} {sin(angle)*layer['radius']:.5f} 0",
                      "    orgwrand "+" ".join(map(str,layer["jitter"]))]
        lines += ["    die "+f"{layer['life']} {layer['minimum']}",
                  "    scale "+" ".join(map(str,layer["scale"])),
                  "    scaledelta "+str(layer["grow"]),
                  "    rgb "+" ".join(map(str,layer["rgb"])),
                  "    alpha "+f"{alpha:.5f}",
                  "    alpharand "+str(layer["alpha_random"]),
                  "    alphadelta "+str(0 if child else round((alpha+layer["alpha_random"])/layer["life"],5)),
                  "    velbias "+" ".join(f"{v:.5f}" for v in path_velocity(layer,sector,hop)),
                  "    velwrand "+" ".join(map(str,layer["velocity_random"])),
                  "    rotation "+" ".join(map(str,layer["rotation"])),
                  "    friction 0 0 0" if "steps" in layer else "    friction 0.15 0.15 0.2",
                  "    flurry 1" if "steps" in layer else "    flurry 3"]
        if child:
            lines += ["    emit "+node_name(layer,sector,hop+1),
                      f"    emitstart {layer['step_time']}", "    emitinterval 5"]
        if layer["name"] == "snap":
            lines += ["    rampmode lerp", "    ramp 35 100 255 0.15 18",
                      "    ramp 70 180 255 0.70 18", "    ramp 230 250 255 0.90 16",
                      "    ramp 150 220 255 0 14", "    ramp 150 220 255 0 14"]
        lines.append("}")
    return "\n".join(lines)+"\n"


def generate(source, output, runtime):
    source, output, runtime = (Path(p).resolve() for p in (source,output,runtime))
    if source == output or output.exists() or runtime.exists():
        raise ValueError("Use fresh output/runtime paths; the source and existing variants are preserved")
    if not re.fullmatch(r"[A-Za-z0-9_-]+",output.stem):
        raise ValueError("Variant basename must contain letters, digits, underscores, or hyphens")
    entities = read(source)
    if (sum(e.keys.get("classname")=="trigger_push" for e in entities)!=4 or
            any(e.keys.get("classname")=="light_globe" for e in entities)):
        raise ValueError("Expected the four-pad Awoken source without existing globe anchors")
    sidecar = source.with_suffix(".assets.json")
    assets = json.loads(sidecar.read_text())
    if assets["map_sha256"] != digest(source):
        raise ValueError("Source runtime assets are stale")
    stage(sidecar.parent/assets["root"],assets["files"],runtime)
    records = {}
    # Quake replacement textures use the BSP basename as their directory.
    # A differently named comparison map needs matching native PNG paths.
    for name, record in assets["files"].items():
        prefix = f"textures/{source.stem}/"
        new_name = f"textures/{output.stem}/"+name[len(prefix):] if name.startswith(prefix) else name
        new_record = dict(record)
        if new_name != name:
            target = runtime/new_name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(runtime/name,target)
            if new_record.get("engine_name") == name[:-4]:
                new_record["engine_name"] = new_name[:-4]
        records[new_name] = new_record
    for layer in LAYERS:
        name = f"particles/awoken_pad/{layer['name']}.png"
        png(runtime/name,layer["name"])
        records[name] = dict(sha256=digest(runtime/name),width=512,height=512,
                             engine_name=name[:-4])
    namespace = "map_"+output.stem
    name = f"particles/{namespace}.cfg"
    (runtime/name).write_text(config(namespace),encoding="ascii")
    records[name] = dict(sha256=digest(runtime/name),kind="fte_particles")
    output.parent.mkdir(parents=True,exist_ok=True)
    anchors = "\n".join('{\n"classname" "light_globe"\n"origin" "'+
                        " ".join(map(str,p))+'"\n"light" "1"\n}\n' for p in PADS.values())
    output.write_bytes(source.read_bytes()+b"\n"+anchors.encode("ascii"))
    write_json(output.with_suffix(".assets.json"),dict(schema=1,map_sha256=digest(output),
               root=os.path.relpath(runtime,output.parent),files=records))
    for suffix in ("materials.json","routes.json","cameras.json"):
        data = json.loads(source.with_suffix("."+suffix).read_text())
        if suffix == "materials.json":
            data["map_sha256"] = digest(output)
        if suffix == "cameras.json":
            data.extend([
                dict(name="vortex-mega",origin=(1408,1780,-640),angles=(27,90,0)),
                dict(name="vortex-rocket",origin=(768,960,-640),angles=(32,270,0)),
                dict(name="vortex-quad",origin=(832,1696,-640),angles=(30,180,0)),
                dict(name="vortex-grenade",origin=(1904,1150,-620),angles=(30,270,0)),
            ])
            for camera in data:
                # Scene rendering was disabled during the physics audit.
                # Give the newly visible static emitters a full lifetime.
                camera["settle_frames"] = 72
        write_json(output.with_suffix("."+suffix),data)
    write_json(output.with_suffix(".particles.json"),dict(schema=1,source=str(source),
               source_sha256=digest(source),map_sha256=digest(output),generator_sha256=digest(__file__),
               anchors=PADS,sectors=SECTORS,layers=LAYERS,runtime_assets=records,
               particles_per_second_per_pad=SECTORS*sum(l["rate"]*(l.get("steps",1)+(l["name"] in STAGGERED)) for l in LAYERS),
               clockwise_fraction=17/24,finite_orbit_steps=True))
    print(output)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source",type=Path,default=ROOT/"src/awoken.map")
    parser.add_argument("--output",type=Path,default=ROOT/"src/awoken_vortex.map")
    parser.add_argument("--runtime",type=Path,default=ROOT/"out/awoken-vortex-assets")
    args = parser.parse_args()
    generate(args.source,args.output,args.runtime)
