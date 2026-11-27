# Cinematic and stylised scenes from a reference

Use this for stylised, concept-art, "epic", fantasy or matte-painting looks, usually from a
reference image. For photoreal requests read `realism` instead. The goal is the reference's
shapes, values and mood, not physical accuracy: big readable silhouettes, depth layers, strong
light and a graded image.

This repo supports Blender 3.6 to 5.x and several APIs changed in that range (marked below).
The compositor, Glare, Principled and Sky details were tested on Blender 5.3; the 3.6 and
4.x notes come from the API changes and are untested. Check anything you are unsure of
with `lookup_api` before scripting: it reads the user's own Blender.

## When to use

Stylised environments, key art, concept-art recreations, "epic" or moody stills and short
shots. Not for photoreal product or archviz work (`realism`).

## Inputs needed

- The reference image (or a clear description), and what must match: layout only, or
  palette and mood too.
- Aspect ratio and output size; still or a short camera move.
- Hero objects that need assets or `generate_3d`, and whether credits may be spent.

Work in stages (see `recreate_reference` prompt): blockout, main structures, detail,
materials, sky and lighting, compositing. After each stage run `look(mode="render")`,
compare with the reference, name the three biggest differences, fix them, then ask the user.

## 1. Match the reference camera first

- Study the reference: where the horizon sits (fraction of frame height), the vanishing
  points, how big the hero reads, and the aspect ratio. Set `scene.render.resolution_x/_y`
  to that aspect before anything else.
- Focal length: wide vistas with deep perspective 18-28 mm; most concept shots 28-50 mm;
  flattened, compressed layers (mountains stacked behind each other) 85-200 mm.
  `cam.data.lens` is in mm against `cam.data.sensor_width` (default 36).
- Horizon: a level camera (rotation X = 90 deg) puts the horizon in the frame centre. Move it
  with `cam.data.shift_y` (keeps verticals straight) rather than tilting. A low horizon
  feels heroic, a high one shows the ground plane.
- Blockout: cubes, cylinders and planes for every large mass, at plausible real scale, placed
  until `look(mode="camera")` overlays the reference layout. Name them `BLK_*` in a
  `Blockout` collection. Don't touch materials yet.
- Optional: load the reference as a camera background image
  (`cam.data.background_images.new()`, `cam.data.show_background_images = True`); it shows
  in the camera viewport only, never in renders.

## 2. Tracks, roads and bridges with Bezier curves

- A path is a Bezier curve (`bpy.data.curves.new(name, "CURVE")`, `dimensions="3D"`,
  `spline = curve.splines.new("BEZIER")`, `spline.bezier_points.add(n-1)`). Set each point's
  `co` and `handle_left_type = handle_right_type = "AUTO"` for smooth flow.
- Give it width with `curve.extrude` (half-width) and thickness with `curve.bevel_depth`, or
  sweep a profile: `curve.bevel_mode = "OBJECT"`, `curve.bevel_object = profile_curve`
  (`bevel_mode` exists from 2.91, so all supported versions).
- Repeating parts (planks, rails, sleepers): an Array modifier (`fit_type="FIT_CURVE"`,
  `curve=` the path) followed by a Curve modifier (`object=` the path) on a small part.
- Bridges: the deck is a curve; supports are an Array of pillars, or a curve with a bevel
  profile arching beneath. Sag a rope bridge by lowering middle points.
- `tilt` on Bezier points banks a track around corners.

## 3. Cliffs, mountains and floating islands

- Start from a subdivided mesh (grid or ico sphere), add a Subdivision Surface modifier,
  then a Displace modifier with a procedural texture
  (`tex = bpy.data.textures.new(name, "CLOUDS")` or `"VORONOI"`), `direction="NORMAL"` or
  `"Z"`, strength 0.5-5 relative to object size. Stack two Displace modifiers: large,
  low-frequency forms first, fine noise second at a smaller `noise_scale`.
- Cliffs: stretch a cube tall, subdivide, displace with Voronoi (sharp cracks) plus Clouds;
  a slightly negative `mid_level` shift breaks the top edge.
- Floating island: flatten the top of a sphere (scale Z, or bisect), then pull the
  underside into a tapering cone (proportional edit, or a Simple Deform `TAPER`), displace
  strongly so it hangs in rocky icicles. Add grass/trees only on the flat top.
