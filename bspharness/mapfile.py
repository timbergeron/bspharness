"""Room palettes, sealed worlds, entities, and Valve 220 output."""

from dataclasses import dataclass, replace
from pathlib import Path

from .geometry import Bounds, box, number


def quoted(value):
    value = str(value)
    if any(c in value for c in ('"', '\\', '\n', '\r', '\x00')):
        raise ValueError(f"Unsafe map string: {value!r}; use forward slashes in paths")
    return f'"{value}"'


@dataclass(frozen=True)
class Palette:
    wall: str = "bh_wall"
    floor: str = "bh_floor"
    ceiling: str = "bh_ceil"
    trim: str = "bh_trim"
    sky: str = "sky_bh"
    scale: float = 1.0


@dataclass(frozen=True)
class Air:
    name: str
    bounds: Bounds
    palette: Palette
    kind: str


class Map:
    def __init__(self, title="BSP Harness", padding=64, **worldspawn):
        if padding < 64:
            raise ValueError("Use at least 64 units of seal padding")
        self.padding = padding
        self.worldspawn = {"classname": "worldspawn", "message": title, **worldspawn}
        self.airs = []
        self.details = []
        self.entities = []
        self.cameras = []

    def room(self, name, mins, maxs, palette=None, kind="room"):
        if kind not in ("room", "sky", "window"):
            raise ValueError("Air kind must be room, sky, or window")
        if any(a.name == name for a in self.airs):
            raise ValueError(f"Duplicate room name: {name}")
        air = Air(name, Bounds(tuple(mins),tuple(maxs)), palette or Palette(), kind)
        self.airs.append(air)
        return air

    def detail(self, *brushes):
        self.details.extend(brushes)

    def entity(self, classname, origin=None, brushes=(), **keys):
        entity = {"classname": classname, **keys}
        if origin is not None:
            if len(origin) != 3:
                raise ValueError("Entity origin needs three coordinates")
            entity["origin"] = " ".join(map(number, origin))
        self.entities.append((entity, tuple(brushes)))
        return entity

    def light(self, origin, intensity=300, color=(255,219,175), **keys):
        return self.entity("light", origin, light=number(intensity),
                           _color=" ".join(map(number,color)), **keys)

    def camera(self, name, origin, angles):
        if len(origin) != 3 or len(angles) != 3:
            raise ValueError("Camera needs XYZ and pitch/yaw/roll")
        self.cameras.append({"name":name, "origin":list(origin), "angles":list(angles)})

    def world_brushes(self):
        if not self.airs:
            raise ValueError("Declare at least one air volume")
        lo = tuple(min(a.bounds.mins[i] for a in self.airs)-self.padding for i in range(3))
        hi = tuple(max(a.bounds.maxs[i] for a in self.airs)+self.padding for i in range(3))
        solids = [Bounds(lo,hi)]
        for air in self.airs:
            solids = [piece for solid in solids for piece in solid.subtract(air.bounds)]
        # Split along palette boundaries so a plane shared by two rooms or a
        # sky well can receive different materials on each rectangular patch.
        for axis in range(3):
            cuts = sorted({v for a in self.airs for v in (a.bounds.mins[axis],a.bounds.maxs[axis])})
            for cut in cuts:
                solids = [piece for solid in solids for piece in solid.split(axis,cut)]
                if len(solids) > 50000:
                    raise ValueError("Air partition exceeds 50k brushes; split into modules")
        directions = {"top":(2,1), "bottom":(2,-1), "north":(1,1),
                      "south":(1,-1), "east":(0,1), "west":(0,-1)}
        brushes = []
        for solid in solids:
            sides, scales = {}, {}
            for side,(axis,sign) in directions.items():
                plane = solid.maxs[axis] if sign > 0 else solid.mins[axis]
                candidates = []
                for air in self.airs:
                    boundary = air.bounds.mins[axis] if sign > 0 else air.bounds.maxs[axis]
                    if abs(plane-boundary) > 1e-6:
                        continue
                    area = 1
                    for i in range(3):
                        if i != axis:
                            area *= max(0,min(solid.maxs[i],air.bounds.maxs[i])-max(solid.mins[i],air.bounds.mins[i]))
                    if area > 0:
                        candidates.append((area,air))
                if candidates:
                    air = max(candidates,key=lambda pair:pair[0])[1]
                    palette = air.palette
                    if air.kind == "sky" or (air.kind == "window" and axis != 2):
                        tex = palette.sky
                    elif air.kind == "window":
                        tex = palette.trim
                    else:
                        tex = palette.floor if side == "top" else palette.ceiling if side == "bottom" else palette.wall
                    sides[side] = tex
                    scales[side] = palette.scale
            # Scale is global for a brush. Set per-face scales after construction.
            brush = box(*solid.mins,*solid.maxs,**sides)
            brush.faces = tuple(replace(face,scale=scales.get(side,1.0)) for face,side in zip(brush.faces,directions))
            brushes.append(brush)
        return brushes

    def write(self, path, wads):
        path = Path(path)
        brushes = self.world_brushes() + self.details
        worldspawn = {**self.worldspawn,"wad":";".join(Path(w).resolve().as_posix() for w in wads)}
        if worldspawn["classname"] != "worldspawn":
            raise ValueError("World classname must be worldspawn")
        sections = []
        for keys, entity_brushes in [(worldspawn,brushes),*self.entities]:
            lines = ["{",*(f"{quoted(k)} {quoted(v)}" for k,v in keys.items())]
            lines.extend(b.text() for b in entity_brushes)
            lines.append("}")
            sections.append("\n".join(lines))
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text("// Game: Quake\n// Format: Valve\n"+"\n".join(sections)+"\n",encoding="ascii")
        return path
