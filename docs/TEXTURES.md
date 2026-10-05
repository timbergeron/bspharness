# Texture sources

Makkon assets are excluded from the harness for now. Downloaded WADs stay
local in `assets/wads/`; the repository tracks links and generators.

## Start with stock id1

Extract from your local Quake install:

```sh
python3 -m bspharness id-wad /path/to/id1/pak0.pak /path/to/id1/pak1.pak \
  --output assets/wads/id1.wad --palette assets/palette.lmp
```

Both PAKs contain BSPs with embedded textures rather than a standalone WAD.
The command collects those miptex lumps into one WAD2. Later PAK/map
definitions win when names repeat. Unused missing texture slots in original
BSPs are skipped; malformed dimensions or mip offsets fail extraction.
The generated WAD and palette are not committed.

## Other WAD links

These links were checked on 2026-10-05. The style column suggests how we
might use each library; inspect previews before choosing a room palette.
The downloads do not become automatic harness dependencies.

| Library | Suggested direction | Download/source |
| --- | --- | --- |
| Knave | Gothic stone, ornament, and fortress interiors | [knave.wad](https://www.quaketastic.com/files/texture_wads/knave.wad) |
| IKBase | Industrial base and machinery | [ikbase.wad](https://www.quaketastic.com/files/texture_wads/ikbase.wad) |
| IKWhite jam set | Pale temple architecture | [jam2_ikwhite.wad](https://www.quaketastic.com/files/texture_wads/jam2_ikwhite.wad) |
| Honey | Warm, weathered medieval spaces | [honeywad.wad](https://www.quaketastic.com/files/texture_wads/honeywad.wad) |
| Arcane Dimensions | A broad material library for varied zones | [ad.wad](https://www.quaketastic.com/files/texture_wads/ad.wad) |
| DevQTex v2 | Layout blockouts and scale references | [devqtex_v2.zip](https://www.quaketastic.com/files/texture_wads/devqtex_v2.zip) |
| LibreQuake | Open-source alternative materials | [texture-wads directory](https://github.com/lavenderdotpet/LibreQuake/tree/main/texture-wads), [license](https://github.com/lavenderdotpet/LibreQuake/blob/main/docs/COPYING) |

For more libraries, browse [Quaketastic's WAD archive](https://www.quaketastic.com/files/texture_wads/)
or [Quaddicted's WAD archive](https://www.quaddicted.com/files/wads/).
Preserve each pack's readme, author credits, and usage terms with your local
copy, then credit textures used in the map release. A mirror URL alone does
not establish an asset license. Some collections mix original and adapted
game textures; inspect the pack's provenance before publishing a map.

Example local download:

```sh
curl -fsSL https://www.quaketastic.com/files/texture_wads/knave.wad -o assets/wads/knave.wad
python3 -m bspharness wad-info assets/wads/knave.wad
python3 -m bspharness wad-preview assets/wads/knave.wad \
  --palette assets/palette.lmp --output out/textures/knave
```

## Original development WAD

```sh
python3 -m bspharness blockout-wad assets/wads/blockout.wad
```

This produces `bh_wall`, `bh_floor`, `bh_ceil`, `bh_trim`, `bh_accent`,
`bh_light`, `sky_bh`, `trigger`, `clip`, `skip`, and `black`. They are original
procedural patterns encoded as Quake palette indices. No palette bytes or
third-party texture art are included. `bh_light` intentionally uses
fullbright indices; the architectural materials do not.

Use Quake WAD2, not Half-Life WAD3. Names must fit 15 ASCII bytes plus their
terminator; dimensions must be positive multiples of 16, up to 1024 here,
with four complete mip levels. Choose texture scale for the material's
resolution; no single scale is correct for every WAD.
Use [Material](MATERIALS.md) for texel density, shared physical repeat sizes,
and alignment anchors. Duplicate names resolve from the last WAD in the
MAP's list with the pinned ericw compilers.
