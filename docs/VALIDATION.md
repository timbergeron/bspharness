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