- Distant mountains need no detail: big displaced planes, coloured by fog (section 5).
- For fine control use a geometry nodes setup, but displaced meshes render faster to
  iterate.

## 4. Hero objects: generate or download

Don't model complex hero objects (a dragon, a ship, a castle with ornament, a character)
from primitives. Search `search_assets` first (Poly Haven, Sketchfab, Poly Pizza for
stylised); if nothing fits, `generate_3d` from a text prompt or the cropped reference. One
generation is one object: use it for the hero, never for terrain or the whole scene. Scale
imports from their reported world bounding box. Simple architecture, rocks and paths you
model yourself.

## 5. Storm skies, fog and atmosphere

- Sky: world shader with a gradient (`ShaderNodeTexGradient` -> ColorRamp -> Background),
  or Sky Texture. Sky Texture types differ: `NISHITA` in 3.6/4.x; in 5.x the identifiers are
  `SINGLE_SCATTERING`/`MULTIPLE_SCATTERING` (plus PREETHAM, HOSEK_WILKIE). Read
  `bpy.types.ShaderNodeTexSky.bl_rna.properties["sky_type"].enum_items` before setting.
- Storm clouds: a large dome or a few huge planes behind the scene with an emissive/diffuse
  material driven by Noise texture -> ColorRamp (dark blue-grey to near-black), or a cube with
  a Principled Volume whose Density comes from a Noise texture through a ColorRamp
  (`Principled Volume` inputs: Color, Density, Anisotropy, Emission Strength, ...).
  An HDRI of overcast sky is a fast alternative (`search_assets`, asset_type hdris).
- Volumetric fog: a big cube enclosing the scene, material output Volume <- Principled
  Volume (or Volume Scatter) with Density 0.005-0.05 and Anisotropy 0.3-0.6 for god rays.
  Keep the camera inside or outside consistently. EEVEE: `scene.eevee.volumetric_end` must
  reach past the farthest object; lower `volumetric_tile_size` for sharper fog. Cycles is
  slower but more accurate for shafts of light.
- Depth layers: each layer back gets lighter and bluer (aerial perspective). If volumes are
  too slow, fake it with the Mist pass (`view_layer.use_pass_mist = True`,
  `scene.world.mist_settings.start/depth`) mixed in the compositor.

## 6. Lightning, glow and wet surfaces

- Lightning: a Bezier curve (or a mesh line) with jagged points and a few forks, small
  `bevel_depth`, material Emission Color blue-white, Emission Strength 20-200. A bright Area
  or Point light near the strike lights the scene. Glare (section 8) makes it bloom.
- Emissive materials (windows, runes, lava, crystals): Principled BSDF `Emission Color` and
  `Emission Strength` in 4.x/5.x; in 3.6 the input is `Emission` (and `Emission Strength`).
  Check `"Emission Color" in node.inputs`. Find the node by type, never by name.
- Wet materials: lower Roughness to 0.05-0.2, darken Base Color 20-40 %, add a Noise or
  Musgrave/Noise mask so wetness is patchy; puddles are near-zero roughness with a flat
  normal. Coat (`Coat Weight` in 4.x+, `Clearcoat` in 3.6) gives a wet sheen over rough
  stone.
- Stylised materials: limited palette, ColorRamp with Constant interpolation on a Layer
  Weight or Noise for painterly bands, exaggerated roughness contrast.

## 7. Rain

- Cheapest and best-looking for stills: a few large planes in front of the camera with a
  streaked transparent texture (stretched Noise -> ColorRamp into Alpha, Emission for
  backlit streaks), angled with the wind. Add motion blur feel by stretching in Y.
- Particle rain: an emitter plane above the scene, hair or object particles of a thin
  stretched emissive/glass mesh, `render_type="OBJECT"`. Heavier to iterate.
- Splashes and ripples only near the camera; mist does the rest.

## 8. Compositing: glare and grading

The compositor API changed in 5.0:

- 3.6/4.x: `scene.use_nodes = True`; tree is `scene.node_tree`; it already contains Render
  Layers and Composite.
- 5.x: `scene.node_tree` is gone. Create
  `tree = bpy.data.node_groups.new("Comp", "CompositorNodeTree")`, assign
  `scene.compositing_node_group = tree`, add a Render Layers node and a Group Output node
  (create the output socket with `tree.interface.new_socket("Image", in_out="OUTPUT",
  socket_type="NodeSocketColor")`).
  Check with `"compositing_node_group" in bpy.types.Scene.bl_rna.properties`.
