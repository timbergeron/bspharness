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
paths. Put a validated recovered WAD first when old texture names have been
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
QA waits for the player to land, dumps edicts, then enables god/noclip for
camera screenshots. `host_maxfps 72` and 100-frame gaps help avoid filename
collisions and allow light settling. Pass `--timeout 240` for a slow software
renderer. On Linux, a compatible SDL/Mesa setup may use
`SDL_VIDEODRIVER=offscreen LIBGL_ALWAYS_SOFTWARE=1 LP_NUM_THREADS=2`.

The stock SP audit checks a live player with full health and `FL_ONGROUND`,
and checks item/weapon classnames near expected XY positions. It skips
entities flagged out of SP. It is a smoke test: dynamic items, SP-only pickups,
mods, multiplayer spawn logic, and movement routes need further checks.
The report explicitly leaves visual review pending. Review every screenshot
for darkness, blocked passages, material alignment, sky, and z-fighting.

## Package

```sh
python3 -m bspharness package out/atrium/final/atrium.bsp \
  --credits examples/atrium-readme.txt --output dist/atrium.zip \
  --qa-report /path/to/quake/bspharness_qa_pass1/qa.json
```

Source and artifact hashes must match the successful build; a supplied QA
report must pass and match the same BSP. The ZIP includes BSP, optional LIT,
source, credits, build/validation reports, and optional QA report. Review
credits for the actual texture variant. External skyboxes and mod files are
not currently included automatically; stage those dependencies separately
and test the complete release install before publishing it.

The atrium example is a blockout, not a release-quality gameplay map. Engine
loading and automated item checks supplement movement/combat playtesting.
