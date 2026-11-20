# Writing bpy code that works in any Blender

- Inspect first: read the scene (`get_scene_info`, `get_objects`) before changing anything.
- Find shader nodes by `node.type` (e.g. `"BSDF_PRINCIPLED"`), never by `node.name`:
  names are translated in non-English Blender builds.
- Don't hardcode enum values that change between versions (render engines, file formats).
  Read them: `[i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]`.
- Operators depend on mode, active object and selection. Set all three explicitly, and use
  `bpy.context.temp_override(...)` for operators that need a specific area.
- After changing transforms or modifiers, call `bpy.context.view_layer.update()` before reading
  `matrix_world` or evaluated geometry.
- In Edit Mode use `bmesh` and call `bmesh.update_edit_mesh(mesh)` to flush changes.
- Objects made with `bpy.data` must be linked to a collection to appear in the scene.
- Return dicts/lists from scripts rather than printing.
