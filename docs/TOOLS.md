# MCP Tools (overview)

## Blender app and files (core profile)

- **`open_blender(file_path="", version="", wait=True, list_installs_only=False, reopen_last=False)`** — starts Blender if the addon is not answering; does nothing if it already is, or while a Blender it launched is still starting.
  - `version` picks an install, e.g. `"5.3"` or `"5.2.1"`; the default is the newest. Versions come from the install folder name, or from `blender --version` (Steam installs).
  - `list_installs_only=True` lists every install found (path, version, source) without launching.
  - `wait=False` returns at once; `get_addon_status` reports `"blender": "starting"` until the addon answers.
  - `reopen_last=True` opens the file that was open when `close_blender` last quit Blender, for a quick restart (e.g. after reinstalling the addon). The server remembers it until it restarts.
  - `blender.path` / `BLENDER_MCP_BLENDER_PATH` overrides the search.
- **`close_blender(save=False, discard_changes=False)`** — quits Blender. Refuses on unsaved changes unless one of the flags is set. The reply names the file that was open, which `open_blender(reopen_last=True)` reopens.
- **`blend_file(action, path="", overwrite=False, discard_changes=False, recursive=False, keep_old=False)`** — manages the open `.blend` file:

| action | what it does |
|--------|--------------|
| `info` | Current path, and whether there are unsaved changes |
| `save` | Save in place, or to `path` |
| `save_as` | Save to `path` and keep working there; needs `overwrite` to replace a file |
| `save_copy` | Write a copy to `path`; keep working on the current file |
| `rename` | Rename the file on disk; `path` is a new name or a full path (`.blend` added if missing). Moves the old `.blend` and `.blend1` to the system trash (`keep_old=True` leaves them); refuses if the target exists |
| `open` | Open `path`; refuses on unsaved changes unless `discard_changes` |
| `new` | Start a new file; refuses on unsaved changes unless `discard_changes` |
| `revert` | Reload the last saved version, dropping unsaved changes |
| `list` | `.blend` files in `path` (default: the current file's folder); `recursive` includes subfolders |
| `recent` | Blender's File > Open Recent list, with missing files marked |
| `autosaves` | Autosave files and the last session (`quit.blend`) in Blender's temporary folder, newest first |
| `recover` | Open the autosave at `path`, or the last session when `path` is empty. The last session keeps its original path, so `save` writes over that file; an autosave points at the temporary folder, so keep it with `save_as`. The reply says where a save would go. Only files in Blender's temporary folder are accepted. Refuses on unsaved changes unless `discard_changes` |

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
