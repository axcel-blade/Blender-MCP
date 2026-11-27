# Materials, UVs, texture painting and baking

Tested on Blender 5.3 (marked [5.3]). Notes for 3.6 and 4.x are untested (marked
[untested]). Photoreal material values are in `realism`; engine export rules in
`game_assets`.

## Basics (all versions)

- Colors go on shader node inputs (Principled BSDF "Base Color"). `material.diffuse_color`
  only changes the Solid-mode viewport.
- Image maps other than color (roughness, metallic, normal, displacement) need
  `image.colorspace_settings.is_data = True` (Non-Color).
- Normal maps go through a Normal Map node into the BSDF "Normal" input.
- Check `mesh.users` before editing shared data; editing a shared material changes every
  object that uses it.
- Check the result with `look(mode="material")` or `look(mode="render")`.

## When to use

Creating or fixing materials, unwrapping UVs for textures, painting textures in Blender,
and baking procedural materials, lighting (AO) or high-poly detail into image textures.

## Inputs needed

- The look (reference images, real material names) and the destination: Blender render
  only (procedural is fine) or export (needs image textures and UVs).
- Texture resolution (1K/2K/4K) and texel density if it is a game or XR asset.
- Existing UVs and materials on the object: keep them unless the user agrees.

## Workflow

1. Material: one Principled BSDF; find it by `node.type == "BSDF_PRINCIPLED"`. Input names
   changed in 4.0 ("Specular" -> "Specular IOR Level", "Emission" -> "Emission Color",
   "Transmission" -> "Transmission Weight", "Subsurface" -> "Subsurface Weight"): check
   `"name" in node.inputs`.
2. UVs: mark seams on hidden edges and `unwrap`, or `smart_project` for hard-surface props;
   then `average_islands_scale` and `pack_islands` with a margin.
3. Texture painting: create an image, add an Image Texture node using it, enter Texture
   Paint mode and let the user paint (strokes need a tablet and the viewport).
4. Baking: Cycles; an Image Texture node with the target image, **selected and active** in
   every material of the object; bake; save the image to disk.
5. Swap the procedural setup for the baked images if exporting; check the result.

## Tested values and code

```python
# [5.3] unwrap, create a target image, bake AO, save
with bpy.context.temp_override(
    active_object=ob, object=ob, selected_objects=[ob], selected_editable_objects=[ob]
):
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15192, island_margin=0.03)  # 66 degrees
    bpy.ops.object.mode_set(mode="OBJECT")
img = bpy.data.images.new(ob.name + "_AO", 1024, 1024)
nt = mat.node_tree
tex = nt.nodes.new("ShaderNodeTexImage")
tex.image = img
for n in nt.nodes:
    n.select = False
tex.select = True
nt.nodes.active = tex  # the bake writes into the active node
scene.render.engine = "CYCLES"
scene.cycles.samples = 16
scene.render.bake.margin = 8  # px of padding around islands
with bpy.context.temp_override(
    active_object=ob, object=ob, selected_objects=[ob], selected_editable_objects=[ob]
):
    bpy.ops.object.bake(type="AO")
img.filepath_raw = path
img.file_format = "PNG"
img.save()
```

- Tested [5.3]: a cube on a floor baked to the expected map (black underside, white top,
  graded sides) in under a second at 16 samples and 512 px.
- Bake types [5.3]: COMBINED, AO, SHADOW, POSITION, NORMAL, UV, ROUGHNESS, EMIT,
  ENVIRONMENT, DIFFUSE, GLOSSY, TRANSMISSION. For DIFFUSE colour only, set
  `scene.render.bake.use_pass_direct = use_pass_indirect = False` (properties exist in
  [5.3]; the result was not checked).
- High to low: select the high-poly, then the low-poly active,
  `bake.use_selected_to_active = True`, `cage_extrusion` 0.01-0.05 m (see `game_assets`).
- UV operators [5.3]: `smart_project`, `unwrap` (methods ANGLE_BASED, CONFORMAL,
  MINIMUM_STRETCH), `cube_project`, `lightmap_pack`, `average_islands_scale`,
  `pack_islands` (margin, rotate, shape_method, margin_method); seams with
  `bpy.ops.mesh.mark_seam()` on selected edges. All need Edit Mode with faces selected.
- Image pixels: `img.pixels.foreach_set(numpy_float_array)` then `img.update()`; much faster
  than assigning `img.pixels[:]`.
- Texture paint [5.3]: `bpy.ops.paint.texture_paint_toggle`, `add_texture_paint_slot`,
  `project_image`; brush strokes from scripts need a viewport and are unreliable.
- Samples for bakes: AO and NORMAL 16-64, COMBINED 128+ (noise bakes in).

## Common mistakes

- No Image Texture node selected and active in a material: "No active image found" or the
  bake writes into the wrong image.
- Baking without UVs, or with overlapping UVs: smeared, overwritten bakes.
- Forgetting to save the image: baked images live only in memory until saved or packed.
- Non-Color images left as sRGB (normal, roughness): wrong shading.
- Bake margin too small: seams show when mip-mapped in engines (use 8-16 px at 1K-2K).
- Editing a shared material for one object: duplicate it first (`mat.copy()`).

## Verification checklist

- [ ] Correct Principled input names for the user's version; colour spaces set.
- [ ] UVs: no overlaps (for bakes), islands inside 0-1, consistent texel density.
- [ ] Baked images look right (open or `look`), saved to disk, connected in the material.
- [ ] `look(mode="material")` and `look(mode="render")` show the intended surface.

## Manual work and external tools

- Hand painting is the user's work with a tablet in Texture Paint mode; set up the image,
  slots and brushes, then hand over.
- Substance Painter, Armor Paint or Quixel Mixer for layered PBR painting; export maps and
  connect them here.
- Material add-ons and asset libraries must be added by the user: safe execution mode
  refuses enabling add-ons and changing preferences. Explain that and never bypass it.
