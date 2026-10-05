# Building high-quality Quake maps

The harness should let us work at the level of routes, spaces, architectural
kits, materials, light, and gameplay. Python generates repeatable geometry;
the mapper still makes the design decisions. Deterministic builds and engine
evidence make those decisions easier to iterate.

## Quality targets

- **Layout:** connected routes, useful verticality, clear destinations,
  sightline control, and deliberate movement choices. Define the game mode
  and player experience before adding decoration.
- **Architecture:** strong silhouette and proportions, repeated modules,
  coherent transitions, readable support structures, and detail density that
  serves the space. Avoid decorating an untested layout.
- **Materials:** per-zone palettes, consistent scale, intentional trim,
  controlled accents, and previews selected by appearance. Stock textures
  are a supported starting point; Makkon assets are deferred.
- **Lighting:** contrast without hiding gameplay, a clear direction for sun,
  plausible fixtures, warm/cool separation where useful, bounce, and bounded
  minimum light. Compare fixed cameras after each lighting change.
- **Gameplay:** adequate clearance and headroom, useful spawn orientation,
  safe item placement, intentional combat/puzzle flow, and mod-correct
  entity behavior. Single-player progression and multiplayer item economy
  need different design passes.
- **Reliability:** sealed structural geometry, valid hulls, complete VIS and
  lighting, sane format budgets, preserved originals, and matching asset
  credits. Engine QA and playtesting are part of completion.

## Current building blocks

`Map.room` declares AABB air volumes. Their union is subtracted from a solid
world with 64-unit padding. Adjoining volumes form openings. Structural
solids are split at room boundaries before adjacency chooses face textures,
so a sky well and a wall can receive separate materials.

`box`, `ramp`, and custom convex `Brush`/`Face` geometry add details. Every
face is oriented against an interior point, and brush construction rejects
degenerate/nonconvex input. Valve 220 UV axes align to world directions.
`Map.entity`, `Map.light`, and brush-entity lists handle Quake entities.

`Material` adds physical texel density or repeat sizes, shared anchors and
phase, compatible-image families, and tangent projection for slopes.
`Map.wall_run` unrolls vertical paths around corners. `TransitionRule` and
explicit room transitions generate doorway frames and flush floor trim.
The final BSP is checked for shared-edge phase, repeat density, declared
corner wraps, and the expected WAD dimensions. Source-bound material
contracts and seam reports are hashed into build/package evidence. See
[MATERIALS.md](MATERIALS.md) for usage and limits.

Compilation uses explicit profiles and format choices. Each run retains
logs, tool hashes, source hashes, artifact hashes, and a validation report.
QSS-M uses a post-connect script to capture repeatable cameras and audit
spawned entities. WAD and BSP readers catch malformed texture data before
engine testing. Stock PAK extraction stays local.

The air-volume shell seals structural geometry; arbitrary details or brush
entities can still create blocked routes, bad contents, or gameplay mistakes.
The compiler and runtime checks remain necessary.

## Next capabilities

1. **Architectural kits:** stairs, door/window frames, arches, columns,
   vaults, beams, trim, and curved wall segments with shared dimensions and
   material roles. Keep each kit deterministic and inspectable in `.map`.
2. **Layout specifications:** a room/route graph with dimensions, elevation,
   encounter/item intent, and a material/lighting theme, compiled into the
   existing Python API. Add clearance and connectivity checks before detail.
3. **Terrain and organic spaces:** convex decomposition for rock/cliff kits,
   caves, terrain, and asymmetric exterior silhouettes. Budget BSP splits
   and clipnodes from the start.
4. **Gameplay verification:** route traversal, standing/jump clearances,
   teleporter/push-trigger checks, mod-specific entity expectations, and
   multiplayer spawn/item audits. Current QA is a stock SP smoke pass.
5. **Surgical map edits:** structured MAP parsing and exact scoped transforms
   for relighting, void safety, and geometry repairs; preserve imported
   sources and compare compiled bounds against references.
6. **Visual iteration:** named camera comparisons, exposure variants,
   automated asset staging, and custom skybox/mod packaging. Separate
   automatic collection from a human visual review.

The original manual supplies recipes and earlier observations for several
of these. Treat them as references until implemented and tested in this repo.
