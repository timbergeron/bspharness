# High-resolution generated textures

The October 6 texture pass imports all 26 user-supplied PNGs from
`textures_gen/`. `art.json` records their original SHA256, dimensions and
channels. Copies in `assets/awoken/` remain byte-identical. The incoming
folder, PNGs, generated WAD, runtime replacements and build products are
excluded from Git; the release archive includes the complete source art.
The previous three-image recipe is preserved in `art-v1.json`.

All 26 surface masters retain their native RGB/RGBA channels and exact
bytes. Most are 1254 × 1254. Carvings and waterfalls are 887 × 1774; the
carved strip is 2172 × 724; lights are 2508 × 627.

QSS-M's horizontal mip routine walks pairs of pixels across the entire
buffer instead of restarting each row. On odd-width mip levels this shifts
successive rows, producing diagonal smearing. Even an initially even width
such as 1254 reaches an odd 627-pixel mip. Native upload dimensions alone
cannot detect this visual defect; it was found in the close camera review
and confirmed in `Quake/gl_texmgr.c:TexMgr_MipMapW`.

`runtime.py` therefore derives power-of-two runtime PNGs without reducing
any axis. Most surfaces become 2048 × 2048; portrait reliefs and waterfalls
become 1024 × 2048; strips and lights become 4096 × 1024. Lanczos
interpolation preserves source detail rather than inventing new detail.
The untouched native masters accompany the release. Normalized BSP UVs
retain the original artwork's physical aspect ratio, including the 3:1
carved strip. Alpha remains a channel, rather than an opaque background.

BSP29 embeds compact indexed miptex fallbacks with the source aspect ratio.
Engine replacement UVs use those fallbacks' physical repeat sizes, so the
high-resolution images do not multiply lightmap density or compiler work.

`materials.py` directly imports finished artwork. It does not redraw the
mortar joints, replace carvings, recolor the stone, or flatten PNG alpha.
Only embedded fallbacks use Quake's palette and reduced dimensions. Their
opaque colors exclude the fullbright range; cutouts use index 255.

## Placement

- Base masonry and quiet plain stone cover the architectural shell and its
  existing chamfers. Cliff art covers the recovered rough-rock regions.
- Moss wall and floor variants occupy coherent damp courts. Floor wetness
  has its own lower waterside area, with the same world texture phase.
- The 3:1 carved trim occupies the broad central fascias of the 17 profiled
  cornices. Its physical repeat retains the supplied aspect ratio.
- Tall scroll reliefs use the modeled recessed surrounds; square motifs fit
  recovered square panels. Pad artwork fits
  the complete 80 × 80 floor insets. Light strips retain their 4:1 proportion.
- High-resolution metal replaces the recovered metal/grille regions. Both dense and
  sparse hanging ivy use the retained nonblocking foliage brushes.
- The pond uses the supplied green water. Eight high-resolution waterfall frames wrap
  the supplied streaks downward with Quake's standard texture animation.
- The 1774 × 887 sky master is interpreted as a 2:1 equirectangular panorama
  and projected onto six 512 × 512 cube faces using Quake's sky axes.
  Each 90-degree face has roughly 443 source samples; larger output faces
  would add interpolation rather than detail. The original stays in source/art.

The remaining imported assets are available for a later geometry pass:
un-jointed wet wall, heavily worn stone, roots, transparent
grate, grass atlas, bark, canopy and earth. Their native masters and WAD
entries are preserved. Existing thin solid grille bars keep their modeled
shape and use metal; applying a transparent grate on top would duplicate it.
Grass/canopy atlases need isolated UV regions and new foliage geometry.
The wet wall's pattern differs from the masonry and is not declared as a
seam-compatible masonry variant. No trees or large new decoration are
added in this material pass. No Makkon textures are used.

Common world coordinates keep material phase stable. Separate generated
images can still differ in joints, color or border detail: a clean UV audit
alone does not prove that their painted edges are seamless. Camera review
covers the principal courts and close architectural details; broader
playtesting remains useful.

## Build and install

```sh
python3 maps/awoken/build.py --style video
python3 -m bspharness build src/awoken.map --profile final --threads 8 \
  --timeout 3600 --max-faces 16000 --max-clipnodes 8500
```

The generator writes `src/awoken.assets.json`, binding runtime PNG hashes
and dimensions to the MAP. The compiler snapshots those files into the
build's `runtime/` directory. QA automatically stages that snapshot into a
fresh game directory, checks the engine's `imagelist` dimensions and rejects
fallbacks or reduced uploads. Camera inspection verifies the mipmap result. Packaging checks the same
bundle against movement, deathmatch and accepted visual review reports.

Extract `maps/`, `textures/` and `gfx/` from the release archive into the
same Quake game directory. Set `gl_load24bit 1`, `gl_max_size 0`,
`gl_picmip 0`, `r_fastturb 0` and `r_fastsky 0` before `map awoken`.
Use QSS-M with high-resolution external PNG and masked texture support. The BSP/LIT alone
remain a playable indexed fallback, but the PNG folders are required for
the full-color high-resolution presentation. Hardware can impose its own
texture limits; QA records the actual uploaded dimensions.

External texture variants do not require rebuilding unchanged BSP/LIT files.
`bspharness bind-assets <bsp> <assets.json> --out <fresh-directory>` verifies
the exact compiled MAP hash, preserves the original build, copies the
unchanged BSP/LIT/evidence and binds a new checked runtime bundle. All QA
and accepted visual reviews must be redone for that bundle before release.
