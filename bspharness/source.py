"""Focused reader for brush MAPs with Valve 220 axes and optional Q2 flags."""

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
import re

from .geometry import Brush, Face

NUM = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
POINT = r"\(\s*("+NUM+r")\s+("+NUM+r")\s+("+NUM+r")\s*\)"
AXIS = r"\[\s*("+NUM+r")\s+("+NUM+r")\s+("+NUM+r")\s+("+NUM+r")\s*\]"
FACE = re.compile(r"\s*"+r"\s*".join((POINT,POINT,POINT))+r"\s+(\S+)\s+"+
                  AXIS+r"\s+"+AXIS+r"\s+("+NUM+r")\s+("+NUM+r")\s+("+NUM+
                  r")(?:\s+(-?\d+)\s+(-?\d+)\s+(-?\d+))?\s*")
KEY = re.compile(r'\s*"((?:\\.|[^"\\])*)"\s+"((?:\\.|[^"\\])*)"\s*')


@dataclass(frozen=True)
class SourceFace:
    points: tuple
    texture: str
    uaxis: tuple
    vaxis: tuple
    uoff: float
    voff: float
    scale: float
    vscale: float
    contents: int = 0
    flags: int = 0
    value: int = 0

    def mapped(self, texture):
        # Face uses positive scales; reflect an axis for a negative input.
        return Face(self.points,texture,abs(self.scale),self.uoff,self.voff,
                    tuple(x*(1 if self.scale>0 else -1) for x in self.uaxis),
                    tuple(x*(1 if self.vscale>0 else -1) for x in self.vaxis),abs(self.vscale))


@dataclass(frozen=True)
class SourceBrush:
    faces: tuple

    def mapped(self, material):
        """Material may be one texture/Material or a per-source-face function."""
        return Brush.from_planes(f.mapped(material(f) if callable(material) else material) for f in self.faces)


@dataclass
class SourceEntity:
    keys: dict
    brushes: list


def parse(text):
    entities,entity,brush = [],None,None
    for lineno,line in enumerate(text.splitlines(),1):
        # Remove comments only outside quoted entity strings.
        line = re.sub(r'"(?:\\.|[^"\\])*"|//.*',
                      lambda m:"" if m[0].startswith("//") else m[0],line).strip()
        if not line:
            continue
        if line=="{":
            if entity is None:
                entity = SourceEntity({},[])
            elif brush is None:
                brush = []
            else:
                raise ValueError(f"MAP line {lineno}: nested patches/brush definitions are unsupported")
        elif line=="}":
            if brush is not None:
                if len(brush)<4:
                    raise ValueError(f"MAP line {lineno}: brush needs at least four planes")
                entity.brushes.append(SourceBrush(tuple(brush)))
                brush = None
            elif entity is not None:
                entities.append(entity)
                entity = None
            else:
                raise ValueError(f"MAP line {lineno}: unmatched closing brace")
        elif entity is None:
            raise ValueError(f"MAP line {lineno}: expected an entity")
        elif brush is None:
            match = KEY.fullmatch(line)
            if match is None:
                raise ValueError(f"MAP line {lineno}: expected quoted entity key/value")
            def unescape(value):
                return value.replace('\\"','"').replace('\\\\','\\')
            key,value = map(unescape,match.groups())
            if key in entity.keys:
                raise ValueError(f"MAP line {lineno}: duplicate key {key}")
            entity.keys[key] = value
        else:
            match = FACE.fullmatch(line)
            if match is None:
                raise ValueError(f"MAP line {lineno}: expected a Valve 220 brush face")
            g = match.groups()
            v = [float(x) for x in (*g[:9],*g[10:21])]
            if not all(isfinite(x) for x in v):
                raise ValueError(f"MAP line {lineno}: geometry and texture axes must be finite")
            face = SourceFace(tuple(tuple(v[i:i+3]) for i in (0,3,6)),g[9],
                              tuple(v[9:12]),tuple(v[13:16]),v[12],v[16],v[18],v[19],
                              *(int(x or 0) for x in g[21:24]))
            # Validate finite geometry/UVs without constraining Q2 texture paths.
            face.mapped("skip")
            brush.append(face)
    if entity is not None or brush is not None:
        raise ValueError("MAP ended inside an entity or brush")
    if not entities or entities[0].keys.get("classname")!="worldspawn" or any(
            e.keys.get("classname")=="worldspawn" for e in entities[1:]):
        raise ValueError("MAP needs exactly one leading worldspawn")
    return entities


def read(path):
    return parse(Path(path).read_text(encoding="utf-8"))
