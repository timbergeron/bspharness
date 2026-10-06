"""Reference-directed stone profiles; the recovered brush shell stays explicit.

Only edges with exposed faces on both sides are eased. Cuts remove stone,
so the rebuilt player hull follows the visible shape. Shared wall joints,
sky, liquids, clips, triggers and small grate bars are left alone.
"""

from itertools import combinations, product
from math import cos, floor, pi, sin

from bspharness import Material
from bspharness.geometry import Brush, Face, cross, dot, normalize, vector

STONE = {"aw_stone", "aw_trim", "aw_pave"}


class Solids:
    """A small spatial index of the immutable, recovered opaque world."""
    def __init__(self, brushes):
        self.cells = {}
        for b in brushes:
            lo = tuple(min(p[i] for p in b.vertices) for i in range(3))
            hi = tuple(max(p[i] for p in b.vertices) for i in range(3))
            planes = [(normalize(f.normal), dot(normalize(f.normal), f.points[1])) for f in b.faces]
            record = (lo, hi, planes, all(f.texture in STONE for f in b.faces))
            for cell in product(*(range(floor(a/128), floor(z/128)+1) for a,z in zip(lo,hi))):
                self.cells.setdefault(cell, []).append(record)

    def occupied(self, p):
        return any(all(a-0.001 <= x <= b+0.001 for a,x,b in zip(lo,p,hi)) and
                   all(dot(n,p)-d <= 0.001 for n,d in planes)
                   for lo,hi,planes,_ in self.cells.get(tuple(floor(x/128) for x in p), ()))

    def continues(self, p, normals, distances, rounded, radius, walking):
        for lo,hi,planes,eligible in self.cells.get(tuple(floor(x/128) for x in p), ()):
            size=tuple(b-a for a,b in zip(lo,hi))
            smooth=abs(normals[0][2])+abs(normals[1][2]) < 0.001 and max(size[:2]) <= 64 and size[2] >= 128
            if (eligible and smooth==rounded and
                    abs(min(2 if walking else 8,min(size)*0.2)-radius)<0.0001 and
                    all(a-0.001 <= x <= b+0.001 for a,x,b in zip(lo,p,hi)) and
                    all(dot(n,p)-d <= 0.001 for n,d in planes) and
                    all(any(dot(n,q)>0.99999 and abs(d-e)<0.001 for q,e in planes)
                        for n,d in zip(normals,distances))):
                return True
        return False


def plane(n, p, material):
    """An outward cutting plane, independent of its defining triangle size."""
    u = normalize(cross(n, (0,0,1) if abs(n[2]) < 0.9 else (0,1,0)))
    v = cross(n,u)
    # Face.normal uses cross(a-b,c-b), rather than the usual (b-a,c-a).
    return Face((tuple(p[i]+u[i]*64 for i in range(3)), p,
                 tuple(p[i]+v[i]*64 for i in range(3))), material)


def ease(brush, world):
    if any(f.texture not in STONE for f in brush.faces):
        return brush, []
    lo = tuple(min(p[i] for p in brush.vertices) for i in range(3))
    hi = tuple(max(p[i] for p in brush.vertices) for i in range(3))
    size = tuple(b-a for a,b in zip(lo,hi))
    if min(size) < 8:
        return brush, []
    cuts, records = [], []
    trim = Material("aw_trim", repeat=(128,128))
    for a,b in combinations(brush.faces,2):
        na,nb = normalize(a.normal),normalize(b.normal)
        if abs(dot(na,nb)) > 0.001:
            continue
        edge = [p for p in brush.vertices if
                abs(dot(na,vector(p,a.points[1]))) < 0.001 and
                abs(dot(nb,vector(p,b.points[1]))) < 0.001]
        if len(edge) != 2:
            continue
        start,end = edge
        length = sum((x-y)**2 for x,y in zip(start,end))**0.5
        if length < 24 or not all(400 < p[0] < 2800 and 400 < p[1] < 2300 and
                                  -760 <= p[2] <= -160 for p in edge):
            continue
        # Small radii on treads and walking ledges retain the landing width.
        walking = any(n[2] > 0.99 for n in (na,nb))
        radius = min(2 if walking else 8, min(size)*0.2)
        rounded = abs(na[2])+abs(nb[2]) < 0.001 and max(size[:2]) <= 64 and size[2] >= 128
        if radius < 1.5:
            continue
        # Both faces must be exposed along the entire edge, not just its middle.
        # Keep every shared structural joint intact.
        exposed = True
        for t in (0.04,0.15,0.35,0.5,0.65,0.85,0.96):
            p = tuple(x+(y-x)*t for x,y in zip(start,end))
            for n,other in ((na,nb),(nb,na)):
                q = tuple(p[i]+n[i]*1.5-other[i]*(radius+1) for i in range(3))
                if world.occupied(q):
                    exposed = False
                    break
            if not exposed:
                break
        if not exposed:
            continue
        # A cut plane spans the entire brush. If either end meets another
        # solid, easing this edge would also nick that architectural joint.
        direction = tuple((y-x)/length for x,y in zip(start,end))
        protected=False
        for p,sign in ((start,-1),(end,1)):
            inner=tuple(p[i]+sign*direction[i]*0.5-(na[i]+nb[i])*radius*0.35 for i in range(3))
            outer=tuple(p[i]+sign*direction[i]*0.5+(na[i]+nb[i])*radius*0.35 for i in range(3))
            if (world.occupied(inner) and not world.occupied(outer) and
                    not world.continues(inner,(na,nb),(dot(na,start),dot(nb,start)),rounded,radius,walking)):
                protected=True
                break
        if protected:
            continue
        # Broad masonry uses a crisp chamfer like the angular QC frames.
        # Slender upright supports get four facets for a gentler silhouette.
        angles = (pi/8,pi/4,3*pi/8) if rounded else (pi/4,)
        center = tuple(start[i]-radius*(na[i]+nb[i]) for i in range(3))
        for theta in angles:
            n = tuple(na[i]*cos(theta)+nb[i]*sin(theta) for i in range(3))
            p = tuple(center[i]+radius*n[i] if rounded else
                      start[i]-radius*(na[i]+nb[i])/2 for i in range(3))
            cuts.append(plane(n,p,trim))
        records.append({"start":start,"end":end,"size":radius,
                        "profile":"quarter-round" if rounded else "chamfer",
                        "cut_planes":len(angles)})
    if not cuts:
        return brush, []
    refined = Brush.from_planes((*brush.faces,*cuts))
    # Removing an existing plane completely makes qbsp report a redundant
    # plane. Drop it, but never relax any surviving boundary.
    refined = Brush.from_planes(f for f in refined.faces if len(refined.face_vertices(f)) >= 3)
    return refined, records


