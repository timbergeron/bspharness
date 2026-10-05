# Material scale, alignment, and transitions

The harness maps materials using real WAD dimensions, wraps declared wall
paths around corners, generates doorway/floor borders, and checks the final
BSP's texture coordinates. These tools support deliberate material joins;
the texture artwork and final appearance still need review in Quake.

## Try the diagnostic map

```sh
python3 tools/bootstrap.py
python3 examples/materials.py
python3 -m bspharness build src/materials_demo.map --profile final
python3 -m bspharness seams out/materials_demo/final/materials_demo.bsp
```

[The generator](../examples/materials.py) creates original diagnostic
textures locally: matching 64px/128px floor patterns, brick walls, and
utility trim. It also writes three engine cameras. It requires no downloaded
textures. Use the QA procedure in [WORKFLOW.md](WORKFLOW.md) to view it.

## Choose physical scale

`Palette` roles and brush texture arguments accept either texture names or
`Material` objects. Names retain the existing `Palette.scale` behavior;
each `Material` supplies its own mapping and overrides that scale.

```python
from bspharness import Material, Palette

brick = Material("warmbrick", density=0.5)
palette = Palette(wall=brick)
```

`density` means texture pixels per world unit. `0.5` maps one pixel to two
Quake units. At that density a 64px image repeats every 128 units, while a
128px image repeats every 256 units. This preserves pixel size, which may
change the apparent size of motifs in differently sized images.

Use `repeat=(width, height)` for images whose entire pattern should occupy
the same physical area, including rectangular textures:

```python
small = Material("tile64", repeat=(128, 128),
                 anchor=(64, 32, 0), family="floor_tiles")
large = Material("tile128", repeat=(128, 128),
                 anchor=(64, 32, 0), family="floor_tiles")
```

These two images each repeat over 128x128 units. The exporter derives
independent U/V scales from their WAD widths and heights. Choose density or
repeat; supplying both is rejected. Neither defaults to a resolution-aware
repeat: a bare `Material("name")` uses one pixel per world unit.

The pinned modern and stable ericw compilers resolve duplicate texture
names from the **last WAD** in worldspawn's list. `TextureLibrary` follows
that order. Compiled dimensions must match the material contract, so custom
compiler behavior or a changed WAD cannot silently alter physical scale.

## Anchor related patterns

`anchor=(x,y,z)` defines the shared world position of a pattern's origin.
`phase=(u,v)` shifts that origin in fractions of the image's repeat: a phase
of `(0.25,0.5)` places the anchor one quarter of a repeat across and halfway
down. A shared anchor, phase, projection, and repeat align adjoining
coplanar faces even if the compiler splits them into many polygons.

Use a shared `family` only when different texture images have compatible
artwork in normalized UV space, such as the same tile pattern at different
resolutions. The checker treats them as related and checks their normalized
coordinates. Family declarations apply by texture name, so one name must
not belong to conflicting families. The harness does not infer compatible
colors, mortar lines, trim heights, or edge artwork from filenames.

`projection="world"` uses the existing dominant world axes. For sloped
faces, `projection="surface"` creates tangent, orthonormal axes to preserve
the requested density along the surface. Tangent projection alone does not
define continuous mapping across arbitrary angled surfaces.

## Wrap vertical walls

Declare a 2D path along the actual wall faces. U follows cumulative distance
along the path; V follows height. The following run follows a rectangular
room's inner perimeter:

```python
arena.wall_run(brick, [(-384, -256), (384, -256),
                      (384, 256), (-384, 256), (-384, -256)],
               z_anchor=0, start=0)
```

Path direction controls horizontal texture direction. `start` is an initial
distance in world units; `z_anchor` defaults to the material anchor's Z.
Material phase still applies, while the path supplies the horizontal
origin. A closed path needs a perimeter that closes on an integer repeat
if the closing corner is to be seamless. Use intentional trim where a
pattern cannot close cleanly.

