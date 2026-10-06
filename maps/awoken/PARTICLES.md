# Jump-pad electric vortex

`particles.py` generates an optional FTE particle variant from the existing
video-style Awoken MAP and its sidecars. It preserves that source and uses a
separate BSP basename. The original map's brushes, collision and push triggers
are copied verbatim. Four silent, nonblocking stock `light_globe` entities
provide static emitter origins; `r_effect ... replace` substitutes their
sprites with particles. No custom `progs.dat` or CSQC is needed.

The effect is an original approximation of the supplied Awoken reference,
now tuned toward ancient machinery containing a miniature blue cyclone.
The uploaded `goal.png` is the current visual target: long electric-blue
filaments, a few white star-like knots, branching lightning and lifted sparks.
The earlier cyan dash treatment is preserved in the previous build bundles.
Nine layers share a roughly 96-unit footprint:

- Broad faint blue haze, further reduced so it does not conceal the filaments.
- Electric-blue core: overlapping, curved strokes with a sharp spine and
  faint glow sheath, continuing along finite six-step paths.
- Main ring: longer, irregular blue filaments with occasional offshoots.
- Rising wisps: finite eight-step paths rising about 22 units around the edge.
- Travelling hot spots: finite ten-step paths with a brightness envelope and
  original white-core/blue-halo star sprites; roughly six to seven paths alive.
- Interior energy snaps: approximately three live branching bolts on average,
  using soft blue → cyan → almost white → transparent ramps.
- Sparse blue point sparks lifting above the outside edge.
- Extremely faint center glow and a few outward-feeding motes.

Seventeen of twenty-four sectors per layer rotate clockwise when viewed from
above; opposing sectors are distributed around the circumference and offset
between layers for turbulence. Textured sparks align to their
world velocity, so the direction survives changes in camera angle. Hot spots
and rising wisps emit one successor at each short path step, changing velocity
to follow chords around the ring. The paths terminate rather than recirculate
or branch. There is no orbital force solver or custom game/engine code.
Frame timing and small random offsets keep the motion imperfect. Sparse
layers use invisible, phase-delayed seeds to prevent sector emissions from
arriving in synchronized batches. Each seed emits exactly one visible path
and dies before it can emit again; all paths remain finite.

The nine original 512 × 512 RGBA sprites are drawn analytically as sharp
filaments, branching bolts and star highlights. They are individual puffs and
strokes rather than a spinning ring decal. Everything is additive; center
particles remain very faint, and sparks are uncommon. The nominal budget, including path
continuations, is about 706 particles per second per visible pad. Static
emitters follow the engine's normal visibility culling. Actual occupancy and
appearance require in-engine review for each tuned bundle.

Continuations use native **`count 0 0 1`**, whose third argument supplies one
particle independently of density. Standalone `countextra` was silently ignored
inside native blocks, so the earlier continuation accents did not spawn. The
corrected recipe was checked in motion as well as in all four pad views. See
[the harness particle guide](../../docs/PARTICLES.md) for the reusable lessons,
including short named chains, emission timing, and reference comparisons.

The retained Q2 ornaments stand above three of the video-style pad markings.
Those emitters use the ornaments' visible tops, four units above Z=-728;
the grenade emitter uses its higher marking. Emitting from the buried
markings would hide most of the haze inside the opaque pad geometry.

Run from the repository root after generating the video-style source:

```sh
python3 maps/awoken/particles.py
python3 maps/awoken/particle_build.py
python3 -m bspharness qa out/awoken-vortex-final/awoken_vortex.bsp \
  --engine /absolute/path/to/QSS-M --basedir /path/to/quake \
  --routes src/awoken_vortex.routes.json --gamedir awoken_vortex_movement
python3 -m bspharness qa out/awoken-vortex-final/awoken_vortex.bsp \
  --engine /absolute/path/to/QSS-M --basedir /path/to/quake \
  --cameras src/awoken_vortex.cameras.json --gamedir awoken_vortex_cameras
```

`particle_build.py` uses absolute pinned qbsp paths with `-onlyents` on a
copy of `out/awoken/final/awoken.bsp`. It requires the exact compiled source
plus the four declared anchors, a nonempty reference PRT, and a verified
reference build. It compares all original entities, all fourteen other BSP
lumps, all BSPX payloads, and external LIT bytes before accepting the result.
The full VIS, lighting and collision bake is inherited and recorded in
`inherited-build.json`. BSP29, BSP2 and 2PSB preservation have compiler tests.
`--reference`, `--source`, and `--output` override the local defaults.

Alternatively, compile `src/awoken_vortex.map` normally with the harness and
the existing Awoken face/clipnode budgets. This repeats the original map's
VIS and lighting work. The particle presentation does not need a new bake.

Output/runtime paths must be fresh. For another revision use `--output` and
`--runtime`; retain the basename when comparing particle settings. Native
replacement textures are rebound to that BSP's basename automatically.
The generated `.particles.json` records the source and generator hashes,
layer settings, anchors and exact runtime asset hashes.

Install a packaged variant into a separate game directory with `maps/`,
`textures/`, `gfx/`, and `particles/` together, then load `awoken_vortex`.
QSS-M versions with map particle configs automatically load
`particles/map_awoken_vortex.cfg`. For FTE or other versions that require
explicit loading, select `r_particledesc "classic map_awoken_vortex"` before
loading the map. The config replaces `progs/s_light.spr`, so it belongs only
to this variant. Engines without FTE model emission will show the four stock
globe sprites; use the original Awoken release for those engines.

For an effect-only iteration, generate a new asset bundle with the same map
basename, then use `bspharness bind-assets` to snapshot it into a fresh build
directory. It verifies the exact compiled MAP hash and retains BSP/LIT bytes.
Collect fresh camera/motion evidence for every tuned bundle before packaging.

`particle_preview.py` uses a close, 70-degree camera for comparison with the
reference. It captures a 1448 × 1086 two-second engine loop with 24 frames, checks
the screenshot hashes, and uses FFmpeg to encode an MP4 and a standalone
offline HTML player. It takes a verified BSP, `--engine`, `--basedir`, and
fresh `--gamedir`/`--output` paths. On headless Linux use the same SDL offscreen
and Mesa environment settings as ordinary engine QA.

FTE's [particle specification](https://github.com/fte-team/fteqw/blob/master/specs/particles.txt)
documents the native effect chains, worldspace biases, alpha and sprite fields.
