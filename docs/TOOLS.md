# MCP Tools (overview)

Tool groups map to Blender addon handlers over the bridge.

- **Scene** — `get_scene_info`, `get_objects`, `diagnose_blender_connection`, …
- **Objects** — `create_cube`, `move_object`, `delete_object`, …
- **Meshes / Modifiers / Materials / Geometry Nodes**
- **Cameras / Lighting / Rendering / Animation**
- **Screenshots** — `get_viewport_screenshot`, `capture_multiple_angles`, …
- **Import/Export / Collections / Assets / Scripting**

All tools return structured JSON with `success`, `result` / `error`, and `operation_id` when available.

## Visual verification

After modeling, call `get_viewport_screenshot` or `capture_camera_view`, inspect the image, fix issues, then confirm completion.
