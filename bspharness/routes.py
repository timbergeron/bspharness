"""Authored QSS-M movement probes, executed with walking collision enabled."""

from dataclasses import asdict, dataclass
from math import isfinite
import re

from .geometry import Bounds
from .materials import finite_tuple

BUTTONS = ("forward","back","moveleft","moveright","jump")


@dataclass(frozen=True)
class Move:
    frames: int
    buttons: tuple = ("forward",)
    expect: Bounds = None

    def __post_init__(self):
        object.__setattr__(self,"buttons",tuple(self.buttons))
        if (not isinstance(self.frames,int) or isinstance(self.frames,bool) or not 1<=self.frames<=3600
                or any(b not in BUTTONS for b in self.buttons) or len(set(self.buttons))!=len(self.buttons)):
            raise ValueError("Move needs 1..3600 frames and distinct supported movement buttons")
        if self.expect is not None and not isinstance(self.expect,Bounds):
            raise ValueError("Movement checkpoint must be Bounds")


@dataclass(frozen=True)
class WalkRoute:
    name: str
    origin: tuple
    angles: tuple
    actions: tuple
    finish: Bounds
    speed: float = 200
    settle: int = 36
    start_tolerance: float = 8
    min_health: float = 100

    def __post_init__(self):
        if not re.fullmatch(r"[A-Za-z0-9_-]+",self.name):
            raise ValueError("Route names need letters, digits, underscores, or hyphens")
        object.__setattr__(self,"origin",finite_tuple(self.origin,3,"Route origin"))
        object.__setattr__(self,"angles",finite_tuple(self.angles,3,"Route angles"))
        object.__setattr__(self,"actions",tuple(self.actions))
        if not self.actions or any(not isinstance(a,Move) for a in self.actions) or not isinstance(self.finish,Bounds):
            raise ValueError("Route needs Move actions and finish Bounds")
        if (not isfinite(self.speed) or not 1<=self.speed<=320 or
                not isinstance(self.settle,int) or not 1<=self.settle<=720 or
                not isfinite(self.start_tolerance) or not 0<self.start_tolerance<=32 or
                not isfinite(self.min_health) or self.min_health<1):
            raise ValueError("Invalid route speed, settling time, origin tolerance, or health expectation")

    def metadata(self):
        return asdict(self)

    @classmethod
    def from_dict(cls,value):
        def bounds(value):
            return Bounds(tuple(value["mins"]),tuple(value["maxs"]))
        actions = tuple(Move(a["frames"],a.get("buttons",("forward",)),
                             bounds(a["expect"]) if a.get("expect") is not None else None)
                        for a in value["actions"])
        options = {k:value[k] for k in ("speed","settle","start_tolerance","min_health") if k in value}
        return cls(value["name"],value["origin"],value["angles"],actions,bounds(value["finish"]),**options)


def routes_from_json(values):
    if not isinstance(values,list):
        raise ValueError("Routes JSON must be a list of authored routes")
    routes = tuple(WalkRoute.from_dict(value) for value in values)
    if len({r.name for r in routes})!=len(routes):
        raise ValueError("Route names must be unique within a QA pass")
    return routes
