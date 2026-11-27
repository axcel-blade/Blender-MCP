# Modelling and sculpting

Tested on Blender 5.3 (marked [5.3]). Notes for 3.6 and 4.x are untested (marked
[untested]). Check uncertain names with `lookup_api`. Materials and realism details are in
`materials` and `realism`; engine budgets in `game_assets`.

## When to use

Building objects that libraries and `generate_3d` don't cover well: hard-surface props,
architecture pieces, furniture, mechanical parts, and organic forms by sculpting. Search
assets first for anything common (`search_assets`).

## Inputs needed

- Real dimensions (or a reference with a known size) and how close the camera gets.
- Use: still render (any density), animation (clean quads, edge loops at joints), game
  (budget), print (`3d_printing`).
- Style: hard-surface (bevels, crisp panels) or organic (sculpt, subdivision).

## Workflow

1. Block out with primitives at real scale in a named collection; check proportions with
   `look(mode="angles")` before adding detail.
2. Hard surface: keep the base low-poly and non-destructive. Modifier stack order:
   Mirror -> (Boolean cutters) -> Bevel -> Subdivision (optional) -> Weighted Normal.
   Hide boolean cutters (`display_type = "WIRE"`, `hide_render = True`).
3. Organic: block with metaballs, a skin modifier or primitives, join, voxel remesh to get
   even topology, then sculpt big forms -> secondary forms -> details. Add Multires only
   once the forms are final.
4. Thickness: Solidify on single-sided shells (walls, cloth, leaves).
5. Detail in passes, looking from the camera after each pass; stop at the detail level the
   shot needs.
6. Clean up: apply scale, recalculate normals, merge by distance, remove loose geometry,
   then name and put the object in its collection.

## Tested values and code

- Bevel modifier [5.3]: `width` 0.002-0.01 m for props, 0.02-0.05 m for furniture and
  architecture; `segments` 2-3; `limit_method = "ANGLE"` (also NONE, WEIGHT, VGROUP);
  `harden_normals = True` with a Weighted Normal modifier after it.
- Subdivision: `levels = 1` viewport, `render_levels = 2`. Add support loops or bevels so
  corners stay sharp.
- Mirror: `use_bisect_axis[0] = True` cuts off the other half; `use_clip` keeps the seam.
- Solidify `thickness`: 0.003 m paper, 0.02 m plank, 0.2 m wall.
- bmesh for precise geometry [5.3]:

```python
import bmesh

bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.05, segments=3, affect="EDGES", profile=0.5)
bm.to_mesh(mesh)
bm.free()
```

- Voxel remesh [5.3]: `mesh.remesh_voxel_size = 0.01-0.05` (smaller = denser; a 1 m object
  at 0.01 is about 60k faces), then `bpy.ops.object.voxel_remesh()` with the object active.
  It replaces the mesh: keep a copy first.
- Sculpt mode [5.3]: `bpy.ops.object.mode_set(mode="SCULPT")`; `bpy.ops.sculpt` has
  `dynamic_topology_toggle`, `mask_flood_fill`, `face_sets_create`. Brush strokes from
  scripts (`brush_stroke`) need a viewport context and are unreliable; for scripted
  "sculpting" use Displace modifiers with textures, proportional transforms in bmesh, or
  the full-profile `sculpt_deform` tool.
- Multires: `ob.modifiers.new("Multires", "MULTIRES")`, then subdivide with
  `bpy.ops.object.multires_subdivide(modifier="Multires", mode="CATMULL_CLARK")`.
- Auto smooth: `bpy.ops.object.shade_auto_smooth(angle=0.5236)` [5.3, adds a modifier in
  4.1+]; before 4.1 `mesh.use_auto_smooth` [untested].

## Common mistakes

- Scale not applied: bevel width and solidify thickness come out uneven. Apply scale first
  (`bpy.ops.object.transform_apply(scale=True)`).
- Bevel before Mirror or Boolean: seams and broken bevels. Keep the order above.
- Subdivision without support loops: everything turns into blobs.
- Boolean on non-manifold meshes: holes and artefacts. Check with
  `bm.edges` where `not e.is_manifold` before cutting.
- Sculpting on low, uneven topology: stretched details. Remesh first.
- Modelling unseen detail: spend effort where the camera looks.

## Verification checklist

- [ ] Dimensions match the brief (`ob.dimensions`), scale applied, origin sensible.
- [ ] No non-manifold edges where a closed solid is needed; normals face outwards.
- [ ] `look(mode="angles")` from front, side and top; `look(mode="material")` shows clean
      shading without pinching or dark seams.
- [ ] Face count suits the use (`len(evaluated.data.polygons)`).
- [ ] Objects named, in their collection; cutters hidden from render.

## Manual work and external tools

- Detailed character and creature sculpting is hand work with a tablet; offer a blockout
  and leave the sculpt to the user, or use `generate_3d` / Sketchfab.
- Retopology of sculpts for animation is mostly manual (or Instant Meshes, Quad Remesher).
- CAD-precise parts may be faster in a CAD tool, exported as STEP/OBJ and cleaned here.
- Modelling add-ons (Hard Ops, BoxCutter, Bool Tool) must be installed and enabled by the
  user: safe execution mode refuses enabling add-ons and registering classes. Explain that
  to the user and never try to bypass it.
