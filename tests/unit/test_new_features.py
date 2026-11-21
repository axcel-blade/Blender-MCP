"""Tests for image results, asset downloads, generation jobs and addon status."""

from __future__ import annotations

import base64
import io
import json
import zipfile

import httpx
import pytest

from blender_mcp.exceptions import AssetDownloadFailedError, InvalidParameterError
from blender_mcp.providers import downloads
from blender_mcp.providers.ai_3d import generation as gen
from blender_mcp.tools import status
from blender_mcp.utils.results import to_image_content

PNG = base64.b64encode(b"\x89PNG fake").decode()


def _mock_client(monkeypatch, module, handler):
    real = httpx.AsyncClient

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real(*args, **kwargs)

    monkeypatch.setattr(module.httpx, "AsyncClient", factory)


def test_to_image_content_extracts_nested_images():
    payload = {
        "success": True,
        "result": {"angles": [{"image_base64": PNG}, {"image_base64": PNG}]},
    }
    blocks = to_image_content(payload)
    assert [b.type for b in blocks] == ["text", "image", "image"]
    assert "image_base64" not in blocks[0].text
    summary = json.loads(blocks[0].text)
    assert summary["result"]["angles"][1]["image_index"] == 1
    assert blocks[1].mimeType == "image/png"


def test_to_image_content_failure_is_text_only():
    blocks = to_image_content({"success": False, "error": "no viewport"})
    assert len(blocks) == 1 and "no viewport" in blocks[0].text


@pytest.mark.parametrize("bad", ["../evil.txt", "/abs/x", "a/../../x", "C:/x"])
def test_safe_join_rejects_traversal(tmp_path, bad):
    with pytest.raises(InvalidParameterError):
        downloads.safe_join(tmp_path, bad)


