"""Visible fixture lights and a restrained daylight/bounce starting recipe."""

from math import isfinite

from .geometry import Bounds, box, number


def lighting_recipe(sun=180, sky=70, minlight=6, bounce=1, dirt=0.5,
                    sun_angles=(35,-55,0), sun_color=(255,222,185), sky_color=(165,195,235)):
    """Worldspawn keys; brightness values are starting points for camera review."""
    if any(not isfinite(x) or x<0 for x in (sun,sky,minlight,bounce,dirt)):
        raise ValueError("Lighting values must be finite and nonnegative")
    if not isinstance(bounce,int) or bounce>8:
        raise ValueError("Bounce count must be an integer from 0 to 8")
    if any(len(value)!=3 for value in (sun_angles,sun_color,sky_color)):
        raise ValueError("Sun angles and lighting colors need three coordinates")
    if any(not isfinite(x) for x in sun_angles) or any(not isfinite(x) or not 0<=x<=255
                                                    for color in (sun_color,sky_color) for x in color):
        raise ValueError("Sun angles must be finite and lighting colors must be RGB in 0..255")
    return {"_sunlight":number(sun),"_sunlight2":number(sky),"_minlight":number(minlight),
            "_bounce":number(bounce),"_bouncecolorscale":"1","_dirt":"1" if dirt else "-1",
            "_dirtscale":number(dirt),"_dirtdepth":"96",
            "_sun_mangle":" ".join(map(number,sun_angles)),
            "_sunlight_color":" ".join(map(number,sun_color)),
            "_sunlight2_color":" ".join(map(number,sky_color))}


def fixture(arena, mins, maxs, face="south", housing="bh_trim", emitter="bh_light",
            intensity=260, color=(255,210,150), inset=4, offset=12, **light_keys):
    """Recessed housing and a single emitting face with a light outside it."""
    bounds = Bounds(tuple(mins),tuple(maxs))
    if len(color)!=3 or any(not isfinite(x) or not 0<=x<=255 for x in color) or not isfinite(intensity) or intensity<=0:
        raise ValueError("Fixture needs positive intensity and an RGB color in 0..255")
    axes = {"east":(0,1),"west":(0,-1),"north":(1,1),"south":(1,-1),"top":(2,1),"bottom":(2,-1)}
    if face not in axes or not isfinite(inset) or inset<=0 or not isfinite(offset) or offset<4:
        raise ValueError("Fixture needs a known face, positive inset, and light offset >=4")
    axis,sign = axes[face]
    plane = bounds.maxs[axis] if sign>0 else bounds.mins[axis]
    lo,hi = list(mins),list(maxs)
    for i in range(3):
        if i!=axis:
            lo[i] += inset
            hi[i] -= inset
            if lo[i]>=hi[i]:
                raise ValueError("Fixture inset consumes the emitting face")
    # Place the housing behind the face rather than adding a coplanar decal.
    hlo,hhi = list(mins),list(maxs)
    if sign>0:
        hhi[axis] = plane-2
        lo[axis] = plane-2
    else:
        hlo[axis] = plane+2
        hi[axis] = plane+2
    if hlo[axis]>=hhi[axis]:
        raise ValueError("Fixture housing must be deeper than two units")
    plate = box(*lo,*hi,texture=housing,**{face:emitter})
    arena.detail(box(*hlo,*hhi,texture=housing),plate,mode="wall")
    origin = list(bounds.center)
    origin[axis] = plane+sign*offset
    # Linear falloff avoids the singular hotspot of a light almost touching
    # its own small face; callers can select other ericw falloff modes.
    return arena.light(tuple(origin),intensity,color,**{"delay":"0",**light_keys})
