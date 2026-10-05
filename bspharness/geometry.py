"""Convex brushes and an axis-aligned air-volume complement."""

from dataclasses import dataclass, replace
from functools import cached_property
from itertools import combinations
from math import isfinite, sqrt
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


def normalize(value):
    length = sqrt(dot(value, value))
    if length < EPS:
        raise ValueError("Cannot normalize a zero vector")
    return tuple(x/length for x in value)


def world_axes(normal):
    ax, ay, az = map(abs, normal)
    if az >= ax and az >= ay:
        return (1, 0, 0), (0, -1, 0)
    if ax >= ay:
        return (0, 1, 0), (0, 0, -1)
    return (1, 0, 0), (0, 0, -1)


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
    uaxis: tuple = None
    vaxis: tuple = None
    vscale: float = None
    material: object = None

    def __post_init__(self):
        if not isinstance(self.texture, str):
            from .materials import Material
            if not isinstance(self.texture, Material):
                raise ValueError("Face texture must be a name or Material")
            object.__setattr__(self, "material", self.texture)
            object.__setattr__(self, "texture", self.texture.texture)
        texture_name(self.texture)
        if not isfinite(self.scale) or self.scale <= 0:
            raise ValueError("Texture scale must be positive")
        if len(self.points) != 3 or any(len(p) != 3 for p in self.points):
            raise ValueError("A face needs three 3D points")
        if not all(isfinite(x) for p in self.points for x in p):
            raise ValueError("Face coordinates must be finite")
        if dot(self.normal, self.normal) < EPS:
            raise ValueError("Degenerate face")
        if self.vscale is not None and (not isfinite(self.vscale) or self.vscale <= 0):
            raise ValueError("V texture scale must be positive")
        if not all(isfinite(x) for x in (self.uoff, self.voff)):
            raise ValueError("Texture offsets must be finite")
        if (self.uaxis is None) != (self.vaxis is None):
            raise ValueError("Supply both texture axes")
        if self.uaxis is not None:
            for axis in (self.uaxis, self.vaxis):
                if len(axis) != 3 or not all(isfinite(x) for x in axis) or dot(axis,axis) < EPS:
                    raise ValueError("Texture axes must be finite nonzero 3D vectors")
            if dot(cross(self.uaxis, self.vaxis), cross(self.uaxis, self.vaxis)) < EPS:
                raise ValueError("Texture axes must be independent")

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

    @property
    def axes(self):
        return (self.uaxis, self.vaxis) if self.uaxis is not None else world_axes(self.normal)

    def uv(self, point):
        u, v = self.axes
        return dot(u,point)/self.scale+self.uoff, dot(v,point)/(self.vscale or self.scale)+self.voff

    def line(self):
        if self.material is not None and self.uaxis is None:
            raise ValueError("Resolve Material faces through Map.write or Material.map_face before emitting MAP text")
        u, v = self.axes
        points = " ".join("( " + " ".join(map(number, p)) + " )" for p in self.points)
        return (f"{points} {self.texture} [ {' '.join(map(number, u))} {number(self.uoff)} ] "
                f"[ {' '.join(map(number, v))} {number(self.voff)} ] 0 {number(self.scale)} {number(self.vscale or self.scale)}")


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

    @cached_property
    def vertices(self):
        """Intersect planes, rather than treating MAP plane points as bounds."""
        planes = [(normalize(f.normal), f.points[1]) for f in self.faces]
        vertices = {}
        for (a,pa),(b,pb),(c,pc) in combinations(planes,3):
            determinant = dot(a,cross(b,c))
            if abs(determinant) < 1e-8:
                continue
            terms = [(dot(a,pa),cross(b,c)),(dot(b,pb),cross(c,a)),(dot(c,pc),cross(a,b))]
            point = tuple(sum(distance*axis[i] for distance,axis in terms)/determinant for i in range(3))
            if all(dot(normal,vector(point,origin)) <= 1e-4 for normal,origin in planes):
                vertices[tuple(round(x,6) for x in point)] = point
        if len(vertices) < 4:
            raise ValueError("Brush has no bounded convex volume")
        return tuple(vertices.values())

    def face_vertices(self, face):
        normal = normalize(face.normal)
        return tuple(p for p in self.vertices if abs(dot(normal,vector(p,face.points[1]))) < 1e-4)

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
