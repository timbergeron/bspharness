# Awoken texture generation brief

This brief uses both supplied Quake Champions recordings. The original duel
recording supplies the broad material and architectural reference. The
103.84-second Clutch Dash recording supplies clearer moss coverage, jump-pad
markings, carved plaques, roots and exterior vegetation. Their identities
and inspected frame hashes are recorded in [reference.json](reference.json).
Descriptions are interpretations of compressed video, not recovered source
textures or measured material properties.

Generate **1–10 first**. They cover the largest visible surfaces and the most
recognizable details of the existing map. Items 11–20 add controlled variants
and secondary materials. Items 21–26 support exterior/environment work;
foliage and cliff artwork also need geometry and authored placements.

## Delivery and shared direction

- Deliver individual full-color PNGs with the filenames below. Use RGBA with
  real transparent backgrounds for cutouts. Do not pre-index to the Quake
  palette or add retro pixelation; conversion and mipmaps happen in the harness.
- Dimensions are **source-master sizes**, not required WAD dimensions. The
  intended compiled working sizes are generally 128–256 pixels per dimension,
  preserving rectangular aspect ratios. Check that broad forms still read at
  those sizes. Fine noise should not be the main source of detail.
- Supply diffuse/albedo artwork. Even illumination and small local recess
  contrast are useful; broad cast shadows, sun patches, glossy reflections,
  baked blue light and scene lighting will conflict with the map's lighting.
  Normal/roughness/height maps are optional working references and are not
  consumed by the current BSP/WAD path.
- Keep all stone in one family: weathered pale-to-medium gray temple stone,
  subtle warm/olive mineral tones, muted green moss, restrained brown roots.
  Use visible material grain without chalk-white centers or black mortar.
- Make variants by editing the approved base. Preserve every joint, block
  position, crack and UV orientation. Keep the same narrow edge band where
  practical so clean/mossy/wet variants can meet without abrupt color changes.
  Horizontal bands in a family must keep the same vertical registration.
- Tiling means the first and last edges genuinely join. A square image alone
  does not guarantee this. Generate a single asset, without perspective,
  presentation boards, grids of alternatives, watermarks or text.
- The existing stone bevels, cornices and relief rims are modeled. Their
  textures should describe the material or carving surface, rather than
  paint an additional large architectural bevel or doorway onto the stone.
- No Makkon assets. Artwork should be original, informed by the supplied
  references. Do not include the recording's HUD, weapons, players or effects.

For flat opaque surfaces, prepend this to each description:

> Original diffuse/albedo game texture for an ancient overgrown stone temple
> arena. Flat orthographic surface filling the image, evenly lit, broad forms
> readable at 128–256 pixels, restrained grain and wear, consistent gray/olive
> stone family. No perspective, scene, directional illumination, cast shadows,
> glossy highlights, lettering, logo or watermark. Follow the specified tiling
> and aspect ratio exactly.

Use frontal isolated cutout wording for foliage and the panorama wording for
the sky; they are exceptions to the flat opaque surface prompt.

## First batch

### 1. `aw_wall_base.png` — primary ashlar masonry

**Master:** 1024×1024. **Tiling:** both axes. **Use:** main arena walls;
replacement for the current `aw_stone` artwork.

Massive rectangular gray temple blocks with broad, nearly planar centers.
Compose two block widths across the tile and four horizontal courses;
alternate courses offset by half a block. Narrow recessed joints, gently
worn edges, sparse small chips and occasional short cracks. Subtle mineral
variation between blocks, with minimal moss. Avoid small brickwork, cobbles,
deep black gaps and uniform speckled noise. This layout preserves the current
nominal 128×64-unit wall-block rhythm within a 256×256-unit texture repeat.

### 2. `aw_wall_moss.png` — moss-covered masonry variant

**Master:** 1024×1024. **Tiling:** both axes, compatible with item 1.
**Use:** exterior courts, shaded lower wall courses and damp corners.

Edit item 1 without moving any masonry joints. Add irregular broad patches
of muted olive and sage moss over roughly a quarter to a third of the
surface, concentrated in joints, lower block edges and a few patches across
block faces. Keep plenty of exposed stone and visible courses. Moss has a
soft uneven fringe and restrained texture; avoid fluorescent green, evenly
distributed green noise or a painted green wash across every block.

### 3. `aw_stone_plain.png` — plain architectural stone

**Master:** 1024×1024. **Tiling:** both axes. **Use:** arch jambs, columns,
cornice faces, relief rims and ledge sides; replacement for `aw_trim` grain.

A continuous slab of the same stone as item 1, without masonry joints.
Broad quiet areas, subtle cloudy mineral variation, fine grain, occasional
small pits and very sparse hairline cracks. Slight olive/warm-gray tone,
matching the wall-block interiors. Avoid borders, painted bevels, molding
strips or large cracks that repeat conspicuously on narrow supports. Let the
modeled stone profiles provide their own edge highlights and shadows.

