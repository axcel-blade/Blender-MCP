"""Tool replies stay in the model's context, so their size is bounded."""

from blender_mcp.utils.results import (
    MAX_RESULT_CHARS,
    MAX_STREAM_CHARS,
    clip_text,
    compact_script_result,
)


def test_clip_text_keeps_head_and_tail():
    text = "A" * 5000 + "END"
    clipped = clip_text(text, 300)
    assert clipped.startswith("A") and clipped.endswith("END")
    assert "chars omitted" in clipped
    assert len(clipped) < 400


def test_clip_text_leaves_short_and_non_strings():
    assert clip_text("short", 100) == "short"
    assert clip_text(None, 100) is None


def test_compact_script_result_clips_streams_and_result():
    payload = {
        "success": True,
        "result": {
            "success": True,
            "stdout": "x" * (MAX_STREAM_CHARS * 3),
            "stderr": "",
            "traceback": None,
            "error": None,
            "result": list(range(10_000)),
            "duration_ms": 12.345678,
        },
    }
    entry = compact_script_result(payload)["result"]
    assert len(entry["stdout"]) < MAX_STREAM_CHARS + 100
    assert "stderr" not in entry and "traceback" not in entry and "error" not in entry
    assert isinstance(entry["result"], str)
    assert len(entry["result"]) < MAX_RESULT_CHARS + 100
    assert "result_truncated" in entry
    assert entry["duration_ms"] == 12.3


def test_compact_script_result_keeps_small_results_intact():
    payload = {"success": True, "result": {"stdout": "hi", "result": {"a": 1}}}
    assert compact_script_result(payload)["result"] == {"stdout": "hi", "result": {"a": 1}}


def test_compact_script_result_passes_failures_through():
    failure = {"success": False, "error": "nope"}
    assert compact_script_result(failure) == failure
