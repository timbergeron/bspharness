"""Measure shared-edge UV continuity using compiled BSP face polygons."""

from collections import Counter, defaultdict
from dataclasses import dataclass
from math import isfinite, sqrt
import struct

from .geometry import dot, normalize, vector
from .materials import Material, WallRun


@dataclass(frozen=True)
class Surface:
    index: int
    model: int
    texture: str
    size: tuple
    normal: tuple
    vertices: tuple
    uv_rows: tuple

    def uv(self, point):
        return tuple(dot(row[:3],point)+row[3] for row in self.uv_rows)

    def density(self, normalized=False):
        values = []
        for row,size in zip(self.uv_rows,self.size):
            tangent = tuple(x-dot(row[:3],self.normal)*n for x,n in zip(row[:3],self.normal))
            values.append(sqrt(dot(tangent,tangent))/(size if normalized else 1))
        return tuple(values)


def bsp_surfaces(bsp):
    """Read each face's exact polygon, texture dimensions, and final texinfo."""
    extended = bsp.format!="bsp29"
    vertices = list(struct.iter_unpack("<3f",bsp.lump("vertices")))
    edges = list(struct.iter_unpack("<II" if extended else "<HH",bsp.lump("edges")))
    surfedges = [x[0] for x in struct.iter_unpack("<i",bsp.lump("surfedges"))]
    planes = list(struct.iter_unpack("<4fi",bsp.lump("planes")))
    texinfo = list(struct.iter_unpack("<8fii",bsp.lump("texinfo")))
    textures = bsp.lump("textures")
    count, = struct.unpack_from("<i",textures)
    offsets = struct.unpack_from(f"<{count}i",textures,4)
    slots = []
    for offset in offsets:
        if offset==-1:
            slots.append(None)
        else:
            raw,width,height = struct.unpack_from("<16sII",textures,offset)
            slots.append((raw.split(b"\0",1)[0].decode("ascii"),(width,height)))
    models = bsp.lump("models")
    faces = bsp.lump("faces")
    result = []
    for model in range(bsp.count("models")):
        first,total = struct.unpack_from("<ii",models,model*64+56)
        if first<0 or total<0 or first+total>bsp.count("faces"):
            raise ValueError("Invalid model face range")
        for index in range(first,first+total):
            plane,side,start,length,info = struct.unpack_from("<iiiii" if extended else "<HHiHH",faces,index*bsp.sizes["faces"])
            rows = texinfo[info]
            texture,size = slots[rows[8]]
            polygon = []
            for edge_index in surfedges[start:start+length]:
                edge = edges[abs(edge_index)]
                polygon.append(vertices[edge[0] if edge_index>=0 else edge[1]])
            normal = tuple((-1 if side else 1)*x for x in planes[plane][:3])
            if not all(isfinite(x) for p in polygon for x in p) or not all(isfinite(x) for x in rows[:8]):
                raise ValueError("Nonfinite vertex or texture mapping")
            result.append(Surface(index,model,texture,size,normalize(normal),tuple(polygon),(rows[:4],rows[4:8])))
    return result


def shared_edges(surfaces):
    """Group collinear intervals; partial overlaps include BSP T-junctions."""
    lines = defaultdict(list)
    for surface in surfaces:
        points = surface.vertices
        for a,b in zip(points,points[1:]+points[:1]):
            delta = vector(b,a)
            if dot(delta,delta)<1e-10:
                continue
            axis = normalize(delta)
            if next(x for x in axis if abs(x)>1e-8)<0:
                axis = tuple(-x for x in axis)
            origin = tuple(x-dot(a,axis)*u for x,u in zip(a,axis))
            key = (surface.model,tuple(round(x,5) for x in axis),tuple(round(x,4) for x in origin))
            lo,hi = sorted((dot(a,axis),dot(b,axis)))
            lines[key].append((lo,hi,surface,axis,origin))
    seen = set()
    for intervals in lines.values():
        intervals.sort(key=lambda item:item[0])
        for i,(lo,hi,a,axis,origin) in enumerate(intervals):
            for blo,bhi,b,_,_ in intervals[i+1:]:
                if blo>=hi-1e-5:
                    break
                if a.index==b.index:
                    continue
                start,end = max(lo,blo),min(hi,bhi)
                if end-start<1e-5:
                    continue
                p = tuple(x+start*u for x,u in zip(origin,axis))
                q = tuple(x+end*u for x,u in zip(origin,axis))
                pair = (min(a.index,b.index),max(a.index,b.index),tuple(round(x,4) for x in p),tuple(round(x,4) for x in q))
                if pair not in seen:
                    seen.add(pair)
                    yield a,b,p,q