Only vertical faces with the same texture name, lying fully within one
path segment, are wrapped. Segments may pass across openings without
creating new walls. A run that matches no source faces fails export, and
overlapping matching runs are rejected. Partially covered faces retain
their ordinary mapping; review the seam report's unchecked wall corners.
The path does not automatically wrap slopes, floors, ceilings, or trim.

## Put trim between different materials

Adjoining room air volumes create openings. A rule can frame openings
where the rooms' wall or floor textures match a chosen pair:

```python
from bspharness import TransitionRule

trim = Material("bh_trim", repeat=(64, 64))
arena.transition_rule(TransitionRule((warm, cool), trim,
                                     width=16, depth=8))
```

Rules add two jamb brushes and a header. `width` sets jamb/header thickness;
`depth` sets frame thickness across the opening plane. The default floor
threshold is a strip `width` units across the opening plane, retextured
from the existing floor. It adds no raised slab or coplanar overlay.

An explicit room transition takes precedence over automatic matching:

```python
arena.transition("west", "east", trim, width=16, depth=8,
                 frame=True, threshold=False)
```

Transitions require room boxes that share a vertical X/Y opening. Framed
openings must retain at least 96 units of width and 128 units of height.
Thresholds require equal floor heights; use `threshold=False` for steps.
Trim cannot extend past its room volumes, and overlapping floor strips
with different trim textures are rejected. Conflicting automatic rules
require an explicit room transition. Arbitrary overlaps, slopes, stairs,
and curved room connections need authored geometry.

Trim contacts declare intentional material boundaries. Their texture pairs
are exempt from the generic boundary warning throughout that map; this is
a texture-pair declaration, not a geometric proof that every contact has
trim. UV checks between related textures continue to run.

## Check the compiled joins

Material maps write a `.materials.json` contract beside the `.map`, bound
to its source SHA-256. Builds automatically audit these maps and fail on
seam errors. Regenerate both files after changing the generator; editing
only the MAP leaves stale metadata and fails the next build.

The audit uses final BSP polygons, image dimensions, and texinfo, including
partial shared edges at T-junctions. It checks:

- Related coplanar faces: matching phase along the entire edge and equal
  physical repeat density in both UV directions.
- Declared wall wraps: matching phase along the corner edge.
- Material dimensions: the compiled images match the export's WAD lookup.

Whole-repeat offsets are equivalent. Comparing edge frequency as well as
endpoint phase catches reversed or mismatched frequencies that happen to
agree at both endpoints. Different coplanar images without a family or a
declared trim pair produce review warnings. Errors fail strict builds;
warnings remain visible in `seams.json`.

Legacy string-only maps retain their build behavior. Opt into checks with
`build --check-seams`, or inspect an existing BSP independently:

```sh
python3 -m bspharness seams /path/to/map.bsp --output out/seam-review.json
python3 -m bspharness seams /path/to/map.bsp \
  --materials /path/to/map.materials.json
```

The standalone command discovers a sidecar beside the BSP. An explicitly
requested missing contract is an error. For independent BSPs, a supplied
contract expresses the intended family/path rules; build-time source hashes
provide the stronger source binding. `Map.write(..., check_seams=False)`
keeps the contract/report but permits seam errors during exploration;
`build --check-seams` always enforces the errors.

Successful builds hash the contract and seam report. Verification and ZIP
packaging reject modified evidence and include both files in the package.
Sky, liquids, and tool textures are excluded from shared-edge UV checking;
separate brush models are not compared against one another.

## Review appearance in Quake

The report counts checked edges, checked wrapped edges, and undeclared wall
corners. A passing report does not mean every corner was checked. Review
the screenshots for actual artwork joins, filtering, lighting seams,
deliberate trim corners, and z-fighting, then test movement through the
openings. This system does not blend unrelated images, author transition
artwork, enforce a universal material palette, or prove gameplay quality.
