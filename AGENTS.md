# Working on bspharness

This is the working repository for building high-quality Quake 1 maps from
code. Read README.md, docs/WORKFLOW.md, and docs/DESIGN.md before map work.
docs/operator-manual.md is the original field manual; its local paths and
version-specific observations are historical, not portable configuration.

- Do not add Makkon assets. Keep PAKs, extracted id1 textures, downloaded
  WADs, palettes, skyboxes, compiler binaries, and build products untracked.
  Links, original generators, and source metadata belong in Git.
- Preserve original map sources and BSPs. Patch a copy. Preserve BSP29/BSP2
  and monochrome/colored-light contracts unless an upgrade is requested.
- Use absolute compiler paths and preserve subprocess exit codes. A missing
  PRT, leak, missing texture, empty VIS/lightdata, invalid miptex, or excessive
  reference clipnode growth must fail the build.
- For ornate imported maps, try the pinned stable qbsp; use modern vis/light.
- Gameplay and visual quality require engine checks. Compile success alone
  does not prove items spawn, floors collide, lighting reads well, or routes
  play well. Review screenshots and play the map before calling it finished.
- Run `python3 -m unittest discover -s tests -v`. After pipeline or geometry
  changes, also run `python3 tools/bootstrap.py` and
  `BSPHARNESS_INTEGRATION=1 python3 -m unittest discover -s tests -v`.
- Keep the core dependency-free on Python 3.10+. Do not add shell pipelines
  that hide a failing compiler or automatically replace user engine maps.