def audit(surfaces, contract=None, pixel_tolerance=0.02):
    if not isfinite(pixel_tolerance) or pixel_tolerance<=0:
        raise ValueError("Seam tolerance must be positive pixels")
    contract = contract or {}
    if contract.get("schema",1)!=1:
        raise ValueError("Unsupported material contract schema")
    families = {}
    sizes = {}
    for material in contract.get("materials",[]):
        key = material["texture"].casefold()
        family = material.get("family")
        if "width" in material and "height" in material:
            sizes[key] = (material["width"],material["height"])
        if family:
            if key in families and families[key]!=family:
                raise ValueError(f"Ambiguous alignment family for {key}")
            families[key] = family
    allowed = {frozenset(t.casefold() for t in pair) for pair in contract.get("allowed_pairs",[])}
    runs = [WallRun(Material(r["texture"]),tuple(r["path"]),r["z_anchor"],r["start"])
            for r in contract.get("wall_runs",[])]
    usable = [s for s in surfaces if not s.texture.casefold().startswith(("sky","*"))
              and s.texture.casefold() not in ("trigger","clip","skip")]
    issues,checked,wrapped_edges,corners = [],0,0,0
    mismatched = {(s.texture,s.size,sizes[s.texture.casefold()]) for s in surfaces
                  if s.texture.casefold() in sizes and sizes[s.texture.casefold()]!=s.size}
    for texture,actual,expected in sorted(mismatched):
        issues.append({"severity":"error","kind":"texture_dimensions_mismatch","texture":texture,
                       "expected":list(expected),"actual":list(actual),
                       "message":"Compiled texture dimensions disagree with the material's WAD lookup"})
    for a,b,p,q in shared_edges(usable):
        ta,tb = a.texture.casefold(),b.texture.casefold()
        same = ta==tb
        related = same or (ta in families and families.get(ta)==families.get(tb))
        coplanar = dot(a.normal,b.normal)>1-1e-5
        wrapped = any(r.material.texture.casefold() in (ta,tb) and r.segment(a.vertices,a.normal)
                      and r.segment(b.vertices,b.normal) for r in runs)
        if not coplanar and not wrapped:
            if same and abs(a.normal[2])<1e-5 and abs(b.normal[2])<1e-5:
                corners += 1
            continue
        record = {"faces":[a.index,b.index],"textures":[a.texture,b.texture],
                  "edge":[list(p),list(q)]}
        if not related:
            if coplanar and frozenset((ta,tb)) not in allowed:
                issues.append({**record,"severity":"warning","kind":"material_boundary",
                               "message":"Different coplanar materials meet without a declared trim rule or alignment family"})
            continue
        checked += 1
        if wrapped and not coplanar:
            wrapped_edges += 1
        au,av = a.uv(p),a.uv(q)
        bu,bv = b.uv(p),b.uv(q)
        first = [x/asize-y/bsize for x,y,asize,bsize in zip(au,bu,a.size,b.size)]
        last = [x/asize-y/bsize for x,y,asize,bsize in zip(av,bv,a.size,b.size)]
        residual = max(abs(delta-round(delta))*max(asize,bsize) for delta,asize,bsize in zip(first,a.size,b.size))
        # An integer-cycle difference at the endpoints is insufficient:
        # opposite/mismatched frequencies can still diverge along the edge.
        drift = max(abs(end-start)*max(asize,bsize) for start,end,asize,bsize in zip(first,last,a.size,b.size))
        if residual>pixel_tolerance or drift>pixel_tolerance:
            issues.append({**record,"severity":"error","kind":"uv_discontinuity",
                           "phase_error_pixels":round(residual,6),"edge_drift_pixels":round(drift,6),
                           "message":"Related texture UVs disagree along a shared edge"})
        if coplanar:
            da,db = a.density(True),b.density(True)
            if any(abs(x-y)>1e-5*max(x,y,1e-6) for x,y in zip(da,db)):
                issues.append({**record,"severity":"error","kind":"repeat_density_mismatch",
                               "density_a":list(da),"density_b":list(db),
                               "message":"Related coplanar textures have different physical repeat sizes"})
    errors = [i for i in issues if i["severity"]=="error"]
    warnings = [i for i in issues if i["severity"]=="warning"]
    return {"schema":1,"passed":not errors,"checked_edges":checked,"checked_wrapped_edges":wrapped_edges,
            "unchecked_wall_corners":corners,
            "pixel_tolerance":pixel_tolerance,"counts":dict(Counter(i["kind"] for i in issues)),
            "errors":errors,"warnings":warnings,
            "scope":"Compiled shared-edge UV continuity; artwork compatibility and undeclared corners require visual review"}


def check_bsp(bsp, contract=None):
    validation = bsp.validate()
    if not validation["passed"]:
        raise ValueError("Validate BSP before seam analysis: "+"; ".join(validation["errors"]))
    return audit(bsp_surfaces(bsp),contract)
