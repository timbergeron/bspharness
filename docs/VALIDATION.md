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
