# Awoken for Quake 1

This recipe adapts **4Bidden's Quake 2 remake** into a BSP29 deathmatch arena
with colored lighting. It retains the brush layout, eleven DM starts,
vertical connections, four push pads, teleporter and void hazards. Materials
come from local original Quake PAKs and the 26 supplied generated PNGs.
The current presentation uses high-resolution full-color external textures with
portable indexed BSP fallbacks. Makkon assets are excluded. The Q2 BSP
is preserved and decompiled on a working copy. [Reference metadata](reference.json)
records the download, exact hash, credits, and secondary Xowoken inspection.

The editable Xowoken source was useful to inspect, but its Q3 patches and
models make it a substantially different conversion job. The Q2 brush
reference provides the geometry used here. This is a Q1 adaptation of that
remake, rather than a claim of measured equivalence to the QC original.

The [verified baseline](baseline.json) records the latest final BSP/LIT hashes,
compiler and engine hashes, 26 passing movement probes, the actual DM
spawn/item audit, and all eight reviewed camera captures. The final BSP has
full VIS and colored lighting. The original [stock baseline](baselines/stock-v1.json)
retains the first release's 7,631 faces and 4,453 clipnodes. Harness tests and compiler integration cover the asset pipeline as well
as geometry and collision. This establishes a
playable build; a populated match remains necessary to assess balance.

## Build

Run from the repository root. First bootstrap the pinned tools and extract
your locally owned stock WAD as described in the main README. Then obtain
the reference:

```sh
mkdir -p out/references/awoken
curl -fsSL http://q2.packetflinger.com/dl/baseq2/maps/awoken.bsp \
  -o out/references/awoken/q2-awoken-original.bsp
python3 maps/awoken/build.py
python3 -m bspharness build src/awoken.map --profile draft \
  --max-faces 12000 --max-clipnodes 8000
```

`build.py` rejects a reference whose SHA-256 does not match the recorded
4Bidden BSP. Override local paths with `--reference`, `--stock-wad`, or
`--output`. It writes MAP, material contract, cameras, routes and conversion
metadata to `src/`. Keep each draft revision in its own `--out` directory
when comparing results.

The default `--style stock` needs only the local stock WAD. For the current
video-directed presentation, copy the supplied `aw_*.png` files into
`assets/awoken/` with the names and hashes in `art.json`, and extract
`assets/palette.lmp` alongside the stock WAD. FFmpeg handles raster I/O and
reference frames; the harness core uses the Python standard library.

```sh
python3 maps/awoken/build.py --style video
```

[Art metadata](art.json) records all 26 incoming masters, their native
sizes, channels and exact hashes. [Texture notes](TEXTURES.md) explain
placement, reserved assets, projection, fallbacks and installation. Native
masters retain the originals' dimensions and bytes; runtime PNGs upscale
without reducing either axis to avoid QSS-M odd-width mipmap row skew. `materials.py`
creates an indexed WAD and full-color runtime replacements, while
`build.py` writes the source-bound `.assets.json`. QA and packaging verify
that exact texture bundle. Extract `maps/`, `textures/` and `gfx/` from the
release into the same game directory; BSP/LIT alone use small fallbacks.
The old three-image art metadata remains in `art-v1.json`.

[Polish notes](POLISH.md) record the first video pass. [Geometry notes](GEOMETRY.md)
describe the 464 eased edges, 17 shaped cornices, collision joints, budgets
and video observations. That geometry is retained in the texture pass.

The conversion maps every retained texture and gameplay class explicitly.
The stock style removes 150 Q2 alpha foliage/decal/mist brushes and five
origin brushes; the video style restores 45 of those brushes using original vine art. It
makes the five rotating ornaments static nonblocking details, and adapts
ammo/health corner origins. Source emission produces exposed fixture
lights; covered courts receive broad fill. Sun, sky, bounce and ambient
occlusion remain part of the lighting recipe.

