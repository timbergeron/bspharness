# Architectural kits and geometry roles

Build a sealed layout and test its walking surfaces before adding ornament.
Kits return ordinary convex brushes; dimensions, materials, and compiler
roles stay inspectable in the generated Valve 220 MAP.

## Choose the geometry role

| Call | Compiler behavior | Typical use |
| --- | --- | --- |
| `arena.structural(*brushes)` | World solids; sealing and visibility | Floors, stairs, landings, major partitions |
| `arena.detail(*brushes)` | Solid `func_detail` | Columns, arches, substantial decoration |
| `arena.detail(*brushes, mode="wall")` | Solid `func_detail_wall`; avoids splitting underlying world faces | Molding, beams, light housings |
| `arena.detail(*brushes, mode="fence")` | Solid `func_detail_fence`; preserves world faces behind it | Grates and fence textures |
| `arena.detail(*brushes, mode="illusionary")` | `func_detail_illusionary`; no collision | Hanging wires and small decoration |

Detail cannot seal the map. The room union supplies the outer shell;
structural partitions control visibility. Illusionary detail casts shadows
when requested with `_shadow="1"`. Fence brushes block gunfire through
transparent pixels. Compiler detail merges into the world instead of
spawning game entities. See the
[ericw detail documentation](https://ericw-tools.readthedocs.io/en/latest/qbsp.html#detail-brush-support).

**Version 0.3 migration:** `Map.detail` previously emitted structural world
brushes. It now defaults to `func_detail`. Replace old calls with
`Map.structural`, or use `mode="structural"`, to retain their previous
sealing and visibility behavior. The atrium's ramps and platform have been
migrated. String materials and material coordinates keep their behavior.

## Kit dimensions

```python
from bspharness import Map, Palette, arch, beam, column, stairs, trim_profile

arena = Map("Kit example")
palette = Palette()
arena.structural(*stairs((-256,64,0),width=128,rise=12,run=24,steps=8,
                         along="x",palette=palette))
arena.detail(*arch((0,0,0),width=192,spring=112,rise=80,
                   thickness=24,depth=32,segments=12,palette=palette))
arena.detail(*column((192,128,0),height=176,radius=24,palette=palette),
             _phong="1",_phong_angle="40")
arena.detail(*beam((-240,0,240),(240,0,240),width=24,height=16,
                   palette=palette),mode="wall")
arena.detail(*trim_profile((-240,240,192),(240,240,192),
                           widths=(16,24,20),heights=(8,8,8),palette=palette),
             mode="wall")
```

| Kit | Coordinate and material contract |
| --- | --- |
| `stairs` | Origin is the first tread's lower start corner. Runs along `x`, `-x`, `y`, or `-y`; width extends along the positive perpendicular axis. Rise/run are per step. Top elevation is `origin.z + steps*rise`. Treads use floor; sides use trim. |
| `arch` | Origin is the opening's center at floor level. Depth follows `axis="x"` or `"y"`; width follows the other horizontal axis. Spring is vertical opening height; rise adds the elliptical crown. Trim forms ring/jambs. Optional `wall_height` adds wall-colored spandrels. |
| `column` | Origin is the base center. Height includes shaft, plinth, capital, and plates. Wall forms the shaft; trim forms end details. |
| `beam` | Start/end are 3D center points. Width/height describe the local cross-section. Uses ceiling. |
| `trim_profile` | Start/end are a horizontal bottom centerline. Widths/heights define successive layers. Uses trim. |

Stairs require width >=64, risers <=18, runs >=16, and 1..128 steps.
Those limits do not prove landing space, headroom, or clearance around other
solids; use engine movement probes. Arches consist of straight convex
wedges. Keep segment counts modest and review their slope/corner mapping.
`Material` anchors and repeats work on all kits.

## Fixture lighting

```python
from bspharness import fixture, lighting_recipe

arena = Map("Light example",**lighting_recipe(
    sun=180,sky=70,minlight=6,bounce=1,dirt=0.5))
fixture(arena,(-32,240,144),(32,248,184),face="south",
        intensity=260,color=(255,210,150),offset=16)
```

`fixture` builds a recessed housing, a plate with one emitting texture face,
and a point light outside it. Faces are east, west, north, south, top, and
bottom. Default inset is 4 units; housing depth must exceed 2 units and light
offset must be at least 4. The housing uses solid wall detail. Choose your
palette's housing/emitter textures and size the emitter's `Material.repeat`
and anchor to fit its panel, as the reference hall does.

`lighting_recipe` sets sun, upper sky light, bounce, colored bounce, ambient
occlusion, and minimum light. Daylight needs a sky opening. Recipe values
and fixture brightness are starting points for camera review. The emitting
face marks a source; it is not a calibrated surface-light simulation.
Additional fixture keyword keys select falloff and other compiler settings.
See [ericw lighting](https://ericw-tools.readthedocs.io/en/latest/light.html).

## Budget the compiled result

```sh
python3 -m bspharness build src/reference_hall.map --profile final \
  --max-faces 3500 --max-clipnodes 5000
```

Build/validation reports record faces, nodes, clipnodes, leaves, models,
VIS/light/texture bytes, and total BSP bytes. The CLI exposes face and
clipnode limits; Python `build(..., budgets={...})` accepts every recorded
metric name. An exceeded limit fails validation and prevents packaging.
These project budgets supplement format validation and the existing 2x
reference clipnode-growth check. Review them as the layout grows.
`bspharness.collision.Hull.contents(point)` queries a compiled player hull
for collision debugging; it does not solve movement or connectivity.
