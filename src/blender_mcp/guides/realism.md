# Realistic results

Use this whenever the request says realistic, photoreal, lifelike, real-world, cinematic or
"looks real". Default primitives, flat colors and a single point light read as a toy. Realism
comes from six things; skip none of them.

## 1. Real assets before primitives

- Search first: `search_assets` on Poly Haven (CC0 scanned models, PBR textures, HDRIs) and
  Sketchfab (specific real objects). Prefer a scanned/photoreal model over modeling one from cubes.
- Use `generate_3d` for a bespoke hero object the libraries don't have.
- Don't mix low-poly (Poly Pizza) props with photoreal scans in one frame.
- Scale every import to real size and set it on the ground.

## 2. Geometry that catches light

- Nothing in reality has a perfectly sharp edge: add a Bevel modifier (width 2-10 mm,
  2-3 segments, `limit_method='ANGLE'`) to every hard-surface object you model.
- Subdivision Surface + shade smooth for organic forms; shade auto-smooth for hard surfaces.
- Model thickness (walls, table tops, glass) rather than single planes.
- Break perfection: slight rotation/scale variation on repeated props, no exact grid alignment.

## 3. PBR materials, never flat colors

- Use image textures (Poly Haven `textures`) or `create_procedural_material` presets. A bare
  Principled BSDF with only Base Color is not realistic.
- Every surface needs roughness variation (noise/grunge into Roughness) and a normal or bump map.
- Physically plausible values: metals Metallic 1.0 with roughness 0.1-0.4; dielectrics
  Metallic 0.0. Base colors stay between ~0.03 and ~0.85 albedo: no pure black or pure white.
- Glass: Transmission 1.0, IOR 1.45-1.52, roughness ~0. Water IOR 1.33.
- Non-color maps (roughness, normal, displacement) use Non-Color color space.
- Use real-world UV / texture scale (a floor plank ~ 15-20 cm wide, a brick ~ 21x6.5 cm).

## 4. Lighting

- Always an HDRI from Poly Haven (`import_external_asset` asset_type="hdris") or `set_sky`
  (Nishita/physical sky) for daylight. Reflections need an environment.
- Add a key light that matches the HDRI's sun direction; use area lights (soft shadows),
  not point lights. Use real color temperatures (tungsten 2700-3200 K, daylight 5500-6500 K).
- Interiors: light enters through windows; add a portal or area light at each window.
- Color management: view transform `AgX` (or `Filmic` in older Blender), look Medium Contrast.

## 5. Render engine

- Cycles for final realism (`configure_cycles`): 128-512 samples with denoising,
  light paths with enough transmission/glossy bounces. EEVEE only when speed matters; then
  turn on raytracing / screen-space reflections, soft shadows and ambient occlusion.

## 6. Camera like a photographer

- Focal length 35-50 mm for scenes, 85-135 mm for products; never extreme wide by default.
- Camera at human eye height (~1.6 m) for environments, slight downward angle for products.
- Depth of field with a real f-stop (f/2.8-f/8) focused on the subject.
- Compose (rule of thirds), and add subtle compositor touches: slight vignette, glare/bloom on
  bright highlights only.

## Verify

`look` in rendered mode from the camera. Compare against a real photo of the subject in your
head: are edges catching highlights, do surfaces vary, are shadows soft and grounded, is
anything floating or perfectly clean? Fix the worst issue and look again before reporting.
