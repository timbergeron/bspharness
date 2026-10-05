"""Extract locally owned id1 textures and palette without distributing PAKs."""

from pathlib import Path
import struct
import tempfile

from .bsp import BSP
from .wad import write_wad


def entries(path):
    data = Path(path).read_bytes()
    if len(data) < 12:
        raise ValueError("Truncated PAK header")
    magic,offset,length = struct.unpack_from("<4sii",data)
    if magic != b"PACK" or offset < 12 or length < 0 or length%64 or offset+length > len(data):
        raise ValueError("Invalid Quake PAK directory")
    seen = set()
    for pos in range(offset,offset+length,64):
        raw,start,size = struct.unpack_from("<56sii",data,pos)
        name = raw.split(b"\0",1)[0].decode("ascii")
        if start < 12 or size < 0 or start+size > len(data) or name in seen:
            raise ValueError(f"Invalid or duplicate PAK entry: {name}")
        seen.add(name)
        yield name,data[start:start+size]


def extract_id_wad(paks, output, palette=None):
    textures, maps = {}, []
    palette_data = None
    # Later PAKs and later maps take precedence, matching load order for
    # repeated texture names. No archive filenames are used as disk paths.
    with tempfile.TemporaryDirectory(prefix="bspharness-pak-") as temp:
        source = Path(temp)/"source.bsp"
        for pak in paks:
            for name,payload in entries(pak):
                if name == "gfx/palette.lmp":
                    if len(payload) != 768:
                        raise ValueError("Invalid palette.lmp in PAK")
                    palette_data = payload
                if name.startswith("maps/") and name.endswith(".bsp"):
                    source.write_bytes(payload)
                    textures.update({t["name"]:t["data"] for t in BSP(source).textures().values()})
                    maps.append(name)
    if not textures:
        raise ValueError("No BSP textures found in the supplied PAKs")
    if palette:
        if palette_data is None:
            raise ValueError("No gfx/palette.lmp found; supply pak0.pak")
        palette = Path(palette)
        palette.parent.mkdir(parents=True,exist_ok=True)
        palette.write_bytes(palette_data)
    write_wad(output,textures)
    return {"textures":len(textures),"maps":len(maps),"output":str(output)}
