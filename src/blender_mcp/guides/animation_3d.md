# 3D animation

Tested on Blender 5.3 (marked [5.3]). Notes for 3.6 and 4.x come from the API changes and are
untested (marked [untested]). Check anything uncertain with `lookup_api`.

## When to use

Keyframed motion of objects, cameras, lights, materials or rigs: bouncing props, camera
moves, product turntables, mechanical loops, character blocking. Rig building is a separate
topic; 2D/Grease Pencil and motion-graphics guides cover those styles.

## Inputs needed

- Frame rate and length (seconds or frames), and the deliverable: playblast, render, or
  export to a game engine (then read `game_assets` too).
- What moves, how, and the mood of the timing (snappy, floaty, mechanical).
- Whether to keep the user's existing actions: never overwrite one without asking.

## Workflow

1. Set timing first: `scene.render.fps` (24 film, 25 PAL, 30 web, 60 games), `fps_base` 1,
   `scene.frame_start`/`frame_end`. Changing fps later re-times everything.
2. Block key poses only (stepped feel): every key's interpolation `CONSTANT`. Review with
   `look(mode="camera")` at the key frames (`scene.frame_set(f)` then look).
3. Breakdowns: add in-between keys where the arc or spacing needs shaping.
4. Spline: switch to `BEZIER`, set easing, fix overshoot and floatiness in the curves.
5. Polish: overlap (parts lag the parent by 2-4 frames), follow-through, secondary motion
   with F-Curve modifiers (Noise for shake, Cycles for loops).
6. Camera: animate an Empty the camera follows (`TRACK_TO` or `DAMPED_TRACK`), or put the
   camera on a curve with `FOLLOW_PATH`. Keep moves slow; one idea per shot.
7. Render a few frames with `look(mode="render")` (it renders the current frame), then a
   preview animation, then the final.

## Tested values and code

- Timing at 24 fps: a ball drop of 1 m lands in ~11 frames; a blink 3-5 frames; a head
  turn 8-12; a camera push-in 72-120. Anticipation 4-8 frames before the action.
- Keys and F-Curves [5.3]. Since 4.4 actions are layered with slots, and in 5.0 `action.fcurves`
  was removed. Use the channel bag:

```python
from bpy_extras import anim_utils
ob.keyframe_insert("location", index=2, frame=1)   # works in every version
ad = ob.animation_data
cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
fc = cb.fcurves.find("location", index=2)
for k in fc.keyframe_points:
    k.interpolation = "BEZIER"; k.easing = "EASE_IN_OUT"
fc.modifiers.new("CYCLES")          # loop the curve
```

  In 3.6-4.3 use `ad.action.fcurves.find(...)` [untested]. Write code that tries the channel
  bag and falls back: `getattr(ad.action, "fcurves", None)`.
- Interpolation enum includes CONSTANT, LINEAR, BEZIER, SINE, QUAD, CUBIC, ...; easing AUTO,
  EASE_IN, EASE_OUT, EASE_IN_OUT [5.3].
- Drivers [5.3]: `d = ob.driver_add("rotation_euler", 2); d.driver.expression = "frame*0.1"`.
  Simple expressions run without "Auto Run Python Scripts"; ones calling functions do not.
- NLA [5.3]: `tr = ad.nla_tracks.new(); tr.strips.new("walk", 1, action)` to layer and
  repeat actions. `bpy.ops.nla.bake` bakes constraints/drivers into keys (needs selection).
- Motion blur: `scene.render.use_motion_blur = True`, shutter 0.5 (180 degrees).
- Evaluate a value without stepping the scene: `fc.evaluate(frame)`.

## Common mistakes

- Reading `action.fcurves` in 5.x: AttributeError. Use the channel bag above.
- Keys on every channel (`keyframe_insert("location")` keys X, Y and Z): pass `index` when
  only one axis moves, or curves fight later edits.
- Even spacing everywhere: robotic. Real motion eases in and out; mechanical loops are LINEAR.
- Forgetting `scene.frame_set()` before reading animated values or looking: the viewport
  shows the old frame. Restore the user's current frame afterwards.
- Rotation over 180 degrees with Euler keys flips; key in small steps or use quaternions.
- Scaling to zero (invisible) breaks normals and physics; hide with visibility keys instead.
- Changing fps after animating; the motion speeds up or slows down.

## Verification checklist

- [ ] fps, start and end frame match the brief; the user's current frame is restored.
- [ ] `look(mode="camera")` at first, middle, last and key frames shows the intended poses.
- [ ] No pops: sample the F-Curves with `fc.evaluate()` every frame and flag jumps.
- [ ] Loops: the first and last frames match (or a Cycles modifier is on).
- [ ] Spot-check render frames with `look(mode="render")`; motion blur on if wanted.
- [ ] Existing actions untouched unless the user agreed.

## Manual work and external tools

- Judging timing needs playback: render a preview (`render_animation` in the full profile, or
  `bpy.ops.render.render(animation=True)` with a small resolution) and ask the user to watch it.
- Graph-editor polish and motion capture cleanup are faster by hand.
- Frame-change handlers (`bpy.app.handlers.frame_change_pre`) are refused by safe execution
  mode. Use drivers or bake the motion to keys instead, and tell the user rather than
  trying to work around the mode.