### 4. `aw_floor_base.png` — terrace and corridor paving

**Master:** 1024×1024. **Tiling:** both axes. **Use:** primary walking surfaces;
replacement for the current `aw_pave` artwork.

Large square gray stone flags arranged two across and two down. Thin joints,
slightly rounded worn edges, broad scuffed centers and restrained chips.
The stone matches items 1 and 3, with gently warmer wear at the walking
surface. Sparse cracks and tiny mineral flecks; keep the centers clear.
Avoid cobbles, checkerboard value changes, gravel, scattered leaves and
baked sunlight. Preserve a calm readable plane under fast player movement.

### 5. `aw_floor_moss.png` — mossy paving variant

**Master:** 1024×1024. **Tiling:** both axes, compatible with item 4.
**Use:** outdoor terraces and paving beside foliage or water.

Edit item 4 with exactly the same joints and slab shapes. Add broad irregular
moss patches around joint intersections and along some slab edges, extending
onto selected faces while keeping the worn centers mostly exposed. Olive,
sage and restrained earthy green, with a few damp brown stains. Avoid
uniform coverage, raised grass or loose debris. This should read as old
paving colonized by moisture and vegetation, like the second clip's terraces.

### 6. `aw_relief_a.png` — tall ornamental carving

**Master:** 512×1024. **Tiling:** none; one complete panel. **Use:** the eleven
modeled tall relief surrounds; replacement for the current `aw_panel` motif.

A narrow vertical stone carving with stacked interlocking scroll or
serpent-like ribbons, rounded grooves, stepped angular accents and a narrow
incised inner border. Dense enough to feel deliberately carved, with a clear
large-scale rhythm rather than arbitrary scratches. Match the stone family,
with subtle brown/olive weathering in recesses. Keep the motif centered and
inside the panel. Do not paint an external stone frame, pedestal, doorway,
strong side lighting or a glowing emblem; the outer rim is already modeled.

### 7. `aw_trim_carved.png` — repeating ornamental band

**Master:** 1024×256. **Tiling:** horizontal only. **Use:** selected wall bands
and architectural friezes; needs dedicated face assignments.

A continuous narrow carved temple frieze on matching stone. Repeating
angular meanders mixed with restrained interlocking scroll forms; consistent
line width, large readable recesses and slim plain stone margins above and
below. The pattern must connect at the left/right boundary. Shallow wear and
small moss stains, without broad shadow gradients. Do not render a projecting
cornice: this decorates an existing stone band rather than supplying its shape.

### 8. `aw_vine_dense.png` — hanging vine curtain

**Master:** 1024×1024 RGBA. **Tiling:** horizontal only; sparse taper at bottom.
**Use:** existing 45 hanging-vine placements; replacement for `{aw_vine}`.

Frontal hanging woody strands and roots with irregular clusters of small
olive/sage leaves. Dense attachment near the upper edge, several longer
tendrils below, and generous open gaps through the middle and lower areas.
Roughly half the image should remain transparent. Avoid a flat hedge,
uniform leaf spacing, giant leaves, flowers, wall backgrounds or painted
ground shadows. Strands crossing a side edge must continue at the opposite
edge. Keep stems and leaves broad enough to survive palette conversion.

### 9. `aw_pad.png` — angular jump-pad marking

**Master:** 1024×1024. **Tiling:** none; one centered square marking.
**Use:** four lift/push-pad landmarks; replacement for the round arrow design.

A bold ivory stone meander made from thick right-angle paths on a dark
recessed stone plate, matching the angular maze visible around 0:30 in the
Clutch Dash clip. A clear square overall footprint, consistent stroke widths,
slightly worn corners and restrained material grain. Keep the motif within
an even small margin. Avoid lettering, arrows, circular rings, flames and
painted blue glow. The existing landmark lights supply their own color.
Its UV repeat will need fitting to the actual pad plate when imported.

### 10. `aw_water.png` — green court water

**Master:** 1024×1024. **Tiling:** both axes. **Use:** pond surfaces;
replacement for `*aw_water`.

Muted olive-green water with broad gentle ripple variation and subdued
green-gray depth tones. Sparse soft ripple ridges, irregular but periodic,
with enough contrast to read after downsampling. Avoid bright white wave
crests, a visible shoreline, pebbles, pool tiles, reflected trees or a baked
sun reflection. Supply an opaque texture master; water motion and any
surface transparency are engine/material settings, not alpha painted here.

## Variants and secondary materials

### 11. `aw_wall_wet.png` — damp wall variant

**Master:** 1024×1024. **Tiling:** both axes, compatible with item 1.
**Use:** wall bases beside water and beneath the waterfall.

