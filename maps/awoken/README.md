# Awoken for stock Quake 1

This recipe adapts **4Bidden's Quake 2 remake** into a BSP29 deathmatch arena
with colored lighting. It retains the brush layout, eleven DM starts,
vertical connections, four push pads, teleporter and void hazards. Materials
come from local original Quake PAKs; Makkon assets are excluded. The Q2 BSP
is preserved and decompiled on a working copy. [Reference metadata](reference.json)
records the download, exact hash, credits, and secondary Xowoken inspection.

The editable Xowoken source was useful to inspect, but its Q3 patches and
models make it a substantially different conversion job. The Q2 brush
reference provides the geometry used here. This is a Q1 adaptation of that
remake, rather than a claim of measured equivalence to the QC original.

The [verified baseline](baseline.json) records the final BSP/LIT hashes,
compiler and engine hashes, 23 passing movement probes, the actual DM
spawn/item audit, and all five reviewed camera captures. The final BSP has
7,631 faces and 4,453 clipnodes, with full VIS and colored lighting. All 62
harness tests passed with compiler integration enabled. This establishes a
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

The conversion maps every retained texture and gameplay class explicitly.
It removes 150 Q2 alpha foliage/decal/mist brushes and five origin brushes,
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

The recipe authors **23 movement probes**: all eleven spawn locations,
three main walks, four pad flights and landings, the teleporter, three stair
legs, and a normal running jump/drop from GL to the lower nailgun area.
Every route verifies collision, position, ground at start/finish, and health;
flight/jump checkpoints also verify height. These use stock SP physics.

```sh
python3 -m bspharness build src/awoken.map --profile final \
  --max-faces 12000 --max-clipnodes 8000 --timeout 1800
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
`SDL_VIDEODRIVER=offscreen LIBGL_ALWAYS_SOFTWARE=1 LP_NUM_THREADS=2`.
Use a fresh QA gamedir each time. The DM pass checks actual stock DM spawn
logic and the quad; QSS-M disables positioning commands in DM, so authored
routes and fixed cameras run separately in SP. Run movement without cameras
for the faster 320x200 pass. All five camera images need visual review.

Record a visual review JSON with `artifacts` copied from the build manifest
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

This validates every report against both BSP and LIT, includes all 23
current route specifications, checks all five screenshot hashes, and
requires the explicit review for those artifacts. It creates `dist/awoken.zip`
with source, credits and evidence, plus directly usable files in
`dist/awoken/`. The installation needs only `awoken.bsp` and
`awoken.lit` in the chosen game's `maps/` directory; no custom game code.

The evidence covers sampled collision/routes, stock entities and reviewed
views. A populated match is the next test for combat timing and item balance.
Generated geometry, textures, engine captures and build products are local
artifacts; the repository tracks the reproducible recipe and provenance.