def _zip(tmp_path, entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    archive = tmp_path / "a.zip"
    archive.write_bytes(buf.getvalue())
    return archive


def test_extract_zip_blocks_zip_slip(tmp_path):
    archive = _zip(tmp_path, {"../../escape.glb": b"x"})
    with pytest.raises(InvalidParameterError):
        downloads.extract_zip(archive, tmp_path / "out")


def test_extract_zip_finds_model(tmp_path):
    archive = _zip(tmp_path, {"scene/scene.gltf": b"{}", "scene/textures/a.png": b"x"})
    assert downloads.extract_zip(archive, tmp_path / "out").name == "scene.gltf"


async def test_fetch_refuses_http(tmp_path):
    async with httpx.AsyncClient() as client:
        with pytest.raises(AssetDownloadFailedError):
            await downloads.fetch_file(client, "http://x/y", tmp_path / "y")


async def test_fetch_enforces_size_limit(tmp_path):
    transport = httpx.MockTransport(lambda r: httpx.Response(200, content=b"x" * 100))
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(AssetDownloadFailedError):
            await downloads.fetch_file(client, "https://h/f", tmp_path / "f", max_bytes=10)
    assert not (tmp_path / "f").exists()


async def test_polyhaven_model_downloads_gltf_and_includes(monkeypatch, tmp_path):
    include = {"textures/chair_diff.jpg": {"url": "https://dl.polyhaven.org/d.jpg"}}
    files = {
        "gltf": {"1k": {"gltf": {"url": "https://dl.polyhaven.org/c.gltf", "include": include}}}
    }

    def handler(request: httpx.Request):
        if request.url.path == "/files/chair":
            return httpx.Response(200, json=files)
        return httpx.Response(200, content=b"data")

    _mock_client(monkeypatch, downloads, handler)
    got = await downloads.download_polyhaven("chair", "models", "1k", root=tmp_path)
    assert got["kind"] == "model" and got["path"].endswith("chair.gltf")
    assert (tmp_path / "polyhaven_chair" / "textures" / "chair_diff.jpg").exists()


async def test_polyhaven_texture_detects_type_and_maps(monkeypatch, tmp_path):
    files = {
        "Diffuse": {"2k": {"jpg": {"url": "https://dl/d.jpg"}}},
        "Rough": {"2k": {"jpg": {"url": "https://dl/r.jpg"}}},
    }

    def handler(request: httpx.Request):
        if request.url.path == "/info/brick":
            return httpx.Response(200, json={"type": 1})
        if request.url.path == "/files/brick":
            return httpx.Response(200, json=files)
        return httpx.Response(200, content=b"img")

    _mock_client(monkeypatch, downloads, handler)
    got = await downloads.download_polyhaven("brick", None, "1k", root=tmp_path)
    assert got["kind"] == "texture"
    assert set(got["maps"]) == {"base_color", "roughness"}


async def test_polypizza_download(monkeypatch, tmp_path):
    def handler(request: httpx.Request):
        if "api.poly.pizza" in str(request.url):
            assert request.headers["x-auth-token"] == "k"
            return httpx.Response(200, json={"Download": "https://static.poly.pizza/m.glb"})
        return httpx.Response(200, content=b"glb")

    _mock_client(monkeypatch, downloads, handler)
    got = await downloads.download_polypizza("abc", "k", root=tmp_path)
    assert got["path"].endswith("abc.glb")


async def test_sketchfab_does_not_leak_token_to_storage(monkeypatch, tmp_path):
    def handler(request: httpx.Request):
        if "api.sketchfab.com" in str(request.url):
            return httpx.Response(200, json={"glb": {"url": "https://storage.example/m.glb"}})
        assert "authorization" not in request.headers
        return httpx.Response(200, content=b"glb")

    _mock_client(monkeypatch, downloads, handler)
    got = await downloads.download_sketchfab("uid1", "secret", root=tmp_path)
    assert got["kind"] == "model"


async def test_meshy_text_job_refines_then_downloads(monkeypatch, tmp_path):
    monkeypatch.setattr(gen, "asset_dir", lambda s, i: tmp_path)
    done = {"status": "SUCCEEDED", "progress": 100, "model_urls": {"glb": "https://m/x.glb"}}

    def handler(request: httpx.Request):
        url = str(request.url)
        if request.method == "POST":
            mode = json.loads(request.content)["mode"]
            return httpx.Response(200, json={"result": "refine1" if mode == "refine" else "prev1"})
        if url.endswith("/prev1"):
            return httpx.Response(200, json={"status": "SUCCEEDED", "progress": 100})
        if url.endswith("/refine1"):
            return httpx.Response(200, json=done)
        return httpx.Response(200, content=b"glb")

    _mock_client(monkeypatch, gen, handler)
    job = await gen.start("meshy", "k", prompt="a chair", image_url=None)
    await gen.poll(job, "k")
    assert job.stage == "refine" and job.status == "running"
    await gen.poll(job, "k")
    assert job.status == "succeeded" and job.path.endswith(".glb")


async def test_tripo_failed_job(monkeypatch):
    def handler(request: httpx.Request):
        if request.method == "POST":
            return httpx.Response(200, json={"data": {"task_id": "t1"}})
        return httpx.Response(200, json={"data": {"status": "failed"}})

    _mock_client(monkeypatch, gen, handler)
    job = await gen.start("tripo", "k", prompt=None, image_url="https://img/x.png")
    await gen.wait(job, "k", 0)
    assert job.status == "failed"


async def test_generation_requires_input():
    with pytest.raises(Exception, match="prompt"):
        await gen.start("meshy", "k", prompt=None, image_url=None)


def test_guides_available():
    assert {"bpy", "materials", "scene"} <= set(status.list_guides())
    assert "BSDF_PRINCIPLED" in status.read_guide("bpy")
    with pytest.raises(ValueError):
        status.read_guide("../secret")


def test_addon_warnings_detect_outdated():
    from blender_mcp import __version__

    current = {"addon_version": __version__, "commands": ["import_local_asset", "lookup_api"]}
    assert status.addon_warnings(current) == []
    assert len(status.addon_warnings({"addon_version": "0.0.1", "commands": []})) == 2


def test_new_tools_registered():
    from blender_mcp.config import load_settings
    from blender_mcp.server import create_server

    names = set(create_server(load_settings())._tool_manager._tools)  # noqa: SLF001
    for tool in ("generate_3d", "get_generation_status", "get_addon_status", "get_guide"):
        assert tool in names
    assert "search_scene" in names