Edit the approved masonry base, keeping every joint and crack in place.
Add broad uneven damp stains, roughly 15–25% darker than dry stone in the
affected patches, faint vertical mineral trails and small green-black algae
patches in sheltered recesses. Keep the original stone legible. No shiny
specular streaks, puddles, a painted waterline or a blanket of near-black grime.

### 12. `aw_stone_worn.png` — eroded plain stone variant

**Master:** 1024×1024. **Tiling:** both axes, compatible with item 3.
**Use:** lower column faces, old support surfaces and exposed ledge sides.

Edit the plain stone with localized broader erosion, shallow pitting,
restrained cracks and gentle mineral discoloration. Keep the same average
tone and edge colors. Large quiet areas should still occupy most of the
image. Avoid rubble silhouettes, painted masonry joints or heavy marbling.
Actual missing corners and broken silhouettes will remain geometry work.

### 13. `aw_floor_wet.png` — damp paving variant

**Master:** 1024×1024. **Tiling:** both axes, compatible with item 4.
**Use:** water approaches, lower courts and waterfall-adjacent paving.

Keep the same slab layout and wear as item 4. Add subdued darker damp
patches, moss/algae confined mostly to joints and a few broad water stains
on the slab interiors. No mirror reflections, painted puddle edges, white
highlights or standing-water waves. This represents wet stone rather than
another water surface and should join cleanly to dry paving.

### 14. `aw_relief_b.png` — square ornamental plaque

**Master:** 1024×1024. **Tiling:** none; one complete plaque.
**Use:** square niche accents suggested by the second clip; new placements.

A square temple carving with two nested incised borders and a compact
central stepped or interlocking symbol. Surround it with restrained smaller
scroll details, leaving enough plain stone to make the center readable.
Weathered gray stone with muted olive staining and gentle recess contrast.
Avoid neon cyan, blue illumination, a painted doorway or an external cast
shadow. Its outer framing and recess depth can be modeled separately.

### 15. `aw_vine_sparse.png` — sparse hanging foliage

**Master:** 1024×1024 RGBA. **Tiling:** horizontal only.
**Use:** arches, important sightlines and selected existing vine faces.

Use the same leaf shape, woody stems and colors as item 8, with about
two-thirds of the image transparent. Several uneven thin hanging strands,
small separated leaf clusters and an irregular taper. Avoid a miniature
version of the whole dense curtain, rectangular clusters and hair-thin stems
that disappear when reduced. Preserve open gaps around the main silhouettes.

### 16. `aw_roots.png` — exposed root strands

**Master:** 512×1024 RGBA. **Tiling:** none.
**Use:** hanging or wall-adjacent root cards; thicker roots need geometry.

Several separated tapering brown-gray roots and woody lianas hanging
vertically, some gently curved or forked, with rough longitudinal grain and
small olive stains. A few tiny leaves are acceptable but roots dominate.
Substantial transparent gaps and clear ends, with no background wall, soil,
cast shadows or glossy wet highlights. Do not braid everything into a single
thick rope; each strand should have a readable silhouette.

### 17. `aw_fall.png` — waterfall master

**Master:** 512×1024. **Tiling:** both axes, with vertical continuity essential.
**Use:** the existing translucent waterfall brush models.

Soft elongated vertical water strands in muted gray-green and pale gray,
separated by subdued darker lanes. Irregular broad streak widths, subtle
periodic breakup and restrained fine spray within the surface. Avoid
horizontal waves, shoreline, rocks, a waterfall top/bottom or a white opaque
sheet. Supply one opaque color master; the harness will make matched scrolling
animation frames and apply transparency. Do not generate unrelated frames.

### 18. `aw_light.png` — narrow fixture strip

**Master:** 1024×256. **Tiling:** horizontal only.
**Use:** visible light fixtures; replacement for selected stock fixture art.

A narrow pale ivory luminous inset with a subtle desaturated cyan center,
surrounded by dark aged metal or stone. Simple repeated panel divisions,
small wear at the housing edges and broad readable shapes. The glow stays
inside the strip; no bloom halo, rays, lit wall or scene lighting. Keep the
housing sufficiently dark to separate the emitter from the surrounding stone.
Emission will be assigned deliberately during import and lighting.

### 19. `aw_metal.png` — aged structural metal

**Master:** 1024×1024. **Tiling:** both axes.
**Use:** grille bars, fixture housings and restrained hardware.

Continuous dark desaturated bronze/iron material with quiet oxidation,
sparse worn areas and faint green-brown patina. Matching the temple's subdued
palette, with no chrome reflections, gold shine, industrial warning stripes,
panel seams or rivets. This is a material for modeled hardware, so avoid
painting a whole grille into the texture. Keep enough midtone grain for
metal bars to remain readable in shadow.

### 20. `aw_grate.png` — small masked vent grille

