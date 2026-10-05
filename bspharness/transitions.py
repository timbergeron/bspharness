"""Intentional material borders at adjoining room openings."""

from dataclasses import dataclass
from math import isfinite

from .geometry import Bounds, box
from .materials import Material


def name(material):
    return material.texture if isinstance(material,Material) else material


@dataclass(frozen=True)
class TransitionRule:
    textures: tuple
    trim: object
    width: float = 16
    depth: float = 8
    frame: bool = True
    threshold: bool = True

    def __post_init__(self):
        object.__setattr__(self,"textures",tuple(name(t) for t in self.textures))
        if len(self.textures) != 2 or self.textures[0].casefold()==self.textures[1].casefold():
            raise ValueError("Transition rule needs two different texture names")
        if not all(isfinite(x) and x>0 for x in (self.width,self.depth)):
            raise ValueError("Transition width and depth must be positive")
        if not self.frame and not self.threshold:
            raise ValueError("Enable a doorway frame or floor threshold")

    def matches(self, a, b):
        wanted = {t.casefold() for t in self.textures}
        return any({name(getattr(a.palette,role)).casefold(),name(getattr(b.palette,role)).casefold()}==wanted
                   for role in ("wall","floor"))


@dataclass(frozen=True)
class Portal:
    rooms: tuple
    axis: int
    plane: float
    low: tuple
    high: tuple
    rule: TransitionRule

    @classmethod
    def between(cls, a, b, rule):
        for axis in (0,1):
            if abs(a.bounds.maxs[axis]-b.bounds.mins[axis]) < 1e-6:
                plane = a.bounds.maxs[axis]
            elif abs(b.bounds.maxs[axis]-a.bounds.mins[axis]) < 1e-6:
                plane = b.bounds.maxs[axis]
            else:
                continue
            low = tuple(max(a.bounds.mins[i],b.bounds.mins[i]) for i in range(3))
            high = tuple(min(a.bounds.maxs[i],b.bounds.maxs[i]) for i in range(3))
            across = 1-axis
            if low[across]>=high[across] or low[2]>=high[2]:
                continue
            available = min(room.bounds.maxs[axis]-room.bounds.mins[axis] for room in (a,b))
            if ((rule.frame and rule.depth/2>available) or
                    (rule.threshold and rule.width/2>available)):
                raise ValueError(f"Transition {a.name}/{b.name} extends beyond its rooms")
            if rule.frame and (high[across]-low[across]-2*rule.width<96 or high[2]-low[2]-rule.width<128):
                raise ValueError(f"Transition {a.name}/{b.name} would reduce clearance below 96x128")
            if rule.threshold and abs(a.bounds.mins[2]-b.bounds.mins[2])>1e-6:
                raise ValueError(f"Transition {a.name}/{b.name} has different floor heights; disable threshold")
            return cls((a.name,b.name),axis,plane,low,high,rule)
        return None

    def frame_brushes(self):
        if not self.rule.frame:
            return []
        lo,hi = list(self.low),list(self.high)
        lo[self.axis] = self.plane-self.rule.depth/2
        hi[self.axis] = self.plane+self.rule.depth/2
        across = 1-self.axis
        result = []
        for side in (0,1):
            start,end = lo.copy(),hi.copy()
            if side==0:
                end[across] = lo[across]+self.rule.width
            else:
                start[across] = hi[across]-self.rule.width
            result.append(box(*start,*end,texture=self.rule.trim))
        start = lo.copy()
        start[2] = hi[2]-self.rule.width
        result.append(box(*start,*hi,texture=self.rule.trim))
        return result

    @property
    def band(self):
        if not self.rule.threshold:
            return None
        lo,hi = list(self.low),list(self.high)
        lo[self.axis] = self.plane-self.rule.width/2
        hi[self.axis] = self.plane+self.rule.width/2
        lo[2] -= 1
        hi[2] = self.low[2]
        return Bounds(tuple(lo),tuple(hi))

    def covers_floor(self, bounds):
        band = self.band
        return band is not None and abs(bounds.maxs[2]-self.low[2])<1e-6 and all(
            bounds.mins[i]>=band.mins[i]-1e-6 and bounds.maxs[i]<=band.maxs[i]+1e-6 for i in (0,1))

    def metadata(self):
        return {"rooms":list(self.rooms),"axis":self.axis,"plane":self.plane,
                "low":list(self.low),"high":list(self.high),"trim":name(self.rule.trim),
                "width":self.rule.width,"depth":self.rule.depth,
                "frame":self.rule.frame,"threshold":self.rule.threshold}