Three originally vertical pads receive a horizontal launch component
toward their landing ledges. This avoids repeated vertical bouncing under
stock Q1 air acceleration. The angled grenade pad retains its original
launch. Q2 rail becomes lightning and its slugs become large cells; the
machinegun becomes nailgun, chaingun/hyperblaster become super nailguns,
and bullets/former cells become nails. RL, GL and SSG retain their roles.
Quad uses 1792 to exclude all SP skills while remaining available in DM.

## Verify and finish

The recipe authors **26 movement probes**: all eleven spawn locations,
three main walks, four pad flights and landings, the teleporter, three stair
legs, and a normal running jump/drop from GL to the lower nailgun area,
and return walks across the lower court, rocket terrace and grenade bridge.
Every route verifies collision, position, ground at start/finish, and health;
flight/jump checkpoints also verify height. These use stock SP physics.

```sh
python3 -m bspharness build src/awoken.map --profile final \
  --max-faces 16000 --max-clipnodes 8500 --timeout 1800
python3 -m bspharness qa out/awoken/final/awoken.bsp \
  --routes src/awoken.routes.json --basedir /path/to/quake \
  --engine /path/to/QSS-M --gamedir awoken_final_movement --timeout 600
python3 -m bspharness qa out/awoken/final/awoken.bsp --mode dm \
  --basedir /path/to/quake --engine /path/to/QSS-M \
  --gamedir awoken_final_dm --timeout 180
python3 -m bspharness qa out/awoken/final/awoken.bsp \
  --cameras src/awoken.cameras.json --basedir /path/to/quake \
  --engine /path/to/QSS-M --gamedir awoken_final_cameras --timeout 600
```

Final uses full VIS and `-extra4`, with external LIT and embedded RGB. For
software rendering on Linux, prefix QA commands with
`SDL_VIDEODRIVER=offscreen LIBGL_ALWAYS_SOFTWARE=1 LP_NUM_THREADS=8`.
Use a fresh QA gamedir each time. The DM pass checks actual stock DM spawn
logic and the quad; QSS-M disables positioning commands in DM, so authored
routes and fixed cameras run separately in SP. Run movement without cameras
for the faster 320x200 pass. All eight camera images need visual review.

Use `compare-qa` for the portable paired camera report. A standalone slider
with sixteen inspected frames from both supplied videos is also available:

```sh
python3 maps/awoken/review.py /path/to/geometry-camera-qa.json \
  /path/to/high-resolution-camera-qa.json --output dist/awoken-review.html
```

This export checks screenshot hashes, camera coordinates, engine identity,
render settings and the reference frame hashes before embedding every
image. The HTML opens offline and needs no adjacent image files.

Record a visual review JSON with `artifacts` and `runtime_assets` copied from the build manifest
and a `cameras` object keyed by each camera name. Each entry needs
`"accepted": true`, its screenshot `sha256`, and notes from opening its image.
Then package all evidence:

```sh
python3 maps/awoken/package.py \
  --movement /path/to/quake/awoken_final_movement/qa.json \
  --deathmatch /path/to/quake/awoken_final_dm/qa.json \
  --cameras /path/to/quake/awoken_final_cameras/qa.json \
  --review out/awoken/visual-review.json
```

This validates every report against both BSP and LIT, includes all 26
current route specifications, checks all eight screenshot hashes, and
requires the explicit review for those artifacts. It creates `dist/awoken.zip`
with source, credits and evidence, plus directly usable files in
`dist/awoken/`. Extract `maps/`, `textures/` and `gfx/` into the same game
directory for the high-resolution presentation. BSP/LIT alone remain an
indexed fallback. No custom game code is required.

An optional [FTE jump-pad vortex variant](PARTICLES.md) adds electric-blue
filaments, moving white hot spots, rising arcs and sparse lightning at the four
pad bases. Its generator preserves this baseline and creates a separately
named map with original procedural sprites. General implementation and QA
lessons are in [the harness particle guide](../../docs/PARTICLES.md).

The evidence covers sampled collision/routes, stock entities and reviewed
views. A populated match is the next test for combat timing and item balance.
Generated geometry, textures, engine captures and build products are local
artifacts; the repository tracks the reproducible recipe and provenance.