def cornice(brush, world):
    """Cut a continuous cyma-like band into exposed upper stone beams.

    Convex horizontal slices retain the original rear volume and roof seal.
    The profile is entirely inside the reference solid, with an 8-unit lip,
    a recessed fascia and a small lower reveal.
    """
    if len(brush.faces) != 6 or any(max(abs(v) for v in normalize(f.normal)) < 0.99999
                                  for f in brush.faces):
        return (brush,), []
    lo = tuple(min(p[i] for p in brush.vertices) for i in range(3))
    hi = tuple(max(p[i] for p in brush.vertices) for i in range(3))
    height = hi[2]-lo[2]
    if not 96 <= height <= 160:
        return (brush,), []
    selected = []
    for face in brush.faces:
        n = normalize(face.normal)
        if abs(n[2]) > 0.001:
            continue
        axis = 0 if abs(n[0]) > 0.99 else 1
        across = 1-axis
        if hi[across]-lo[across] < 128 or hi[axis]-lo[axis] < 24:
            continue
        if all(not world.occupied(tuple(face.points[1][i]+n[i]*1.5 if i==axis else
                                        lo[i]+(hi[i]-lo[i])*t if i==across else
                                        lo[2]+height*z for i in range(3)))
               for t in (0.04,0.2,0.4,0.6,0.8,0.96) for z in (0.04,0.2,0.5,0.8,0.96)):
            selected.append((face,n))
    if not selected:
        return (brush,), []
    profile = ((0,8),(8,0),(20,0),(26,6),(42,6),(46,2),
               (height-24,2),(height-20,0),(height-8,0),(height,8))
    trim = Material("aw_trim",repeat=(128,128))
    result = []
    for (z0,d0),(z1,d1) in zip(profile,profile[1:]):
        low,high = lo[2]+z0,lo[2]+z1
        faces = list(brush.faces)
        faces.extend((plane((0,0,-1),(0,0,low),trim),plane((0,0,1),(0,0,high),trim)))
        for face,n in selected:
            slope = (d1-d0)/(high-low)
            normal = normalize((n[0],n[1],slope))
            p = tuple(face.points[1][i]-n[i]*d0 if i!=2 else low for i in range(3))
            faces.append(plane(normal,p,trim))
        # Co-planar cap/outer planes are replaced, not duplicated.
        unique = {}
        for f in faces:
            n = normalize(f.normal);key = tuple(round(x,6) for x in n)
            distance = dot(n,f.points[1])
            if key not in unique or distance < dot(n,unique[key].points[1])+0.00001:
                unique[key] = f
        piece = Brush.from_planes(unique.values())
        result.append(Brush.from_planes(f for f in piece.faces if len(piece.face_vertices(f)) >= 3))
    return tuple(result), [{"normal":n,"profile":profile} for _,n in selected]


def profiles(arena, solids, cornices=()):
    world = Solids(solids)
    records, bands = [], []
    original = set(solids)
    headers = set(cornices)
    def refine(b):
        if b not in original:
            return (b,)
        pieces, band = cornice(b,world) if b in headers else ((b,), [])
        if band:
            bands.append({"center":b.interior,"faces":band,"slices":len(pieces)})
            # Only a simple rear core participates in visibility and sealing.
            # The exact shaped foreground remains solid compiler wall detail.
            trim=Material("aw_trim",repeat=(128,128))
            cuts=[plane(tuple(n),tuple(f.points[1][i]-n[i]*8 for i in range(3)),trim)
                  for f in b.faces for n in [normalize(f.normal)]
                  if any(dot(n,record["normal"])>0.99999 for record in band)]
            # Replace the original exposed planes with the inset core planes.
            faces=[f for f in b.faces if not any(dot(normalize(f.normal),normalize(c.normal))>0.99999
                                               for c in cuts)]
            core=Brush.from_planes((*faces,*cuts))
            arena.detail(*pieces,mode="wall",_phong_angle="30",_phong_angle_concave="1")
            return (core,)
        result = []
        for piece in pieces:
            replacement, edges = ease(piece,world)
            if edges:
                records.append({"center":piece.interior,"edges":edges})
            result.append(replacement)
        return tuple(result)
    arena.details = [piece for b in arena.details for piece in refine(b)]
    arena.entities = [(keys,tuple(piece for b in brushes for piece in refine(b)) if
                       keys["classname"] in ("func_detail", "func_detail_wall") else brushes)
                      for keys,brushes in arena.entities]
    return {"eased_brushes":len(records),"eased_edges":sum(len(r["edges"]) for r in records),
            "edge_records":records,"profiled_cornices":len(bands),"cornice_records":bands}
