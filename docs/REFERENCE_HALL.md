# Ember Cloister reference hall

`examples/reference_hall.py` builds a stock-textured benchmark: a vaulted
nave, two-level gallery and arcade, stair landing, entry arch, raised apse,
sky lantern, and visible warm/cool fixtures. It provides a repeatable area
for judging architecture, material scale, lighting, and movement together.
It has four pickups and no combat or progression.

## Build and inspect

Extract `assets/wads/id1.wad` from your own original Quake PAKs using the
README's `id-wad` command, then run:

```sh
python3 examples/reference_hall.py
python3 -m bspharness build src/reference_hall.map --profile draft \
  --max-faces 3500 --max-clipnodes 5000
python3 -m bspharness build src/reference_hall.map --profile final \
  --max-faces 3500 --max-clipnodes 5000
python3 -m bspharness qa out/reference_hall/final/reference_hall.bsp \
  --cameras src/reference_hall.cameras.json --routes src/reference_hall.routes.json \
  --engine /path/to/QSS-M --basedir /path/to/quake \
  --gamedir hall_final_pass1 --timeout 360
```

Use a fresh gamedir per pass. Review five images: entry arch, nave, upper
gallery, arcade, and apse. Six walking probes cover the entrance, stairs,
landing-to-gallery join, upper-gallery arch, arcade opening, and stepped
dais. They verify sampled movements, not full connectivity or gameplay.

The hall uses gray stone, gold stone trim, cobbles, timber, bronze, stock
light panels, and the original purple sky. Continuity within textures is
checked. Gold-to-gray arch/spandrel joins and other intentional material
contacts remain review warnings. Unwrapped corners and curved arch mapping
need camera review; passing seams does not certify all artwork joins.

## Keep a visual baseline

Retain an approved local QA directory with its PNGs and report. Camera
coordinates are fixed in the generator. New reports record those views,
render settings, engine hash, BSP/LIT hashes, and each PNG hash. After a change:

```sh
python3 -m bspharness compare-qa /path/to/baseline/qa.json \
  /path/to/new-pass/qa.json --output out/hall-comparison-01
```

Open `index.html` for side-by-side views. The tool copies original images
into a portable folder and rejects modified screenshots or different camera
sets. Different views, render settings, dimensions, and engine binaries are
shown as warnings. Older reports expose missing camera/render metadata.
Failed QA passes remain visibly failed when compared for diagnosis.
The tool never approves art automatically.

Judge floor readability, fixture placement, warm/cool separation, gallery
shadows, arch silhouettes, trim joins, sky, and z-fighting. The recorded
review in `examples/reference-hall-baseline.json` identifies the local
approved build and camera evidence; PNGs remain local build products. This
is an architecture/lighting reference, not a finished gameplay map.

## Package

```sh
python3 -m bspharness package out/reference_hall/final/reference_hall.bsp \
  --credits examples/reference-hall-readme.txt --output dist/reference_hall.zip \
  --qa-report /path/to/quake/hall_final_pass1/qa.json
```

PAKs, WADs, palette, and third-party assets remain local. The package
contains the map's embedded stock textures, BSP/LIT, source, credits, and
build/QA evidence. Makkon textures are excluded.
