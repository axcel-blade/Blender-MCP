from blender_mcp.protocol.messages import BridgeRequest, BridgeResponse


def test_request_roundtrip_shape():
    req = BridgeRequest(command="get_scene_info", params={"limit": 1})
    data = req.to_dict()
    assert data["type"] == "request"
    assert data["command"] == "get_scene_info"
    assert data["params"]["limit"] == 1
    assert data["id"]


def test_response_to_tool_result_success():
    resp = BridgeResponse(id="abc", success=True, result={"ok": 1}, duration_ms=12.5)
    payload = resp.to_tool_result()
    assert payload["success"] is True
    assert payload["result"]["ok"] == 1
    assert payload["operation_id"] == "abc"


def test_response_to_tool_result_error():
    resp = BridgeResponse(
        id="abc",
        success=False,
        error_code="OBJECT_NOT_FOUND",
        error="missing",
    )
    payload = resp.to_tool_result()
    assert payload["success"] is False
    assert payload["error_code"] == "OBJECT_NOT_FOUND"
