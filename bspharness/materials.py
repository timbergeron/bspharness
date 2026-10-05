"""Physical texture scale, alignment anchors, and unrolled wall paths."""

from dataclasses import asdict, dataclass, replace
from math import isfinite, sqrt

from .geometry import dot, normalize, texture_name, vector, world_axes
from .wad import read_wad


def finite_tuple(value, size, label):
    if len(value) != size or not all(isfinite(x) for x in value):
        raise ValueError(f"{label} needs {size} finite coordinates")
    return tuple(value)


class TextureLibrary:
    """WAD dimensions/artwork with the last WAD taking precedence (ericw)."""
    def __init__(self, wads):
        self.textures = {}
        for wad in wads:
            self.textures.update(read_wad(wad))

    def __getitem__(self, name):
        try:
            return self.textures[name.casefold()]
        except KeyError as exc:
            raise ValueError(f"Material texture is missing from WADs: {name}") from exc


@dataclass(frozen=True)
class Material:
    texture: str
    density: float = None
    repeat: tuple = None
    anchor: tuple = (0,0,0)
    phase: tuple = (0,0)
    family: str = None
    projection: str = "world"

    def __post_init__(self):
        texture_name(self.texture)
        if self.density is not None and self.repeat is not None:
            raise ValueError("Choose texel density or world repeat size, not both")
        if self.density is not None and (not isfinite(self.density) or self.density <= 0):
            raise ValueError("Texel density must be positive pixels per world unit")
        if self.repeat is not None:
            object.__setattr__(self,"repeat",finite_tuple(self.repeat,2,"Repeat"))
            if min(self.repeat) <= 0:
                raise ValueError("Repeat sizes must be positive")
        object.__setattr__(self,"anchor",finite_tuple(self.anchor,3,"Anchor"))
        object.__setattr__(self,"phase",finite_tuple(self.phase,2,"Phase"))
        if self.projection not in ("world","surface"):
            raise ValueError("Material projection must be world or surface")
        if self.family is not None and (not isinstance(self.family,str) or not self.family):
            raise ValueError("Material family must be a nonempty name")

    def scales(self, texture):
        if self.repeat is not None:
            return self.repeat[0]/texture["width"], self.repeat[1]/texture["height"]
        scale = 1/(self.density if self.density is not None else 1)
        return scale,scale

    def axes(self, normal):
        u,v = world_axes(normal)
        if self.projection == "surface":
            normal = normalize(normal)
            u = normalize(tuple(x-dot(u,normal)*n for x,n in zip(u,normal)))
            # Preserve world-facing orientation while making the axes tangent
            # and orthonormal, so slopes have the requested physical density.
            v = tuple(x-dot(v,normal)*n-dot(v,u)*a for x,n,a in zip(v,normal,u))
            v = normalize(v)
        return u,v

    def map_face(self, face, library, axes=None, origin=None, distance=0):
        texture = library[self.texture]
        su,sv = self.scales(texture)
        u,v = axes or self.axes(face.normal)
        anchor = self.anchor if origin is None else origin
        uoff = self.phase[0]*texture["width"]-dot(u,anchor)/su+distance/su
        voff = self.phase[1]*texture["height"]-dot(v,anchor)/sv
        return replace(face,texture=self.texture,material=self,scale=su,vscale=sv,
                       uaxis=u,vaxis=v,uoff=uoff,voff=voff)

    def metadata(self, library):
        texture = library[self.texture]
        return {**asdict(self),"width":texture["width"],"height":texture["height"],
                "scales":list(self.scales(texture))}


@dataclass(frozen=True)
class WallRun:
    material: Material
    path: tuple
    z_anchor: float = 0
    start: float = 0

    def __post_init__(self):
        if not isinstance(self.material,Material):
            raise ValueError("A wall run requires a Material")
        object.__setattr__(self,"path",tuple(finite_tuple(p,2,"Wall path point") for p in self.path))
        if len(self.path) < 2 or not all(isfinite(x) for x in (self.z_anchor,self.start)):
            raise ValueError("Wall run needs at least two points and finite offsets")
        if any(a==b for a,b in zip(self.path,self.path[1:])):
            raise ValueError("Wall path contains a zero-length segment")

    def segment(self, vertices, normal):
        """Match one complete vertical face to a declared path segment."""
        if abs(normalize(normal)[2]) > 1e-5:
            return None
        distance = self.start
        for a,b in zip(self.path,self.path[1:]):
            delta = vector(b,a)
            length = sqrt(dot(delta,delta))
            tangent = (delta[0]/length,delta[1]/length,0)
            local = [vector(p,(a[0],a[1],0)) for p in vertices]
            positions = [dot(p,tangent) for p in local]
            if (vertices and all(abs(p[0]*tangent[1]-p[1]*tangent[0]) < 1e-4 for p in local)
                    and min(positions)>=-1e-4 and max(positions)<=length+1e-4
                    and max(positions)-min(positions)>1e-4):
                return tangent,(a[0],a[1],self.z_anchor),distance
            distance += length
        return None

    def map_face(self, face, vertices, library):
        matched = self.segment(vertices,face.normal)
        if matched is None:
            return None
        tangent,origin,distance = matched
        return self.material.map_face(face,library,(tangent,(0,0,-1)),origin,distance)

    def metadata(self):
        return {"texture":self.material.texture,"path":[list(p) for p in self.path],
                "z_anchor":self.z_anchor,"start":self.start}
