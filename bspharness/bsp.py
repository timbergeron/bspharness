"""Read Quake BSP29, BSP2, and 2PSB; validate compile products."""

from collections import Counter
from pathlib import Path
import re
import struct

from .wad import validate_miptex, write_wad

NAMES = ("entities","planes","textures","vertices","visibility","nodes","texinfo",
         "faces","lighting","clipnodes","leaves","marksurfaces","edges","surfedges","models")


class BSP:
    def __init__(self, path):
        self.path = Path(path)
        self.data = self.path.read_bytes()
        if len(self.data) < 124:
            raise ValueError("Truncated BSP header")
        magic = self.data[:4]
        self.format = {struct.pack('<i',29):"bsp29",b"BSP2":"bsp2",b"2PSB":"2psb"}.get(magic)
        if not self.format:
            raise ValueError(f"Unsupported Quake BSP version: {magic!r}")
        self.directory = [struct.unpack_from("<ii",self.data,4+i*8) for i in range(15)]
        occupied = []
        for name,(offset,length) in zip(NAMES,self.directory):
            if length < 0 or offset < 0 or offset+length > len(self.data) or (length and offset < 124):
                raise ValueError(f"Invalid {name} lump range")
            if length:
                occupied.append((offset,offset+length,name))
        occupied.sort()
        if any(a[1] > b[0] for a,b in zip(occupied,occupied[1:])):
            raise ValueError("Overlapping BSP lumps")
        extended = self.format != "bsp29"
        self.sizes = {"planes":20,"vertices":12,"texinfo":40,"faces":28 if extended else 20,
                      "nodes":44 if self.format=="bsp2" else 32 if extended else 24,
                      "clipnodes":12 if extended else 8,
                      "leaves":44 if self.format=="bsp2" else 32 if extended else 28,
                      "marksurfaces":4 if extended else 2,"edges":8 if extended else 4,
                      "surfedges":4,"models":64}
        for name,size in self.sizes.items():
            if len(self.lump(name)) % size:
                raise ValueError(f"Misaligned {name} records")
        end = max(offset+length for offset,length in self.directory)
        self.bspx = {}
        pos = (end+3)&~3
        if self.data[pos:pos+4] == b"BSPX":
            if pos+8 > len(self.data):
                raise ValueError("Truncated BSPX header")
            count, = struct.unpack_from("<i",self.data,pos+4)
            if count < 0 or pos+8+count*32 > len(self.data):
                raise ValueError("Invalid BSPX directory")
            for i in range(count):
                raw,offset,length = struct.unpack_from("<24sii",self.data,pos+8+i*32)
                name = raw.split(b"\0",1)[0].decode("ascii")
                if length < 0 or offset < pos+8+count*32 or offset+length > len(self.data):
                    raise ValueError(f"Invalid BSPX {name} range")
                if name in self.bspx:
                    raise ValueError("Duplicate BSPX lump")
                self.bspx[name] = {"offset":offset,"bytes":length}

    def lump(self, name):
        offset,length = self.directory[NAMES.index(name)]
        return self.data[offset:offset+length]

    def count(self, name):
        return len(self.lump(name))//self.sizes[name]

    def entities(self):
        text = self.lump("entities").rstrip(b"\0").decode("latin-1")
        return [dict(re.findall(r'"([^"\n]+)"\s*"([^"\n]*)"',block))
                for block in re.findall(r'\{([^{}]*)\}',text)]

    def textures(self):
        data = self.lump("textures")
        if len(data) < 4:
            raise ValueError("Missing miptex directory")
        count, = struct.unpack_from("<i",data)
        if count < 0 or 4+count*4 > len(data):
            raise ValueError("Invalid miptex directory")
        offsets = struct.unpack_from(f"<{count}i",data,4)
        result = {}
        for offset in offsets:
            if offset == -1:
                # Original id maps can have unused -1 directory slots.
                # Validation checks texinfo to reject *referenced* holes.
                continue
            if offset < 4+count*4 or offset+40 > len(data):
                raise ValueError("Invalid miptex offset")
            # Bound each texture by the next miptex, not by the entire lump.
            end = min((x for x in offsets if x > offset),default=len(data))
            payload = data[offset:end]
            texture = validate_miptex(payload)
            name = texture["name"]
            # Repeated directory names occur in original id BSPs. Preserve
            # the last embedded definition when exporting a name-based WAD.
            result[name.casefold()] = {**texture,"data":payload}
        return result

    def model_bounds(self):
        data = self.lump("models")
        return [{"model":f"*{i}","mins":list(struct.unpack_from("<3f",data,i*64)),
                 "maxs":list(struct.unpack_from("<3f",data,i*64+12))}
                for i in range(self.count("models"))]

    def validate(self, expected_format=None, reference=None):
        errors = []
        if expected_format and self.format != expected_format:
            errors.append(f"Expected {expected_format}, got {self.format}")
        for name in ("visibility","lighting","models","nodes","clipnodes"):
            if not self.lump(name):
                errors.append(f"Empty {name} lump")
        entities = self.entities()
        if not entities or entities[0].get("classname") != "worldspawn":
            errors.append("Missing worldspawn")
        if not any(e.get("classname")=="info_player_start" for e in entities):
            errors.append("Missing info_player_start")
        if self.format == "bsp29" and self.count("clipnodes") > 32767:
            errors.append("Clipnode count exceeds strict vanilla BSP29 budget; use explicit BSP2")
        if reference and self.count("clipnodes") > max(1,reference.count("clipnodes"))*2:
            errors.append("Clipnode count exceeds 2x reference; try stable qbsp")
        extended = self.format != "bsp29"
        edges = list(struct.iter_unpack("<II" if extended else "<HH",self.lump("edges")))
        if any(a>=self.count("vertices") or b>=self.count("vertices") for a,b in edges):
            errors.append("Invalid vertex index in edge")
        surfedges = [x[0] for x in struct.iter_unpack("<i",self.lump("surfedges"))]
        if any(abs(x)>=len(edges) for x in surfedges):
            errors.append("Invalid edge index in surfedge")
        faces = self.lump("faces")
        for offset in range(0,len(faces),self.sizes["faces"]):
            plane,side,first,count,texinfo = struct.unpack_from("<iiiii" if extended else "<HHiHH",faces,offset)
            if plane<0 or plane>=self.count("planes") or first<0 or count<3 or first+count>len(surfedges) or texinfo<0 or texinfo>=self.count("texinfo"):
                errors.append("Invalid face references")
                break
        nodes = self.lump("nodes")
        for offset in range(0,len(nodes),self.sizes["nodes"]):
            plane,a,b = struct.unpack_from("<iii" if extended else "<ihh",nodes,offset)
            if plane<0 or plane>=self.count("planes") or any(c>=self.count("nodes") if c>=0 else -c-1>=self.count("leaves") for c in (a,b)):
                errors.append("Invalid node or leaf reference")
                break
        marks = [x[0] for x in struct.iter_unpack("<I" if extended else "<H",self.lump("marksurfaces"))]
        if any(x>=self.count("faces") for x in marks):
            errors.append("Invalid marksurface face reference")
        try:
            textures = self.textures()
            data = self.lump("textures")
            count, = struct.unpack_from("<i",data)
            offsets = struct.unpack_from(f"<{count}i",data,4)
            info = self.lump("texinfo")
            for offset in range(0,len(info),40):
                index, = struct.unpack_from("<i",info,offset+32)
                if index<0 or index>=count or offsets[index]==-1:
                    errors.append("Texinfo references a missing texture")
                    break
        except (ValueError,UnicodeError,struct.error) as exc:
            errors.append(str(exc))
            textures = {}
        return {"format":self.format,"bytes":len(self.data),"lumps":{
                    name:{"bytes":len(self.lump(name)),**({"count":self.count(name)} if name in self.sizes else {})} for name in NAMES},
                "bspx":self.bspx,"entities":dict(Counter(e.get("classname","?") for e in entities)),
                "models":self.model_bounds(),"textures":[{k:v for k,v in t.items() if k not in ("pixels","data")} for t in textures.values()],
                "errors":errors,"passed":not errors}

    def extract_wad(self, path):
        return write_wad(path,{t["name"]:t["data"] for t in self.textures().values()})
