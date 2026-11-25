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

## 7. Environments and landscapes

- Terrain is a displaced heightfield, never a flat plane: hills, a plateau for buildings,
  plus a Displace modifier (clouds/voronoi) so cliffs break up. Round its outline or hide
  its edge out of frame.
- Blend materials by slope: Geometry Normal Z through a color ramp mixes rock on steep
  faces with grass on flat ones. Add a noise to the factor so the border isn't a clean line.
- Break every silhouette: scatter displaced boulders on cliffs and slopes.
- Vegetation decides whether a landscape reads as real. Prefer real tree/bush models
  (Poly Haven, Sketchfab, `generate_3d`) over sphere blobs, which read as a toy. Scatter
  hundreds of linked duplicates by ray-casting onto the evaluated terrain, skipping steep
  normals, with random rotation, scale and species. Keep greens dark and desaturated.
- Architecture needs detail at several scales: corbels and merlons under roofs, window
  frames, finials, steep roofs with overhang. Plain boxes read as blockouts.
- Light from the side, low and warm (4000-4600 K), so walls and rocks get raking shadows.

## Pitfalls seen in real builds

- `bpy.ops.object.transform_apply()` applies location too by default, moving every origin
  to the world origin. Pass `location=False, rotation=False` when you only mean scale, or
  measure positions from `bound_box` centers.
- Image textures on primitives you modeled stretch or blur unless mapped: use Object
  coordinates into a Mapping node at real-world scale, and set image nodes to Box projection.
- Check a texture asset by rendering it: names lie (a "rock wall" may be brick).
- Boolean cutters: hide them in render and viewport, and never delete them.
- `film_transparent = True` hides the sky but keeps its lighting; use it when the user wants
  only the models.
- `look` in a viewport is not a final render. For realism checks, render with Cycles to a file
  and inspect that image.

## Verify

`look` in rendered mode from the camera. Compare against a real photo of the subject in your
head: are edges catching highlights, do surfaces vary, are shadows soft and grounded, is
anything floating or perfectly clean? Fix the worst issue and look again before reporting.
