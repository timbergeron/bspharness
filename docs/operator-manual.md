> Historical field notes imported from `../mapharness.md` on 2026-10-05.
> The `$DM`/`$Q` paths, example assets, and observed compiler quirks describe
> earlier projects. Use this repo's README and WORKFLOW for current commands.
> No Makkon textures or skyboxes are included or downloaded by this harness.

# Quake Map Harness — Complete Operator's Manual

An editor-free, fully scriptable toolchain for **creating Quake 1 maps from
code** and **performing surgical edits on existing maps**, with automated
in-engine QA. Everything is a shell command or a small dependency-free Python
script; verification is done by parsing the BSP binary and by making the
engine drive itself, take screenshots, and dump its entity state.

Proven on four deliverables:

| project | what the harness did |
|---|---|
| **sundial** | 1on1/2on2 QW duel map generated 100% from Python — layout, brushes, textures, items, lighting, compiled BSP with embedded colored lighting |
| **dm3 relit** | relit id's dm3 using only sunlight + emissive surfaces + bounce, in every modern BSPX lighting format (DECOUPLED_LM, LIGHTGRID, HDR) |
| **tbsketch_05_7 / tbsketch_30** | fixed walkable-sky voids: lowered sky floors, extended seal walls, added kill triggers, recompiled ornate TB maps |
| **start.map** | sealed a 512×512 floor hole with a glass pane cloned from the map's own glass construction, BSP2 preserved |

Conventions in this manual:
- `$DM` = harness root, here `~/codedev/dmjam`
- `$Q`  = QSS-M install, here `~/Desktop/qssm`
- All Python is 3.x, stdlib only. All BSP/WAD parsing is `struct.unpack`.

---

# Part I — Setup

## 1.1 Directory layout

```
$DM/
├── tools/
│   ├── qbsp, vis, light, bsputil, bspinfo    ericw-tools 2.0.0-alpha11
│   ├── v018/…/bin/qbsp                       ericw-tools v0.18.2-rc1 (fallback)
│   ├── build.sh                              full iteration loop (§4.6)
│   ├── wadview.py                            WAD → PNG previews (§5.1)
│   ├── makewad.py                            utility-WAD generator (§5.2)
│   └── relight_dm3.py                        example map-transform script (§8.2)
├── wads/          all 16 Makkon WADs (~5GB) + sundial_util.wad
├── skybox/env/    Makkon skyboxes: 35 sets of six TGAs
├── refs/          palette.lmp, reference maps + extracted entity lumps,
│                  WAD listings, texture preview PNGs, extracted wads
├── src/           map sources — generated (gen.py output) or patched copies
├── out/           compile products: .bsp .lit .prt .log
├── ramaps/        user-provided maps under edit (+ *_old.bsp backups,
│                  *_fixed.map patched sources, *_orig.wad extractions)
└── dist/          release zips
$Q/dmjam/          engine test gamedir: maps/, gfx/env/, configs/, shots.cfg
```

## 1.2 Install compile tools

```sh
mkdir -p $DM/tools && cd $DM/tools
curl -sL -o ericw.zip https://github.com/ericwa/ericw-tools/releases/download/2.0.0-alpha11/ericw-tools-2.0.0-alpha11-Darwin.zip
unzip -q ericw.zip && chmod +x qbsp light vis bsputil bspinfo
# x86_64 binaries; run fine on Apple Silicon via Rosetta.

# fallback qbsp (mandatory for detail-heavy TB maps — see Part V)
mkdir -p v018 && cd v018
curl -sL -o e18.zip https://github.com/ericwa/ericw-tools/releases/download/v0.18.2-rc1/ericw-tools-v0.18.1-32-g6660c5f-Darwin.zip
unzip -q e18.zip    # binary: ericw-tools-v0.18.1-32-g6660c5f-Darwin/bin/qbsp
```

## 1.3 Assets

**Makkon WADs** (slipseer resource 28). The resource page is multi-file; each
file is `index.php?resources/makkon-textures.28/version/NNN/download&file=NNNN`.
Download all zips, extract only `*.wad` into `$DM/wads/`. ~5GB total. Note the
WADs are periodically renamed internally — current packs use `conc_`, `tch_`,
`stn_`, `ind_`, `urb_` prefixes; **older maps may reference retired names**
(e.g. `stone_tan_*` predates the `stn_` rename) — recovery procedure in §7.2.

**Makkon skyboxes** (resource 139): single zip of TGAs,
`mak_<name>_{bk,dn,ft,lf,rt,up}.tga` → `$DM/skybox/env/`.

**Quake palette**: copy `id1/gfx/palette.lmp` (768 bytes = 256×RGB) from any
extracted id1 install to `$DM/refs/palette.lmp`. Required by wadview/makewad.
(If you only have pak files, extract it — pak reader in §6.6.)

**Utility WAD**: run `python3 tools/makewad.py` → `wads/sundial_util.wad`
containing `trigger`, `clip`, `skip`, `black` (16×16 flats) and `sky_sundial`
(a 256×128 dual-layer sky quantized from a real skybox TGA, so software
renderers see something sane). Reference it from any map that needs tool
textures.

## 1.4 Engine test gamedir

```sh
mkdir -p $Q/dmjam/maps $Q/dmjam/gfx/env $Q/dmjam/configs
echo "exec shots.cfg" > $Q/dmjam/configs/connect.cfg    # the QA hook — §4.1
```

A bsp in `$Q/dmjam/maps/` **shadows** the id1 map of the same name when the
engine runs `-game dmjam` — safe testing of edited id/custom maps without
touching the real install.

---

# Part II — The compile pipeline in depth

## 2.1 Standard pipeline

```sh
cd $DM/out
$DM/tools/qbsp -leaktest $DM/src/MAP.map MAP.bsp
$DM/tools/vis MAP.bsp
$DM/tools/light -extra4 -lit -bspxlit MAP.bsp
```

