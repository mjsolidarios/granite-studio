# Procedural headstone granite (v2): calibrated against the photos

There are six Blender scripts, each saved in its dataset folder. Every script is self-contained: the core is shared and only the `PRESET` block differs. They were tested in Blender 5.2 LTS and work in Blender 4.0 or later, in Cycles or EEVEE.

| Folder | Script | Finishes created |
|---|---|---|
| 1st | `1st_GS01_SaltPepper.py` | Polished, Honed (wave side panels) |
| 2nd | `2nd_GS02_FlameSwirl.py` | Polished, Honed (flame ribbons) |
| 3rd | `3rd_GS03_DarkMaroon.py` | Polished, Honed (side panel) |
| 4th | `4th_GS04_FoldedRock.py` | Polished, **RockPitched** (displaced), Honed |
| 5th | `5th_GS05_HighContrast.py` | Polished, Honed (flame ribbons) |
| 6th | `6th_GS06_RustRed.py` | Polished, Honed |

## What changed in v2

**Calibrated, not eyeballed.** For each folder, a 23–31 cm patch of polished stone was cut from a photo, with no text or reflections in it. The shader's albedo was then rendered at the same physical size with an orthographic camera and emission-only shading, and the two were compared numerically. The comparison covered mean colour, luminance percentiles (p5–p95), contrast (σ), share of reddish pixels, spatial frequency spectrum and anisotropy. Presets were tuned until these statistics matched.

| Folder | Photo mean sRGB / σ / p5–p95 / reddish | Shader |
|---|---|---|
| 1st | 58 55 55 / 27.6 / 10–101 / 10 % | 58 54 55 / 23.2 / 13–96 / 9 % |
| 2nd | 81 76 75 / 22.5 / 41–114 / 18 % | 76 71 70 / 23.4 / 31–112 / 24 % |
| 3rd | 47 41 36 / 18.3 / 10–71 / 52 % | 49 41 37 / 17.1 / 13–71 / 51 % |
| 4th | 59 57 56 / 25.7 / 13–98 / 9 % | 55 52 51 / 23.5 / 12–93 / 12 % |
| 5th | 69 66 68 / 33.9 / 11–125 / 15 % | 73 69 72 / 31.6 / 16–129 / 16 % |
| 6th | 82 69 62 / 27.1 / 27–116 / 94 % | 84 71 65 / 24.3 / 31–113 / 93 % |

The first-pass shader had about a quarter of the photos' contrast (σ ≈ 7 vs ≈ 27). It also had periodic "zebra" banding.

**Better geology model.** Each layer of the stone is modelled separately:

- **Matrix:** fine (≈1.5 mm) Voronoi crystals.
- **Melanosome:** broad, darker biotite-rich layers.
- **Rose layers:** garnet / K-feldspar, now cloud-based. The old periodic wave bands are almost gone because they caused the stripes.
- **Leucosome:** grey quartz-feldspar clouds.
- **Speckle:** discrete 1–4 mm black biotite clots, mostly inside the grey clouds. These give the salt-and-pepper look in 1st and 5th.
- **Schlieren:** thin, broken black streaks.
- **Lamination:** fine foliation stripes that follow the folds and show only in dark or rose layers (3rd, 4th, 6th).
- **Flow:** everything is sampled in one folded flow space: rotate → stretch → macro sweep → fold → crinkle.

**Realistic honed finish.** Honing now lifts the light minerals strongly while biotite stays dark, so the pattern survives on matte faces, as in the photos. It is checked against the honed ribbons in 2nd (photo 123 126 129, shader 123 121 122) and 5th (172 168 163 vs 159 156 157).

## Seed control

There are three levels, and they add together:

1. **Material seed.** In the material node editor, change the "Granite" group node's `Seed` input. It updates live and any number works. You can also set `SEED = …` at the top of the script, or run `set_seed(42)` or `set_seed(42, "GS04_FoldedRock")` from the Python console.
2. **Per-object seed.** Go to Object Properties → Custom Properties → `granite_seed`. You can also call `set_object_seed(obj, 7)`, or `randomize_selected_seeds(start=1)` to number every selected object. This property can be keyframed or driven.
3. **Automatic.** `Object Random Seed = 1` (the default) adds Object Info ▸ Random, so duplicates differ without any setup. Set it to 0 to make copies identical.

`Seed Variation` (0–1, default 0.35) lets the seed also nudge the warp strength and the amounts of rose and grey patches, not just move the pattern. Set it to 0 for "same stone, different cut".

All three paths were verified in Blender:
- same seed: correlation 0.996
- different `granite_seed`: 0.08
- material Seed 5 vs 6: −0.05
- re-setting Seed 5: pixel-identical

## Group inputs (tune without code)

