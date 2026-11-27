# Game-ready assets

Tested on Blender 5.3 (marked [5.3]). Notes for 3.6 and 4.x are untested (marked
[untested]). Check uncertain names with `lookup_api`.

## When to use

Props, environment pieces, vehicles or characters for Unity, Unreal, Godot or the web
(three.js, Babylon). Not for renders only in Blender: those can be as heavy as they like.

## Inputs needed

- Target engine and format: glTF/GLB (Godot, web, most engines), FBX (Unity, Unreal).
- Triangle budget and platform: mobile prop 500-3k tris, PC prop 2k-15k, hero 20k-60k,
  character 15k-80k.
- Texture resolution and texel density (e.g. 512 px/m mobile, 1024 px/m PC), and whether
  textures may be shared (trim sheets, atlases).
- LODs, collision and animation needed or not.

## Workflow

1. Scale and orientation: 1 Blender unit = 1 m. Model facing -Y (Blender front); the
   exporters convert to the engine's axes. Origin at the base centre for props, at the
   hinge for doors. Apply rotation and scale (`bpy.ops.object.transform_apply`).
2. Low-poly: model to silhouette; spend triangles where the outline is seen. Remove hidden
   faces and interior geometry. Or retopologise a sculpt / generated mesh (Decimate is a
   last resort; it makes messy topology for deforming meshes).
3. Shading: `bpy.ops.object.shade_auto_smooth(angle=0.5236)` (30 degrees) [5.3; in 4.1+ it
   adds a "Smooth by Angle" geometry-nodes modifier; before 4.1 set
   `mesh.use_auto_smooth = True`, untested]. Mark hard edges as UV seams too.
4. UVs: one non-overlapping UV map in 0-1 for baking; `bpy.ops.uv.smart_project` for props,
   seams + `unwrap` for organic shapes, then `pack_islands` with a margin. Keep texel
   density even across the asset.
5. Bake high to low (if a high-poly exists): Cycles, `bake.use_selected_to_active = True`,
   a small `cage_extrusion`, bake NORMAL, AO, then base colour/roughness as needed
   (read `get_guide("materials")` for material setup).
6. Materials: one Principled BSDF per material with image textures; few materials per
   asset (each is a draw call). glTF reads Principled inputs directly.
7. LODs and collision: duplicate and decimate for LODs (`_LOD0`, `_LOD1` at ~50 %, `_LOD2`
   ~25 %); collision as simple convex meshes named `UCX_<asset>_01` (Unreal).
8. Export, then re-import into a clean scene and check (below).

## Tested values and code

```python
# [5.3] selected objects, modifiers applied on export
bpy.ops.export_scene.gltf(filepath=p + ".glb", export_format="GLB",
                          use_selection=True, export_apply=True)
bpy.ops.export_scene.fbx(filepath=p + ".fbx", use_selection=True,
                         apply_scale_options="FBX_SCALE_UNITS",
                         axis_forward="-Z", axis_up="Y",
                         add_leaf_bones=False, mesh_smooth_type="FACE")
```

- glTF `export_format` choices are filled in at run time (GLB, GLTF_SEPARATE); don't read
  them from `bl_rna` [5.3]. Animation exports by default (`export_animations`).
- FBX scale: `FBX_SCALE_UNITS` is the common choice for Unity (avoids a 100x object scale);
  Unreal usually imports the default at the right size. Check the size after import in the
  engine [not tested in an engine]. `add_leaf_bones=False` avoids extra bones;
  `bake_anim=True` for animation.
- Count triangles on evaluated geometry:
  `ev = ob.evaluated_get(depsgraph); sum(len(p.vertices) - 2 for p in ev.data.polygons)`.
- Bake types [5.3]: COMBINED, AO, SHADOW, POSITION, NORMAL, UV, ROUGHNESS, EMIT,
  ENVIRONMENT, DIFFUSE, GLOSSY, TRANSMISSION. Baking needs the Cycles engine, an image
  texture node selected as active in each material, and can take minutes: pass a larger
  `timeout` to execute_blender_code.
- Normal maps: baked in tangent space, image Non-Color, OpenGL (Y+) convention; Unreal and
  DirectX engines want Y flipped (Unreal's importer has an option).

## Common mistakes

- Unapplied scale: the asset imports 100x too big or small, physics and lightmaps break.
- N-gons and non-planar quads triangulate differently in the engine: add a Triangulate
  modifier before baking so bake and engine agree.
- Overlapping or out-of-bounds UVs when baking: garbage lightmaps and bakes.
- Flipped normals (black faces in engine): `bpy.ops.mesh.normals_make_consistent()`.
- Too many materials, or 4K textures on a mug.
- Exporting the whole scene (cameras, lights, helpers): use `use_selection=True`.
- Procedural shader nodes don't export: bake them to images first.

## Verification checklist

- [ ] Triangle count per LOD within budget; materials and texture sizes within budget.
- [ ] Scale and rotation applied; origin where the engine needs it; real-world size.
- [ ] One clean UV map, no overlaps, even texel density; normals consistent.
- [ ] `look(mode="material")` and `look(mode="angles")` show no shading artefacts.
- [ ] Re-import the exported file into a new collection: same size, orientation,
      materials and textures; then delete the re-import.
- [ ] File names and object names follow the engine convention (`SM_`, `SK_`, `UCX_`).

## Manual work and external tools

- Final check in the engine itself (lighting, LOD switching, collision) is the user's step.
- Clean retopology of characters is mostly manual (or external tools such as Instant Meshes).
- Texture painting at scale is easier in Substance Painter, Armor Paint or Krita.
- Exporter add-ons (e.g. game-engine bridges) must be installed and enabled by the user:
  safe execution mode refuses enabling add-ons and changing preferences. Explain that to
  the user; don't try to bypass it.
