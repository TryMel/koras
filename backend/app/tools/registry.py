"""Validated tool contracts exposed to the agent planner.

Device-provider contracts describe commands dispatched by the trusted mobile
client; this registry does not execute side effects.
"""

import math
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.core.config import settings

class ToolContract(BaseModel):
    tool_id: str
    name: str
    description: str
    version: str = "1.0.0"
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    risk_level: int = 1
    permissions: List[str] = Field(default_factory=list)
    requires_confirmation: bool = False
    requires_authentication: bool = False
    enabled: bool = True
    supports_preview: bool = True
    supports_idempotency: bool = False
    supports_rollback: bool = False
    timeout_seconds: int = 10
    supported_platforms: List[str] = Field(default_factory=lambda: ["android", "backend"])
    provider: str = "native"

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, ToolContract] = {}
        self._register_default_tools()

    def register(self, contract: ToolContract):
        self._tools[contract.tool_id] = contract

    def get(self, tool_id: str) -> Optional[ToolContract]:
        return self._tools.get(tool_id)

    def list_all(self) -> List[ToolContract]:
        return list(self._tools.values())

    def validate_parameters(self, tool: ToolContract, parameters: Dict[str, Any]) -> Optional[str]:
        """Validate the JSON-schema subset used by registered tools."""
        schema = tool.input_schema
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for name in required:
            if name not in parameters or parameters[name] is None or parameters[name] == "":
                return f"Paramètre requis manquant : {name}."
        for name, value in parameters.items():
            property_schema = properties.get(name)
            if property_schema is None:
                return f"Paramètre inattendu : {name}."
            expected = property_schema.get("type")
            if expected == "string":
                if not isinstance(value, str):
                    return f"Paramètre invalide : {name} doit être un texte."
                if len(value) < property_schema.get("minLength", 0):
                    return f"Paramètre invalide : {name} est trop court."
                if len(value) > property_schema.get("maxLength", 8000):
                    return f"Paramètre invalide : {name} est trop long."
            elif expected == "number":
                if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                    return f"Paramètre invalide : {name} doit être un nombre fini."
                if "minimum" in property_schema and value < property_schema["minimum"]:
                    return f"Paramètre invalide : {name} est inférieur au minimum."
            elif expected == "integer":
                if not isinstance(value, int) or isinstance(value, bool):
                    return f"Paramètre invalide : {name} doit être un entier."
            elif expected == "boolean" and not isinstance(value, bool):
                return f"Paramètre invalide : {name} doit être un booléen."
            elif expected == "array" and not isinstance(value, list):
                return f"Paramètre invalide : {name} doit être une liste."
            elif expected == "object" and not isinstance(value, dict):
                return f"Paramètre invalide : {name} doit être un objet."
            if "enum" in property_schema and value not in property_schema["enum"]:
                return f"Paramètre invalide : {name} n'est pas une valeur autorisée."
        return None

    def _register_default_tools(self):
        # 1. Phone Call
        self.register(ToolContract(
            tool_id="call_contact",
            name="Appeler un contact",
            description="Initie un appel téléphonique vers un numéro ou contact vérifié",
            risk_level=2,
            permissions=["android.permission.CALL_PHONE"],
            requires_confirmation=True,
            input_schema={
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string"},
                    "phone_number": {"type": "string"}
                },
                "required": ["contact_name"]
            },
            output_schema={"type": "object", "properties": {"success": {"type": "boolean"}}},
            supports_rollback=False,
            provider="device"
        ))

        # 2. Send SMS
        self.register(ToolContract(
            tool_id="send_sms",
            name="Envoyer un SMS",
            description="Prépare et transmet un SMS à un destinataire",
            risk_level=2,
            permissions=["android.permission.SEND_SMS"],
            requires_confirmation=True,
            input_schema={
                "type": "object",
                "properties": {
                    "contact_name": {"type": "string"},
                    "phone_number": {"type": "string"},
                    "message": {"type": "string"}
                },
                "required": ["contact_name", "message"]
            },
            output_schema={"type": "object", "properties": {"sent": {"type": "boolean"}}},
            provider="device"
        ))

        # 3. Open Application
        self.register(ToolContract(
            tool_id="open_app",
            name="Ouvrir une application",
            description="Lance une application installée sur l'appareil Android",
            risk_level=1,
            permissions=[],
            requires_confirmation=False,
            input_schema={
                "type": "object",
                "properties": {
                    "app_name": {"type": "string"},
                    "package_name": {"type": "string"}
                },
                "required": ["app_name"]
            },
            output_schema={"type": "object", "properties": {"opened": {"type": "boolean"}}},
            provider="device"
        ))

        # 4. Read Notification
        self.register(ToolContract(
            tool_id="read_notification",
            name="Lire une notification",
            description="Consulte et vocalise les dernières notifications autorisées",
            risk_level=0,
            permissions=["android.permission.BIND_NOTIFICATION_LISTENER_SERVICE"],
            requires_confirmation=False,
            input_schema={"type": "object", "properties": {"limit": {"type": "integer", "default": 3}}},
            output_schema={"type": "object", "properties": {"notifications": {"type": "array"}}},
            provider="device"
        ))

        # 5. Open Navigation / Maps
        self.register(ToolContract(
            tool_id="open_maps",
            name="Ouvrir la navigation",
            description="Ouvre Google Maps ou le GPS vers une destination ou POI",
            risk_level=1,
            permissions=["android.permission.ACCESS_FINE_LOCATION"],
            requires_confirmation=False,
            input_schema={
                "type": "object",
                "properties": {
                    "destination": {"type": "string"}
                },
                "required": ["destination"]
            },
            output_schema={"type": "object", "properties": {"success": {"type": "boolean"}}},
            provider="device"
        ))

        # 6. Create Reminder
        self.register(ToolContract(
            tool_id="create_reminder",
            name="Créer un rappel",
            description="Enregistre un rappel ou alarme sur le téléphone",
            risk_level=1,
            permissions=[],
            requires_confirmation=False,
            supports_rollback=True,
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "time": {"type": "string"}
                },
                "required": ["title"]
            },
            output_schema={"type": "object", "properties": {"created": {"type": "boolean"}}},
            provider="device"
        ))

        # 7. Accessibility Read Screen
        self.register(ToolContract(
            tool_id="read_screen",
            name="Lire l'écran via Accessibilité",
            description="Lit et extrait sémantiquement les composants visibles à l'écran via AccessibilityService",
            risk_level=0,
            permissions=["android.permission.BIND_ACCESSIBILITY_SERVICE"],
            requires_confirmation=False,
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {"screen_elements": {"type": "array"}}},
            provider="device"
        ))

        self.register(ToolContract(
            tool_id="search_contact", name="Chercher un contact",
            description="Recherche localement un contact autorisé sur Android", risk_level=0,
            permissions=["android.permission.READ_CONTACTS"],
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            output_schema={"type": "object", "properties": {"contacts": {"type": "array"}}}, provider="device"
        ))
        self.register(ToolContract(
            tool_id="open_url", name="Ouvrir une adresse web",
            description="Ouvre une URL dans le navigateur Android", risk_level=1,
            input_schema={"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]},
            output_schema={"type": "object", "properties": {"opened": {"type": "boolean"}}}, provider="device"
        ))
        self.register(ToolContract(
            tool_id="search_web", name="Rechercher une information",
            description="Ouvre une recherche web dans le navigateur", risk_level=1,
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
            output_schema={"type": "object", "properties": {"opened": {"type": "boolean"}}}, provider="device"
        ))
        self.register(ToolContract(
            tool_id="create_event", name="Créer un événement",
            description="Prépare un événement dans le calendrier Android", risk_level=2,
            requires_confirmation=True,
            input_schema={"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}}, "required": ["title"]},
            output_schema={"type": "object", "properties": {"opened": {"type": "boolean"}}}, provider="device"
        ))
        self.register(ToolContract(
            tool_id="accessibility_click", name="Activer un élément accessible",
            description="Active un élément par son libellé via AccessibilityService activé par l’utilisateur", risk_level=1,
            permissions=["android.permission.BIND_ACCESSIBILITY_SERVICE"], requires_confirmation=True,
            input_schema={"type": "object", "properties": {"label": {"type": "string"}}, "required": ["label"]},
            output_schema={"type": "object", "properties": {"clicked": {"type": "boolean"}}}, provider="device"
        ))

        # 8. Transfer Money (Section 19 - Sandbox/Controlled)
        self.register(ToolContract(
            tool_id="transfer_money",
            name="Transfert d'argent sécurisé",
            description="Exécute un transfert de fonds vers un bénéficiaire via connecteur agréé",
            risk_level=4,
            permissions=[],
            requires_confirmation=True,
            requires_authentication=True,
            enabled=settings.ENABLE_FINANCIAL_CONNECTORS,
            supports_preview=True,
            supports_idempotency=True,
            supports_rollback=False,
            timeout_seconds=30,
            input_schema={
                "type": "object",
                "properties": {
                    "amount": {"type": "number"},
                    "currency": {"type": "string", "default": "XOF"},
                    "recipient": {"type": "string"},
                    "provider": {"type": "string", "default": "wave"}
                },
                "required": ["amount", "recipient"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "transaction_id": {"type": "string"},
                    "status": {"type": "string"},
                    "idempotency_key": {"type": "string"}
                }
            },
            provider="partner"
        ))

tool_registry = ToolRegistry()
