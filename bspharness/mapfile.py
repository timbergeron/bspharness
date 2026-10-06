"""Room palettes, sealed worlds, entities, and Valve 220 output."""

from dataclasses import dataclass, replace
from copy import copy
import hashlib
from itertools import combinations
import json
from pathlib import Path

from .geometry import Bounds, box, number
from .materials import Material, TextureLibrary, WallRun
from .transitions import Portal, TransitionRule, name


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
    def __init__(self, title="BSP Harness", padding=64, shell="rooms", **worldspawn):
        if padding < 64:
            raise ValueError("Use at least 64 units of seal padding")
        self.padding = padding
        if shell not in ("rooms","explicit"):
            raise ValueError("Map shell must be rooms or explicit")
        self.shell = shell
        self.worldspawn = {"classname": "worldspawn", "message": title, **worldspawn}
        self.airs = []
        self.details = []
        self.entities = []
        self.cameras = []
        self.wall_runs = []
        self.transition_rules = []
        self.transitions = []

    def room(self, name, mins, maxs, palette=None, kind="room"):
        if self.shell=="explicit":
            raise ValueError("Explicit-shell maps use imported or authored structural brushes")
        if kind not in ("room", "sky", "window"):
            raise ValueError("Air kind must be room, sky, or window")
        if any(a.name == name for a in self.airs):
            raise ValueError(f"Duplicate room name: {name}")
        air = Air(name, Bounds(tuple(mins),tuple(maxs)), palette or Palette(), kind)
        self.airs.append(air)
        return air

    def structural(self, *brushes):
        """Solid geometry that participates in sealing and visibility."""
        self.details.extend(brushes)

    def detail(self, *brushes, mode="detail", **keys):
        """Compiler detail geometry, with collision controlled by its role."""
        modes = {"detail":"func_detail", "wall":"func_detail_wall",
                 "fence":"func_detail_fence", "illusionary":"func_detail_illusionary"}
        if mode=="structural":
            if keys:
                raise ValueError("Structural brushes cannot have entity keys")
            self.structural(*brushes)
            return None
        if mode not in modes:
            raise ValueError(f"Unknown detail mode: {mode}")
        if not brushes:
            raise ValueError("Detail needs at least one brush")
        return self.entity(modes[mode],brushes=brushes,**keys)

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

    def wall_run(self, material, path, z_anchor=None, start=0):
        run = WallRun(material,tuple(path),material.anchor[2] if z_anchor is None else z_anchor,start)
        self.wall_runs.append(run)
        return run

    def transition_rule(self, rule):
        if not isinstance(rule,TransitionRule):
            raise ValueError("Register a TransitionRule")
        self.transition_rules.append(rule)

    def transition(self, a, b, trim, **options):
        if a==b:
            raise ValueError("A transition needs two different rooms")
        self.transitions.append((a,b,TransitionRule((a,b),trim,**options)))

    def portals(self):
        rooms = {a.name:a for a in self.airs if a.kind=="room"}
        portals = {}
        for a,b,rule in self.transitions:
            if a not in rooms or b not in rooms:
                raise ValueError(f"Transition references an unknown room: {a}/{b}")
            portal = Portal.between(rooms[a],rooms[b],rule)
            if portal is None:
                raise ValueError(f"Transition rooms must share a vertical opening: {a}/{b}")
            key = frozenset((a,b))
            if key in portals:
                raise ValueError(f"Duplicate transition for {a}/{b}")
            portals[key] = portal
        for a,b in combinations(rooms.values(),2):
            key = frozenset((a.name,b.name))
            if key in portals:
                continue
            matched = [r for r in self.transition_rules if r.matches(a,b)]
            candidates = [p for r in matched if (p:=Portal.between(a,b,r)) is not None]
            if len(candidates)>1:
                raise ValueError(f"Multiple transition rules match {a.name}/{b.name}; declare a room transition")
            if candidates:
                portals[key] = candidates[0]
        result = list(portals.values())
        for a,b in combinations(result,2):
            if (a.band is not None and b.band is not None and abs(a.low[2]-b.low[2])<1e-6
                    and name(a.rule.trim).casefold()!=name(b.rule.trim).casefold()
                    and all(min(a.band.maxs[i],b.band.maxs[i])-max(a.band.mins[i],b.band.mins[i])>1e-6
                            for i in (0,1))):
                raise ValueError(f"Conflicting floor trim bands at {a.rooms}/{b.rooms}")
        return result

    def world_brushes(self):
        if self.shell=="explicit":
            return []
        if not self.airs:
            raise ValueError("Declare at least one air volume")
        lo = tuple(min(a.bounds.mins[i] for a in self.airs)-self.padding for i in range(3))
        hi = tuple(max(a.bounds.maxs[i] for a in self.airs)+self.padding for i in range(3))
        solids = [Bounds(lo,hi)]
        for air in self.airs:
            solids = [piece for solid in solids for piece in solid.subtract(air.bounds)]
        portals = self.portals()
        bands = [p.band for p in portals if p.band is not None]
        # Split along palette boundaries so a plane shared by two rooms or a
        # sky well can receive different materials on each rectangular patch.
        for axis in range(3):
            cuts = sorted({v for a in self.airs for v in (a.bounds.mins[axis],a.bounds.maxs[axis])})
            cuts = sorted(set(cuts)|{v for b in bands for v in (b.mins[axis],b.maxs[axis])})
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
            for portal in portals:
                if portal.covers_floor(solid):
                    # Retexture a partition of the existing floor. No
                    # coplanar overlay, raised step, or extra collision slab.
                    sides["top"] = portal.rule.trim
                    scales["top"] = 1.0
            # Scale is global for a brush. Set per-face scales after construction.
            brush = box(*solid.mins,*solid.maxs,texture=self.airs[0].palette.wall,**sides)
            brush.faces = tuple(replace(face,scale=scales.get(side,1.0)) for face,side in zip(brush.faces,directions))
            brushes.append(brush)
        for portal in portals:
            brushes.extend(portal.frame_brushes())
        return brushes

    def write(self, path, wads, check_seams=None):
        path = Path(path)
        wads = list(wads)
        brushes = self.world_brushes() + [copy(b) for b in self.details]
        entities = [(keys,tuple(copy(b) for b in entity_brushes)) for keys,entity_brushes in self.entities]
        worldspawn = {**self.worldspawn,"wad":";".join(Path(w).resolve().as_posix() for w in wads)}
        if worldspawn["classname"] != "worldspawn":
            raise ValueError("World classname must be worldspawn")
        all_brushes = brushes+[b for _,entity_brushes in entities for b in entity_brushes]
        materials = {f.material for b in all_brushes for f in b.faces if f.material is not None}
        materials.update(run.material for run in self.wall_runs)
        enabled = bool(materials or self.transitions or self.transition_rules or self.wall_runs)
        contract = None
        if enabled or check_seams:
            library = TextureLibrary(wads)
            run_matches = [0]*len(self.wall_runs)
            for brush in all_brushes:
                faces = []
                for face in brush.faces:
                    mapped = face.material.map_face(face,library) if face.material is not None else face
                    matches = []
                    for index,run in enumerate(self.wall_runs):
                        if run.material.texture.casefold()==face.texture.casefold():
                            value = run.map_face(face,brush.face_vertices(face),library)
                            if value is not None:
                                matches.append(value)
                                run_matches[index] += 1
                    if len(matches)>1:
                        raise ValueError(f"Overlapping wall runs at {face.points[1]}")
                    faces.append(matches[0] if matches else mapped)
                brush.faces = tuple(faces)
            if any(count==0 for count in run_matches):
                raise ValueError("A wall run matched no faces; check its texture, path, and face extents")
            portals = self.portals()
            # Only declared trim contacts are intentionally exempt from the
            # generic material-boundary warning. UV checks still run.
            allowed = set()
            for portal in portals:
                for room in self.airs:
                    if room.name in portal.rooms:
                        for role in ("wall","floor","ceiling"):
                            allowed.add(tuple(sorted((name(getattr(room.palette,role)),name(portal.rule.trim)))))
            contract = {"schema":1,"strict":True if check_seams is None else bool(check_seams),
                        "materials":[m.metadata(library) for m in sorted(materials,key=repr)],
                        "wall_runs":[r.metadata() for r in self.wall_runs],
                        "transitions":[p.metadata() for p in portals],
                        "allowed_pairs":[list(p) for p in sorted(allowed)]}
        sections = []
        for keys, entity_brushes in [(worldspawn,brushes),*entities]:
            lines = ["{",*(f"{quoted(k)} {quoted(v)}" for k,v in keys.items())]
            lines.extend(b.text() for b in entity_brushes)
            lines.append("}")
            sections.append("\n".join(lines))
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text("// Game: Quake\n// Format: Valve\n"+"\n".join(sections)+"\n",encoding="ascii")
        sidecar = path.with_suffix(".materials.json")
        if contract is not None:
            contract["map_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            sidecar.write_text(json.dumps(contract,indent=2)+"\n",encoding="utf-8")
        elif sidecar.exists():
            sidecar.unlink()
        return path
