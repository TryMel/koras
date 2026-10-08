import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from mcp.koras_mcp_server import handle_request


def test_mcp_initialization_and_notifications():
    initialized = handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {},
    })
    assert initialized["result"]["protocolVersion"] == "2024-11-05"
    assert initialized["result"]["capabilities"]["tools"] == {}
    assert handle_request({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_mcp_never_simulates_a_device_action():
    response = handle_request({
        "jsonrpc": "2.0",
        "id": "call-1",
        "method": "tools/call",
        "params": {"name": "open_app", "arguments": {"app_name": "WhatsApp"}},
    })
    assert response["result"]["isError"] is True
    assert "Aucune action n'a été exécutée" in response["result"]["content"][0]["text"]


def test_mcp_financial_preview_is_non_executable():
    response = handle_request({
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "transfer_money_preview",
            "arguments": {"amount": 5000, "recipient": "Maman"},
        },
    })
    text = response["result"]["content"][0]["text"]
    assert '"status": "preview_only"' in text
    assert "aucun fonds ne sera déplacé" in text


def test_mcp_rejects_invalid_calls_and_malformed_json_rpc():
    missing_parameter = handle_request({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "send_sms", "arguments": {"contact_name": "Maman"}},
    })
    assert missing_parameter["error"]["code"] == -32602

    invalid_request = handle_request({"jsonrpc": "1.0", "method": "ping"})
    assert invalid_request["error"]["code"] == -32600
