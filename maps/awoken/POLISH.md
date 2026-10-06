# Awoken video reference pass

The supplied 640x360, 30 fps recording is recorded by hash in
[reference.json](reference.json). Six native frames and contact sheets were
inspected locally. The video is visual guidance; the Q2 BSP remains the
brush-layout reference.

| Video time | Observed element | Treatment in the Q1 adaptation |
| --- | --- | --- |
| 0:00 | Large angular door opening and thick stone jambs | Retain the recovered profiles; map the rough brown frames to neutral stone |
| 0:50 | Green water and cool light at the lower court | Original muted green water texture and localized blue light cues |
| 1:20 | Recessed carved panels and broad stone bands | Original geometric relief texture, with eleven shallow beveled wall panels |
| 2:30 | Pale gray-green courtyard, large blocks and blue-lit lower opening | Periodic ashlar courses, consistent anchors, and lower exposure appropriate to pale stone |
| 6:00 | Clean large stone faces, narrow carved accents and quiet flooring | Restrained slab grain, smaller relief accents and regular flagstones |
| 9:40 | Hanging roots/vines, stone terraces and contrasting shade | Restore 45 original vine-brush locations using original masked foliage; retain roof shadows |

Three new bitmap sources were made with the built-in imagegen tool.
[art.json](art.json) retains the exact prompts and source SHA-256 values.
They are converted locally to WAD2 with opaque colors below the fullbright
range and index 255 reserved for the vine cutout. Captured video pixels are
not used as map textures. Makkon remains excluded.

`materials.py` authors exact repeating masonry joints and paving lines from
the neutral material grain. Vines use a shared world anchor; recovered Q2
offsets would break continuity where adjacent panels meet. `polish.py`
places beveled carvings only on sufficiently large exposed wall faces. All
new reliefs, pad markings and foliage are compiler illusionary details.
The player collision count remains 4,453 clipnodes.

The lighting recipe uses lower sun/sky values, one bounce, and a common
0.45 factor on point lights. The pale albedo needs less illumination than
the original dark stock palette. Cool cues identify the pad/teleporter
areas while stone frames retain a consistent material treatment.

Use the five original camera coordinates for before/after review. Final
validation still requires all 23 movement probes, an actual deathmatch
spawn/item audit, and reviewed screenshots bound to both BSP and LIT.
The stock recipe and its first release baseline remain available. Trees,
grass and bushes are not restored in this pass; populated match balance
and measured equivalence to the QC layout remain separate work.
