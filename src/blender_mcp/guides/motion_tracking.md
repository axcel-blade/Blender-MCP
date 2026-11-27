# Motion tracking (camera solve)

Tested on Blender 5.3 with a synthetic 40-frame shot (marked [5.3]). Notes for 3.6 and 4.x
are untested (marked [untested]). Compositing the result is in `rendering_compositing`.

## When to use

Putting 3D objects into real footage: matching a moving camera (camera solve), stabilising
shaky footage, tracking a planar surface (screen replacement), or tracking an object.

## Inputs needed

- The footage (video or image sequence) on disk, inside the allowed directories.
- Camera data if known: focal length (mm) and sensor width (mm); otherwise refine it.
- Which frames show the most parallax (camera moving sideways relative to near and far
  points) for the solve keyframes.
- What will be added and where (on the floor, on a wall), so you can set the ground plane.

## Workflow

1. Load: `clip = bpy.data.movieclips.load(path)` (first frame of a sequence, or the
   video). Match the scene: fps, frame range (`clip.frame_duration`), resolution
   (`clip.size`).
2. Camera: `clip.tracking.camera.sensor_width` and `focal_length` from the real camera.
3. Track: detect features on frame 1, track forwards (and backwards from the last frame
   if needed). Aim for 8+ tracks on every frame, spread over the image and in depth.
4. Solve with keyframes A/B far apart with good parallax.
5. Clean: delete short and high-error tracks, solve again; repeat until the average
   error is below 0.5 px (below 0.3 for close-ups).
6. Orient: set the floor (3 tracks on the ground), origin and scale with
   `bpy.ops.clip.set_plane`, `set_origin` and `set_scale` on selected tracks [untested],
   then `setup_tracking_scene` [5.3] to create the camera solver constraint and background.
7. Add 3D objects, a shadow catcher on the floor plane, and render over the footage.

## Tested values and code

Clip operators need a Clip Editor. Borrow an area and **always give it back**:

```python
# [5.3] tested end to end: 114 features detected, 40 cameras solved
win = bpy.context.window_manager.windows[0]
area = max(win.screen.areas, key=lambda a: a.width * a.height)
old = area.ui_type
try:
    area.type = "CLIP_EDITOR"
    area.spaces.active.clip = clip
    region = next(r for r in area.regions if r.type == "WINDOW")
    tr = clip.tracking
    tr.camera.sensor_width = 36
    tr.camera.focal_length = 35
    tr.settings.default_pattern_size = 21
    tr.settings.default_search_size = 71
    tr.objects[0].keyframe_a = 1
    tr.objects[0].keyframe_b = 20
    with bpy.context.temp_override(
        window=win, screen=win.screen, area=area, region=region, edit_movieclip=clip
    ):
        scene.frame_set(clip.frame_start)
        bpy.ops.clip.detect_features(threshold=0.1, min_distance=40, margin=20)
        bpy.ops.clip.track_markers(backwards=False, sequence=True)
        bpy.ops.clip.solve_camera()
        bpy.ops.clip.select_all(action="SELECT")
        bpy.ops.clip.clean_tracks(frames=20, error=2.0, action="DELETE_TRACK")
        bpy.ops.clip.solve_camera()
        bpy.ops.clip.setup_tracking_scene()  # adds a CAMERA_SOLVER constraint
finally:
    area.ui_type = old
error = tr.reconstruction.average_error if tr.reconstruction.is_valid else None
```

- Measured [5.3]: the first solve had 4.0 px error; after `clean_tracks(frames=20,
  error=2.0)` it dropped to 0.07 px with 29 tracks. Clean before trusting any solve.
- `detect_features`: threshold 0.1-0.5 (lower = more features), `min_distance` 40-120 px
  depending on resolution, `margin` 16-32 px away from the frame edge.
- Pattern size 15-31 px, search size 61-121 px (larger for fast motion).
- `refine_intrinsics_focal_length = True` lets the solver refine an unknown focal length;
  it needs good parallax.
- `setup_tracking_scene` also creates helper objects, collections, a "Tracking Setup"
  compositor group and new view layers: use it in a scene you own, and tell the user.
- Needs the Blender UI: it does not work in background mode. The full-profile tools
  `load_movie_clip` and `track_camera_motion` wrap this.

## Common mistakes

- Leaving the borrowed area as a Clip Editor: the user loses their 3D view. Restore it.
- Wrong sensor width (e.g. 36 mm for a phone): the scale and perspective are off.
- Tracks only on one depth plane or one image region: the solve has no parallax.
- Tracking moving things (people, cars, reflections, water): delete those tracks.
- Trusting the first solve: errors above 1 px make objects slide. Clean and re-solve.
- Scene fps or frame range not matching the clip: objects drift in time.

## Verification checklist

- [ ] `reconstruction.is_valid` and average error under 0.5 px; cameras for every frame.
- [ ] Scene fps, range and resolution match the clip; the borrowed area is restored.
- [ ] Floor, origin and scale set; a test object sits still on the floor in
      `look(mode="render")` at the first, middle and last frames.
- [ ] Moving objects and reflections were not used as tracks.

## Manual work and external tools

- Hard shots (motion blur, low texture, zooms, rolling shutter) need manual track placement
  and keyframe choice by the user in the Clip Editor.
- Lens distortion: solve with distortion coefficients, or undistort in another tool.
- Dedicated trackers (SynthEyes, 3DEqualizer, PFTrack) export cameras to Blender via FBX
  or Alembic for difficult shots.
- Tracking add-ons must be enabled by the user; safe execution mode refuses enabling
  add-ons and registering handlers. Explain that and never bypass it.
