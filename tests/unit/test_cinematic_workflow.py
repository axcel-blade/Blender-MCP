"""look(mode="render"), the cinematic guide/prompt, and render side-effect regressions."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock

import pytest

from blender_mcp.config import Settings
from blender_mcp.server import INSTRUCTIONS, create_server
from blender_mcp.tools.registry import CORE_TOOLS
from blender_mcp.tools.status import list_guides, read_guide

ROOT = Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------- server side


def _register_look(settings: Settings, reply=None):
    import blender_mcp.tools.screenshots as screenshots

    bridge = AsyncMock()
    bridge.send_command.return_value = reply or {
        "success": True,
        "result": {"camera": "Cam", "image_base64": "aGk="},
    }
    fake = NS()
    fake.tool = lambda name: lambda f: setattr(fake, name, f) or f
    screenshots.register(fake, NS(settings=settings, bridge=bridge))
    return fake, bridge


async def test_look_render_sends_capped_render_command():
    settings = Settings(
        render_max_samples=64,
        render_max_resolution_x=800,
        render_max_resolution_y=600,
        render_max_time_seconds=240,
    )
    fake, bridge = _register_look(settings)
    blocks = await fake.look(mode="render", camera="Cam", max_size=512, samples=9999)
    command, params = bridge.send_command.await_args.args
    assert command == "capture_render_view"
    assert params["camera"] == "Cam"
    assert params["max_size"] == 512
    assert params["samples"] == 64
    assert params["max_samples"] == 64
    assert params["max_resolution"] == 600
    assert params["timeout"] == 240
    assert [b.type for b in blocks] == ["text", "image"]


async def test_look_render_clamps_max_size_and_honours_timeout_override():
    settings = Settings(screenshot_max_size=256, command_timeouts={"capture_render_view": 900})
    fake, bridge = _register_look(settings)
    await fake.look(mode="render", max_size=10_000)
    _, params = bridge.send_command.await_args.args
    assert params["max_size"] == 512
    assert params["timeout"] == 900
    assert "samples" not in params


@pytest.mark.parametrize("group", ["rendering", "screenshots"])
async def test_look_render_respects_tool_groups(group):
    settings = Settings()
    setattr(settings.tool_groups, group, False)
    fake, bridge = _register_look(settings)
    blocks = await fake.look(mode="render")
    bridge.send_command.assert_not_awaited()
    assert "disabled" in blocks[0].text


async def test_look_render_passes_errors_through():
    reply = {"success": False, "error": "The scene has no active camera."}
    fake, _ = _register_look(Settings(), reply)
    blocks = await fake.look(mode="render")
    assert len(blocks) == 1 and "no active camera" in blocks[0].text


def test_render_look_timeout_registered():
    from blender_mcp.protocol.timeouts import SLOW_COMMAND_TIMEOUTS

    assert SLOW_COMMAND_TIMEOUTS["capture_render_view"] >= 300


def test_core_profile_unchanged():
    names = {t.name for t in create_server(Settings())._tool_manager.list_tools()}  # noqa: SLF001
    assert names == set(CORE_TOOLS)
    assert len(CORE_TOOLS) == 16


def test_cinematic_guide_registered_and_covers_topics():
    assert "cinematic" in list_guides()
    text = read_guide("cinematic").lower()
    for topic in (
        "focal length",
        "horizon",
        "blockout",
        "bezier",
        "bridge",
        "displace",
        "floating island",
        "storm",
        "volumetric fog",
        "lightning",
        "emission",
        "wet",
        "rain",
        "glare",
        "color balance",
        "generate_3d",
        'look(mode="render")',
        "compositing_node_group",
    ):
        assert topic in text, topic


def test_instructions_and_prompt_route_to_guides():
    assert 'get_guide("cinematic")' in INSTRUCTIONS
    assert 'get_guide("realism")' in INSTRUCTIONS
    from blender_mcp.prompts.registry import register_prompts

    prompts = {}
    fake = NS(prompt=lambda: lambda f: prompts.setdefault(f.__name__, f))
    register_prompts(fake)
    text = prompts["recreate_reference"]("a stormy canyon")
    for stage in (
        "Blockout",
        "Main structures",
        "Detail",
        "Materials",
        "Sky and lighting",
        "Compositing",
    ):
        assert stage in text
    assert "look(mode='render'" in text
    assert "three biggest differences" in text
    assert "wait for their feedback" in text


# --------------------------------------------------------------------------- addon side


class FakeImageSettings:
    def __init__(self):
        self.file_format = "OPEN_EXR"
        self.color_mode = "RGBA"
        self.color_depth = "32"


class FakeRender:
    def __init__(self):
        self.engine = "CYCLES"
        self.filepath = "//user_out/"
        self.resolution_percentage = 100
        self.resolution_x = 1920
        self.resolution_y = 1080
        self.use_compositing = False
        self.image_settings = FakeImageSettings()


class FakeBpy(types.ModuleType):
    def __init__(self):
        super().__init__("bpy")
        self.cam = NS(name="Cam", type="CAMERA")
        self.other_cam = NS(name="Cam2", type="CAMERA")
        self.scene = NS(
            render=FakeRender(),
            cycles=NS(samples=4096),
            eevee=NS(taa_render_samples=64),
            camera=self.cam,
        )
        self.context = NS(scene=self.scene)
        objects = {"Cam": self.cam, "Cam2": self.other_cam, "Cube": NS(name="Cube", type="MESH")}
        self.data = NS(objects=objects, images=[])
        self.calls: list[dict] = []
        self.write = True
        self.fail = False
        self.ops = NS(render=NS(render=self._render))

    def _render(self, write_still=False, **_):
        self.calls.append(
            {
                "write_still": write_still,
                "camera": self.scene.camera.name,
                "pct": self.scene.render.resolution_percentage,
                "samples": self.scene.cycles.samples,
                "compositing": self.scene.render.use_compositing,
                "format": self.scene.render.image_settings.file_format,
            }
        )
        if self.fail:
            raise RuntimeError("GPU out of memory")
        if write_still and self.write:
            Path(self.scene.render.filepath).write_bytes(b"NEW")
        return {"FINISHED"}


@pytest.fixture
def addon(monkeypatch):
    bpy = FakeBpy()
    monkeypatch.setitem(sys.modules, "bpy", bpy)
    pkg = types.ModuleType("blender_addon")
    pkg.__path__ = [str(ROOT / "blender_addon")]
    handlers = types.ModuleType("blender_addon.handlers")
    handlers.__path__ = [str(ROOT / "blender_addon" / "handlers")]
    handlers.command = lambda name: lambda fn: fn
    monkeypatch.setitem(sys.modules, "blender_addon", pkg)
    monkeypatch.setitem(sys.modules, "blender_addon.handlers", handlers)
    for name in (
        "blender_addon.screenshots",
        "blender_addon.utils",
        "blender_addon.utils.objects",
        "blender_addon.handlers.rendering",
        "blender_addon.handlers.screenshots",
    ):
        monkeypatch.delitem(sys.modules, name, raising=False)

    def load(name, rel):
        spec = importlib.util.spec_from_file_location(name, ROOT / rel)
        mod = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, mod)
        spec.loader.exec_module(mod)
        return mod

    load("blender_addon.utils", "blender_addon/utils/__init__.py")
    load("blender_addon.utils.objects", "blender_addon/utils/objects.py")
    shot = load("blender_addon.screenshots", "blender_addon/screenshots.py")
    rendering = load("blender_addon.handlers.rendering", "blender_addon/handlers/rendering.py")
    screenshots = load(
        "blender_addon.handlers.screenshots", "blender_addon/handlers/screenshots.py"
    )
    monkeypatch.setattr(rendering, "_prefs", lambda: None)
    monkeypatch.setattr(shot, "_resize_png_if_needed", lambda path, size: path.read_bytes())
    monkeypatch.setattr(
        shot,
        "capture_viewport",
        lambda **kw: {"camera": bpy.scene.camera.name, "image_base64": "x", **kw},
    )
    return NS(bpy=bpy, rendering=rendering, screenshots=screenshots)


def _assert_restored(bpy):
    r = bpy.scene.render
    assert r.filepath == "//user_out/"
    assert r.engine == "CYCLES"
    assert r.resolution_percentage == 100
    assert r.use_compositing is False
    assert r.image_settings.file_format == "OPEN_EXR"
    assert r.image_settings.color_depth == "32"
    assert bpy.scene.cycles.samples == 4096
    assert bpy.scene.eevee.taa_render_samples == 64
    assert bpy.scene.camera is bpy.cam


def test_render_look_renders_from_named_camera_and_restores(addon):
    result = addon.screenshots.capture_render_view(
        {"camera": "Cam2", "max_size": 480, "max_samples": 32}
    )
    call = addon.bpy.calls[0]
    assert call["camera"] == "Cam2"
    assert call["compositing"] is True
    assert call["write_still"] is True
    assert call["pct"] == 25  # 1920 * 25% = 480
    assert call["samples"] == 32
    assert result["image_base64"] == "TkVX"  # b"NEW"
    assert result["resolution"] == [480, 270]
    _assert_restored(addon.bpy)


def test_render_look_without_camera_errors(addon):
    addon.bpy.scene.camera = None
    with pytest.raises(ValueError, match="no active camera"):
        addon.screenshots.capture_render_view({})
    assert addon.bpy.calls == []


def test_render_look_rejects_non_camera(addon):
    with pytest.raises(ValueError, match="not a camera"):
        addon.screenshots.capture_render_view({"camera": "Cube"})


def test_render_look_failure_restores_settings(addon):
    addon.bpy.fail = True
    with pytest.raises(RuntimeError, match="out of memory"):
        addon.screenshots.capture_render_view({"camera": "Cam2"})
    _assert_restored(addon.bpy)


def test_render_never_returns_stale_file(addon, tmp_path):
    out = tmp_path / "old.png"
    out.write_bytes(b"OLD")
    addon.bpy.write = False  # render "finishes" but writes nothing
    with pytest.raises(RuntimeError, match="no new image"):
        addon.rendering.render_scene({"output_path": str(out)})
    assert addon.rendering.get_render_result({}) == {"available": False}


def test_render_without_write_still_uses_render_result(addon, tmp_path):
    out = tmp_path / "old.png"
    out.write_bytes(b"OLD")
    saved = []

    def save_render(filepath, scene=None):
        Path(filepath).write_bytes(b"FRESH")
        saved.append(filepath)

    addon.bpy.data.images.append(NS(type="RENDER_RESULT", save_render=save_render))
    result = addon.rendering.render_scene({"output_path": str(out), "write_still": False})
    assert result["image_base64"] == "RlJFU0g="  # b"FRESH", never b"OLD"
    assert out.read_bytes() == b"OLD"
    assert not Path(saved[0]).exists()


def test_render_without_write_still_and_no_result_errors(addon):
    with pytest.raises(RuntimeError, match="no Render Result"):
        addon.rendering.render_scene({"write_still": False})


def test_preview_render_restores_settings(addon, tmp_path):
    addon.rendering.render_preview(
        {"engine": "BLENDER_EEVEE", "output_path": str(tmp_path / "p.png")}
    )
    call = addon.bpy.calls[0]
    assert call["pct"] == 25 and call["samples"] == 16 and call["format"] == "PNG"
    _assert_restored(addon.bpy)


def test_preview_render_failure_restores_settings(addon, tmp_path):
    addon.bpy.fail = True
    with pytest.raises(RuntimeError):
        addon.rendering.render_preview(
            {"engine": "BLENDER_EEVEE", "output_path": str(tmp_path / "p.png")}
        )
    _assert_restored(addon.bpy)


def test_capture_camera_view_restores_active_camera(addon):
    result = addon.screenshots.capture_camera_view({"camera": "Cam2"})
    assert result["camera"] == "Cam2"
    assert addon.bpy.scene.camera is addon.bpy.cam


def test_render_look_uses_samples_of_active_engine(addon):
    addon.bpy.scene.render.engine = "BLENDER_EEVEE"
    addon.bpy.scene.cycles.samples = 4096
    addon.bpy.scene.eevee.taa_render_samples = 24
    result = addon.screenshots.capture_render_view({"camera": "Cam2", "max_samples": 32})
    assert result["samples"] == 24


TEMPLATE_GUIDES = (
    "cinematic",
    "animation_3d",
    "game_assets",
    "modelling",
    "rigging",
    "animation_2d",
    "rendering_compositing",
    "vfx_simulation",
    "motion_tracking",
    "video_editing",
    "geometry_nodes",
    "archviz_product",
    "3d_printing",
    "motion_graphics",
    "xr_assets",
    "scientific_viz",
    "materials",
    "bpy",
)
TEMPLATE_SECTIONS = (
    "## When to use",
    "## Inputs needed",
    "## Common mistakes",
    "## Verification checklist",
    "## Manual work and external tools",
)


@pytest.mark.parametrize("name", TEMPLATE_GUIDES)
def test_guides_follow_template_and_are_routed(name):
    assert name in list_guides()
    text = read_guide(name)
    for section in TEMPLATE_SECTIONS:
        assert section in text, (name, section)
    assert "Tested" in text and "untested" in text  # version status is marked
    assert "safe execution mode" in " ".join(text.lower().split())
    assert "```python" in text
    assert name in INSTRUCTIONS


def test_animation_guide_uses_5x_channelbag_api():
    text = read_guide("animation_3d")
    assert "action_get_channelbag_for_slot" in text
    assert "action.fcurves" in text  # explains the removal / fallback


def test_game_assets_guide_covers_exports():
    text = read_guide("game_assets")
    for item in ("export_scene.gltf", "export_scene.fbx", "LOD", "UCX_", "use_selected_to_active"):
        assert item in text


def test_batch_two_guides_use_current_apis():
    assert "arm.collections.new" in read_guide("rigging")
    gp = read_guide("animation_2d")
    assert "GREASEPENCIL" in gp and "add_strokes" in gp and "GPENCIL" in gp
    assert "voxel_remesh" in read_guide("modelling")


def test_batch_three_guides_use_current_apis():
    render = read_guide("rendering_compositing")
    assert 'media_type = "VIDEO"' in render and "ShaderNodeMix" in render
    assert "rigidbody.object_add" in read_guide("vfx_simulation")
    tracking = read_guide("motion_tracking")
    assert "area.ui_type = old" in tracking and "clean_tracks" in tracking


def test_batch_four_guides_use_current_apis():
    video = read_guide("video_editing")
    assert "strips.new_effect" in video and "length=" in video
    gn = read_guide("geometry_nodes")
    assert "props.inputs" in gn and "interface.new_socket" in gn
    assert "is_portal" in read_guide("archviz_product")


def test_batch_five_guides_use_current_apis():
    printing = read_guide("3d_printing")
    assert "wm.stl_export" in printing and "global_scale=1000" in printing
    assert "ensure_lookup_table" in printing
    assert "bevel_factor_end" in read_guide("motion_graphics")
    xr = read_guide("xr_assets")
    assert "usd_export" in xr and "export_draco_mesh_compression_enable" in xr


def test_last_batch_guides():
    sci = read_guide("scientific_viz")
    assert "pointclouds.new" in sci and "foreach_set" in sci
    mats = read_guide("materials")
    assert "object.bake" in mats and "smart_project" in mats and "Non-Color" in mats
    bpy_guide = " ".join(read_guide("bpy").split())
    for refused in ("register_class", "bpy.app.handlers", "addon_utils", "subprocess"):
        assert refused in bpy_guide
    assert "never try to get around the mode" in bpy_guide.lower()


def test_every_guide_is_named_in_instructions():
    for name in list_guides():
        assert name in INSTRUCTIONS, name


# --------------------------------------------------------------- track_camera_motion area


class FakeArea:
    def __init__(self, ui_type, size, clip=None):
        self.ui_type = ui_type
        self.width = self.height = size
        self.spaces = NS(active=NS(clip=clip))
        self.regions = [NS(type="HEADER"), NS(type="WINDOW")]

    @property
    def type(self):
        return "CLIP_EDITOR" if self.ui_type == "CLIP_EDITOR" else self.ui_type

    @type.setter
    def type(self, value):
        self.ui_type = value


@pytest.fixture
def library(addon, monkeypatch):
    handlers = sys.modules["blender_addon.handlers"]
    handlers.dispatch = lambda *a, **k: None
    handlers.history = lambda: []
    spec = importlib.util.spec_from_file_location(
        "blender_addon.handlers.library", ROOT / "blender_addon/handlers/library.py"
    )
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "blender_addon.handlers.library", mod)
    spec.loader.exec_module(mod)
    return mod


def _windows(bpy, *areas):
    bpy.context.window_manager = NS(windows=[NS(screen=NS(areas=list(areas)))])


def test_clip_override_restores_borrowed_area(addon, library):
    view3d = FakeArea("VIEW_3D", 800)
    _windows(addon.bpy, FakeArea("OUTLINER", 200), view3d)
    with library._clip_override("clip") as override:
        assert override["area"] is view3d and view3d.type == "CLIP_EDITOR"
    assert view3d.ui_type == "VIEW_3D"


def test_clip_override_restores_area_when_tracking_fails(addon, library):
    view3d = FakeArea("VIEW_3D", 800)
    _windows(addon.bpy, view3d)
    with pytest.raises(RuntimeError), library._clip_override("clip"):
        raise RuntimeError("solve failed")
    assert view3d.ui_type == "VIEW_3D"


def test_clip_override_reuses_open_clip_editor_and_restores_its_clip(addon, library):
    editor = FakeArea("CLIP_EDITOR", 300, clip="user_clip")
    view3d = FakeArea("VIEW_3D", 800)
    _windows(addon.bpy, view3d, editor)
    with library._clip_override("new_clip") as override:
        assert override["area"] is editor and editor.spaces.active.clip == "new_clip"
    assert editor.spaces.active.clip == "user_clip"
    assert view3d.ui_type == "VIEW_3D"
