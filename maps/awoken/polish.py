"""Small carved reliefs attached to recovered wall faces, without collision."""

from math import sqrt

from bspharness import Material
from bspharness.geometry import Brush, Face, dot, normalize, vector


def carvings(arena, solids, limit=12):
    planes = [[(normalize(f.normal), f.points[1]) for f in b.faces] for b in solids]
    def buried(p):
        return any(all(dot(n, vector(p, o)) < -0.01 for n, o in faces) for faces in planes)
    candidates = []
    for brush, boundary in zip(solids, planes):
        for face in brush.faces:
            if face.texture != "aw_stone":
                continue
            n = normalize(face.normal)
            if abs(n[2]) > 1e-6 or max(abs(n[0]), abs(n[1])) < 0.999:
                continue
            verts = brush.face_vertices(face)
            axis = 0 if abs(n[0]) > 0.99 else 1
            across = 1-axis
            lo = [min(p[i] for p in verts) for i in range(3)]
            hi = [max(p[i] for p in verts) for i in range(3)]
            if hi[across]-lo[across] < 160 or hi[2]-lo[2] < 176:
                continue
            p = tuple((a+b)/2 for a,b in zip(lo,hi))
            if not (600 < p[0] < 2350 and 700 < p[1] < 2150 and -660 < p[2] < -320):
                continue
            corners = [tuple(p[i]+(u if i==across else v if i==2 else 0)
                             for i in range(3)) for u in (-36,36) for v in (-68,68)]
            if any(any(dot(q,vector(c,o)) > 1e-5 for q,o in boundary) or
                   buried(tuple(c[i]+n[i]*8 for i in range(3))) for c in corners):
                continue
            candidates.append((sum((p[i]-t)**2 for i,t in enumerate((1408,1500,-480))),p,n,axis,across))
    placed = []
    for _,p,n,axis,across in sorted(candidates):
        if any(sqrt(sum((a-b)**2 for a,b in zip(p,q))) < 192 for q in placed):
            continue
        def ring(depth,width,height):
            return [tuple(p[i]+(n[i]*depth if i==axis else u if i==across else v)
                          for i in range(3)) for u,v in ((-width,-height),(width,-height),
                                                        (width,height),(-width,height))]
        back,front = ring(-0.5,36,68),ring(4,32,64)
        anchor = list(p);anchor[across]-=32;anchor[2]+=64
        panel = Material("aw_panel",repeat=(64,128),anchor=tuple(anchor))
        trim = Material("aw_trim",repeat=(128,128))
        faces = [Face(tuple(back[:3]),trim),Face(tuple(front[:3]),panel)]
        faces.extend(Face((back[i],back[(i+1)%4],front[(i+1)%4]),trim) for i in range(4))
        arena.detail(Brush(faces,tuple(p[i]+n[i]*1.75 for i in range(3))),
                     mode="illusionary",_shadow="1")
        placed.append(p)
        if len(placed) == limit:
            break
    return placed