- **qbsp** `-leaktest` makes an unsealed map a hard error instead of a
  warning + broken vis. Other useful flags: `-bsp2` (large maps / >32k
  clipnode indices), `-noclip` (skip collision hulls, blockout previews),
  `-onlyents` (re-emit entity lump only — instant item/light entity edits
  without recompiling geometry, but NOT for light changes since light bakes).
- **vis**: reads `MAP.prt` produced by qbsp — the `.prt` must sit beside the
  bsp. Without it vis "succeeds" with ~empty visdata. Small maps: seconds.
  A tiny compressed visdata (~1–2KB) is *normal* for open-plan maps where
  every leaf sees everything (e.g. a tower floating in a skybox).
- **light** `-extra4` = 4×4 supersampling (final quality; drop for drafts).
  `-lit` writes external `MAP.lit` (colored light for all engines);
  `-bspxlit` embeds the same RGB data as a BSPX `RGBLIGHTING` lump.
  Vanilla mono lightdata is always written too → the bsp works everywhere.

## 2.2 Advanced lighting formats (the dm3 treatment)

```sh
light -extra4 \
  -world_units_per_luxel 8 \
  -lightgrid \
  -bspxhdr \
  -lit -bspxlit MAP.bsp
```

| flag | BSPX lump | effect |
|---|---|---|
| `-world_units_per_luxel 8` | `DECOUPLED_LM` | lightmap density decoupled from texinfo; 8u/luxel = 4× vanilla shadow resolution (razor-sharp beam shadows). Per-entity override key: `_world_units_per_luxel`. |
| `-lightgrid` | `LIGHTGRID_OCTREE` | baked 3D light samples; dynamic entities (players, items, gibs) get correct ambient instead of floor-sample guessing. `-lightgrid_dist x y z` controls spacing (default 32³). |
| `-bspxhdr` | `LIGHTING_E5BGR9` | HDR lightmaps (RGB9E5); smooth overbrights. `-hdr` writes an HDR .lit instead. |
| `-bspxlit` | `RGBLIGHTING` | classic colored lighting embedded |

QSS-M supports all four (verified in its `gl_model.c`). Old engines ignore
BSPX and use the vanilla lump. Cost example: dm3 full advanced bake ≈ 2.5 min
on M1 Pro; a big open map with `_sunlight2 800` ≈ 6–7 min.

## 2.3 Worldspawn lighting key reference

```
"_sunlight"           "300"              sun intensity
"_sunlight_color"     "255 193 130"
"_sun_mangle"         "40 -50 0"         yaw pitch roll. yaw = compass direction the
                                         light TRAVELS toward (sun sits at yaw+180);
                                         pitch negative = downward. "0 -90 0" = noon.
"_sunlight_penumbra"  "3"                soft sun edge, degrees
"_sunlight2"          "400"              sky dome light (emitted from all sky faces,
"_sunlight2_color"    "255 205 170"      hemispherical) — the main outdoor fill
"_sunlight3"          "200"              upward dome (ground bounce fake)
"_bounce"             "1"                enable radiosity bounces (int = passes)
"_bouncescale"        "1.25"
"_bouncecolorscale"   "1"                texture-colored bounce; MAX IS 1 (warns above)
"_dirt"               "1"                baked AO
"_dirtscale"          ".7"               higher = darker AO; 0.65–0.9 typical
"_dirtdepth"          "256"              occlusion ray length
"_anglescale"         "1"                n·l falloff strength (0.6 = softer interiors)
"_minlight"           "16"               floor for playability; 12–16 for MP maps
```

**Sun geometry math you'll actually use:** at pitch p, a wall of height h
casts a shadow of length h/tan(|p|). Pitch −38° over a 520u parapet shadows
665u — the entire yard. Steepening to −50° (shadow 0.84×h) is what produced
sundial's signature diagonal shadow line. For light beams through a window at
height H above the floor, the pool lands H/tan(|p|) horizontally away, split
into x/y by cos(yaw)/sin(yaw).

## 2.4 Light entities

Point light (Makkon-style, measured from his dmak4 BSP):

```
{ "classname" "light" "origin" "X Y Z"
  "light" "500" "_color" "255 219 175" "delay" "5" "wait" "2" }
```
`delay 5` = inverse-square falloff, `wait` scales the falloff distance
(2–3 typical). Warm 255/219/175 is Makkon's standard interior color; accent
colors: cool blue `150 220 255` (item markers), teal/purple for teleporters,
`255 120 40` lava glow.

Sun-via-entity alternative (Makkon uses this): a light with `"_sun" "1"`,
`"target"` pointing at an info_target — direction = entity→target vector.
Worldspawn `_sun_mangle` is simpler for codegen.

Surface lights — one template makes every face with that texture emit:

```
{ "classname" "light" "origin" "0 0 128"
  "_surface" "tlight02" "light" "380" "_color" "255 230 180" "delay" "2" }
```
This is the core of the "relight with no point lights" method: sun + dome +
one template per emissive texture (fixtures, teleporter surfaces, EXIT signs,
computer LEDs, lava) + `_bounce 2`. Related light flags:
`-surflight_subdivide n`, `-surflight_radiosity 0|1`, `-emissivequality high`.

## 2.5 Tool quirks (each one cost real debugging time)

- ericw binaries resolve **bare relative paths against the binary's own
  directory**, not the CWD. Always pass absolute paths.
- `bsputil -extract-textures foo.bsp` is the only working arg form; it writes
  `foo.wad` next to the bsp (the `-extract-textures out.wad in.bsp` form in
  the help errors with `std::exception`).
- Progress bars flood non-tty output: filter with `grep -viE 'est:|^\['`.
- "brush has multiple face contents (SOLID vs SKY)" — harmless if you mix sky
  and wall textures on one brush; qbsp keeps SOLID contents, sky *faces*
  still render skybox and still emit sun in light.
