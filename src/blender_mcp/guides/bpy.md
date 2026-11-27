# Writing bpy code that works in any Blender

Tested on Blender 5.3 (marked [5.3]). Notes for 3.6 and 4.x are untested (marked
[untested]). Topic guides cover their own APIs; this one is about scripts in general,
batch work and what safe execution mode allows.

## Rules for every script

- Inspect first: read the scene (`get_scene_info`, `get_objects`) before changing anything.
- Find shader nodes by `node.type` (e.g. `"BSDF_PRINCIPLED"`), never by `node.name`:
  names are translated in non-English Blender builds.
- Don't hardcode enum values that change between versions (render engines, file formats).
  Read them: `[i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]`,
  or assign inside try/except TypeError: the message lists the valid values.
- Operators depend on mode, active object and selection. Set all three explicitly, and use
  `bpy.context.temp_override(...)` for operators that need a specific area.
- After changing transforms or modifiers, call `bpy.context.view_layer.update()` before reading
  `matrix_world` or evaluated geometry.
- In Edit Mode use `bmesh` and call `bmesh.update_edit_mesh(mesh)` to flush changes. After
  `bm.from_mesh()`, call `bm.faces.ensure_lookup_table()` before indexing `bm.faces[i]` [5.3].
- Objects made with `bpy.data` must be linked to a collection to appear in the scene.
- Return dicts/lists from scripts rather than printing.

## When to use (batch work)

Changing many objects at once (rename, re-material, apply transforms, export each),
processing data (vertices, attributes, pixels), running the same steps on several files,
and anything where an add-on would normally be written.

## Inputs needed

- Exactly which objects: by collection, name pattern, type or selection. Show the list to
  the user before destructive batch changes.
- Whether the change should be one undo step (one script) or several.

## Workflow

1. Select targets with the data API: `[o for o in bpy.data.objects if o.type == "MESH" and
   o.name.startswith("SM_")]`, or walk a collection with `col.all_objects`.
2. Dry run: return what would change (names, counts) without changing it.
3. Apply in one script with the data API; avoid operators in loops where a data call exists.
4. Report counts and anything skipped; `look` at a sample.

## Tested values and code

```python
# [5.3] dry run first, apply only after the user agrees
def batch_prefix(objects, prefix, apply=False):
    plan = [(o.name, prefix + o.name) for o in objects if not o.name.startswith(prefix)]
    if apply:
        for old, new in plan:
            bpy.data.objects[old].name = new
    return {"apply": apply, "count": len(plan), "changes": plan[:50]}

targets = [o for o in bpy.data.objects if o.type == "MESH"]
result = batch_prefix(targets, "SM_")          # returns the plan, renames nothing
```

- Bulk data [5.3]: `mesh.vertices.foreach_get("co", buf)` / `foreach_set` with a numpy
  float32 array were ~14x faster than a Python loop on 3.7k vertices. Same for attributes
  (`attr.data.foreach_set("value", arr)`), image pixels and point clouds.
- Data API beats operators: `ob.data.materials.append(mat)`, `col.objects.link(ob)`,
  `ob.modifiers.new(...)`, `bpy.data.objects.remove(ob)` need no context.
- Removing an object with `bpy.data.objects.remove` can free its unused data in 5.3; read
  `ob.data` *before* removing and guard later access against `ReferenceError` [5.3].
- Operators on many objects: one `temp_override(selected_objects=[...], active_object=a,
  object=a)` instead of changing the user's selection; restore selection if you change it.
- Long scripts: pass `timeout` to execute_blender_code (default 60 s, max 3600 s).
- Batch over files: `bpy.ops.wm.open_mainfile` replaces the user's session; use the
  `blend_file` tool (it refuses on unsaved changes) or `bpy.data.libraries.load(path)` to
  read data from other files without opening them.

## Safe execution mode

The add-on's Safe execution mode (on by default) parses every script before it runs and
refuses it if it would:

- run other programs (`subprocess`, `os.system`, `os.startfile`, ...), including pip;
- delete files or folders (`os.remove`, `shutil.rmtree`, `Path.unlink()` ...);
- use the network (`socket`, `urllib`, `requests`, ...);
- change Blender beyond this file: `bpy.utils.register_class`, `bpy.app.handlers`,
  `bpy.app.timers.register`, `addon_utils` (enabling add-ons), `bpy.ops.preferences.*`,
  `bpy.ops.extensions.*`, saving preferences or the startup file, `script.reload`;
- end the session (quit, factory settings, load the startup file);
- reach around the checks (`eval`, `exec`, `__import__`, `importlib`, dunder attributes).

So writing or registering an add-on, panel, operator, frame-change handler or timer is
refused. When a task needs one: tell the user which line was refused and why, offer an
alternative that runs once (a plain script, drivers, baked keys, the full-profile tools),
and if they really need the add-on, they install it themselves or turn the mode off in
the add-on preferences. Never try to get around the mode (aliases, string tricks,
encoded code): that is exactly what it guards against. It is a guard, not a sandbox.

## Common mistakes

- Operators inside loops relying on the current selection: slow and fragile.
- Holding Python references across operations that rebuild data (undo, mode switches,
  removal): `ReferenceError`. Re-fetch by name.
- Per-element Python loops over large meshes or images.
- Changing the user's selection, mode, frame or active object and not restoring them.
- Hidden failures: return counts and errors instead of silently skipping.

## Verification checklist

- [ ] The target list was shown or returned before destructive changes.
- [ ] Result counts match expectations; skipped items reported with reasons.
- [ ] User state restored (selection, active object, mode, frame, scene).
- [ ] A sample of the result checked with `look` or `get_object_info`.

## Manual work and external tools

- Real add-ons (UI panels, operators, handlers) are written as files and installed by the
  user through Preferences; you can draft the code as a file for them to review.
- Command-line batch jobs (`blender -b file.blend --python script.py`) run outside this MCP.
