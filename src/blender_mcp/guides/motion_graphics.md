# Motion graphics

Tested on Blender 5.3 (marked [5.3]). Notes for 3.6 and 4.x are untested (marked
[untested]). Keyframes and F-Curves are in `animation_3d`, glare and grading in
`cinematic` and `rendering_compositing`, procedural setups in `geometry_nodes`.

## When to use

Animated logos and titles, kinetic typography, explainer graphics, product feature
call-outs, abstract loops, data-driven animation, social media clips and lower thirds.

## Inputs needed

- Format: aspect (16:9, 9:16, 1:1), fps (25/30 common for web, 60 smooth), length.
- Brand: fonts (files on disk), colours (hex values), logo (SVG or image).
- Text content and timing (when each line appears); music and its beats if any.
- Loop or not; transparent background (for compositing) or a full frame.

## Workflow

1. Frame: set resolution, fps and range; an orthographic camera (`cam.data.type = "ORTHO"`)
   for flat graphic looks, or a long lens (85-135 mm) for subtle depth.
2. Text and shapes: text objects (FONT curves) for titles; curves with bevel for lines and
   strokes; simple meshes or geometry nodes for patterns. Load brand fonts with
   `bpy.data.fonts.load(path)`.
3. Materials: Emission or flat colours for graphic looks (EEVEE), matching brand hex
   values (convert sRGB hex to linear before setting).
4. Animate with intent: staggered entrances (offset each element 2-4 frames), ease-out
   moves, overshoot for energy; time to the music's beats.
5. Draw-on effects: animate curve `bevel_factor_end` 0 -> 1, the Build modifier on meshes,
   or geometry nodes (Trim Curve).
6. Polish: motion blur, a little glare on emissive elements, colour grade.
7. Render with EEVEE; check key frames with `look(mode="render")`.

## Tested values and code

```python
# [5.3] extruded centred title and a line that draws on over 30 frames
cu = bpy.data.curves.new("Title", "FONT")
cu.body = "MOTION"
cu.extrude = 0.05
cu.bevel_depth = 0.01
cu.align_x = "CENTER"
cu.align_y = "CENTER"
title = bpy.data.objects.new("Title", cu)
collection.objects.link(title)

path = bpy.data.curves.new("Line", "CURVE")
path.dimensions = "3D"
sp = path.splines.new("BEZIER")
sp.bezier_points.add(2)
for i, bp in enumerate(sp.bezier_points):
    bp.co = (i, 0, 0)
    bp.handle_left_type = bp.handle_right_type = "AUTO"
path.bevel_depth = 0.02
path.bevel_factor_end = 0.0
path.keyframe_insert("bevel_factor_end", frame=1)
path.bevel_factor_end = 1.0
path.keyframe_insert("bevel_factor_end", frame=30)
```

  Tested [5.3]: at frame 15 `bevel_factor_end` evaluates to 0.474 (Bezier ease).
- Font curve properties [5.3]: `body`, `size`, `extrude`, `bevel_depth`, `align_x`,
  `align_y`, `offset_x`, `space_character`, `body_format` (per-character styling).
- Hex to linear colour: `c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4` for
  each channel c in 0-1.
- Timing at 30 fps: element entrance 10-15 frames, stagger 2-4 frames, hold text at least
  1.5-2 s per line (reading speed ~3 words per second), logo resolve 20-40 frames.
- Text in geometry nodes: `GeometryNodeStringToCurves` [5.3] for procedural or data-driven
  text (counters, labels).
- Per-letter animation: convert a copy of the text to mesh (`bpy.ops.object.convert`,
  target MESH) and separate by loose parts, or use geometry nodes; keep the editable text.
- Loops: make the first and last frames match, use Cycles F-Curve modifiers on rotations.

## Common mistakes

- Fonts referenced from the user's system without loading them: renders fall back to the
  default font. Load the font file and check `cu.font`.
- Colours typed in as sRGB numbers directly: everything looks washed out. Convert to linear.
- Everything moving at once with linear timing: busy and mechanical. Stagger and ease.
- Text too small or on screen too briefly for mobile viewers.
- Filmic/AgX view transforms desaturating brand colours: use Standard for exact brand
  colours (`view_settings.view_transform = "Standard"`).
- Converting the only copy of text to mesh: it can no longer be edited.

## Verification checklist

- [ ] Resolution, fps, length and safe margins (keep text inside ~90 % of the frame).
- [ ] Brand fonts loaded and colours match (Standard view transform, linear values).
- [ ] `look(mode="render")` at each beat: entrances, holds and exits read clearly.
- [ ] Loops are seamless if required; motion blur and glare as intended.
- [ ] Text stays legible at the delivery size (check a small render too).

## Manual work and external tools

- Final timing to music is best judged by the user watching a preview.
- Complex 2D compositing or templates may be faster in After Effects or DaVinci Fusion;
  render with transparent background (`film_transparent`, PNG RGBA or EXR) for them.
- Logo vectors: import SVG (`bpy.ops.import_curve.svg`, present in [5.3]; arguments untested) or prepare them in
  Illustrator/Inkscape.
- Animation add-ons (e.g. text effects packs) must be enabled by the user; safe execution
  mode refuses enabling add-ons and frame-change handlers. Use drivers or keyframes
  instead, explain the limit, and never bypass it.
