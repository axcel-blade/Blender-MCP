# XR assets (AR, VR and web 3D)

Tested on Blender 5.3 (marked [5.3]). Notes for 3.6 and 4.x are untested (marked
[untested]). General engine-asset rules (UVs, baking, LODs, FBX) are in `game_assets`;
this guide adds what is specific to AR/VR and real-time web viewers.

## When to use

Models for AR Quick Look (iOS USDZ), Android Scene Viewer and web viewers
(`<model-viewer>`, three.js, Babylon), WebXR scenes, VR headsets (Quest, Vision Pro via
USDZ/Reality Composer), and e-commerce product viewers.

## Inputs needed

- Target platform and format: USDZ (Apple), GLB (Android, web, most engines).
- File size limit (web/AR: aim for under 5-10 MB; Quest standalone scenes stricter).
- Real-world size (AR places objects at true scale) and where the origin should sit.
- Animation needed or not; whether materials may be simplified.

## Workflow

1. Real scale in metres, origin at the base centre (the AR anchor point), facing -Y
   (front); apply all transforms.
2. Budget: single objects 10k-100k triangles for mobile AR, 1-2 materials, textures
   1024-2048 px (power of two), baked to Base Color, ORM (occlusion/roughness/metallic) and
   Normal (see `game_assets` for baking).
3. Materials: Principled BSDF with image textures only; procedural nodes, complex mixes
   and most shader tricks don't export. Transparency via Alpha with blend mode set.
4. Animation: object or armature keyframes export; constraints and drivers must be baked.
5. Export GLB (optionally Draco-compressed) and/or USDZ.
6. Re-import into a clean scene, check size, look and file size; then test on the device.

## Tested values and code

```python
# [5.3] web/Android GLB with Draco mesh compression, and Apple USDZ
with bpy.context.temp_override(selected_objects=[ob], active_object=ob, object=ob):
    bpy.ops.export_scene.gltf(
        filepath=base + ".glb",
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_draco_mesh_compression_enable=True,
    )
    bpy.ops.wm.usd_export(filepath=base + ".usdz", selected_objects_only=True)
```

- Tested [5.3]: both exports finished for a simple test mesh (GLB with Draco 1.0 KB, USDZ
  1.8 KB). The USD exporter writes a zipped USDZ when the file name ends in `.usdz`.
- glTF options [5.3]: `export_draco_mesh_compression_level` (0-10, default 6),
  `export_image_format` (AUTO, JPEG, WEBP...; JPEG for colour maps shrinks files),
  `export_jpeg_quality`, `export_image_quality`. Draco needs a decoder in the viewer
  (three.js DRACOLoader; `<model-viewer>` includes it).
- USD options [5.3]: `export_materials`, `generate_preview_surface` (UsdPreviewSurface for
  Quick Look), `usdz_downscale_size` (cap texture size), `convert_orientation`,
  `root_prim_path`, `export_animation`. Option names changed across 3.6-4.x [untested]:
  read them with `bpy.ops.wm.usd_export.get_rna_type().properties`.
- Triangle and size estimate before export: count evaluated triangles (`game_assets`) and
  sum image sizes (`img.size[0] * img.size[1] * 4` bytes uncompressed per image).
- Typical AR sizes: furniture true size (a chair ~0.45 m seat), tabletop products at true
  size, characters 1.6-1.8 m.

## Common mistakes

- Wrong scale or origin: the object floats, sinks or appears gigantic in AR.
- Procedural or node-heavy materials: export as grey. Bake to image textures first.
- 4K textures on a phone AR model: slow loading, crashes. 2K is plenty for most objects.
- Separate meshes for every part: many draw calls. Join static parts that share a material.
- Draco-compressed GLBs in viewers without a Draco decoder: the model won't load.
- Animations driven by constraints or drivers: not exported. Bake them to keys.
- Testing only in Blender: AR viewers differ (lighting, colour). Test on the device.

## Verification checklist

- [ ] Real-world dimensions (`ob.dimensions`) and origin at the base; transforms applied.
- [ ] Triangles, material count, texture sizes and final file size within budget.
- [ ] Re-imported GLB/USDZ looks the same with `look(mode="material")`; then delete it.
- [ ] Animation plays from the exported file (if any).
- [ ] The user has tested it in the target viewer or device.

## Manual work and external tools

- Device testing (iPhone Quick Look, Android Scene Viewer, Quest browser) is the user's step.
- Apple Reality Converter / Reality Composer Pro for USDZ fine-tuning; glTF tooling such as
  gltf-transform or the Khronos glTF Validator for optimisation and checks, run by the user
  (safe execution mode refuses starting external programs).
- WebXR app code (three.js scenes) lives outside Blender.
- Exporter add-ons or extensions beyond the bundled ones must be enabled by the user; safe
  execution mode refuses enabling add-ons. Explain that and never bypass it.
