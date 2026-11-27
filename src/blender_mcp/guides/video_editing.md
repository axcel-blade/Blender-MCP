# Video editing (Video Sequencer)

Tested on Blender 5.3 (marked [5.3]). The sequencer API was renamed in 5.0, so notes for 3.6
and 4.x are untested (marked [untested]). Video encoding settings are in
`rendering_compositing`.

## When to use

Cutting rendered shots or footage together, titles and lower thirds, transitions, fades,
music and sound, simple colour and speed changes, and encoding the final video. For heavy
editorial work (many hours of footage, proxies, advanced grading) suggest a dedicated editor.

## Inputs needed

- Clips (movies, image sequences, scenes from this file) and audio, on disk in allowed
  folders, with their frame rates.
- Target fps, resolution, length and format (H.264 MP4 for delivery, ProRes/EXR for
  further work).
- The cut: order, rough timings, titles text, music.

## Workflow

1. Settings first: scene fps and resolution match the main footage; `frame_start/end` cover
   the edit. Mismatched fps is the most common cause of drift.
2. Lay clips on channels: picture on 1-2, overlays and titles above, sound on separate
   channels. Higher channels draw on top.
3. Cut: place strips end to end, trim with `frame_offset_start/end` or split, keep a
   few frames of handle for transitions.
4. Transitions: overlap two strips and add a CROSS (or GAMMA_CROSS, WIPE) effect over the
   overlap; fades with `bpy.ops.sequencer.fades_add` or keyframed `blend_alpha`.
5. Titles: TEXT effect strips; colour and position on the strip.
6. Sound: `new_sound`, then volume keys for ducking under dialogue.
7. Check frames with `look(mode="render")` (it renders the sequencer when it has strips,
   but still needs a scene camera, so add one if the edit scene has none), then encode (see `rendering_compositing`), and report the output path.

## Tested values and code

```python
# [5.3] 5.0+ names: sequence_editor.strips / strips_all (was sequences / sequences_all)
se = scene.sequence_editor_create()
a = se.strips.new_image("ShotA", "/path/f_0001.png", channel=1, frame_start=1)
for i in range(2, 25):                       # build an image sequence
    a.elements.append(f"f_{i:04d}.png")
b = se.strips.new_movie("ShotB", "/path/b.mp4", channel=2, frame_start=18)
x = se.strips.new_effect("Dissolve", "CROSS", channel=3, frame_start=18,
                         length=7, input1=a, input2=b)
t = se.strips.new_effect("Title", "TEXT", channel=4, frame_start=1, length=48)
t.text = "Hello"; t.font_size = 80; t.location = (0.5, 0.15)
```

- `new_movie` and `new_sound` were not run (no test footage) [untested]; their
  arguments match `new_image` per `lookup_api`.
- Tested [5.3]: an image strip, a 7-frame CROSS between two strips and a TEXT strip render
  correctly through `bpy.ops.render.render` (frame 20 showed the dissolve and the title).
- `new_effect` takes `length` in 5.x; older versions took `frame_end` [untested]. Pass
  arguments by keyword and read the TypeError if one is rejected.
- Effect types [5.3]: CROSS, GAMMA_CROSS, WIPE, ADD, SUBTRACT, MULTIPLY, ALPHA_OVER,
  ALPHA_UNDER, COLOR, TEXT, GLOW, GAUSSIAN_BLUR, ADJUSTMENT, SPEED, MULTICAM, COLORMIX.
- Strip properties [5.3]: `transform.offset_x/scale_x/rotation/origin`, `blend_type`,
  `blend_alpha`, `color_tag`; speed changes via `retiming_keys` (4.0+; SPEED effect before).
- Operators [5.3]: `bpy.ops.sequencer.split`, `fades_add`, `render_video`; they need a
  Sequencer area, so prefer the data API above where possible.
- Dissolves 12-24 frames, fades to black 12-24 frames, titles at least 2-3 s on screen;
  lower thirds in the lower 20 % of the frame.
- `scene.render.use_sequencer` must stay on for strips to render.
- Before 5.0 use `se.sequences` / `sequences_all` [untested]; code that must run on both:
  `strips = getattr(se, "strips", None) or se.sequences`.

## Common mistakes

- Using 4.x names (`sequences`, `frame_end=`) in 5.x, or the reverse.
- Scene fps not matching footage: audio drifts, clips play at the wrong speed.
- Variable-frame-rate phone footage: convert to constant frame rate first (external).
- Strips overlapping on the same channel by accident: the later one is pushed elsewhere;
  read back `channel` and `frame_final_start` after adding.
- Encoding straight from a heavy 3D scene strip: render the scene to frames first.
- Forgetting audio in the export: set `ffmpeg.audio_codec` (e.g. "AAC").

## Verification checklist

- [ ] Scene fps, resolution and range match the edit; every strip is where intended
      (list `name, channel, frame_final_start, frame_final_end`).
- [ ] Spot-check cut points, transitions and titles with `look(mode="render")`.
- [ ] Audio levels: no clipping; music ducks under speech.
- [ ] Final file exists, plays, has the expected duration and audio.

## Manual work and external tools

- Judging rhythm and timing needs playback by the user.
- Long-form or multicam editing, advanced grading and audio mixing: DaVinci Resolve,
  Premiere, Audacity; Blender can export an EDL-like list or rendered shots for them.
- Converting variable-frame-rate footage or unusual codecs: FFmpeg or HandBrake, run by
  the user (safe execution mode refuses starting external programs).
- Sequencer add-ons (e.g. subtitle tools) must be enabled by the user; safe execution mode
  refuses enabling add-ons. Explain that and never bypass it.
