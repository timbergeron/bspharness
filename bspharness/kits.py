"""Small architectural kits with shared material roles and explicit dimensions."""

from math import cos, isfinite, pi, sin

from .geometry import Brush, Face, box, cross, normalize, vector
from .mapfile import Palette


def positive(**values):
    if any(not isfinite(v) or v<=0 for v in values.values()):
        raise ValueError("Kit dimensions must be positive and finite: "+", ".join(values))


def prism(polygon, low, high, axis, texture, top=None):
    """Extrude a convex 2D cross-section along one world axis."""
    if len(polygon)<3 or not isfinite(low) or not isfinite(high) or high<=low:
        raise ValueError("Prism needs a convex polygon and positive depth")
    other = [i for i in range(3) if i!=axis]
    def point(p, depth):
        result = [0,0,0]
        result[axis] = depth
        result[other[0]],result[other[1]] = p
        return tuple(result)
    a,b = [point(p,low) for p in polygon],[point(p,high) for p in polygon]
    center = tuple(sum(p[i] for p in a+b)/len(a+b) for i in range(3))
    faces = [Face(tuple(a[:3]),texture),Face(tuple(b[:3]),top or texture)]
    faces.extend(Face((a[i],a[(i+1)%len(a)],b[(i+1)%len(a)]),texture) for i in range(len(a)))
    return Brush(faces,center)


def stairs(origin, width=160, rise=12, run=24, steps=16, along="x", palette=None):
    """Solid treads; origin is the foot/start corner, rise and run are per step."""
    positive(width=width,rise=rise,run=run)
    if width<64 or rise>18 or run<16 or not isinstance(steps,int) or not 1<=steps<=128:
        raise ValueError("Walking stairs need width >=64, rise <=18, run >=16, and 1..128 steps")
    if along not in ("x","-x","y","-y"):
        raise ValueError("Stairs run along x, -x, y, or -y")
    palette = palette or Palette()
    axis = 0 if along.endswith("x") else 1
    across,sign = 1-axis,-1 if along.startswith("-") else 1
    result = []
    for step in range(steps):
        lo,hi = list(origin),list(origin)
        ends = (origin[axis]+sign*step*run,origin[axis]+sign*(step+1)*run)
        lo[axis],hi[axis] = min(ends),max(ends)
        hi[across] += width
        hi[2] += (step+1)*rise
        result.append(box(*lo,*hi,texture=palette.trim,top=palette.floor))
    return tuple(result)


def arch(origin, width=256, spring=128, rise=None, thickness=24, depth=32,
         segments=12, axis="y", palette=None, jambs=True, wall_height=None):
    """An elliptical opening: two jambs and convex ring voussoirs."""
    rise = width/2 if rise is None else rise
    positive(width=width,spring=spring,rise=rise,thickness=thickness,depth=depth)
    if wall_height is not None and (not isfinite(wall_height) or wall_height<=spring+rise+thickness):
        raise ValueError("Arch wall height must be above its outer crown")
    if width<96 or spring<64 or not isinstance(segments,int) or not 4<=segments<=32:
        raise ValueError("Arch needs width >=96, spring >=64, and 4..32 segments")
    if axis not in ("x","y"):
        raise ValueError("Arch depth axis must be x or y")
    palette = palette or Palette()
    extrude_axis = 0 if axis=="x" else 1
    across = 1-extrude_axis
    center,floor = origin[across],origin[2]
    lo,hi = origin[extrude_axis]-depth/2,origin[extrude_axis]+depth/2
    radius = width/2
    result = []
    for side in ((-1,1) if jambs else ()):
        x0,x1 = sorted((center+side*radius,center+side*(radius+thickness)))
        polygon = ((x0,floor),(x1,floor),(x1,floor+spring),(x0,floor+spring))
        result.append(prism(polygon,lo,hi,extrude_axis,palette.trim))
    for i in range(segments):
        a,b = i*pi/segments,(i+1)*pi/segments
        def ring(theta, outer):
            return (center+(radius+outer*thickness)*cos(theta),
                    floor+spring+(rise+outer*thickness)*sin(theta))
        result.append(prism((ring(a,0),ring(a,1),ring(b,1),ring(b,0)),lo,hi,extrude_axis,palette.trim))
        if wall_height is not None:
            p,q = ring(a,1),ring(b,1)
            result.append(prism((p,q,(q[0],floor+wall_height),(p[0],floor+wall_height)),
                                lo,hi,extrude_axis,palette.wall))
    return tuple(result)


def column(origin, height=176, radius=24, sides=8, band=16, palette=None):
    """Faceted shaft, wider plinth/capital, and narrow square end plates."""
    positive(height=height,radius=radius,band=band)
    if height<=4*band or not isinstance(sides,int) or not 6<=sides<=24:
        raise ValueError("Column needs height >4*band and 6..24 sides")
    palette = palette or Palette()
    x,y,z = origin
    def ring(r,low,high,texture):
        polygon = tuple((x+r*cos(2*pi*i/sides+pi/sides),y+r*sin(2*pi*i/sides+pi/sides))
                        for i in range(sides))
        return prism(polygon,z+low,z+high,2,texture)
    outer = radius+8
    return (box(x-outer,y-outer,z,x+outer,y+outer,z+band/2,texture=palette.trim),
            ring(outer,band/2,band,palette.trim),
            ring(radius,band,height-band,palette.wall),
            ring(outer,height-band,height-band/2,palette.trim),
            box(x-outer,y-outer,z+height-band/2,x+outer,y+outer,z+height,texture=palette.trim))


def beam(start, end, width=24, height=24, palette=None):
    """A rectangular beam between 3D center points; width/height are local."""
    positive(width=width,height=height)
    palette = palette or Palette()
    direction = normalize(vector(end,start))
    reference = (0,0,1) if abs(direction[2])<0.99 else (0,1,0)
    u = normalize(cross(direction,reference))
    v = normalize(cross(direction,u))
    corners = []
    for p in (start,end):
        corners.append([tuple(p[i]+su*u[i]*width/2+sv*v[i]*height/2 for i in range(3))
                        for su,sv in ((-1,-1),(1,-1),(1,1),(-1,1))])
    a,b = corners
    faces = [Face(tuple(a[:3]),palette.ceiling),Face(tuple(b[:3]),palette.ceiling)]
    faces.extend(Face((a[i],a[(i+1)%4],b[(i+1)%4]),palette.ceiling) for i in range(4))
    return (Brush(faces,tuple((x+y)/2 for x,y in zip(start,end))),)


def trim_profile(start, end, widths=(16,24,20), heights=(8,8,8), palette=None):
    """Layered horizontal molding; start/end define the bottom center line."""
    if len(widths)!=len(heights) or not widths or abs(start[2]-end[2])>1e-6:
        raise ValueError("Trim needs matching profile layers and a horizontal run")
    palette = palette or Palette()
    result,offset = [],0
    # Beam's ceiling role becomes the molding's trim role.
    material_palette = Palette(ceiling=palette.trim)
    for width,height in zip(widths,heights):
        positive(width=width,height=height)
        a,b = [list(p) for p in (start,end)]
        a[2] += offset+height/2
        b[2] += offset+height/2
        result.extend(beam(a,b,width,height,material_palette))
        offset += height
    return tuple(result)
