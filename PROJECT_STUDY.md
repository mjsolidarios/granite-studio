# Project study and reproduction notes

Studied on 2026-10-07 from the existing source, material guide, calibration
metadata, render logs, and the macro before/after comparison sheet. There was no
prior Git repository or Claude conversation transcript in the project. The
version narrative below is reconstructed from those artifacts, not an exact
record of Claude's prompts or editing sequence.

## Which files to use

- The seven scripts in `1st` through `6th` and `additional` are the current
  working scripts. Each includes its own preset and complete shared core.
- `Blender/v4/` contains earlier v4 copies. Every corresponding active script
  adds three material node frames and `granite_version = "v4 macro"`; the
  remaining source matches its v4 copy. Do not overwrite the active copies with
  these snapshots accidentally.
- `Blender/backup_v3_scripts/` preserves the previous material implementation.
  Some headers still call it v2; folder naming and the material guide identify
  these as the pre-microdetail backup.
- `Blender/Granite_Macro_v4.blend` is the saved scene. The material guide says it
  preserves `*_ORIG` materials and `GRANITE_*_ORIG` groups with fake users; this
  has not been verified by loading the binary scene during this study.
- `Blender/macro_stage.py` builds a reusable macro inspection scene.
- `_report/hd_render.py` implements beauty, detail, edge, patch, seeds, and lineup
  render jobs for the six original stones. It does not include GS07 in `FILES`.
- `_cal/ov.json` holds tuned preset overrides, including colour ramps.
  `_report/renders_v4/ladder_geo.json` holds recorded camera/geometry data.
- Dataset folders contain original photo references and, for Bahama Blue,
  swatches and existing heart renders. `Claude outputs/` and
  `Blender/Macro_before_after.jpg` contain useful comparison sheets.
- `Report/` contains the existing material, Bahama Blue, macro microdetail,
  and four HD report PDFs. Report generation source is absent.

## Architecture and existing changes

All seven active scripts have the same core from `import bpy` onward; their
headers, `SEED`, and `PRESET` blocks differ. All seven v4 snapshot cores also
match each other. Keep shared-core changes consistent across active scripts
while preserving the distinct preset values and reference observations.

`_G` wraps Blender node construction, connections, math, vector math, noise,
ramps, and mixing. Socket helpers handle enabled inputs and the Fac/Factor
alias. `build_granite_group(P)` constructs `GRANITE_<id>`: seeded object
coordinates, rotated/stretched/warped flow, mineral masks, crystals, colour,
roughness, and height. It exposes Grain Cell, Grain Edge, and Grain Dist to the
microdetail stage.

The guide describes v2 calibration against photo patches at matching physical
sizes: mean sRGB, luminance percentiles, contrast, reddish pixel fraction,
spatial frequency, and anisotropy. It records removal of strong periodic bands,
more contrast, discrete biotite specks, and mineral-aware honed lightening.
The underlying measurement/crop/tuning scripts are absent, so the numerical
tables are historical evidence rather than a runnable calibration suite.

The pre-v4 core includes Bahama Blue controls for coherent layer undulation,
dark mottling, pale veins, and flamed specks. Bahama Blue uses blue ramps even
in the historically named `rose` channel; that name does not imply red mineral.

The v3-to-v4 source comparison shows irregular warped crystal outlines, a
second population of larger crystals, grain outputs, angular flamed grains,
and separate `MICRO_<id>` groups. `build_micro_paradiso(P)` handles the six
original stones; `build_micro_bahama(P)` handles GS07. They add physically
scaled crystal facets, roughness variation, mineral relief, pits, boundaries,
scratches, and waviness. Paradiso adds garnet and lamellae; Bahama Blue adds
fine sparkle and flamed spalls/mica glints. Heights use metres (`UM = 1e-6`).

`build_material()` connects Object coordinates and a shared `SEED` Value node
to Pattern -> Microdetail -> Principled BSDF (IOR 1.54). RockPitched also uses
pattern displacement. `build_all(P, seed=None, assign_to_selected=True)` rebuilds
groups/materials and optionally assigns Polished to selected meshes. Run it in
a disposable scene or save a copy first: same-named groups/materials are rebuilt.