- "N faces crunched away by being too small" — cosmetic, ignore.
- Worldspawn `"wad"` values ≥127 chars → harmless warning.
- Liquid/teleport `*textures` define brush **contents**: a brush mixing a
  `*tele` face with solid faces is a "mixed contents" error. Visual tele/lava
  panes must be all-`*texture` brushes (they become non-solid, walk-through);
  put solid trim frames around them as separate brushes.
- `light` styles: `_bouncestyled 1` lets styled (switchable) lights bounce.

---

# Part III — Generating a map from code (the sundial method)

The generator (`$DM/src/gen.py`, ~500 lines, stdlib only) emits a Valve-220
`.map`. Three ideas make codegen robust enough to ship: **air-volume
complement** (§3.2), **adjacency texturing** (§3.3), and **auto-oriented
faces** (§3.1). Then geometry becomes arithmetic.

## 3.1 Brush emitters — never hand-wind a plane

A Valve-220 face line is:

```
( x1 y1 z1 ) ( x2 y2 z2 ) ( x3 y3 z3 ) TEXNAME [ ux uy uz uoff ] [ vx vy vz voff ] rot sx sy
```

The three points define the plane; winding determines the normal:
`n = cross(p1−p2, p3−p2)` must point OUT of the brush. Getting this right by
construction is fragile — instead every brush is passed an interior point and
each face is flipped if `dot(n, p2 − interior) < 0`:

```python
class Face:
    def __init__(self, pts, tex, scale=1.0, uoff=0, voff=0):
        self.pts, self.tex, self.scale = pts, tex, scale
        self.uoff, self.voff = uoff, voff
    def normal(self):
        p1,p2,p3 = self.pts
        return cross(vsub(p1,p2), vsub(p3,p2))
    def line(self):
        u,v = uv_axes(self.normal())
        p = " ".join(f"( {fnum(a[0])} {fnum(a[1])} {fnum(a[2])} )" for a in self.pts)
        return (f"{p} {self.tex} [ {u[0]} {u[1]} {u[2]} {fnum(self.uoff)} ] "
                f"[ {v[0]} {v[1]} {v[2]} {fnum(self.voff)} ] 0 {fnum(self.scale)} {fnum(self.scale)}")

class Brush:
    def __init__(self, faces, interior):
        self.faces = []
        for f in faces:
            n = f.normal()
            d = dot(n, vsub(f.pts[1], interior))
            if abs(d) < EPS: raise ValueError("degenerate face")
            if d < 0:
                f = Face((f.pts[2], f.pts[1], f.pts[0]), f.tex, f.scale, f.uoff, f.voff)
            self.faces.append(f)
```

UV axes: world-aligned by dominant normal axis (this makes 512px textures at
scale 1.0 tile seamlessly across brush seams with zero alignment work —
Makkon textures are designed for exactly this):

```python
def uv_axes(n):
    ax, ay, az = abs(n[0]), abs(n[1]), abs(n[2])
    if az >= ax and az >= ay:  return (1,0,0), (0,-1,0)   # floors/ceilings
    if ax >= ay:               return (0,1,0), (0,0,-1)   # X-facing walls
    return (1,0,0), (0,0,-1)                              # Y-facing walls
```

Two emitters cover 95% of geometry:

```python
def box(x0,y0,z0,x1,y1,z1, tex=DEFAULT, top=None, bottom=None,
        north=None, south=None, east=None, west=None, scale=1.0):
    """Axis-aligned box with optional per-face textures."""
    t = lambda o: o if o else tex
    faces = [
        Face(((x0,y0,z1),(x0,y1,z1),(x1,y1,z1)), t(top), scale),     # +z
        Face(((x0,y0,z0),(x1,y0,z0),(x1,y1,z0)), t(bottom), scale),  # -z
        Face(((x0,y1,z0),(x1,y1,z0),(x1,y1,z1)), t(north), scale),   # +y
        Face(((x0,y0,z0),(x0,y0,z1),(x1,y0,z1)), t(south), scale),   # -y
        Face(((x1,y0,z0),(x1,y0,z1),(x1,y1,z1)), t(east), scale),    # +x
        Face(((x0,y0,z0),(x0,y1,z0),(x0,y1,z1)), t(west), scale),    # -x
    ]
    return Brush(faces, ((x0+x1)/2,(y0+y1)/2,(z0+z1)/2))

def ramp(x0,y0,x1,y1, zbase, zs, ze, along='x', tex=DEFAULT, top=STAIRTEX):
    """Wedge prism: top surface slopes from zs (at low coord) to ze (at high
    coord) along the given axis; flat bottom at zbase. Degenerate end caps
    (where slope meets base) are fine — qbsp discards zero-area faces."""
    if along=='x': slope = ((x0,y0,zs),(x1,y0,ze),(x1,y1,ze))
    else:          slope = ((x0,y0,zs),(x0,y1,ze),(x1,y1,ze))
    faces = [Face(slope, top),
             Face(((x0,y0,zbase),(x1,y0,zbase),(x1,y1,zbase)), tex),
             Face(((x0,y1,zbase),(x1,y1,zbase),(x1,y1,zbase+8)), tex),
             Face(((x0,y0,zbase),(x0,y0,zbase+8),(x1,y0,zbase)), tex),
             Face(((x1,y0,zbase),(x1,y0,zbase+8),(x1,y1,zbase)), tex),
             Face(((x0,y0,zbase),(x0,y1,zbase),(x0,y1,zbase+8)), tex)]
    # interior: a point inside near the tall end, low
    ...
    return Brush(faces, interior)
```

## 3.2 Air-volume complement — sealed by construction

**You never build walls.** Declare the playable space as AABBs; the solid
world is computed as `world_bounds − union(air)`:

```python
air('A',      -832,-192,0,  -320,448,448)                 # RA atrium
air('B',      -320,64,0,     320,256,320)                 # corridor abutting A
air('C',       320,-64,0,    896,576,384)                 # open yard
air('C_sky',   320,-64,384,  896,576,448, kind='sky')     # sky cap above C
air('A_win1', -864,-64,224, -832,64,384,  kind='window')  # window into A's wall
```

