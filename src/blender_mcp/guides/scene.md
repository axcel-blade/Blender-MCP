# Building a scene

1. Inspect the scene and units (meters by default). Work in a new, named collection.
2. Block out with primitives at real-world scale; name every object.
3. Imported or generated models arrive at arbitrary scale. Pass `target_size` or read
   `world_bounding_box` and scale/ground them yourself.
4. Light it: an HDRI from Poly Haven (`import_external_asset` with asset_type="hdris") plus a key light.
5. Place a camera, then look: `capture_camera_view` / `capture_viewport`. Fix what's wrong
   and capture again before reporting that you're done.
6. `generate_3d` is for single bespoke objects only, never whole scenes or the ground.
