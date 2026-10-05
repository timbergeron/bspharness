# Initial harness verification — 2026-10-05

Verified locally on Linux x86_64 with Python 3.14, checksum-pinned ericw
2.0.0-alpha11/v0.18.2-rc1, and the available QSS-M build.

- **14 tests passed**, including real BSP29/BSP2/2PSB compiles, stable qbsp
  with modern VIS/light, monochrome and showcase lighting contracts,
  intentional leak/missing-texture failures, corrupted binary inputs,
  geometry volume/winding properties, and package hash validation.
- **Atrium builds passed** with draft, final, and showcase profiles. The
  generated BSP29 has 486 clipnodes. Showcase includes RGBLIGHTING,
  DECOUPLED_LM, LIGHTGRID_OCTREE, and LIGHTING_E5BGR9.
- **Stock texture extraction passed** against locally supplied original
  pak0/pak1: 573 textures from 51 BSP files. WAD previews generated; the
  stock-material atrium compiled with the final profile.
- **QSS-M final camera pass passed**: engine exit 0, four PNGs, player at
  full health and on ground, all ten expected item/weapon entities present,
  and no detected BSP load/collision errors. Software rendering used SDL's
  offscreen driver and Mesa. The first slower draft camera pass needed a
  larger timeout; timeout errors correctly produced a failed report.
- **Screenshots reviewed** for basic geometry and lighting: the atrium,
  warm west room, cool east room, and lower loop are visible and readable.
  SDL's headless relative-mouse warning appears in the notification overlay;
  this is a test-renderer limitation. The example remains an unplaytested
  blockout, not a finished map.
- **Release ZIP generated** with source, BSP/LIT, credits, hashes,
  validation, and the matching passing QA report.

Commands and artifact-level evidence remain in local ignored build/QA
directories. CI repeats the automated checks without game data. macOS and
Windows bundle hashes are pinned, but those platforms were not executed in
this session. Multiplayer gameplay, custom mods, and external skybox
packaging remain outside the current smoke checks.

# Material system verification — 2026-10-05

- **38 tests passed** with compiler integration enabled; the ordinary
  unit run passed 30 tests and skipped the eight compiler tests. Coverage
  includes density/anchor/phase mapping, rectangular image scales, tangent
  projection, unrolled wall corners, transition clearance and flush floors,
  conflicting trims, partial shared edges, deliberate UV and repeat errors,
  and stale/tampered material evidence.
- **Mixed-resolution materials and wrapped corners compiled successfully**
  in BSP29, BSP2, and 2PSB. Actual BSP texinfo matches the intended world
  anchor, repeat dimensions, and rectangular texture density. Both modern
  and stable qbsp choose duplicate textures from the last WAD. The material
  lookup now follows that behavior and compiled dimensions are checked.
- **Material diagnostic final build passed**: 74 checked shared edges,
  including four wrapped corner edges; no seam errors or material-boundary
  warnings. Ten trim wall corners have no declared wrap path and require
  visual review. The report exposes those limits rather than treating
  every corner as checked.
- **Bootstrap and the legacy atrium draft passed** after the changes.
  String-only maps retain their existing mapping/build behavior.
- **QSS-M material camera pass passed**: engine exit 0, three screenshots,
  healthy grounded player, expected armor and rocket launcher present,
  and no detected BSP load/collision errors. The mixed-resolution floor
  pattern remains continuous, doorway borders are flush, and the reviewed
  brick rows align around the visible corner. The software renderer's
  relative-mouse warnings remain visible in the notification overlay.
- **Material release evidence is hash-verified**. Packages include the
  contract and seam report; changing either invalidates verification.
  `dist/materials_demo.zip` was generated with the matching, passing camera
  report and a recorded review of all three screenshots.

The diagnostic uses original generated artwork. It demonstrates material
mechanics, not finished map art or playtested gameplay. Arbitrary image
compatibility, undeclared corners, lighting seams, and full movement routes
still need visual review and playtesting. Local artifacts remain ignored.

# Architecture and movement verification — 2026-10-05

- **55 tests passed** with compiler integration enabled. The ordinary run
  passed 44 and skipped 11 compiler tests. Checks cover convex architectural
  kits, staircase directions and dimensions, fixture faces/light origins,
  compiler geometry roles, movement/checkpoint failures, 3D unique item
  matching, build budgets, camera comparison hashes, and BSP/LIT-bound QA.
  Updated role, lighting-input, and package checks also passed separately.
- **Actual compiler collision checked in BSP29/BSP2/2PSB:** structural,
  default detail, wall detail, and fence detail remain solid; illusionary
  detail has no player collision. Detail entities merge into world model 0.
  Compiled stair treads, arch headroom, and fixture geometry were queried.
- **Bootstrap and both existing generators passed.** The atrium and material
  demo compiled with draft profiles after the geometry-role migration.
- **Ember Cloister final build passed** full VIS, 4x4 light sampling, RGB
  sidecar/embedded lighting, and explicit 3,500-face/5,000-clipnode budgets.
  It contains 2,158 faces, 2,535 clipnodes, 521 leaves, one world model, and
  409,768 BSP bytes. Stock WAD remains local; no Makkon assets are used.
- **Final QSS-M pass passed:** engine exit 0; six actual walking probes
  reached their expected destinations, including 12-unit risers, the
  upper-gallery arch, arcade, and 16-unit dais steps. All four expected
  pickups survived the initial XYZ audit; health and grounded states passed.
  Physics use fixed 1/72-second frames, walking collision, and no god mode
  during probes. Teleport commands only establish each probe's start.
- **Jump/negative controls verified in the engine:** a 40-unit ledge was
  crossed with an observed airborne checkpoint at Z=65.1 and a safe landing.
  Raising the barrier to 128 units stopped the player at Y=-32 and failed
  only the destination check in the completed repeat pass (engine exit 0).
  An earlier parallel run also exceeded its shorter shutdown timeout.
- **All five final PNGs reviewed** by Codex image inspection: navigable
  floors, gallery stairs, arcade silhouettes, visible pendants/wall fixtures,
  warm nave/cool apse, sky lantern, and visible material joins. Notification
  overlays are suppressed in the headless renderer. The tracked baseline
  records source/artifact/engine/camera hashes and review observations.
- **Seam scope remains explicit:** 1,728 shared edges passed, with 156
  material-boundary warnings and 504 unwrapped wall corners. Visible
  deliberate gold/gray/bronze contacts were inspected; unsampled artwork
  contacts and corners still require review for each authored map.
- **Camera comparison and release created:** `out/hall-lighting-comparison/`
  preserves before/after images and exposes the earlier report's missing
  camera/render metadata. `dist/reference_hall.zip` contains matching
  BSP/LIT, source, credits, material/seam/build evidence, and reviewed QA.
  Its ZIP integrity check passed.

The hall is an architectural reference area without combat or progression.
The probes test authored movement samples, not full connectivity, multiplayer,
mod physics, or complete gameplay. Linux offscreen rendering was exercised;
macOS and Windows remain unexecuted in this session. Local build products,
engine data, texture libraries, screenshots, and packages stay untracked.