Subtraction is the classic 6-way split, applied air box by air box:

```python
def sub_box(s, a):          # AABB s minus AABB a -> up to 6 AABBs
    if no_overlap(s, a): return [s]
    out=[]
    if a.x0>s.x0: out.append(left_slab)      # x below
    if a.x1<s.x1: out.append(right_slab)     # x above
    # middle x-band: split in y, then the middle y-band split in z
    ...
    return out

solids=[world_bounds]                # world = union(air) + 64u padding
for a in airs:
    solids = [piece for s in solids for piece in sub_box(s, a.bounds)]
```

Properties that fall out of this:
- **The map cannot leak.** `qbsp -leaktest` passed on the first compile and
  every compile after. This is the single biggest de-risker for codegen.
- **Doorways are free**: where two air boxes abut on a shared plane, the
  overlap of their cross-sections *is* the opening; the non-overlap seals
  automatically as wall/reveal. To make a door: just make the corridor's
  cross-section smaller than the room's wall.
- **Windows**: a small `window` air box embedded in a wall's thickness whose
  outer boundary faces become sky (light enters, view of skybox), with sills
  as trim.
- **Sky wells**: a `sky` air box stacked on a room; all faces bordering it get
  the sky texture; parapet height controls how much sun rakes in (§2.3 math).
- Keep all coordinates on a 32/64 grid; the complement then stays on-grid.
- Wall thickness = the padding (64u minimum keeps hull expansion honest).

One structural subtlety: a single complement solid can border a `room` volume
*and* a `sky`/`window` volume, but a face can only have one texture — so
before texturing, split all solids along the boundary planes of every flagged
(sky/window) volume. Cheap and eliminates the whole class of bugs.

## 3.3 Per-face texturing by adjacency

Every air volume carries a palette: `wall=`, `floor=`, `ceil=`. When emitting
a complement solid, classify each face:

```python
def face_border_air(face_rect, plane_axis, plane_val, normal_sign, airs):
    """Air volume whose boundary coincides with this face's plane and
    overlaps it in 2D; largest overlap wins."""
```
- borders `sky` volume → SKY texture
- borders `window` → SKY if the face is vertical, trim if horizontal (sill)
- borders a room → `floor` if face points up, `ceil` if down, else `wall`
- borders nothing (void side / buried) → default; qbsp strips unseen faces

Per-room palettes give instant art direction: sundial used gray concrete
walls everywhere, one teal accent wall per zone, yellow trim reserved for
item ledges and teleporter frames, distinct wall variants per corridor so
players orient by texture. (Makkon usage rules measured from his own maps:
scale 1.0, huge calm surfaces, trim only at transitions.)

## 3.4 Details, entities, lights

Details (ramps, ledges, plinths, bridges, door-frame trims, glowing light
strips) are ordinary brushes placed **inside** air volumes — they can never
unseal the map. Door frames: three 8u-deep boxes (two jambs + header) around
an opening. Light fixtures: a thin box textured with a fullbright strip
(`+0tch_light_1`) + a point light 24u in front + optionally one `_surface`
template for the glow.

Entities are dicts; brush entities take brush lists:

```python
ent('item_armorInv', (-512,400,296))               # RA
ent('info_player_deathmatch', (-576,-64,24), angle='45')
ent('info_teleport_destination', (-752,384,296), angle='0', targetname='t_ra')
brush_ent('trigger_teleport', [box(...,tex='trigger')], target='t_ra')
brush_ent('trigger_push',     [box(...,tex='trigger')], angle='-1', speed='750')
```

**Entity placement rules (each violated once, each cost a debug cycle):**

| rule | why |
|---|---|
| quad/pent: origin ≥ 24u above the surface | their bbox extends 24 below origin; embedded items are **silently removed** (droptofloor starts solid; dprint needs `developer 1`) |
| health/ammo boxes are corner-origin, 32×32×56 | give side clearance in alcoves; center them by placing origin at corner−16 |
| nothing overlapping ramps/wedges | the wedge's volume extends to its bounding box only visually — compute the slope z at the item's x/y before placing |
| teleport destinations at floor+8 are fine | progs add +27z on spawn |
| `trigger_push` `angle -1` = straight up | apex ≈ speed²/1600 units (Quake gravity 800); 750 → ~351u |
| DM spawns: `info_player_deathmatch` + one `info_player_start` | angle key faces them somewhere sane; keep ≥ 64u from walls |

## 3.5 Gameplay design data (measured, not vibes)

Decompiled entity lumps of five top duel maps (aerowalk, ztndm3, bravado,
skull, pocket) — extraction is §6.1, data in `$DM/refs/*_ents.txt`:

- Footprint ~1400–1900 × 1600–2400, vertical 600–900.
- **Every one has two RLs** and an LG. SSG/GL common; NG/SNG optional.
- Armor economy: RA (control point, high/contested), YA (challenger stack),
  1–2 GA (rotation snacks). Mega in all five; quad in the 2on2-oriented ones.
- 5–8 DM spawns spread across all zones.
- Health ≈ 3×25 + 5–8×15 spread low; ammo low where weapons are strong
  ("RL on high ground ⇒ ammo on low ground" — camping tax).
- ~3 contestable zones for 2on2 ("you can never fully hold all three").
- QW movement: ramps instead of stairs wherever you *want* speed (bunnyhop
  language); stairs only where slowing players is strategic. Slopes ≤ ~30°.
  Standard walkable limit ≈ 45°; step-up ≤ 18u is automatic.
- Useful dims: corridors ≥ 128 (main routes 192+), ceilings 160–256+
  (rocket-jump headroom), door openings ≥ 128 tall / 96 wide, jump gap ≤ 250u
  with speed.

