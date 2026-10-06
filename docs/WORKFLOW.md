# Map workflow

## Generate and iterate

Keep authored generators in `examples/` or a tracked `maps/<name>/`
directory. Generated `.map` files in `src/` are rebuildable outputs. Describe
zones and routes first, compile a draft, and test movement before detail.

```sh
python3 examples/atrium.py
python3 -m bspharness build src/atrium.map --profile draft
```

The output is `out/atrium/draft/atrium.bsp`. Each compiler's exit status is
preserved; logs are not piped through filters that mask failures. A new run
invalidates the previous `build.json` before compilation. Failed runs keep
`failed-build.json` in their `run-*` directory and cannot be packaged as a
current successful build.

`qbsp -leaktest` must produce both the BSP and a nonempty PRT beside it.
VIS and light must produce nonempty lumps. Missing texture warnings fail the
build. Validation checks texture dimensions/mips, lump bounds, several
geometry references, entity census, and brush-model bounds. Showcase builds
must contain all four requested BSPX lighting lumps. This is a focused
validator, not a proof of every binary or gameplay property.

Generators using `Material`, wall runs, or transitions also write a
source-bound `.materials.json`. Regenerate it with the MAP after changes.
Builds audit final BSP texture coordinates and keep `seams.json`; strict
material builds fail on errors. Failed runs retain the report in their
`run-*` directory. Legacy maps can opt in with `--check-seams`. See
[MATERIALS.md](MATERIALS.md) for scale, anchors, corners, and trim rules.

## Compile an imported map

Preserve original sources/BSPs in a local reference directory. Patch a copy
in `src/`, recover embedded textures if needed, and preserve its original
format and lighting contract.

```sh
python3 -m bspharness extract-wad /path/to/original.bsp assets/wads/recovered.wad
python3 -m bspharness wad-info assets/wads/recovered.wad
python3 -m bspharness build src/patched.map --profile final --format bsp2 \
  --qbsp-dir tools/ericw/stable --reference /path/to/original.bsp
```

Update the copied map's worldspawn `wad` list with absolute forward-slash
paths. Put a validated recovered WAD last when old texture names have been
retired. Compiler warnings identify unresolved names. BSP2 stays BSP2;
monochrome maps use `--profile mono` unless a lighting upgrade is requested.

The earlier notes observed severe clipnode growth with the alpha compiler on
ornate detail-heavy maps. Stable qbsp can be selected independently while
modern VIS/light remain in use. A recompile exceeding 2x the reference's
clipnode count fails. Strict BSP29 builds reject more than 32767 clipnodes;
some extended engines tolerate more, but that is not the vanilla contract.

## Inspect materials and lighting

```sh
python3 -m bspharness wad-preview assets/wads/id1.wad \
  --palette assets/palette.lmp --output out/textures/id1
python3 -m bspharness inspect out/atrium/final/atrium.bsp
python3 -m bspharness seams out/materials_demo/final/materials_demo.bsp
```

Select materials from the contact sheet. Keep scale consistent within a
material family, use trim at transitions, and reserve accents for navigation
or important objects. Do lighting comparisons from the same camera list.
Showcase's finer luxels, lightgrid, and HDR cost extra bake time and require
a supporting engine; plain BSP lighting remains present as a fallback.

## Run engine QA

```sh
python3 -m bspharness qa out/atrium/final/atrium.bsp \
  --engine /path/to/QSS-M --basedir /path/to/quake \
  --cameras src/atrium.cameras.json --gamedir bspharness_qa_pass1
```

The gamedir must be new and cannot be `id1`. Its map copies, camera scripts,
screenshots, and reports remain separate from real mod maps. For complete
isolation from normal engine config/backups, create a writable test basedir
with an `id1/` directory and copies or **file symlinks** to your local PAKs;
do not symlink the entire read-only id1 directory.

QSS-M reads `configs/connect.cfg` after signon. That script executes
`shots.cfg`; putting a frame-wait chain into startup `+exec` can stall signon.
QA waits for the player to land, dumps edicts, and runs optional movement
probes before enabling god/noclip for screenshots. A fixed 1/72-second
step, `host_maxfps 72`, and 100-frame camera gaps make collection repeatable.
`host_timescale 0` lets QSS-M honor `host_framerate`; setting timescale to 1
would override the fixed step. QA pins stock gravity, maximum speed,
acceleration, friction, stop speed and edge friction, and records local PAK
hashes alongside the engine hash. Pass `--timeout 360` for a slow software
renderer. On Linux, a compatible SDL/Mesa setup may use
`SDL_VIDEODRIVER=offscreen LIBGL_ALWAYS_SOFTWARE=1 LP_NUM_THREADS=2`.

The stock SP audit checks a live player with full health and `FL_ONGROUND`,
and checks item/weapon classnames near expected XYZ positions. Each expected
item needs a distinct runtime edict, so one pickup cannot stand in for two.
The 24-unit tolerance accounts for stock origin shifts and items falling
onto floors. The SP audit honors the current skill exclusion bit. Stock
spawnflag 2048 means NOT_DEATHMATCH; it does not exclude an item from SP.
Use flags 256+512+1024 (1792) to exclude an entity from all SP skills.

