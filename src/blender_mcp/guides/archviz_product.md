# Architectural visualisation and product shots

Tested on Blender 5.3 (marked [5.3]). Notes for 3.6 and 4.x are untested (marked
[untested]). Read `realism` first for materials, assets and general photoreal rules; this
guide adds what is specific to interiors, exteriors and products. Render settings are in
`rendering_compositing`.

## When to use

Interiors and exteriors of buildings, real-estate and design presentations, furniture and
product renders, packshots on white, turntables and hero product images for ads.

## Inputs needed

- Plans or dimensions (room sizes, ceiling height, window positions), or the product's real
  size and a CAD/model file.
- Mood and time of day (archviz), or background and brand colours (product).
- Deliverables: number of views, aspect ratios, still or turntable, transparent background.

## Workflow

Archviz:
1. Set metric units; model walls with real thickness (exterior 0.3 m, interior 0.1 m),
   ceilings 2.5-2.7 m, doors 2.1 m, windows with frames and glass.
2. Daylight: sun lamp plus sky (or an HDRI) through the windows; an area light set as a
   portal in each window opening for Cycles.
3. Furnish from libraries (`search_assets`); real-scale props, slight disorder.
4. Cameras at 1.2-1.6 m, 18-24 mm for interiors (shift instead of tilt to keep verticals
   straight), 35-50 mm for details.
5. Exposure and colour management (AgX), then test renders per camera.

Product:
1. Import the CAD/model, check scale and normals, bevel sharp CAD edges.
2. Studio: infinite curved backdrop (a bent plane), three-point area lighting (key, fill,
   rim) or an HDRI studio; large soft lights for glossy products.
3. Camera 85-135 mm, low aperture only if the brief wants shallow depth of field.
4. Shadow catcher or transparent film for compositing onto other backgrounds.
5. Turntable: rotate the product (not the camera) 360 degrees over 120-240 frames, linear.

## Tested values and code

```python
# [5.3] window portal, soft key light, straight-verticals camera, product shadow catcher
portal = bpy.data.lights.new("Portal_Window", "AREA")
portal.shape = "RECTANGLE"
portal.size = 1.2
portal.size_y = 1.5
portal.cycles.is_portal = True  # Cycles only, emits no light itself
key = bpy.data.lights.new("Key", "AREA")
key.shape = "DISK"
key.size = 1.5
key.energy = 300
key.use_temperature = True
key.temperature = 5600  # Kelvin
cam.data.lens = 20
cam.rotation_euler[0] = math.radians(90)  # level camera
cam.data.shift_y = 0.1  # reframe without tilting
cam.data.dof.use_dof = True
cam.data.dof.focus_object = product
cam.data.dof.aperture_fstop = 4.0
floor.is_shadow_catcher = True  # Cycles
scene.render.film_transparent = True
```

- Area light shapes [5.3]: SQUARE, RECTANGLE, DISK, ELLIPSE; `spread` narrows the beam.
- Light temperature [5.3]: `use_temperature` and `temperature` exist on lights in 5.x
  (added in 4.x [untested]); otherwise set a blackbody colour.
- Light linking [5.3]: `ob.light_linking` (Cycles from 4.0, EEVEE from 4.2 [untested]) to
  light only the product, or exclude the backdrop.
- Holdout: `ob.is_holdout` for masking. Units: `scene.unit_settings.system = "METRIC"`,
  `length_unit` for display.
- Typical values: interior sun 3-5 (W/m2 strength), window portal same size as the opening,
  product key light 2-4x the size of the product, rim light behind at 120-160 degrees.
- Glass in windows: Transmission 1, roughness 0, IOR 1.5, solidified 6-10 mm; for faster
  interiors use thin glass (Principled `Thin Wall` in 5.x [5.3]).
- `look(mode="render")` restores the user's settings, so test cameras freely with it.

## Common mistakes

- Tilted interior cameras: converging verticals look wrong in architecture. Level the
  camera and use `shift_y`.
- Too wide a lens (12-16 mm) distorting the room; too few light bounces making rooms dark
  (raise `max_bounces` and use portals rather than cranking exposure).
- Glass panes as single faces, or curtains blocking the sun without transmission.
- Products at the wrong scale (CAD in mm imported as metres), shading artefacts on CAD
  triangles (weld, add weighted normals), fingerprints of default grey materials.
- Pure white backgrounds that clip: grade to ~95 % white, or render transparent and
  composite.
- Turntables that orbit the camera when the brief wants the product to spin: orbiting the
  camera keeps the lighting fixed to the product, spinning the product lets highlights
  travel across it. Ask which look is wanted.

## Verification checklist

- [ ] Room and product dimensions match the plans; doors, ceiling and furniture to scale.
- [ ] Verticals straight in every interior view; horizon level.
- [ ] Exposure: no blown windows unless intended; shadows not crushed.
- [ ] Product edges beveled, logo and label readable, colours match the brand references.
- [ ] Transparent or shadow-catcher output checked over a test background if requested.
- [ ] Each camera checked with `look(mode="render")` before final renders.

## Manual work and external tools

- Precise building models often come from CAD/BIM (Revit, ArchiCAD, SketchUp) via IFC,
  FBX or glTF; BIM import add-ons (e.g. Bonsai) must be installed by the user.
- Brand-accurate colours and packaging artwork need the user's files.
- Post-production retouching (Photoshop) is common for final hero images.
- Safe execution mode refuses enabling add-ons and changing preferences; explain that to
  the user and never bypass it.