Makkon lighting recipe (from dmak4's worldspawn + lights, via §6.1):
`_bounce 1, _bouncecolorscale 1(.5 clamps), _dirt 1 _dirtdepth 256
_dirtscale .75, _anglescale 1, _sunlight2 400–600` + warm points as §2.4.

## 3.6 The iteration loop

`$DM/tools/build.sh shots`:

```sh
#!/bin/zsh
set -e
cd $DM/out
python3 $DM/src/gen.py $DM/src/sundial.map
$DM/tools/qbsp -leaktest $DM/src/sundial.map sundial.bsp 2>&1 | grep -iE 'leak|warning|error' || true
$DM/tools/vis sundial.bsp 2>&1 | tail -1
$DM/tools/light -extra4 -lit -bspxlit sundial.bsp 2>&1 | grep -i completed
cp sundial.bsp sundial.lit $Q/dmjam/maps/
if [ "$1" = "shots" ]; then
  rm -f $Q/dmjam/screenshots/*.png
  cd $Q && ./QSS-M.app/Contents/MacOS/QSS-M -basedir $Q -game dmjam \
     -window -width 1280 -height 720 +map sundial >/dev/null 2>&1
  # engine runs shots.cfg via connect.cfg hook, screenshots itself, quits
fi
```

Full round trip ≈ 30s for a duel-sized map. The loop is: look at PNGs →
change numbers in gen.py → rerun. Treat lighting tuning like exposure
bracketing: first bake always reads dark; raise `_minlight`, `_sunlight2`,
point multipliers before touching the sun.

---

# Part IV — In-engine QA automation

## 4.1 The connect.cfg trick (why naive automation fails)

**Do not** pass camera scripts via `+exec` at startup: `wait` commands block
the *same command buffer* that the client↔server signon handshake uses, so
the connection never completes and the console never drops — you screenshot
the console art forever. Instead:

- `<gamedir>/configs/connect.cfg` ← `exec shots.cfg`
  (QSS-M automatically execs `configs/connect.cfg` **after** the client
  connects; a gamedir copy shadows id1's.)

## 4.2 shots.cfg — self-driving cameras

Generate it from Python with a camera list; the pattern:

```
host_maxfps 72
viewsize 120
crosshair 0
r_drawviewmodel 0
con_notifytime 0
god
noclip
alias w "wait;wait;wait;wait;wait;wait;wait;wait;wait;wait"
alias ww "w;w;w;w;w"
alias c1 "setpos -360 -140 380 25 140 0; ww;ww; screenshot; c2"
alias c2 "setpos  820  500 300 20 210 0; ww;ww; screenshot; c3"
...
alias cN "setpos ...; ww;ww; screenshot; quit"
ww
c1
```

- `setpos X Y Z PITCH YAW ROLL`; positive pitch looks down; yaw 0=+x east,
  90=+y north.
- **`host_maxfps 72` is load-bearing twice**: waits are frame-counted (at an
  uncapped 1600fps a 500-frame wait lasts 0.3s), and screenshot filenames are
  timestamped per second — same-second shots overwrite each other.
- `ww;ww` = 100 frames ≈ 1.4s per camera: enough for lightmap/dlight settle.

Launch and collect:

```sh
rm -f $Q/dmjam/screenshots/*.png
$Q/QSS-M.app/Contents/MacOS/QSS-M -basedir $Q -game dmjam \
  -window -width 1280 -height 720 +map MAPNAME >/dev/null 2>&1
# engine exits itself via the final alias's `quit`
ls $Q/dmjam/screenshots/   # read the PNGs, iterate
```

Caveats:
- `setpos` is **blocked under `deathmatch 1`** — scripted cameras are SP-only.
- A noclip camera flying through an item **picks it up** (gone from later
  shots); route around item positions or shrug.
- For DM-only behavior (DM spawn points, quad spawning), run
  `+deathmatch 1` and verify via logs (§4.3), not cameras.

## 4.3 Entity & collision verification (`-condebug` + `edicts`)

```sh
printf 'host_maxfps 72\nalias w "wait;...x10"\nalias ww "w;w;w;w;w"\nww;ww;ww\nedicts\nww\nquit\n' > $Q/dmjam/shots.cfg
$Q/.../QSS-M -basedir $Q -game dmjam -condebug +deathmatch 1 +map MAP >/dev/null 2>&1
# log: $Q/qconsole.log   (basedir, not gamedir)
```

**Item spawn audit** — catches silently-removed embedded items:

```python
import re, struct
log = open(f'{Q}/qconsole.log', encoding='latin-1').read()
spawned = {(round(float(m[0])), round(float(m[1])))
           for m in re.findall(r"origin\s+'? *(-?[\d.]+) +(-?[\d.]+) +(-?[\d.]+)", log)}
d = open('out/MAP.bsp','rb').read()
o,l = struct.unpack('<ii', d[4:12]); ents = d[o:o+l].decode('latin-1')
for block in re.findall(r'\{([^}]*)\}', ents):
    e = dict(re.findall(r'"([^"]+)" "([^"]*)"', block))
    cn = e.get('classname','')
    if cn.startswith(('item_','weapon_')):
        x,y,z = map(float, e['origin'].split())
        if (round(x),round(y)) not in spawned:
            print("MISSING:", cn, e['origin'])
```
(This found 4 dead items on sundial including the quad — all embedded-spawn
victims per the §3.4 rules.)

**Collision smoke test** — proves floors/hulls work without playing:
in the edicts dump, fields print **after** the `classname player` line; a
healthy spawn shows `origin` == the spawn point, `FL_ONGROUND` in flags,
`health 100` after several seconds of game time. If the player fell through,
origin z will have plummeted.

**Log greps that catch corruption**: `Mod_LoadNodes`, `invalid leaf`,
`not 16 aligned` (broken miptex dims), `fell out of level`.

---

# Part V — The two-qbsp rule (clipnode explosions)

**Symptom**: recompiling an ornate, `func_detail`-heavy TrenchBroom map with
alpha11 qbsp produced **1,382,129 clipnodes (16.6MB)** vs the original's 47K
— identical source, out of spec for BSP29 (16-bit clipnode child indices),
2.5× file size. `-maxnodesize`/`-midsplit*` don't help; it's the alpha-line
hull expansion behavior. QSS-M happens to load it, other engines may not.

**Policy:**

| map type | qbsp | vis/light |
|---|---|---|
| code-generated (boxes/wedges, modest detail) | alpha11 | alpha11 |
| id-source recompiles (dm2/dm3/dm4 .map) | alpha11 | alpha11 |
| ornate TB maps (hundreds of func_detail_wall etc.) | **v0.18.2-rc1** (`tools/v018/`; add `-bsp2` if the original was BSP2) | alpha11 |

The outputs interoperate — just run vis with the `.prt` from whichever qbsp
ran. **Always sanity-check a recompile**: clipnode count within ~2× of the
original bsp (§6.7 lump table).

---

# Part VI — BSP / WAD / MAP analysis library

All snippets: pure Python, `struct` only. These turn "I think" into "I know"
and are the backbone of every edit.

## 6.0 Headers

```python
d = open('map.bsp','rb').read()
if d[:4] == b'BSP2':                    # large-format bsp
    lumps = [struct.unpack('<ii', d[4+i*8:12+i*8]) for i in range(15)]
    FACE_SZ, EDGE_FMT, EDGE_SZ = 28, '<II', 8   # all-int32 structs
else:                                    # version 29 (int32 == 29)
    lumps = [struct.unpack('<ii', d[4+i*8:12+i*8]) for i in range(15)]
    FACE_SZ, EDGE_FMT, EDGE_SZ = 20, '<HH', 4
```
Lump order: 0 entities · 1 planes · 2 textures · 3 vertexes · 4 visibility ·
5 nodes · 6 texinfo · 7 faces · 8 lighting · 9 clipnodes · 10 leafs ·
11 marksurfaces · 12 edges · 13 surfedges · 14 models.

## 6.1 Entities lump = plain text (the everything-tool)

```python
o,l = lumps[0]; ents = d[o:o+l].decode('latin-1')
blocks = [dict(re.findall(r'"([^"]+)" "([^"]*)"', b))
          for b in re.findall(r'\{([^}]*)\}', ents)]
```
Uses: extract item layouts from reference maps; read a pro map's worldspawn
lighting recipe; audit your own compile; find spawn/intermission points for
camera placement. (For .map *sources* with nested brush braces, use the
line-based parser in §6.8 instead.)

## 6.2 Brush-entity model bounds (verify triggers/panes to the unit)

```python
mm = re.search(r'"model" "\*(\d+)"', entity_block)
mo,_ = lumps[14]
rec = d[mo + int(mm.group(1))*64 :][:64]
mins = struct.unpack('<fff', rec[0:12]); maxs = struct.unpack('<fff', rec[12:24])
```
(Engine-reported bounds are ±1 from brush geometry — bmodel bbox padding.)
This is how the kill triggers and the glass pane were confirmed in the
shipped BSPs. QSS-M's in-game edict inspector shows the same
(EDICT n / ABSMIN / ABSMAX) — when the user can point at a thing in-engine,
ask for that overlay; it hands you exact geometry and texture names.

## 6.3 Floor rasterizer — find holes and gaps exactly

Reconstruct face polygons and scan-fill them; enclosed uncovered regions are
holes with exact rectangles:

```python
vx,fc,ed,se = (d[lumps[i][0]:lumps[i][0]+lumps[i][1]] for i in (3,7,12,13))
verts = [struct.unpack('<fff', vx[i*12:i*12+12]) for i in range(len(vx)//12)]
edges = [struct.unpack(EDGE_FMT, ed[i*EDGE_SZ:(i+1)*EDGE_SZ]) for i in range(len(ed)//EDGE_SZ)]
surfedges = struct.unpack(f'<{len(se)//4}i', se)
polys=[]
for i in range(len(fc)//FACE_SZ):
    if FACE_SZ==28: planenum,side,firstedge,numedges,texinfo = struct.unpack('<iiiii', fc[i*28:i*28+20])
    else:           planenum,side,firstedge,numedges,texinfo = struct.unpack('<HHiHH', fc[i*20:i*20+12])
    pts=[]
    for k in range(numedges):
        e = surfedges[firstedge+k]
        pts.append(verts[edges[e][0] if e>=0 else edges[-e][1]])
    if all(abs(p[2]-FLOOR_Z) < 2 for p in pts):     # faces on the floor plane
        polys.append(pts)
# rasterize onto a 16u grid (scanline polygon fill), then flood-fill empty
# cells; regions NOT touching the grid border = enclosed holes.
```
Located start.map's hole as exactly 512×512 @ x[1024..1536] y[-256..256].
Also useful inverted: verify a pane/trigger covers a gap completely.

## 6.4 WAD2 read / write / validate

Read: header `WAD2` + numlumps + dirofs; 32-byte dirents, name at offset 16.
Miptex: 16-byte name, int32 w,h, four mip offsets (first == 40), 8-bit
palette-indexed pixels, mips at /2/4/8.

**Always validate extracted textures** — some BSPs embed header-only/corrupt
miptex (dims like `218959117` = `0x0D0CB00D`) that **hang the engine at
load** with console garbage:

```python
ok = (0 < w <= 1024) and (0 < h <= 1024) and offs[0] == 40
```

Write: `tools/makewad.py` shows the full recipe (flat 16×16 utility textures
+ a 256×128 dual-layer sky miptex quantized to the Quake palette with
nearest-RGB, skipping fullbright rows 224–255 for world textures).

## 6.5 Texture previews — decide by looking, never by name

```sh
python3 tools/wadview.py wads/makkon_concrete.wad refs/preview.png \
        conc_w04_gry2 conc_w04_teal2 conc_t02_ylw1 ...
```
Palette-mapped PNG montage, no deps (hand-rolled PNG writer + Quake palette).
This drove every art decision: sundial's gray/teal/yellow scheme, and dm3's
emissive colors (tlight03 turned out *blue*, tele_top yellow circuitry,
comp panels red LEDs — invisible from names alone). Same idea for skyboxes:
decode the TGAs (supports RLE), montage the `_ft` faces, pick.

## 6.6 PAK extraction

```python
# PACK header: ofs,len of a directory of 64-byte entries:
# 56-byte name + int32 offset + int32 length
```
Used to pull dm3.bsp and palette.lmp out of the user's pak1.pak.

## 6.7 Lump-size diff (recompile sanity)

Print all 15 lump sizes for old vs new bsp. Red flags: clipnodes blowing up
(Part V), textures shrinking (missing wads), lightdata 0 (light didn't run),
visdata 0 (missing .prt). `bspinfo MAP.bsp` also lists BSPX lumps
(RGBLIGHTING / DECOUPLED_LM / LIGHTGRID_OCTREE / LIGHTING_E5BGR9) and dumps a
lightmap PNG + geometry OBJ for eyeballing.

## 6.8 Parsing .map sources (TrenchBroom output)

- **Parse line-based**: braces count only on lines that are exactly `{` or
  `}`. Naive char-level brace counting breaks on Makkon's `{alpha`-prefixed
  texture names inside face lines (this silently corrupted an entity census
  before being caught).
- **Plane points are NOT brush extents.** TB writes any three points on the
  plane; deriving AABBs from them overestimates wildly (a 4u-thick glass
  sheet "measured" 192u tall). For exact geometry, query the *compiled* bsp
  (§6.2/§6.3); use .map-derived bounds only as heuristics.
- Valve-220 entity structure: entity `{ kv-lines, then brush blocks `{...}` }`.
  Keep patched output byte-identical outside your edit (replace exact
  strings; assert every replacement matched).

---

# Part VII — Surgical edit recipes

Universal workflow (every recipe follows it):

1. Original `.map` (+ old `.bsp` if it exists) live in `$DM/ramaps/`. Never
   edit originals — patch a copy in `$DM/src/`.
2. **Texture recovery**: `bsputil -extract-textures old.bsp` → wad; validate
   (§6.4); put it first in the worldspawn `"wad"` list with modern wads +
   `sundial_util.wad` behind it. qbsp warnings name any still-missing
   textures — for retired texture names, **binary-grep the disk**
   (`grep -rla 'texname' ~/Desktop ~/codedev`) and extract from whatever old
   compiled bsp contains them (an older compile of the *same* map is the
   best donor; verify dims — one donor had a corrupt main texture).
3. Compile per Part II + Part V. **Match the original's contract**: BSP2
   stays `-bsp2`; a mono-lit original stays mono (no `-lit`); don't "upgrade"
   unless asked.
4. Verify: §6.2 bounds, §4.3 spawn/collision audit, §4.2 screenshots.
5. Deliver to `ramaps/`: new bsp; original preserved as `*_old.bsp` — guard
   with `[ ! -f X_old.bsp ] && mv X.bsp X_old.bsp` so a re-run can't clobber
   the backup with your own build (this almost happened; the original was
   recovered from another copy on disk — always keep one).  Patched source
   saved as `*_fixed.map`.

## 7.1 Recipe: void kill trigger (walkable-sky fix)

Symptom: falling off the map lands you on an invisible-looking "sky floor"
you can walk on. Two maps fixed; both had the same root cause in different
flavors.

**Diagnose before touching anything** (§6.1 + .map parsing):
1. Find all-sky brushes in worldspawn → identify the sky floor slab z and
   perimeter wall extents.
2. Find the lowest *playable* z (non-sky brush tops + spawn origins).
3. Check any existing trigger_hurt's z-range against both. The shipped
   tbsketch_05_7 source had a trigger at z[0..64] — but the sky floor's
   walkable top was −64, the **same level as the playable plaza**, so
   walkers passed *underneath* the trigger, and extending it down would
   have killed players at spawn. A trigger's mere existence proves nothing.

**Fix pattern** (works even when playable floor == sky floor level):
1. Lower the sky-floor slab by ~512u (regex z-shift of the slab's plane
   points inside that one brush).
2. Extend perimeter sky/wall brush bottoms down the same amount — otherwise
   you open a **gap → leak** between wall bottom and new floor.
3. Add a full-footprint `trigger_hurt` `"dmg" "1000"` in the fall zone:
   top ≥ 64u below the lowest playable z, ≥ 300u tall.
4. Verify: model bounds (§6.2); leaktest; spawn collision audit (§4.3);
   screenshot from below the old floor level showing open cloud void.

Deep-void beats hole-shaped triggers: no xy-shape to get wrong, no
spawn-height interactions, and the fall looks intentional (cloud abyss).

## 7.2 Recipe: relight a map (surface-light method)

1. Split the .map into entities (§6.8). Remove `light` + `light_fluoro`
   (dm3: 134 entities). Keep flame-model lights if present (visible props).
2. Worldspawn: add the §2.3 block, tuned to the map's sky texture (dm3's
   purple sky4 → lavender sun `200 210 255` @ `315 -60`, dome `160 170 225`,
   `_bounce 2`, dirt at .9, anglescale 0.6).
3. Render every candidate emissive texture (§6.5) and build the `_surface`
   template list from what they actually look like:
   ```
   tlight02  380  255 230 180     bright warm panels
   tlight01  280  255 210 130     round bulbs
   tlight07/09 260 255 200 90     amber tubes
   tlight03  300  120 170 255     the BLUE one (looked warm by name)
   tele_top  120  255 220 120     circuitry ceiling
   z_exit    100  255 50 30       EXIT sign
   comp1_*    30  255 90 60       LED wash
   *teleport 200  170 140 255     teleporter void
   ```
4. Compile with advanced flags (§2.2). Expect first bake too dark: raise
   `_minlight` (6→12), `_sunlight2`, `_bouncescale` before touching the sun.
5. Gameplay entities remain byte-identical — it's still the same map.

## 7.3 Recipe: seal an opening with the map's own materials

1. Find the map's existing construction for the material: search the texture
   (`ravenglass`), dump the owning entity's keys. start.map's glass =
   `func_wall` + `"alpha" ".25"` + `_shadow 1 _shadowself 1 _mirrorinside 1
   _noclipfaces 1`, panes 4u thick, top flush with the floor plane.
2. Locate the opening **exactly** with the floor rasterizer (§6.3).
3. Append a cloned entity with one brush sized exactly to the opening,
   top coplanar with the floor: exact fit ⇒ no xy overlap with floor brushes
   ⇒ **no z-fighting**; flush ⇒ matches the established look.
4. Verify bounds (§6.2) + screenshots from above *and* below
   (`_mirrorinside` renders the underside).

Entity text used (adapt coords/texture):

```
{
"classname" "func_wall"
"_shadowself" "1"  "_mirrorinside" "1"  "_shadow" "1"  "_noclipfaces" "1"
"alpha" ".25"
{
( 1024 -256 -768 ) ( 1024 256 -768 ) ( 1536 256 -768 ) ravenglass [ 1 0 0 0 ] [ 0 -1 0 0 ] 0 1 1
( 1024 -256 -772 ) ( 1536 -256 -772 ) ( 1536 256 -772 ) ravenglass [ 1 0 0 0 ] [ 0 -1 0 0 ] 0 1 1
( 1024 256 -772 ) ( 1536 256 -772 ) ( 1536 256 -768 ) ravenglass [ 1 0 0 0 ] [ 0 0 -1 0 ] 0 1 1
( 1024 -256 -772 ) ( 1024 -256 -768 ) ( 1536 -256 -768 ) ravenglass [ 1 0 0 0 ] [ 0 0 -1 0 ] 0 1 1
( 1536 -256 -772 ) ( 1536 -256 -768 ) ( 1536 256 -768 ) ravenglass [ 0 1 0 0 ] [ 0 0 -1 0 ] 0 1 1
( 1024 -256 -772 ) ( 1024 256 -772 ) ( 1024 256 -768 ) ravenglass [ 0 1 0 0 ] [ 0 0 -1 0 ] 0 1 1
}
}
```

---

# Part VIII — Troubleshooting index

| symptom | cause | fix |
|---|---|---|
| screenshots show only console | `wait` chains blocked signon | connect.cfg hook (§4.1) |
| screenshots overwrite each other | same-second timestamps at high fps | `host_maxfps 72` + longer waits |
| `setpos` does nothing | deathmatch 1 | camera passes in SP only |
| item missing in game, present in .map | spawned embedded → silently removed | §3.4 rules; audit §4.3 |
| quad specifically missing | −24z bbox | origin ≥ surface+24 |
| engine hangs on map load, console garbage | corrupt extracted miptex | validate dims (§6.4); different donor bsp |
| `Mod_LoadNodes: invalid leaf index` | truncated/oversized lumps | check clipnodes (Part V), format (BSP2?) |
| vis instant + tiny visdata | missing `.prt` | keep prt beside bsp; rerun vis |
| tiny visdata but prt was present | open-plan map, legit | leaf count sanity: `average leafs visible` |
| new bsp 2.5× size of old | alpha11 clipnode explosion | v0.18 qbsp (Part V) |
| "mixed face contents SOLID vs SKY" warnings | per-face sky on solid brushes | harmless; or make whole brush sky |
| "mixed contents" *error* | `*liquid` face on a solid brush | all-liquid brush + separate trim |
| map leaks after editing sky/void geometry | wall bottoms no longer reach floor | extend walls with the floor (§7.1) |
| brush AABBs from .map look absurd | plane points ≠ extents | measure in compiled bsp (§6.8) |
| entity census from .map wrong | `{alpha` texture names broke brace parse | line-based parser (§6.8) |
| textures missing at qbsp | map newer than donor bsp / renamed packs | disk-wide binary grep for donors (§7 step 2) |
| relight looks pitch black in spots | purist surface-light setup | `_minlight 12+`, dome up, bounce up |
| everything compiles but looks flat | no `.lit` loaded | ship `.lit` beside bsp; engines need matching name |

---

# Part IX — Delivery

**Checklist per map:**
- [ ] `qbsp -leaktest` clean; zero missing-texture warnings
- [ ] clipnodes within ~2× of original (recompiles)
- [ ] item audit passes; player spawns `FL_ONGROUND`, health 100
- [ ] brush-entity bounds verified in the shipped bsp
- [ ] screenshots reviewed: geometry, lighting levels, no z-fighting,
      skybox loads (ship `gfx/env/*.tga` beside the bsp)
- [ ] format contract preserved (BSP29/BSP2; .lit vs mono)
- [ ] `ramaps/`: new bsp + guarded `*_old.bsp` backup + `*_fixed.map`
- [ ] `dist/<map>.zip`: `maps/*.bsp` (+`.lit`), skybox TGAs, `.map` source,
      classic readme (credits: Makkon assets, ericw-tools; influences;
      exact build flags)

**Install for play**: drop the zip contents into a mod dir (or id1). The
harness's own test copies live in `$Q/dmjam/` and shadow id1 under
`-game dmjam`.

---

# Appendix — quick numbers

| thing | value |
|---|---|
| player bbox | 32×32×56, origin 24 above feet, eyes +22 |
| step-up | ≤18u automatic |
| walkable slope | <45°; design ramps ≤30° |
| gravity | 800; trigger_push apex ≈ speed²/1600 |
| teleport dest offset | +27z applied by progs |
| item boxes | 32×32×56, corner-origin |
| quad/pent bbox | −16,−16,−24 → 16,16,32 (24 below origin!) |
| Makkon texture scale | 1.0 (512px = 512u) |
| duel map footprint | ~1500×1800, height 600–900 |
| corridors / doors | ≥128 wide (main 192+), ≥128 tall |
| BSP29 clipnode child index | int16 — counts >32767 are out of spec |
| Quake palette | 768 bytes; fullbrights are indices 224–255 |
| sun shadow length | wall_height / tan(|pitch|) |
