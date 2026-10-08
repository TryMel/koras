from app.tools.registry import tool_registry


def test_registered_tool_contracts_reject_missing_and_unexpected_values():
    sms = tool_registry.get("send_sms")
    assert sms is not None
    assert tool_registry.validate_parameters(
        sms,
        {"contact_name": "Maman"},
    ) == "Paramètre requis manquant : message."
    assert tool_registry.validate_parameters(
        sms,
        {"contact_name": "Maman", "message": "Bonjour", "unexpected": True},
    ) == "Paramètre inattendu : unexpected."
    assert tool_registry.validate_parameters(
        sms,
        {"contact_name": "Maman", "message": 123},
    ) == "Paramètre invalide : message doit être un texte."


def test_financial_tool_is_visible_but_disabled_without_a_connector():
    transfer = tool_registry.get("transfer_money")
    assert transfer is not None
    assert transfer.enabled is False
