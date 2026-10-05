# bspharness

A scriptable workshop for building high-quality **Quake 1 BSP maps**: describe
playable spaces in Python, generate sealed Valve 220 geometry, compile with
ericw-tools, inspect the BSP, and collect in-engine evidence with QSS-M.

The aim is deliberate layouts, strong architecture, readable materials,
expressive lighting, and reliable gameplay. The included atrium is a working
blockout example; polished maps still need art direction and playtesting.

## First build

Requires Python 3.10+ and the ericw compilers. The core uses only Python's
standard library. Run these commands from the repository root:

```sh
python3 tools/bootstrap.py
python3 examples/atrium.py
python3 -m bspharness build src/atrium.map --profile draft
python3 -m bspharness inspect out/atrium/draft/atrium.bsp
```

The bootstrap installs checksum-pinned `2.0.0-alpha11` and `v0.18.2-rc1`
bundles for Linux, macOS, or Windows. Linux/Windows bundles require x86_64;
Apple Silicon uses Rosetta. Native custom builds can be passed with
`--qbsp-dir` and `--lighting-dir`.

For final lighting or the extended QSS-M lighting formats:

```sh
python3 -m bspharness build src/atrium.map --profile final
python3 -m bspharness build src/atrium.map --profile showcase
```

`draft` uses fast VIS; `final` uses full VIS, 4x4 light sampling, and external
plus embedded colored lighting. `showcase` also bakes 8-unit luxels, HDR, and
a lightgrid. `mono` keeps standard grayscale BSP lighting and discards the
colored sidecar. Large maps explicitly select `--format bsp2`.

## Original Quake textures

Use your local `pak0.pak` and `pak1.pak`. The harness extracts embedded BSP
textures into a WAD2 and optionally extracts your palette for previews:

```sh
python3 -m bspharness id-wad /path/to/id1/pak0.pak /path/to/id1/pak1.pak \
  --output assets/wads/id1.wad --palette assets/palette.lmp
python3 -m bspharness wad-preview assets/wads/id1.wad \
  --palette assets/palette.lmp --output out/textures/id1
python3 examples/atrium.py --stock-wad assets/wads/id1.wad --output src/atrium_id1.map
python3 -m bspharness build src/atrium_id1.map --profile final
```

Open `out/textures/id1/index.html` to browse the extracted textures by name.
The example also generates original development textures for light strips
and tool materials. No downloaded WAD is needed for the default blockout.

Makkon textures and skyboxes are excluded for now. Other WAD download links
are collected in [the texture catalog](docs/TEXTURES.md). PAKs, WADs,
palettes, compiler binaries, and generated outputs stay out of Git.

## Author maps at the room level

```python
from bspharness import Map, Palette, box, ramp

arena = Map("My map", _bounce="1", _minlight="16")
arena.room("hall", (-384, -256, 0), (384, 256, 320), Palette())
arena.room("side", (384, -128, 0), (768, 128, 192), Palette(wall="bh_accent"))
arena.entity("info_player_start", (0, 0, 24), angle="0")
arena.light((0, 0, 224), 350)
arena.write("src/my_map.map", ["assets/wads/blockout.wad"])
```

Rooms carve air from a padded solid world. Shared boundaries become
doorways, face materials come from room palettes, and sky volumes provide
sunlight openings. Details, ramps, items, lights, and brush entities add
intentional structure inside that shell. See [atrium.py](examples/atrium.py)
for a complete layout with multiple routes and vertical gameplay.

## Engine QA and packaging

```sh
python3 -m bspharness qa out/atrium/final/atrium.bsp \
  --cameras src/atrium.cameras.json --engine /path/to/QSS-M \
  --basedir /path/to/quake --gamedir bspharness_atrium_qa
python3 -m bspharness package out/atrium/final/atrium.bsp \
  --credits examples/atrium-readme.txt --output dist/atrium.zip \
  --qa-report /path/to/quake/bspharness_atrium_qa/qa.json
```

Use a fresh QA gamedir on every pass. QA checks player ground/health, item
survival, engine errors, and screenshot count. Review the PNGs yourself;
automated QA does not judge map design. Packaging checks artifact hashes and
includes the BSP, `.lit` when present, source, credits, and build/validation
reports. QA is optional for development packages; include it for reviewed
releases. Custom skyboxes or mod dependencies need separate asset packaging.

## Repository guide

| Path | Purpose |
| --- | --- |
| `bspharness/` | Geometry, MAP/WAD/PAK/BSP readers, compilation, QA, packaging |
| `examples/` | Tracked generators and map credits |
| `configs/` | Compile profiles and pinned tool downloads/hashes |
| `assets/wads/` | Local, untracked texture libraries |
| `src/`, `out/`, `dist/` | Generated sources, compile evidence, release archives |
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | Build/edit/verify procedures and known limits |
| [docs/DESIGN.md](docs/DESIGN.md) | Quality goals, architecture, and next capabilities |
| [docs/operator-manual.md](docs/operator-manual.md) | Original `mapharness.md` field notes |

## Check the harness

```sh
python3 -m unittest discover -s tests -v
BSPHARNESS_INTEGRATION=1 python3 -m unittest discover -s tests -v
```

Integration checks use the pinned compilers to build BSP29, BSP2, and 2PSB,
exercise the stable-qbsp/modern-light combination, reject leaks and missing
textures, and verify package hashes. No game PAKs or third-party textures are
needed by CI.