| Input | Effect |
|---|---|
| Scale, Flow Angle (+ Jitter), Stretch | Size, direction and elongation of the flow |
| Warp / Fold / Crinkle | Large sweeps / tight folds / ragged edges |
| Rose / Leucosome / Melanosome Amount | How much of each mineral layer appears |
| Biotite Streaks, Speckle Density | Black streaks and black dots |
| Lamination (+ Scale) | Fine foliation stripes |
| Grain Scale | Crystal size (relative to Scale) |
| Brightness, Saturation, Polish Roughness | Overall look |
| Finish (0 = Polished, 1 = Honed), Rock Pitch | Surface finish |

## Usage notes

- Run the script with meshes selected. They receive `<ID>_Polished`; assign the other finishes to side or edge faces.
- Mapping uses Object coordinates in metres, with the front face in the X/Z plane (Blender's front view). Apply scale (Ctrl+A).
- RockPitched uses true displacement (Cycles, "Displacement and Bump"). Give those faces some subdivision; the relief is about 1–3 cm.

## Node setup guide (to rebuild it by hand)

```
seed  = Seed + Attribute(Object,"granite_seed") + ObjectInfo.Random·9973·ObjectRandomSeed
off   = WhiteNoise1D(seed).Color·1000      jitter = (WhiteNoise1D(seed+17.31)−0.5)·2·FlowAngleJitter
var   = (WhiteNoise1D(seed+41.7).Color−0.5)·SeedVariation  → warp ×(1±0.4), rose/leuco thresholds ±0.04

p     = VectorRotate_Y(TexCoord.Object·Scale, FlowAngle+jitter)·(Stretch,1,1) + off
p    += (Noise(p, s0.35,d2).Color−.5)·Warp      # macro sweep
p    += (Noise(p, s1.3, d4).Color−.5)·Fold      # folds
P     = p + (Noise(p, s5, d3).Color−.5)·0.15·Crinkle

lam   = (Wave_bands(P, LamScale, dist3.5, d4) − .5)·Lamination
rose  = smoothstep(0.05·Wave(P,BandScale) + 0.95·Noise(P,s1.6,d6), 0.64−0.22·Rose ±0.05)
leuco = smoothstep(Noise(P,s1.15,d5,dist.4)+0.02·lam,           0.68−0.18·Leuco ±0.055)
mel   = smoothstep(Noise(P,s0.7,d5),                            0.66−0.20·Melano ±0.05)·(1−leuco)
rose *= 1−0.8·leuco
bio   = (|Noise(P,s3.2)−.5| < 0.035·Biotite) · smoothstep(Noise(P,s1.9), .48,.62)
grain = Voronoi(P_rot·(0.8+0.2·Stretch,1,1)·GrainScale + fold-offset).Color.R
spk   = Voronoi(grain-coords·speckle_size): dot(r=0.12–0.34) where cell.R < SpeckleDensity, ×(0.25+0.75·leuco)

C = Ramp_matrix(grain) → mix Ramp_rose(grain) by rose → darken by mel·0.55
    → mix Ramp_leuco(grain) by leuco → black by spk → black by bio
C = HueSat(C, Sat, Value = tone(Noise(P,s0.9)) + 0.6·lam·(1−leuco)) · Brightness
Honed : C·(1+Finish·honed_gain) ⊕screen tint·Finish·honed_mix·0.35
Rock  : C ⊕screen rock_tint·0.8      Rough: 0.06–0.07 polished → 0.55 honed → 0.85 rock
Height: Voronoi.Distance·max(Finish,.15) + 12·Noise(P,s2.5,d10)^1.6·RockPitch → Bump (+Displacement)
```

`granite_preview_sheet.jpg` shows, for each folder: the photo patch, the shader albedo for the same patch, and full renders at the default seed and at seed 2026.


## Dataset "additional": GS07 Bahama Blue (v3)

Script: `additional/additional_GS07_BahamaBlue.py` builds the Polished, Flamed and Honed materials.

**References.** The main reference was the 1 m texture swatch (`bhb3--less-wavy.png`, about 0.5 mm per pixel). The PARVA render and the two workshop photos of the heart memorials were used for the polished face and the flamed rim.

**What the stone shows:**
- A blue-black base, about sRGB 56 60 71. Blue is about 15 units higher than red, and there is no red mineral.
- Near-horizontal layers that bend together in soft waves, about 25–35 cm long and 3–5 cm high.
- A dark, lace-like network of fine crystals over a slate-blue background, at roughly 1–2 cm scale.
- Thin pale, wavy streaks and a few thin dark streaks that follow the layering.
- Flamed edges: a pale grey surface (about sRGB 187) with irregular dark grains 2–4 mm across.

**New controls added to the shared node group.** They default to off, so the six earlier materials still render the same, with about 0.1 % of pixels differing because of render noise.

| Control | What it does |
|---|---|
| Undulation, Undulation Scale | Bends the whole layer stack up and down so the layers wave together |
| Mottle, Mottle Scale, Mottle Threshold | Adds the lace-like dark network (preset values also set vein width and how speckled the dark areas are) |
| Light Veins | Adds thin pale wavy streaks along the layers |
| Flamed specks (preset values) | Sets the dark grains on flamed faces: size, density and how ragged their outlines are |

**Calibration.** The shader was compared with the swatch at the same physical size:

| Patch size | Photo (mean sRGB / σ / p5–p95) | Shader |
|---|---|---|
| 1 m | 56 60 71 / 15.9 / 38–90 | 61 64 74 / 15.8 / 40–91 |
| 25 cm | 58 63 74 / 23.1 / 23–99 | 55 58 67 / 17.3 / 29–86 |
| 10 cm | 57 62 72 / 22.3 / 25–97 | 53 55 64 / 19.3 / 26–86 |
| Flamed rim | 187 186 181 / 31 / 131–231 | 188 187 183 / 26 / 136–222 |

**Seed check.** Seed 7 against seeds 77, 777 and 7777 gives correlations of 0.005, 0.015 and −0.006, so different seeds produce unrelated patterns. Re-entering seed 7 gives a correlation of 1.000, so the same seed reproduces the same pattern.

**Known gaps.**
- At 10–25 cm the shader has less contrast than the swatch, and its brightest slate-blue areas are slightly dimmer.
- The flamed specks are rounder than the stretched grains in the photo.

## v4: macro microdetail (Blender file: Blender/Granite_Macro_v4.blend)

Each material now runs: **Pattern group** (the calibrated colours, unchanged) → **MICRO_<stone> group** (physically scaled surface detail) → Principled BSDF. The originals are kept in the .blend as `*_ORIG` materials and `GRANITE_*_ORIG` groups (fake user set). The v3 scripts are in `Blender/backup_v3_scripts`.

**Changes to the pattern group (affect crystals only; colour statistics re-checked as identical).** Crystals now have irregular, lobate outlines, and about a third are twice the size of the rest. The group also outputs Grain Cell, Grain Edge and Grain Dist so the micro graph can follow the real crystal grid. The Bahama Blue flamed specks are now angular grains instead of round dots (flamed albedo: photo 187 / σ 31; shader 184 / σ 31).

**MICRO_Paradiso.** Distances are in mm, heights in µm.
- Each crystal gets its own polish level and a 0.2° facet tilt.
- Crystals have zoning plus two-scale mottling inside them.
- About 35 % of feldspars show faint, irregular twin lamellae (0.13 mm).
- Biotite is recessed by 1.5 µm with roughness about 0.25, plus irregular cleavage sheen and a few plucked pits (0.18–0.4 mm, 10 µm deep).
- Grain boundaries have hairline cracks (15 µm).
- Garnets are angular, wine-red, 0.5–1 mm with dark rims, glossier and 0.8 µm proud.
- Polishing leaves two sparse scratch sets, slab waviness (±6 µm over about 7 cm) and polish-haze patches.
- Honed finish: the same layers with 4× relief and 3.5× variation.
- Rock-pitched: 0.25 mm spall steps.

**MICRO_BahamaBlue.**
- Fine 0.15 mm roughness flicker instead of large facets, and a smaller 0.13° tilt.
- The dark network adds only +0.10 roughness and a 0.8 µm recess; plucked pits are rare.
- Tight 8 µm boundaries with a faint darker grain mosaic; no garnets or lamellae.
- Flamed: 1.8 mm spall plates stepping up to 0.3 mm, with conchoidal craters, fracture roughness 0.8–0.9, and cleaved mica flakes that glint at roughness 0.22.

**Controls on the Microdetail node:**
- Detail Scale
- Bump Strength (1 = physical)
- Roughness Variation
- Facet Tilt
- Crystal Texture
- Grain Boundaries
- Polish Scratches
- Polish Waviness
- Biotite Pluck
- Paradiso only: Garnet Inclusions
- Bahama Blue only: Fine Sparkle, Flamed Relief, Mica Glints

The Seed is one `SEED` Value node per material; it feeds both groups, and `set_seed()` still works.

**Macro render settings** (scene `MACRO_STAGE`, script `Blender/macro_stage.py`):
- Cycles on GPU (OptiX), 1024 samples with adaptive threshold 0.005, and the OpenImageDenoise denoiser.
- Filter 1.2 px, glossy bounces 6, indirect clamp 10, AgX view transform.
- f/22–32 at a 15–20 cm focus distance.
- Keep the camera within about 30° of the face normal so the depth of field stays usable.
- Give polished faces something to reflect (a large dim card or an HDRI); without it, they render as flat albedo.
- No subdivision is needed for polished or honed faces, because their relief is in µm and handled by bump. Rock-pitched faces need subdivision (adaptive, or about 6 levels) for their displacement.