**Master:** 1024×1024 RGBA. **Tiling:** both axes.
**Use:** selected distant decorative openings; optional masked surface.

A regular grille of narrow aged metal bars, with true transparent openings,
restrained oxidation and no perimeter frame. Use a simple clear spacing that
survives reduction; match item 19's material colors. No black painted voids,
wall background, large diagonal highlights or entire window scene. Existing
modeled bar grilles should normally use item 19; this cutout is for surfaces
where a texture grille is deliberately selected.

## Exterior and environment additions

### 21. `aw_cliff.png` — weathered exterior rock

**Master:** 1024×1024. **Tiling:** both axes.
**Use:** modeled rocky bases and exterior boundaries; new face assignments.

Broad gray-green rock planes with irregular fractures, restrained ledging,
small moss patches in crevices and subtle damp mineral staining. A related
tone to the temple stone but more naturally fractured. No masonry grid,
distinct central boulder, forest scene, silhouette, sunlight or deep black
canyon cracks. The cliff's large shape and breaks belong in geometry.

### 22. `aw_earth.png` — mossy ground cover

**Master:** 1024×1024. **Tiling:** both axes.
**Use:** exterior ground pockets and planted borders; new geometry/assignments.

Muted olive moss over dark brown-gray soil, irregular exposed earth patches,
a few small embedded stones and sparse subdued leaf fragments. Broad patches
with gentle variation rather than uniform green noise. No large roots,
raised grass blades, isolated rocks, walking paths or shadows. Keep the
surface compatible with mossy paving while making the softer earth readable.

### 23. `aw_grass.png` — grass and fern cutout set

**Master:** 1024×1024 RGBA. **Tiling:** none; one atlas with four isolated clumps.
**Use:** new foliage cards around exterior ground and water margins.

Four separated frontal clumps on transparency: two modest tufted grasses,
one broad fern and one small leafy ground plant. Muted green/olive foliage,
restrained brown bases, varied heights and open internal gaps. Leave clear
space between clumps for cropping. No pots, ground plane, shadows, atlas
labels, neon greens or extremely fine blades. Each clump should survive
being cropped and reduced to its own small texture.

### 24. `aw_bark.png` — exterior tree bark

**Master:** 512×1024. **Tiling:** both axes; grain runs vertically.
**Use:** modeled trunks, large branches and thick roots.

Old gray-brown bark with broad longitudinal ridges, shallow fissures,
sparse pale lichen and a little olive moss. Gentle variations in ridge width,
no dominant knot or distinctive mark that repeats on every trunk. Neutral
illumination and quiet recesses; no trunk outline, surrounding leaves,
forest scene or strongly raised highlights. Bark alone does not restore
the large exterior tree silhouettes visible in the footage.

### 25. `aw_canopy.png` — leafy branch cutout

**Master:** 1024×1024 RGBA. **Tiling:** none.
**Use:** new canopy cards or branches for modeled exterior trees.

One irregular spreading branch cluster with small-to-medium muted green
leaves, sparse visible gray-brown branches and roughly half the image
transparent. Vary leaf angles gently and retain open gaps through the
cluster. Avoid a complete round tree crown, hedge square, lit sky background,
sun shafts or tiny indistinct leaf noise. Match the hanging foliage family
while using a wider silhouette appropriate to a canopy branch.

### 26. `aw_sky.png` — pale overcast sky panorama

**Master:** 2048×1024 RGB. **Format:** equirectangular panorama; horizontal seam
must close. **Use:** a separately integrated sky treatment.

Soft pale overcast sky in pearl gray and faint desaturated blue-green, with
broad layered clouds and gentle value variation. Diffuse daylight, no visible
sun disc, dramatic sunset, lightning, sharply defined cloud edges or dark
storm front. No trees, buildings, mountains or ground baked into the sky.
Keep the lower panorama quiet and neutral. This panorama is source art;
it needs conversion to the chosen classic-sky or external-skybox format and
cannot be dropped directly into the current `sky_aw` WAD slot.

## Import notes for the next material pass

The current importer hashes three existing PNG sources, resamples them all
to 128×128, converts the stone to grayscale, and generates its own mortar,
carving and pad markings. It does not yet accept this larger pack unchanged.
When supplied, the new artwork needs a deliberate importer update: preserve
rectangular aspect ratios and useful olive/brown colors, register source
hashes, use the finished masonry/carvings directly, and stop drawing the old
procedural motifs over them. Keep physical repeats and anchors explicit.

The material pass will need downsample/palette previews, a tiled contact
sheet, trim/family alignment checks and final engine views. These textures
improve surface fidelity; trees, statues, large roots, deep carvings and
broken architectural silhouettes still need geometry. The existing verified
BSP/LIT is unchanged by this brief and the additional reference metadata.
