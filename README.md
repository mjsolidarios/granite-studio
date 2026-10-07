# Gravestones: procedural Blender granite

Seven self-contained Blender Python scripts recreate granite materials from
headstone photographs. The current dataset scripts are **v4 macro microdetail**.
This repository captures the existing Claude-produced project as a baseline;
its earlier editing history was not available when Git was initialized.

Start with [the material guide](README_granite_materials.md) for calibration
tables and controls, and [the project study](PROJECT_STUDY.md) for architecture,
version differences, repeatable tasks, and current limitations.

| Dataset | Current script | Finishes |
| --- | --- | --- |
| 1st | `1st/1st_GS01_SaltPepper.py` | Polished, Honed |
| 2nd | `2nd/2nd_GS02_FlameSwirl.py` | Polished, Honed |
| 3rd | `3rd/3rd_GS03_DarkMaroon.py` | Polished, Honed |
| 4th | `4th/4th_GS04_FoldedRock.py` | Polished, RockPitched, Honed |
| 5th | `5th/5th_GS05_HighContrast.py` | Polished, Honed |
| 6th | `6th/6th_GS06_RustRed.py` | Polished, Honed |
| additional | `additional/additional_GS07_BahamaBlue.py` | Polished, Flamed, Honed |

In Blender's Scripting workspace, open a dataset script and run it with meshes
selected. It builds all finishes and assigns Polished to the first material slot
of selected meshes. Assign the other finishes to the appropriate faces. Use
metres, apply object scale, and orient the front face in the X/Z plane.

The existing scripts specify Blender 4.0+; their headers report previous testing
on Blender 5.2 LTS. Those compatibility claims have not been independently
verified in this checkout. The scripts require Blender's `bpy`, `bmesh`, and
`mathutils` as applicable, rather than ordinary standalone Python alone.

`Blender/Granite_Macro_v4.blend` is the existing scene artifact.
`Report/` contains seven existing PDF deliverables. Reference photos, final
comparison sheets, scripts, metadata, logs, reports, and the scene are tracked.
Scratch renders in `_cal`, `_previews`, `_previews_v2`, `_report/renders*`, and
`Blender/macro_tests` remain on disk but are excluded from Git. A clone therefore
does not include those working images. Binary assets currently use ordinary Git.
