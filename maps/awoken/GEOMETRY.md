# Awoken geometry refinement

The supplied recording is the visual authority. Its 640x360 frames do not
provide measured brush coordinates, so new profile dimensions are inferred
and fitted to 4Bidden's recovered layout. This pass improves the existing Q1
adaptation; it does not claim an exact reconstruction of the QC original.

| Native video frame | Shape used as guidance | Geometry treatment |
| --- | --- | --- |
| 0:45 and 1:05 | Thick angular jambs, several layers around an opening | Chamfer exposed stone corners; retain the angular opening and its usable width |
| 1:55 and 10:05 | Distinct upper/lower tiers with projecting stone bands | Shape seventeen upper beams with sloping lips, recessed fascia and lower reveals |
| 2:55 and 4:55 | Narrow ornamental panels surrounded by thick stone | Model four stone frame pieces around each of eleven reliefs; set the carved center seven units behind the rim |
| 6:00 | Flat ashlar faces divided by slender supports | Keep broad stone faces planar and give exposed slender upright corners a finer profile |

`geometry.py` indexes the immutable recovered solids in 128-unit cells.
An edge is eligible only if both adjacent faces are exposed at seven points
along its full length. Shared structural joints, changing arch profiles, sky, water, clips, triggers,
grate bars and small brushes are excluded. The cuts remain inside the
original solid. Every refined walking surface is rebuilt into the player
collision hull; there is no invisible square wall behind a visibly rounded
door jamb.

The final recipe refines **464 edges on 245 brush pieces**: 413 crisp
chamfers and 51 quarter-round transitions on slender supports. A chamfer
uses one cutting plane; a support transition uses three tangent planes.
Profile sizes are capped at eight units and at one fifth of the brush's
smallest dimension. Treads and walking ledges use at most two units. Short
edges below 24 units are retained. The relief surrounds are shallow
nonblocking decoration, like the vines and lift markings.

The cornice profile is split into nine convex horizontal slices. From its
bottom it slopes from an eight-unit inset to the original edge over eight
units, retains a twelve-unit lip, steps into a six-unit reveal, then carries
a two-unit recessed fascia up to the top lip. The rear wall volume remains
continuous as a simple six-plane structural core. The nine shaped slices
are solid compiler wall detail; this preserves their envelope and collision
without adding a visibility partition for each decorative strip. No enclosing shell is added, so a sealing mistake must still
fail the normal leak test.

Lighting uses a 30-degree convex smoothing threshold and a one-degree
concave threshold. This softens the 22.5-degree support facets while keeping
45-degree chamfers and recessed joints distinct. The thresholds follow
[ericw's light documentation](https://ericw-tools.readthedocs.io/en/latest/light.html).
Stone artwork and lighting exposure remain those of the prior video pass.
The inherited flowing waterfall is now a separate pair of nonblocking
`func_illusionary` brush models at alpha 0.42, with eight original animated
texture frames. This fixes the previous opaque green sheet without making
all pond water transparent. The
[QuakeSpasm entity parser](https://github.com/sezero/quakespasm/blob/master/Quake/pr_edict.c)
supports alpha even with stock QuakeC; the actual QSS-M renders are reviewed.

An initial draft rounded all eligible corners with three planes. It
exceeded the original collision growth limit and was discarded. The
angular masonry treatment both matches the footage better and stays within
the two-times reference limit. The reviewed recipe uses a 16,000-face and
8,500-clipnode budget; the prior video release had 8,706 faces and 4,453
clipnodes. The retained [video baseline](baselines/video-v2.json) identifies
that exact previous release. [The current baseline](baseline.json) records
the final measured counts and artifact hashes.

Validation covers all 23 previous movement probes plus return walks through
the lower court, rocket terrace and grenade bridge. An actual stock DM
spawn/item pass remains separate. The five previous fixed views are joined
by close views of a cornice, a relief and the rocket arch. All eight captures
must be inspected and bound to the final BSP and LIT before packaging.
The before/after export uses those same eight views and adds four geometry
reference frames to the six material reference frames.
The engine checks explicitly set `edgefriction 2`, and any rejected console
command invalidates QA. This corrects an earlier harness command that used
the C variable name `sv_edgefriction` and left the engine's default in use.

The source recipe and profile records are included in the release archive.
The old stock release and the preceding video release are preserved locally
as `dist/awoken-v1.zip` and `dist/awoken-v2.zip`. A populated match is still
needed to assess combat balance, and the exterior trees/statue are outside
this architectural pass.