- Glare: `CompositorNodeGlare`. In 3.6/4.x options are properties
  (`node.glare_type = "FOG_GLOW"` or `"BLOOM"` from 4.2, `threshold`, `size`, `mix`).
  In 5.x they are input sockets: `node.inputs["Type"]`, `["Threshold"]`, `["Strength"]`,
  `["Size"]`...; the Type menu takes names such as `"Bloom"` or `"Fog Glow"`, not the old
  upper-case identifiers. Use `lookup_api("CompositorNodeGlare")` to see which applies. Threshold ~1
  so only lightning, emissives and sun catch it.
- EEVEE's own Bloom (`scene.eevee.use_bloom`) exists only before 4.2; use Glare instead.
- Grading: Color Balance (lift/gamma/gain: cool shadows, warm highlights, or a teal-orange
  split), Hue Saturation Value, RGB Curves for contrast, then Lens Distortion with a little
  Dispersion for chromatic fringing, and an Ellipse Mask + Blur + Multiply vignette.
- Colour management: AgX (4.0+) or Filmic (3.6) with a contrast look; read
  `ColorManagedViewSettings.view_transform` enum items, don't hardcode.
- `look(mode="render")` renders with the compositor on, so glare and grading are visible
  there; viewport modes don't show them.

## 9. Render settings for iteration

- EEVEE for fast iterations, Cycles for the final if volumes or wet reflections need it.
  The engine enum under-reports: assign inside try/except TypeError.
- Keep `look(mode="render", max_size=512)` for stage checks; raise samples only for the
  final. Render limits in the server config cap samples and resolution.

## Tested code: compositor with glare [5.3]

```python
sc = bpy.context.scene
if "compositing_node_group" in bpy.types.Scene.bl_rna.properties:   # 5.x
    tree = bpy.data.node_groups.new("Comp", "CompositorNodeTree")
    tree.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = tree.nodes.new("CompositorNodeRLayers"); out = tree.nodes.new("NodeGroupOutput")
    sc.compositing_node_group = tree
    out_socket = out.inputs[0]
else:                                                                # 3.6-4.x [untested]
    sc.use_nodes = True; tree = sc.node_tree
    rl = next(n for n in tree.nodes if n.type == "R_LAYERS")
    out_socket = next(n for n in tree.nodes if n.type == "COMPOSITE").inputs[0]
glare = tree.nodes.new("CompositorNodeGlare")
if "Type" in glare.inputs:                                           # 5.x
    glare.inputs["Type"].default_value = "Fog Glow"
    glare.inputs["Threshold"].default_value = 0.8
else:                                                                # [untested]
    glare.glare_type = "FOG_GLOW"; glare.threshold = 0.8
tree.links.new(rl.outputs["Image"], glare.inputs["Image"])
tree.links.new(glare.outputs["Image"], out_socket)
```

Only replace the user's compositor with their agreement; otherwise insert nodes into it.

## Common mistakes

- Matching details before the layout: a wrong focal length or horizon can't be fixed later
  by materials. Lock the camera in the blockout stage.
- Everything at one depth: no foreground framing, no fog between layers, so it reads flat.
- Fog density too high (everything grey) or a fog cube that doesn't enclose the camera
  path. Start low, raise slowly, render to check.
- Glare threshold too low: the whole frame blooms. Only emissives and the sun should glow.
- Judging glare, fog or grading in viewport modes: they show only in `look(mode="render")`.
- Too many hues: pick a palette of 2-3 hues from the reference and grade towards it.

## Verification checklist

- [ ] Camera aspect, horizon height and focal length match the reference (side by side).
- [ ] Big shapes and depth layers read in a small, blurred render (`max_size=256`).
- [ ] Value structure matches: darkest and brightest areas in the same places.
- [ ] Palette and mood match after grading; highlights glow, the rest does not.
- [ ] Render time is acceptable for the user's machine; samples within limits.
- [ ] After each stage the three biggest differences were listed and the user was asked.

## Manual work and external tools

- Overpaint in Krita or Photoshop is often the fastest final 10 % for key art.
- Hero creatures and characters: `generate_3d`, Sketchfab or a sculpt by hand.
- Add-ons for scattering or skies must be installed and enabled by the user: safe execution
  mode refuses enabling add-ons, registering classes and adding event handlers. Explain
  this to the user and never try to bypass it.
