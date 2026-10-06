# Native FTE particle effects

The harness can snapshot, stage, verify and package original FTE particle
scripts and PNG sprites alongside a map. The [Awoken recipe](../maps/awoken/PARTICLES.md)
is a working example with procedural sprites, static emitters, finite curved
paths and a motion preview. The core remains dependency-free; encoding that
preview additionally requires FFmpeg.

## Assets and installation

Declare sprites under `particles/...png` in the source's `.assets.json`, with
`sha256`, `width`, `height` and an extensionless `engine_name`. Script records
under `particles/...cfg` have `sha256` and `"kind": "fte_particles"`, without
image dimensions or `engine_name`. The allowlist excludes general engine
configs and game binaries. Hash checks apply throughout staging, verified
builds, engine QA and packaging; image uploads must also match their dimensions.

Keep generators and source metadata in Git. Keep generated sprites, compiled
maps, captures and packages untracked. A 512-pixel sprite should be rendered
from its source profile at that resolution; enlarging a small bitmap does not
add filament detail. Transparent borders prevent square edges under filtering.

Install the whole runtime snapshot, including `particles/`, with the BSP/LIT
in a separate game directory. QSS-M builds supporting map particle configs load
`particles/map_<bsp-basename>.cfg`. An engine requiring explicit selection can
use `r_particledesc "classic map_<bsp-basename>"` before loading the map. Check
the actual target engine: native particle support and config loading vary.

## Emitters and preserving the map

A stock `light_globe` can supply a silent, nonblocking static origin. A native
`r_effect progs/s_light.spr <namespace>.<effect> replace` substitutes particles
for its sprite without custom QuakeC or CSQC. This replacement affects that
model throughout the loaded descriptor, so isolate the variant and account
for any existing entities using it.

Place origins above the visible geometry. Awoken's retained metal ornaments
cover some original floor markings; emitting from those buried markings hides
the effect inside opaque brushes. Check each pad's actual surface height.

For new visual anchors, patch a copy with an entity-only compiler pass. Preserve
the BSP format and compare every original entity, every non-entity lump, BSPX
payloads and external LIT bytes. The Awoken helper also requires the exact
compiled MAP plus its declared anchors and a verified reference with a nonempty
PRT. Preserve the original build and its VIS/light evidence.

For subsequent sprite/config tuning, use `bind-assets` with a fresh destination
and the identical compiled MAP hash. This retains BSP/LIT bytes. Collect fresh
runtime and visual evidence for the new assets even when geometry is unchanged.
Replacement texture namespaces must match the variant's BSP basename too.
`bind-assets` inherits the reference build's existing evidence. Keep the new
particle recipe with the tuning evidence as well; an inherited recipe describes
the previous effect, while the new runtime manifest identifies the current
asset bytes.

## Particle syntax and motion

- Use short, explicitly named effects connected by `assoc`. Long anonymous
  `+effect` chains can accumulate nested names and exceed parser name limits.
- In the tested native parser, the second `count` argument is an additional
  random range. It is not an absolute upper bound.
- A continuation that must emit exactly one particle uses **`count 0 0 1`**.
  The third argument is an unconditional extra count, independent of particle
  density. Standalone `countextra 1` is DP effectinfo syntax and was silently
  ignored inside our native `r_part` blocks, preventing continuations from
  spawning. A completed QA script did not expose that omission.
- `type texturedspark` aligns its strip with world velocity. `stretchfactor`
  controls length; negative values select a fixed length. Rotating a normal
  billboard does not establish a world-space tangent from every camera angle.
- Tune visible width in-engine for each render type. Sprite alpha profiles,
  scale and stretch jointly determine the result; PNG dimensions are not world
  dimensions. Long sharp spines with faint glow sheaths read differently from
  short Gaussian dashes, even with the same color and particle count.
- Tangential velocity alone gives a straight trajectory. For curved paths,
  use finite successors with velocities following circle chords. Choose
  `emitstart` before the parent's earliest death, and `emitinterval` longer
  than its lifetime so it emits only once. Terminate the path; avoid recursive
  or branching successors that multiply particle counts.
- Sparse sector emitters can start together and produce batches. Invisible
  seeds with different emission delays spread their phases. Include seeds and
  all continuation steps in the particle budget. Mean occupancy is a tuning
  estimate, not a guarantee for every frame.

Read the [FTE specification](https://github.com/fte-team/fteqw/blob/master/specs/particles.txt)
and the target engine's parser/render code when behavior is uncertain. Log
diagnostics catch some rejected commands and chain problems, but unsupported
fields within blocks may be ignored silently. Verify the intended motion and
each accent visually, rather than relying on parser success alone.

## Review and evidence

Camera JSON supports `settle_frames` from 1 to 7200, defaulting to 10. QA runs
at 72 fixed simulation frames per second, so 72 frames gives about one second
of warmup. Allow for the complete path and staggered startup, rather than only
one hop's lifetime. Inspect startup and later frames; one attractive still
cannot establish rotation, persistent accents or performance.

Capture multiple phases at fixed camera positions, review all emitter sites,
and retain the build/runtime hashes with the screenshots and encoded preview.
Match the reference's framing and aspect ratio when comparing visual detail.
Keep normal gameplay views as well as close-ups. Use isolated QA game folders,
preserve engine exit codes, and verify movement after entity/geometry changes.
Compile success alone does not establish visual or gameplay quality.
