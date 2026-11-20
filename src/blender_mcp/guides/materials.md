# Materials

- Colors go on shader node inputs (Principled BSDF "Base Color"). `material.diffuse_color`
  only changes the Solid-mode viewport.
- Image maps other than color (roughness, metallic, normal, displacement) need
  `image.colorspace_settings.is_data = True` (Non-Color).
- Normal maps go through a Normal Map node into the BSDF "Normal" input.
- Check `mesh.users` before editing shared data; editing a shared material changes every
  object that uses it.
- Check the result in Material Preview (`capture_material_preview`) or a render.
