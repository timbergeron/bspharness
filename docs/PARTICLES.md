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
- `rampmode lerp` with N `ramp r g b alpha scale` lines spaces the entries
  evenly over the type's `die`: entry i applies at age `i * die / N`, so the
  last entry lands one step before death. It interpolates rgb, alpha *and*
  scale. Timing resolution is `die / N`; a 50 ms cut on an 8-second particle
  needs about 100+ entries. Ramp position follows the type's `die`, so
  `diesubrand` ends particles partway through their ramp.
- Visible extent is much smaller than `scale` for soft textures with wide
  transparent margins (roughly a third to a half for vapor sprites). Measure
  in-engine before laying out a composition.
- `blend add` suits glows and mist in dark areas. `blend invmoda` with
  `rgb 0 0 0` and a round soft sprite darkens what is behind it, which makes a
  cheap shadow pocket that adds contrast behind an apparition.

## Timed, triggered and multi-site effects

The Watcher (an apparition on aerowalk_halloween: mist gathers, two eyes hold,
then everything dissolves) established the following patterns with QSS-M's
native parser. Keeping it in one Python generator kept every layer's timing,
the scheduler chain and the `.ent` anchors in sync.

- **One-shot timeline.** For each layer, make an invisible scheduler:
  `type invisible`, `count 0 0 1`, `emit <layer>`, `emitstart <t>`,
  `emitinterval 999` and `die <t + 0.12>`. It emits the layer exactly once at
  time t, then dies. Chain the schedulers with `assoc` from one root so a
  single trigger starts the whole timeline. Each visible layer then uses one
  particle whose ramp encodes its entire envelope. Author envelopes as keyframe
  curves in absolute timeline seconds and sample them into each layer's ramp.
- **Periodic or random trigger.** On an `r_effect`-attached root,
  `spawntime T` rate-limits spawning and `spawnchance p` rolls once per
  allowed spawn. Together they fire on average every `T / p` seconds. Keep T
  longer than the full timeline so an effect cannot restart while it is
  still playing.
- **Anchors only run near the player.** Model-attached effects run only while
  the anchoring entity is processed for the current view (in the PVS).
  Particles at a distant anchor stopped as soon as the camera moved away, and
  distant anchors never roll. Treat `spawnchance` as a per-spot rate while
  the player is nearby; dividing a global rate across every anchor makes the
  effect far too rare.
- **Several sites.** Each `misc_model` anchor keeps its own trail state, so
  anchors fire independently. `r_effect` binds by model name, so a site
  needing a different variant (such as a different facing) needs its own
  copy of the tiny anchor `.spr`.
- **Facing.** `orgbias`, `orgwrand` and velocities are world-axis. A
  composition with a horizontal structure, such as two eyes, collapses when
  seen edge-on. Generate a rotated variant per site from the direction it
  should face, and rotate the box extents and velocity ranges as well.
- **Depth.** Keep focal elements at the same depth as their backdrop. Eyes
  placed 15 units in front of their mist read correctly head-on but slid out
  of the cloud at an angle.
- **Clearance.** Billboards turn toward the camera, so at oblique views a
  sprite near a wall cuts into it along a hard straight line. Keep roughly
  the visible half-width × sin(steepest view angle) of clearance; for the
  Watcher, 17 units clipped at 25° and about 30 did not. Ceilings and lintels
  clip tops the same way, so taper alpha toward the ends of a column rather
  than letting geometry cut it.
- **Measuring a site.** Trace the BSP hull from the intended position to find
  floor, ceiling and the walls ahead, behind and to each side, then place the
  composition to fit. When a site is taken from a player's `viewpos`, confirm
  whether it marks where the effect goes or where it is viewed from.

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

For timed effects in a live engine driven over rcon:

- Sync captures to the effect, not the wall clock. Poll `r_partinfo` and start
  timing when a named layer (for example `map_<bsp>.shade0`) first appears.
  The script schedule then gives each frame's position in the timeline.
- Set `host_timescale 0.25`–`0.5` during capture to sample short phases
  finely, and restore it afterwards.
- Run `noclip` before `setpos`; otherwise the player falls during a long
  capture and the framing drifts.
- Reload particle scripts with separate `r_particledesc classic` and
  `r_particledesc qssm` commands. Joined with `;` in one rcon string, the
  cvar was set to the literal `classic;`. Edits to `.ent` anchors need a map
  restart.
- Generate a test build where every anchor fires on every check
  (`spawnchance 1`) for placement review, then regenerate with the real rate.
- Review each site straight on and from an oblique angle at the normal play
  height. Brightened copies of the frames reveal clipping edges that are
  invisible at game gamma.