## Repeat the main tasks

### Build or tune a stone

Open the corresponding active script in Blender and run it. For controlled
automation, load it into an isolated namespace so its main block does not assign
materials unexpectedly:

```python
from pathlib import Path
root = Path("D:/PC/Gravestones")  # change for another checkout
path = root / "1st/1st_GS01_SaltPepper.py"
ns = {"__name__": "granite_task"}
exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), ns)
mats = ns["build_all"](ns["PRESET"], seed=1, assign_to_selected=False)
```

Change preset-specific geology/colour values in `PRESET`. For a new stone,
copy an active self-contained script, choose a unique ID, and tune against
references with known physical dimensions. Preserve neutral/rose Paradiso
and blue-black Bahama Blue behaviour independently.

### Check seeds and calibration

Use `set_seed(value, preset_id)` to change the shared material SEED node in v4;
the pattern's Seed socket is linked, so editing an unconnected default there is
not the effective v4 control. `set_object_seed(obj, value)` writes
`granite_seed`; `randomize_selected_seeds(start, step)` assigns values in object
name order. The pattern also has Object Random Seed and Seed Variation controls.

For comparisons, hold camera, lighting, geometry, object identity, scale, and
render settings constant. Check same-seed repeatability and different-seed
decorrelation separately. For albedo, connect the pattern Color to Emission,
use an orthographic patch of matching physical width, Standard view transform,
and no denoising, as in `job_patch`. Compare colour, contrast, frequency, and
anisotropy with clean photo regions. Check honed/flamed faces separately.

One source limitation matters: microdetail `_seeded()` combines material Seed
with Object Info Random directly. It does not use `granite_seed` or the
pattern's Object Random Seed toggle. Matching those pattern controls therefore
does not guarantee identical full microdetail across duplicate objects.

### Render surface inspection and report images

After building materials, load the stage inside Blender:

```python
stage_path = root / "Blender/macro_stage.py"
stage = {"__name__": "macro_task"}
exec(compile(stage_path.read_text(encoding="utf-8"), str(stage_path), "exec"), stage)
out = root / "Blender/macro_tests/reproduction.png"
out.parent.mkdir(parents=True, exist_ok=True)
stage["macro_render"](mats[0], str(out), light="soft", fov_mm=40,
                      res=(1600, 1000), samples=1024)
```

Repeat with `grazing` and `side`, and inspect polished, honed, flamed, and
rock-pitched finishes where applicable. `macro_render` defaults to 384 samples;
the guide's higher-quality recommendation is 1024 samples and adaptive threshold
0.005. Configure adaptive threshold/denoiser/filter/bounces explicitly if those
exact guide settings matter; the helper does not set all of them. Keep camera
near the face normal, use f/22-32, and give polished stone something to reflect.
Polished/honed relief uses bump; rock-pitched displacement needs subdivision.
The helper's `seed` and `face_mat_index` parameters are currently unused.

For the six-stone HD jobs, load `_report/hd_render.py` the same way and call
`JOBS[job](str(root), str(output_dir), keys, samples, scale)`; create the output
directory first. Its direct command-line entry point expects ordinary Python
with a compatible `bpy` module. It does not strip Blender's own CLI arguments,
so calling it through `blender --python ... -- ...` needs an argument adapter.
Dedicated GS07 heart, v4 ladder, and PDF report generators are not present.

## Verification at repository initialization

All 23 existing Python files passed `ast.parse` with Python 3.13. Source
comparison verified identical shared cores within each active/snapshot set and
the active-versus-v4 layout-only differences described above. Existing logs
record completed v4 beauty/detail and macro/HD renders; the before/after sheet
visually shows irregular grains and finish-dependent relief. These are previous
artifacts, not fresh render verification.

Only Blender 3.3 was found under the local Blender Foundation installation,
and no Blender executable was found on PATH. The scripts specify 4.0+, so no
runtime/material rebuild/render was attempted with that older installation.
The original material guide's version and calibration claims remain historical
until verified in a compatible Blender environment.
