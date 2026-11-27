# VFX and simulation

Tested on Blender 5.3 (marked [5.3]). Notes for 3.6 and 4.x are untested (marked
[untested]). Rendering of the result is in `rendering_compositing`.

## When to use

Physically driven motion: falling and colliding objects, destruction, cloth and flags,
smoke and fire, liquids, particles (sparks, debris, rain, snow), ocean surfaces, and
geometry-nodes simulations.

## Inputs needed

- Real scale of everything (simulations depend on it: a 100 m "cup" pours like a lake).
- Frame range and fps; how long the effect must last on screen.
- Quality vs time: preview resolution first, final resolution only once motion is approved.
- Where caches may be written (disk space: fluids can take many GB).

## Workflow

1. Scale: apply scale on all simulated objects; build at real size.
2. Choose the solver: rigid body (hard objects), cloth/soft body (fabric, jelly), fluid
   (Mantaflow GAS for smoke/fire, LIQUID for water), particles (many small things),
   geometry-nodes simulation zones (custom procedural effects), Ocean modifier (open sea).
3. Set up at low resolution and a short range; play or step frames and `look`.
4. Adjust physical values (mass, friction, stiffness, viscosity, emission) one at a time.
5. Bake to cache; check key frames with `look(mode="render")`.
6. Raise resolution for the final bake only after the user approves the motion.

## Tested values and code

```python
# [5.3] rigid bodies: operators need the object in context
for ob, kind in ((box, "ACTIVE"), (ground, "PASSIVE")):
    with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
        bpy.ops.rigidbody.object_add(type=kind)
world = scene.rigidbody_world
world.point_cache.frame_end = 120
for f in range(1, 121):          # step frames in order to simulate (or bake)
    scene.frame_set(f)
```

  Tested: a 0.5 m box dropped from 3 m settles on the ground plane by frame 40 at 24 fps.
- Rigid body object [5.3]: `ob.rigid_body.mass`, `friction` 0.5, `restitution` 0-0.3,
  `collision_shape` (CONVEX_HULL default; MESH for concave passive colliders, slower),
  `collision_margin` 0.001-0.04.
- Cloth [5.3]: `ob.modifiers.new("Cloth", "CLOTH").settings` has `quality` 5-10, `mass`
  0.15-0.3 kg (cotton), `tension_stiffness` 15 (cotton) to 40 (denim),
  `bending_stiffness` 0.5-5. Add a Collision modifier to colliders; pin with a vertex group.
- Fluid [5.3]: modifier `FLUID` with `fluid_type` DOMAIN / FLOW / EFFECTOR.
  `domain_settings.domain_type` GAS or LIQUID; `resolution_max` 32-64 preview,
  128-256 final; `cache_type` REPLAY, MODULAR or ALL; set `cache_directory` to a project
  folder (the default is a temporary folder that disappears). Flow types SMOKE, FIRE,
  BOTH, LIQUID. Bake with `bpy.ops.fluid.bake_all()` with the domain active.
- Particles [5.3]: types EMITTER and HAIR; render as objects or collections for debris.
- Force fields include FORCE, WIND, TURBULENCE, VORTEX, DRAG, HARMONIC, CHARGE...
  (`bpy.ops.object.effector_add(type="WIND")`).
- Ocean modifier `OCEAN` and geometry-nodes simulation zones (`GeometryNodeSimulationInput`)
  are available [5.3; simulation zones exist from 4.0].
- Fracture: `bpy.ops.object.add_fracture_cell_objects` (Cell Fracture) is available in this
  5.3 install [5.3]; it is a bundled add-on that may be disabled elsewhere.
- Bakes block Blender: pass a long `timeout` (600-3600 s) to execute_blender_code, or bake
  in chunks of frames.

## Common mistakes

- Unapplied scale or wrong real size: everything floats, explodes or moves in slow motion.
- Overlapping rigid bodies at frame 1: they explode apart. Leave a small gap.
- Jumping frames (frame_set(100) directly) without a bake: the result is wrong or empty.
- Fluid domain too small or flow object outside it; liquid leaking through thin
  effectors (give them thickness, raise resolution or substeps).
- Final-resolution bakes before the motion is approved: hours lost.
- Caches in a temporary folder: lost after restart.

## Verification checklist

- [ ] Real scale, applied transforms, cache folder set and frame range correct.
- [ ] Motion checked at frames start, peak and end with `look` (render mode for smoke,
      fire and liquids).
- [ ] No interpenetration, jitter or explosion; objects come to rest where expected.
- [ ] Bake complete for the full range; file size and bake time reported to the user.
- [ ] Preview resolution replaced by final values only after approval.

## Manual work and external tools

- Judging motion needs playback: render a low-resolution preview and ask the user to watch.
- Very large fluid or destruction shots are better in Houdini or EmberGen, imported as
  VDB (volumes) or Alembic (meshes).
- Add-ons such as Cell Fracture or Molecular must be enabled by the user, and simulation
  scripts that register frame-change handlers are refused by safe execution mode. Explain
  this to the user, bake instead of using handlers, and never bypass the mode.
