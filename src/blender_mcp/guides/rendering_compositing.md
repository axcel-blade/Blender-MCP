# Rendering and compositing

Tested on Blender 5.3 (marked [5.3]). Notes for 3.6 and 4.x are untested (marked
[untested]). Photoreal choices are in `realism`; stylised glare and grading recipes in
`cinematic`. This guide covers engines, quality vs time, passes, output and the compositor.

## When to use

Setting up or speeding up renders, picking EEVEE or Cycles, noise and fireflies, render
passes and multilayer EXR, output formats and video, and compositor work (denoise, depth of
field, grading, masks, Cryptomatte).

## Inputs needed

- Deliverable: still or animation, resolution, frame range, file format (PNG/EXR/video).
- Time budget per frame and hardware (GPU or CPU); whether the user renders or you do.
- Whether later compositing elsewhere (Nuke, Resolve, After Effects) needs passes.

## Workflow

1. Engine: EEVEE for stylised, motion graphics and fast previews; Cycles for accurate
   light transport (glass, caustic-like detail, volumes, interiors).
2. Look development at low cost: `look(mode="render", max_size=512)` with low samples.
3. Quality: raise samples until noise is gone after denoising; fix fireflies at the source
   (clamp indirect, larger lights, fewer caustics) rather than with samples.
4. Passes: enable only what the composite needs (Mist, Z, Normal, AO, Cryptomatte).
5. Compositor: denoise (if not done in render), then grading, glare, lens effects, output.
6. Output: still as PNG (8-bit) or EXR (16/32-bit float, keeps HDR); animation as an image
   sequence first (crash-safe), then encode to video.
7. Final test frame at full resolution, then render the rest.

## Tested values and code

```python
# [5.3] Cycles with denoising, two passes, H.264 video output
try:
    scene.render.engine = "CYCLES"
except TypeError as exc:  # message lists the engines available
    raise ValueError(f"Cycles unavailable: {exc}")
cy = scene.cycles
cy.samples = 256
cy.use_adaptive_sampling = True
cy.adaptive_threshold = 0.02
cy.use_denoising = True
cy.sample_clamp_indirect = 10
vl = scene.view_layers[0]
vl.use_pass_mist = True
vl.use_pass_cryptomatte_object = True
ims = scene.render.image_settings
if "media_type" in ims.bl_rna.properties:  # 5.0+
    ims.media_type = "VIDEO"
else:  # [untested]
    ims.file_format = "FFMPEG"
scene.render.ffmpeg.format = "MPEG4"
scene.render.ffmpeg.codec = "H264"
scene.render.ffmpeg.constant_rate_factor = "HIGH"
```

- Cycles [5.3] via `scene.cycles`: `samples` 128-512 (stills), 64-256 (animation with
  denoising); `use_adaptive_sampling = True`, `adaptive_threshold` 0.01-0.03;
  `use_denoising = True`; `time_limit` (seconds, 0 = off); `max_bounces` 8-12,
  `transparent_max_bounces` 16+ for foliage/hair; `use_light_tree = True` for many lights.
  The `denoiser` choices depend on the hardware, so read them at run time or assign inside
  try/except TypeError. `scene.cycles` only exists once the Cycles add-on is loaded.
- EEVEE (Next, 4.2+) [5.3]: `scene.eevee.taa_render_samples` 64-128, `use_raytracing`,
  `ray_tracing_method`, `use_shadows`, `shadow_ray_count`, `fast_gi_method`. Legacy EEVEE
  settings (`use_gtao`, `use_bloom`, `use_ssr`) are gone in 4.2+ [untested before 4.2].
- Colour management: `scene.view_settings.view_transform` in 5.3 accepts Standard,
  ACES 1.3, ACES 2.0, Khronos PBR Neutral, AgX, Filmic, Filmic Log, False Color, Raw (a
  wrong value raises TypeError listing them). AgX from 4.0; 3.6 has Filmic [untested].
- Passes [5.3]: `view_layer.use_pass_z`, `use_pass_mist`, `use_pass_normal`,
  `use_pass_diffuse_color`, `use_pass_emit`, `use_pass_ambient_occlusion`,
  `use_pass_cryptomatte_object`; denoising data `view_layer.cycles.denoising_store_passes`.
- Output [5.3]: `image_settings.media_type` is IMAGE, MULTI_LAYER_IMAGE or VIDEO; video
  needs `media_type = "VIDEO"` (then `file_format` is FFMPEG) and
  `scene.render.ffmpeg.format/codec/constant_rate_factor`. Before 5.0 set
  `file_format = "FFMPEG"` directly [untested]. Still formats in 5.3: PNG, JPEG, OPEN_EXR,
  WEBP, AVIF, TIFF, HDR and more.
- Compositor setup and Glare: see `cinematic` (5.x uses `scene.compositing_node_group`).
  Useful nodes [5.3]: CompositorNodeDenoise (inputs Image, Albedo, Normal, HDR, Prefilter,
  Quality), CompositorNodeDefocus (Image, Z), CompositorNodeCryptomatteV2,
  CompositorNodeCurveRGB, CompositorNodeEllipseMask, CompositorNodeBlur. In 5.x the old
  CompositorNodeMixRGB is gone: mix with `ShaderNodeMix` inside the compositor tree.
- `render.use_persistent_data = True` speeds up animation renders in Cycles (keeps BVH).
- Render from scripts with `bpy.ops.render.render(write_still=True)`; it blocks Blender, so
  pass `timeout` to execute_blender_code, or use `look(mode="render")` for checks.

## Common mistakes

- Raising samples to kill fireflies: clamp indirect (`sample_clamp_indirect` 5-10) or fix the
  light setup instead.
- Rendering animation straight to video: one crash loses everything. Render PNG/EXR frames.
- 8-bit PNG for footage that will be graded: banding. Use 16-bit or EXR.
- Denoising twice (render and compositor), or denoising passes needed later.
- Hardcoding engine, denoiser or format identifiers that differ between versions.
- Changing the user's render settings for a test and leaving them: restore them, or use
  `look(mode="render")`, which restores them for you.

## Verification checklist

- [ ] Engine, samples, resolution and frame range match the brief.
- [ ] A test frame at full resolution looks clean (noise, fireflies, banding).
- [ ] Time per frame measured and acceptable for the whole range.
- [ ] Passes present in the output (open the EXR layers) if compositing comes later.
- [ ] Output path, format and colour management set; files actually appear on disk.
- [ ] The user's previous settings restored after any test renders.

## Manual work and external tools

- Long final renders: the user starts them (or `batch_render` in the full profile) and lets
  Blender run; a render blocks Blender for its whole duration.
- Render farms and command-line rendering (`blender -b file.blend -a`) run outside this MCP.
- Heavy compositing and editorial: Nuke, DaVinci Resolve, After Effects.
- GPU device selection lives in Preferences; safe execution mode refuses changing
  preferences, so ask the user to pick the device. Never bypass the mode.