An actual stock deathmatch audit is available separately:

```sh
python3 -m bspharness qa out/awoken/final/awoken.bsp --mode dm \
  --engine /path/to/QSS-M --basedir /path/to/quake --gamedir awoken_dm_pass1
```

QSS-M disables `setpos` in deathmatch, so this mode accepts no routes or
cameras. It checks the initial actual DM spawn and all expected DM items,
including the quad. Probe every DM spawn location with a separate SP
collision pass. These checks do not simulate a populated multiplayer match
or prove mod-specific rules or balance. Route/entity passes without cameras
render at 320x200; camera passes retain 1280x720 and identical physics timing.
The report explicitly leaves visual review pending. Review every screenshot
for darkness, blocked passages, material alignment, sky, and z-fighting.

## Probe movement with collision

```python
import json
from bspharness import Bounds, Move, WalkRoute

route = WalkRoute("hall-walk",(0,0,24),(0,0,0),(Move(72),),
                  Bounds((160,-16,20),(240,16,32)))
with open("src/my_map.routes.json","w") as stream:
    json.dump([route.metadata()],stream,indent=2)
```

```sh
python3 -m bspharness qa out/my_map/draft/my_map.bsp \
  --routes src/my_map.routes.json --cameras src/my_map.cameras.json \
  --engine /path/to/QSS-M --basedir /path/to/quake --gamedir movement_pass1
```

`WalkRoute` defines a starting XYZ origin, pitch/yaw/roll, a sequence of
`Move` actions, and expected finish bounds. Speed defaults to 200 units/s,
not running speed. Each action holds its buttons for a fixed frame count:
forward, back, moveleft, moveright, and jump. Empty buttons let momentum
settle. Add `expect=Bounds(...)` to an action for an intermediate checkpoint,
such as airborne jump height. Quake acceleration and stopping momentum
mean distance is not simply speed times duration. Facing remains fixed;
use separate probes for different legs or directions.

The engine positions the player, explicitly disables the noclip that QSS-M's
numeric `setpos` enables, settles, and verifies the start. Relocation while
unsticking is caught by the default 8-unit start tolerance. Start/end must
be grounded, every checkpoint must use walking collision, and health must
stay at least 100 unless a different `min_health` is authored. God mode
invalidates a probe. Position/health observations and route specifications
remain in the report. Teleport placement only establishes each probe's
start; route traversal uses actual player input and collision.

`examples/movement_checks.py` generates two regression maps and their routes.
Build both with the draft profile. Run movement-only QA by omitting
`--cameras`: `movement_open` should jump a 40-unit ledge and pass;
`movement_blocked` deliberately raises it to 128 and must return a failed
QA report and exit 1. Preserve this negative control when changing QA.
These probes supplement movement/combat playtesting; they do not prove
every possible route or mod's physics.

## Recover brush references

`bsputil -decompile reference.bsp` writes `reference.decompile.map`. Preserve
the original and work on a copy. `bspharness.source.read` accepts Valve 220
planes/axes and optional Quake 2 contents/surface/value fields. It preserves
source texture paths and UVs until an explicit material mapping is applied.
Legacy texture projections, Q3 brush definitions, and patches are rejected.

Use `Map(shell="explicit")` and `SourceBrush.mapped(...)` to supply recovered
structural brushes. This mode adds no enclosing box; a missing structural
wall must still produce a compiler leak. Plane intersections recover brush
vertices, and unbounded/zero-volume plane sets fail. Decide which contents
become structural, compiler detail, water, clip, or trigger geometry; remap
gameplay entities and item origins deliberately. Format conversion alone
does not adapt movement or textures. See [Awoken](../maps/awoken/README.md).

## Compare camera passes

```sh
python3 -m bspharness compare-qa baseline/qa.json new-pass/qa.json \
  --output out/comparison-01
```

Open `index.html` and inspect each named pair. Screenshot hashes must match
the input reports. Camera/render differences are reported; image collection
does not judge art quality. New QA reports pin 1280x720, FOV 90 with aspect
adaptation, gamma/contrast 1, trilinear textures, normal lightmaps, and a
hidden weapon/HUD, and retain camera coordinates and engine hashes.
Keep the approved QA directory as a local baseline.

## Package

```sh
python3 -m bspharness package out/atrium/final/atrium.bsp \
  --credits examples/atrium-readme.txt --output dist/atrium.zip \
  --qa-report /path/to/quake/bspharness_qa_pass1/qa.json
```

Source and artifact hashes must match the successful build; a supplied QA
report must pass and match the same BSP. New reports also bind the LIT and
every other build artifact, so changing colored light requires fresh QA.
The ZIP includes BSP, optional LIT,
source, credits, build/validation reports, and optional QA report.
Material contracts and seam reports are included when present, and their
hashes must match the build. Review credits for the actual texture variant.
External skyboxes and mod files are
not currently included automatically; stage those dependencies separately
and test the complete release install before publishing it.

The atrium example is a blockout, not a release-quality gameplay map. Engine
loading and automated item checks supplement movement/combat playtesting.
