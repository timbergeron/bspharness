"""Convex brushes and an axis-aligned air-volume complement."""

from dataclasses import dataclass, replace
from math import isfinite
import re

EPS = 1e-6


def number(value):
    if not isfinite(value):
        raise ValueError("Coordinates must be finite")
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"


def vector(a, b):
    return tuple(x - y for x, y in zip(a, b))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def texture_name(name):
    # Quake stores a 16-byte miptex name, including its terminator.
    if not re.fullmatch(r'[^\s";\\\x00-\x1f]{1,15}', name) or not name.isascii():
        raise ValueError(f"Invalid Quake texture name: {name!r}")
    return name


@dataclass(frozen=True)
class Bounds:
    mins: tuple
    maxs: tuple

    def __post_init__(self):
        if len(self.mins) != 3 or len(self.maxs) != 3:
            raise ValueError("Bounds need three coordinates")
        if not all(isfinite(x) for x in (*self.mins, *self.maxs)):
            raise ValueError("Bounds must be finite")
        if any(a >= b for a, b in zip(self.mins, self.maxs)):
            raise ValueError("Bounds must have positive volume")

    @property
    def center(self):
        return tuple((a+b)/2 for a, b in zip(self.mins, self.maxs))

    @property
    def volume(self):
        x, y, z = (b-a for a, b in zip(self.mins, self.maxs))
        return x*y*z

    def contains(self, point):
        return all(a <= x <= b for a, x, b in zip(self.mins, point, self.maxs))

    def subtract(self, other):
        """Return up to six disjoint boxes for self minus other."""
        low = [max(a, b) for a, b in zip(self.mins, other.mins)]
        high = [min(a, b) for a, b in zip(self.maxs, other.maxs)]
        if any(a >= b for a, b in zip(low, high)):
            return [self]
        lo, hi = list(self.mins), list(self.maxs)
        result = []
        for axis in range(3):
            if lo[axis] < low[axis]:
                end = hi.copy()
                end[axis] = low[axis]
                result.append(Bounds(tuple(lo), tuple(end)))
                lo[axis] = low[axis]
            if hi[axis] > high[axis]:
                start = lo.copy()
                start[axis] = high[axis]
                result.append(Bounds(tuple(start), tuple(hi)))
                hi[axis] = high[axis]
        return result

    def split(self, axis, value):
        if not self.mins[axis] < value < self.maxs[axis]:
            return [self]
        lo, hi = list(self.mins), list(self.maxs)
        lo[axis] = value
        hi[axis] = value
        return [Bounds(self.mins, tuple(hi)), Bounds(tuple(lo), self.maxs)]


@dataclass(frozen=True)
class Face:
    points: tuple
    texture: str
    scale: float = 1.0
    uoff: float = 0
    voff: float = 0

    def __post_init__(self):
        texture_name(self.texture)
        if not isfinite(self.scale) or self.scale <= 0:
            raise ValueError("Texture scale must be positive")
        if len(self.points) != 3 or any(len(p) != 3 for p in self.points):
            raise ValueError("A face needs three 3D points")
        if not all(isfinite(x) for p in self.points for x in p):
            raise ValueError("Face coordinates must be finite")
        if dot(self.normal, self.normal) < EPS:
            raise ValueError("Degenerate face")

    @property
    def normal(self):
        a, b, c = self.points
        return cross(vector(a, b), vector(c, b))

    def oriented(self, interior):
        distance = dot(self.normal, vector(self.points[1], interior))
        if abs(distance) < EPS:
            raise ValueError("Interior point lies on face plane")
        if distance < 0:
            return replace(self, points=self.points[::-1])
        return self

    def line(self):
        ax, ay, az = map(abs, self.normal)
        if az >= ax and az >= ay:
            u, v = (1, 0, 0), (0, -1, 0)
        elif ax >= ay:
            u, v = (0, 1, 0), (0, 0, -1)
        else:
            u, v = (1, 0, 0), (0, 0, -1)
        points = " ".join("( " + " ".join(map(number, p)) + " )" for p in self.points)
        return (f"{points} {self.texture} [ {' '.join(map(str, u))} {number(self.uoff)} ] "
                f"[ {' '.join(map(str, v))} {number(self.voff)} ] 0 {number(self.scale)} {number(self.scale)}")


class Brush:
    def __init__(self, faces, interior):
        self.faces = tuple(f.oriented(interior) for f in faces)
        self.interior = interior
        if len(self.faces) < 4:
            raise ValueError("A convex brush needs at least four faces")
        # Every supplied vertex must lie on or behind every outward plane.
        for face in self.faces:
            for other in self.faces:
                for point in other.points:
                    if dot(face.normal, vector(point, face.points[1])) > EPS:
                        raise ValueError("Brush is not convex or its interior is outside")

    def text(self):
        return "{\n" + "\n".join(f.line() for f in self.faces) + "\n}"


def box(x0, y0, z0, x1, y1, z1, texture="bh_wall", scale=1.0, **sides):
    bounds = Bounds((x0, y0, z0), (x1, y1, z1))
    definitions = [
        ("top", ((x0,y0,z1),(x0,y1,z1),(x1,y1,z1))),
        ("bottom", ((x0,y0,z0),(x1,y0,z0),(x1,y1,z0))),
        ("north", ((x0,y1,z0),(x1,y1,z0),(x1,y1,z1))),
        ("south", ((x0,y0,z0),(x0,y0,z1),(x1,y0,z1))),
        ("east", ((x1,y0,z0),(x1,y0,z1),(x1,y1,z1))),
        ("west", ((x0,y0,z0),(x0,y1,z0),(x0,y1,z1))),
    ]
    unknown = set(sides) - {name for name, _ in definitions}
    if unknown:
        raise ValueError(f"Unknown box sides: {sorted(unknown)}")
    return Brush([Face(points, sides.get(name, texture), scale) for name, points in definitions], bounds.center)


def ramp(x0, y0, x1, y1, base, start, end, along="x", texture="bh_trim", top="bh_floor"):
    """A six-plane sloped prism; both end heights must exceed base."""
    if along not in ("x", "y") or min(start, end) <= base:
        raise ValueError("Ramp needs x/y axis and end heights above its base")
    Bounds((x0,y0,base), (x1,y1,max(start,end)))
    if along == "x":
        vertices = [(x0,y0,start),(x1,y0,end),(x1,y1,end),(x0,y1,start)]
    else:
        vertices = [(x0,y0,start),(x1,y0,start),(x1,y1,end),(x0,y1,end)]
    a, b, c, d = vertices
    ab, bb, cb, db = [(x,y,base) for x,y,_ in vertices]
    faces = [Face((a,b,c), top), Face((ab,bb,cb), texture),
             Face((ab,bb,b), texture), Face((bb,cb,c), texture),
             Face((cb,db,d), texture), Face((db,ab,a), texture)]
    return Brush(faces, ((x0+x1)/2,(y0+y1)/2,(base+(start+end)/2)/2))
