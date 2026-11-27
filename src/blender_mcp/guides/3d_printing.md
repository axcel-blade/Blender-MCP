# 3D printing

Tested on Blender 5.3 (marked [5.3]). Notes for 3.6 and 4.x are untested (marked
[untested]). Modelling technique is in `modelling`.

## When to use

Preparing models for FDM (filament) or resin (SLA/MSLA) printers, or print services:
figurines, enclosures, replacement parts, miniatures, architectural models.

## Inputs needed

- Printer type and build volume (e.g. 220 x 220 x 250 mm), nozzle size (0.4 mm common) or
  resin layer height.
- Final size in millimetres; which face sits on the bed.
- Functional fits: holes for screws, mating parts, tolerances.
- Material (PLA, PETG, resin) if wall thickness or overhangs matter.

## Workflow

1. Units: decide how 1 Blender unit maps to mm. Either model in metres and export with
   `global_scale=1000` (tested, below), or set `unit_settings.scale_length = 0.001` with
   `length_unit = "MILLIMETERS"` and export with `use_scene_unit=True` [untested].
2. Make it one closed (manifold) solid: no holes, no internal faces, no zero-thickness
   parts. Join parts with booleans (Union), not just overlapping.
3. Thickness: at least 2 x nozzle width (0.8-1.2 mm for 0.4 mm nozzles) for FDM walls,
   0.6-1 mm for resin; pins and thin features 2 mm or more.
4. Overhangs: keep under ~45 degrees for FDM or plan supports; flatten the base.
5. Fits: clearance 0.2-0.4 mm per side between mating FDM parts (0.1-0.2 resin); holes come
   out smaller, add 0.1-0.2 mm.
6. Apply all modifiers and transforms, check (below), then export STL (or OBJ/3MF from the
   slicer's side) and open it in the slicer.

## Tested values and code

```python
# [5.3] manifold check and volume with bmesh (works without any add-on)
import bmesh

bm = bmesh.new()
bm.from_mesh(ob.evaluated_get(depsgraph).to_mesh())
bm.faces.ensure_lookup_table()  # needed before indexing bm.faces[...]
non_manifold = [e.index for e in bm.edges if not e.is_manifold]
volume_cm3 = bm.calc_volume() * 1e6  # mesh in metres -> cm3
bm.free()
ob.evaluated_get(depsgraph).to_mesh_clear()

# [5.3] export: metres in Blender -> millimetres in the STL
bpy.ops.wm.stl_export(
    filepath=path, export_selected_objects=True, global_scale=1000.0, apply_modifiers=True
)
```

- Tested [5.3]: a 0.02 m cube exported this way measured exactly 20 mm in the STL, 12
  triangles, volume 8 cm3; deleting one face produced 4 non-manifold edges.
- `bpy.ops.wm.stl_export` is the new C++ exporter (4.1+). The legacy
  `bpy.ops.export_mesh.stl` still answers in this 5.3 install, but prefer the new one;
  in 3.6-4.0 only the legacy exporter exists [untested]. Other exporters in 5.3:
  `wm.obj_export`, `wm.ply_export`, `wm.usd_export`.
- 3D Print Toolbox [5.3]: `bpy.ops.mesh.print3d_check_all` and
  `print3d_clean_non_manifold` exist in this install because the extension is enabled.
  Check with `hasattr(bpy.ops.mesh, "print3d_check_all")`; if missing, use the bmesh check
  above and ask the user to enable the extension.
- Other bmesh checks: zero-area faces (`f.calc_area() < 1e-10`), loose vertices
  (`not v.link_edges`), flipped normals (`bmesh.ops.recalc_face_normals`).
- Fill weight estimate: volume x density (PLA 1.24 g/cm3) x infill share.

## Common mistakes

- Exporting in metres: a 20 mm part arrives as 0.02 mm (or 1000x too big). Measure the
  exported file.
- Unapplied Mirror/Solidify/Boolean modifiers or unapplied scale.
- Overlapping separate shells instead of a boolean union: slicers may print internal walls
  or fail.
- Single-face planes (leaves, text without extrusion): no volume, nothing prints.
- Tiny details below nozzle size disappear; text under ~1 mm stroke is unreadable on FDM.
- Normals flipped inwards: some slicers treat the part as a hole.

## Verification checklist

- [ ] Non-manifold edge count is 0; no loose or zero-area geometry; normals outward.
- [ ] Size in mm matches the brief (read the exported STL bounds, as in the test above).
- [ ] Minimum wall thickness and feature size suit the printer.
- [ ] Flat base on the bed; overhangs acceptable or supports planned.
- [ ] Volume and weight estimate reported; part fits the build volume.

## Manual work and external tools

- Slicing, supports and print settings happen in the slicer (PrusaSlicer, Cura, Bambu
  Studio, Chitubox for resin): the user opens the exported file there.
- Wall-thickness analysis and auto-repair are better in the 3D Print Toolbox extension or
  Meshmixer/PrusaSlicer repair; the extension must be enabled by the user.
- Safe execution mode refuses enabling add-ons or extensions and starting external programs
  (like a slicer). Explain that to the user and never bypass it.
