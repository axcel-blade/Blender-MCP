# MCP Tools (overview)

## Blender app and files (core profile)

- **`open_blender(file_path="", wait=True)`** — starts Blender if the addon is not answering; does nothing if it already is. Set `BLENDER_MCP_BLENDER_PATH` if Blender is not found automatically.
- **`close_blender(save=False, discard_changes=False)`** — quits Blender. Refuses on unsaved changes unless one of the flags is set.
- **`blend_file(action, path="", overwrite=False, discard_changes=False, recursive=False)`** — manages the open `.blend` file:

| action | what it does |
|--------|--------------|
| `info` | Current path, and whether there are unsaved changes |
| `save` | Save in place, or to `path` |
| `save_as` | Save to `path` and keep working there; needs `overwrite` to replace a file |
| `save_copy` | Write a copy to `path`; keep working on the current file |
| `rename` | Rename the file on disk; `path` is a new name or a full path (`.blend` added if missing). Removes the old `.blend` and `.blend1`; refuses if the target exists |
| `open` | Open `path`; refuses on unsaved changes unless `discard_changes` |
| `new` | Start a new file; refuses on unsaved changes unless `discard_changes` |
| `revert` | Reload the last saved version, dropping unsaved changes |
| `list` | `.blend` files in `path` (default: the current file's folder); `recursive` includes subfolders |

## Tool groups (full profile)

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
