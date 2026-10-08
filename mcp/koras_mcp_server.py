"""KORAS MCP server over JSON-RPC 2.0 stdio.

Phone actions are never executed or reported as successful by this process.
They require the authenticated Android connector to perform and observe them.
"""

import json
import logging
import math
import sys
from typing import Any, Dict, Optional

logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s [MCP] %(message)s")

PROTOCOL_VERSION = "2024-11-05"
TOOLS_DEFINITIONS = [
    {
        "name": "call_contact",
        "description": "Demande un appel au connecteur Android après autorisation",
        "inputSchema": {
            "type": "object",
            "properties": {"contact_name": {"type": "string"}, "phone_number": {"type": "string"}},
            "required": ["contact_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "send_sms",
        "description": "Demande l'envoi d'un SMS au connecteur Android après confirmation",
        "inputSchema": {
            "type": "object",
            "properties": {"contact_name": {"type": "string"}, "message": {"type": "string"}},
            "required": ["contact_name", "message"],
            "additionalProperties": False,
        },
    },
    {
        "name": "open_app",
        "description": "Demande l'ouverture d'une application par le connecteur Android",
        "inputSchema": {
            "type": "object",
            "properties": {"app_name": {"type": "string"}},
            "required": ["app_name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "read_screen_accessibility",
        "description": "Demande la lecture de l'écran au service d'accessibilité Android activé par l'utilisateur",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "read_notification",
        "description": "Demande la lecture des notifications autorisées au connecteur Android",
        "inputSchema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 20}},
            "additionalProperties": False,
        },
    },
    {
        "name": "transfer_money_preview",
        "description": "Produit un aperçu indicatif non exécutable; aucun transfert n'est effectué",
        "inputSchema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "exclusiveMinimum": 0},
                "recipient": {"type": "string"},
                "provider": {"type": "string"},
            },
            "required": ["amount", "recipient"],
            "additionalProperties": False,
        },
    },
]

def _error(request_id: Any, code: int, message: str) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

def _success(request_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}

def _validate_tool_arguments(tool: Dict[str, Any], arguments: Any) -> Optional[str]:
    if not isinstance(arguments, dict):
        return "Les arguments doivent être un objet JSON."
    schema = tool["inputSchema"]
    properties = schema["properties"]
    missing = [key for key in schema.get("required", []) if key not in arguments]
    if missing:
        return f"Paramètre requis manquant : {missing[0]}."
    for key, value in arguments.items():
        property_schema = properties.get(key)
        if property_schema is None:
            return f"Paramètre inattendu : {key}."
        expected_type = property_schema.get("type")
        if expected_type == "string" and (not isinstance(value, str) or not value.strip()):
            return f"Paramètre invalide : {key} doit être un texte non vide."
        if expected_type == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                return f"Paramètre invalide : {key} doit être un nombre fini."
            if value <= property_schema.get("exclusiveMinimum", float("-inf")):
                return f"Paramètre invalide : {key} doit être positif."
        if expected_type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                return f"Paramètre invalide : {key} doit être un entier."
            if value < property_schema.get("minimum", 0) or value > property_schema.get("maximum", 2**31 - 1):
                return f"Paramètre invalide : {key} est hors limites."
    return None

def handle_request(request: Any) -> Optional[Dict[str, Any]]:
    request_id = request.get("id") if isinstance(request, dict) else None
    if not isinstance(request, dict):
        return _error(None, -32600, "Requête JSON-RPC invalide.")
    if request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
        return _error(request_id, -32600, "Requête JSON-RPC invalide.")
    if "id" in request and (
        isinstance(request_id, bool) or not isinstance(request_id, (str, int, type(None)))
    ):
        return _error(None, -32600, "Identifiant de requête invalide.")
    if "id" not in request:
        return None

    method = request["method"]
    params = request.get("params", {})
    if not isinstance(params, dict):
        return _error(request_id, -32602, "Les paramètres doivent être un objet JSON.")

    if method == "notifications/initialized":
        return None
    if method == "initialize":
        return _success(request_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
            "serverInfo": {"name": "koras-mcp", "version": "1.0.0"},
        })
    if method == "ping":
        return _success(request_id, {})
    if method == "tools/list":
        return _success(request_id, {"tools": TOOLS_DEFINITIONS})
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        tool = next((item for item in TOOLS_DEFINITIONS if item["name"] == name), None)
        if not tool:
            return _error(request_id, -32602, "Outil MCP inconnu.")
        validation_error = _validate_tool_arguments(tool, arguments)
        if validation_error:
            return _error(request_id, -32602, validation_error)

        if name == "transfer_money_preview":
            preview = {
                "amount": arguments["amount"],
                "fee": None,
                "total": None,
                "currency": "XOF",
                "recipient": arguments["recipient"].strip(),
                "provider": arguments.get("provider", "wave"),
                "status": "preview_only",
                "message": "Aucun connecteur financier n'est activé; aucun frais réel n'est estimé et aucun fonds ne sera déplacé.",
            }
            return _success(request_id, {
                "content": [{"type": "text", "text": json.dumps(preview, ensure_ascii=False)}],
            })

        logging.info("Device tool call requires an attached trusted Android connector: %s", name)
        return _success(request_id, {
            "content": [{
                "type": "text",
                "text": "Aucun connecteur Android n'est attaché à ce serveur MCP. Aucune action n'a été exécutée.",
            }],
            "isError": True,
        })
    if method == "resources/list":
        return _success(request_id, {
            "resources": [
                {"uri": "koras://device/battery", "name": "Niveau de batterie", "mimeType": "application/json"},
                {"uri": "koras://device/network", "name": "État de la connectivité réseau", "mimeType": "application/json"},
            ],
        })
    if method == "resources/read":
        uri = params.get("uri")
        if uri not in {"koras://device/battery", "koras://device/network"}:
            return _error(request_id, -32602, "Ressource KORAS inconnue.")
        return _error(request_id, -32001, "Cette ressource doit être lue par le connecteur Android approuvé.")
    if method == "prompts/list":
        return _success(request_id, {
            "prompts": [{
                "name": "clarification_prompt",
                "description": "Demande une précision lorsque l'intention est incomplète",
                "arguments": [{"name": "question", "required": True}],
            }],
        })
    if method == "prompts/get":
        if params.get("name") != "clarification_prompt" or not isinstance(params.get("arguments"), dict):
            return _error(request_id, -32602, "Prompt ou arguments invalides.")
        question = params["arguments"].get("question")
        if not isinstance(question, str) or not question.strip():
            return _error(request_id, -32602, "Une question de clarification est requise.")
        return _success(request_id, {
            "description": "Clarification de l'intention utilisateur",
            "messages": [{
                "role": "user",
                "content": {"type": "text", "text": question.strip()},
            }],
        })
    return _error(request_id, -32601, "Méthode non supportée.")

def main() -> None:
    logging.info("KORAS MCP Server running (JSON-RPC stdio)...")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            response = _error(None, -32700, "JSON invalide.")
        else:
            response = handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
