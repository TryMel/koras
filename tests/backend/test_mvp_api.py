import asyncio

from sqlalchemy import select

from app.database.models.models import Action, AgentRun, User


def test_local_action_persists_run_and_requires_device_observation(client, registered_user):
    user = registered_user()
    planned = client.post(
        "/api/v1/agent/run",
        headers=user["headers"],
        json={"user_input": "Ouvre Maps", "device_identifier": user["device_identifier"]},
    )
    assert planned.status_code == 200
    body = planned.json()
    assert body["state"] == "READY_TO_EXECUTE"
    assert body["is_terminal"] is False
    assert body["conversation_id"]

    step = body["steps"][0]
    completed = client.post(
        f"/api/v1/agent/runs/{body['run_id']}/steps/{step['step_id']}/result",
        headers=user["headers"],
        json={"status": "verified", "result": {"verified": True, "opened": True}},
    )
    assert completed.status_code == 200
    assert completed.json()["state"] == "SUCCESS"

    status_response = client.get(f"/api/v1/agent/runs/{body['run_id']}", headers=user["headers"])
    assert status_response.status_code == 200
    assert status_response.json()["state"] == "SUCCESS"

    conversation = client.get(
        f"/api/v1/conversations/{body['conversation_id']}",
        headers=user["headers"],
    )
    assert conversation.status_code == 200
    assert [message["role"] for message in conversation.json()["messages"]] == [
        "user", "assistant", "assistant",
    ]

    async def read_persisted_state():
        async with client.app.state.test_session_factory() as session:
            stored_run = await session.get(AgentRun, body["run_id"])
            stored_action = await session.get(Action, step["step_id"])
            return stored_run.status, stored_action.status, stored_run.execution_plan["output"]["state"]

    assert asyncio.run(read_persisted_state()) == ("SUCCESS", "verified", "SUCCESS")


def test_external_action_requires_auth_confirmation_and_device_execution(client, registered_user):
    unauthenticated = client.post("/api/v1/agent/run", json={"user_input": "Appelle maman"})
    assert unauthenticated.status_code == 401

    user = registered_user()
    planned = client.post(
        "/api/v1/agent/run",
        headers=user["headers"],
        json={"user_input": "Appelle maman", "device_identifier": user["device_identifier"]},
    )
    assert planned.status_code == 200
    body = planned.json()
    assert body["state"] == "WAITING_FOR_CONFIRMATION"
    step = body["steps"][0]

    premature = client.post(
        f"/api/v1/agent/runs/{body['run_id']}/steps/{step['step_id']}/result",
        headers=user["headers"],
        json={"status": "verified", "result": {"verified": True}},
    )
    assert premature.status_code == 409

    approved = client.post(
        f"/api/v1/agent/runs/{body['run_id']}/confirm",
        headers=user["headers"],
        json={"step_id": step["step_id"]},
    )
    assert approved.status_code == 200
    assert approved.json()["state"] == "READY_TO_EXECUTE"

    completed = client.post(
        f"/api/v1/agent/runs/{body['run_id']}/steps/{step['step_id']}/result",
        headers=user["headers"],
        json={"status": "verified", "result": {"verified": True, "launched": True}},
    )
    assert completed.status_code == 200
    assert completed.json()["state"] == "SUCCESS"


def test_multi_action_run_requests_each_confirmation_in_order(client, registered_user):
    user = registered_user()
    planned = client.post(
        "/api/v1/agent/run",
        headers=user["headers"],
        json={
            "user_input": "Appelle maman puis crée un événement réunion",
            "device_identifier": user["device_identifier"],
        },
    )
    assert planned.status_code == 200
    body = planned.json()
    assert body["state"] == "WAITING_FOR_CONFIRMATION"
    first_step, second_step = body["steps"]
    assert body["awaiting_confirmation_step_id"] == first_step["step_id"]

    premature_second_approval = client.post(
        f"/api/v1/agent/runs/{body['run_id']}/confirm",
        headers=user["headers"],
        json={"step_id": second_step["step_id"]},
    )
    assert premature_second_approval.status_code == 409

    approved_first = client.post(
        f"/api/v1/agent/runs/{body['run_id']}/confirm",
        headers=user["headers"],
        json={"step_id": first_step["step_id"]},
    )
    assert approved_first.status_code == 200
    assert approved_first.json()["state"] == "READY_TO_EXECUTE"

    completed_first = client.post(
        f"/api/v1/agent/runs/{body['run_id']}/steps/{first_step['step_id']}/result",
        headers=user["headers"],
        json={"status": "verified", "result": {"verified": True, "launched": True}},
    )
    assert completed_first.status_code == 200
    next_run = completed_first.json()
    assert next_run["state"] == "WAITING_FOR_CONFIRMATION"
    assert next_run["awaiting_confirmation_step_id"] == second_step["step_id"]

    approved_second = client.post(
        f"/api/v1/agent/runs/{body['run_id']}/confirm",
        headers=user["headers"],
        json={"step_id": second_step["step_id"]},
    )
    assert approved_second.status_code == 200
    assert approved_second.json()["state"] == "READY_TO_EXECUTE"

    completed_second = client.post(
        f"/api/v1/agent/runs/{body['run_id']}/steps/{second_step['step_id']}/result",
        headers=user["headers"],
        json={"status": "verified", "result": {"verified": True, "launched": True}},
    )
    assert completed_second.status_code == 200
    assert completed_second.json()["state"] == "SUCCESS"


def test_runs_are_private_to_the_authenticated_user(client, registered_user):
    owner = registered_user(phone="+2250700000001", device_identifier="owner-device")
    other = registered_user(phone="+2250700000002", device_identifier="other-device")
    planned = client.post(
        "/api/v1/agent/run",
        headers=owner["headers"],
        json={"user_input": "Ouvre Maps", "device_identifier": owner["device_identifier"]},
    )
    run_id = planned.json()["run_id"]

    status_response = client.get(f"/api/v1/agent/runs/{run_id}", headers=other["headers"])
    assert status_response.status_code == 404


def test_device_revocation_terminates_its_session(client, registered_user):
    user = registered_user()
    devices = client.get("/api/v1/devices", headers=user["headers"])
    assert devices.status_code == 200
    device_id = devices.json()[0]["id"]

    revoked = client.post(f"/api/v1/devices/{device_id}/revoke", headers=user["headers"])
    assert revoked.status_code == 200
    profile = client.get("/api/v1/users/me", headers=user["headers"])
    assert profile.status_code == 401


def test_admin_endpoints_require_an_admin_role(client, registered_user):
    assert client.get("/api/v1/admin/users").status_code == 401
    user = registered_user()
    response = client.get("/api/v1/admin/users", headers=user["headers"])
    assert response.status_code == 403


def test_financial_preview_never_claims_to_execute_without_a_connector(client, registered_user):
    user = registered_user()
    preview = client.post(
        "/api/v1/transactions/preview",
        headers=user["headers"],
        json={"amount": 5000, "recipient": "Maman"},
    )
    assert preview.status_code == 200
    preview_body = preview.json()
    assert preview_body["status"] == "preview_only"
    assert preview_body["transaction_id"] is None
    assert preview_body["estimated_fee"] == 0
    assert "aucun fonds" in preview_body["preview_message"].lower()

    confirmed = client.post(
        f"/api/v1/transactions/{preview_body['idempotency_key']}/confirm",
        headers=user["headers"],
        json={"biometric_authenticated": True},
    )
    assert confirmed.status_code == 503


def test_logout_revokes_the_access_token(client, registered_user):
    user = registered_user()
    logged_out = client.post("/api/v1/auth/logout", headers=user["headers"])
    assert logged_out.status_code == 204
    assert client.get("/api/v1/users/me", headers=user["headers"]).status_code == 401


def test_new_device_login_requires_explicit_registration_before_agent_use(client, registered_user):
    registered_user()
    login = client.post(
        "/api/v1/auth/login",
        json={
            "phone": "+2250700000001",
            "password": "test-password-123",
            "device_identifier": "new-device",
        },
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    blocked = client.post(
        "/api/v1/agent/run",
        headers=headers,
        json={"user_input": "Ouvre Maps", "device_identifier": "new-device"},
    )
    assert blocked.status_code == 403

    registration = client.post(
        "/api/v1/devices/register",
        headers=headers,
        json={"device_identifier": "new-device", "platform": "android"},
    )
    assert registration.status_code == 200
    assert registration.json()["trust_status"] == "trusted"

    allowed = client.post(
        "/api/v1/agent/run",
        headers=headers,
        json={"user_input": "Ouvre Maps", "device_identifier": "new-device"},
    )
    assert allowed.status_code == 200


def test_conversation_access_is_scoped_to_its_owner(client, registered_user):
    owner = registered_user(phone="+2250700000001", device_identifier="owner-device")
    other = registered_user(phone="+2250700000002", device_identifier="other-device")
    created = client.post(
        "/api/v1/conversations",
        headers=owner["headers"],
        json={"title": "Privée"},
    )
    conversation_id = created.json()["id"]

    denied = client.get(
        f"/api/v1/conversations/{conversation_id}",
        headers=other["headers"],
    )
    assert denied.status_code == 404


def test_admin_metrics_use_database_values_and_do_not_claim_unmeasured_accuracy(
    client,
    registered_user,
):
    import asyncio

    user = registered_user()

    async def promote_user():
        async with client.app.state.test_session_factory() as session:
            account = await session.get(User, user["user_id"])
            account.role = "admin"
            await session.commit()

    asyncio.run(promote_user())
    metrics = client.get("/api/v1/admin/metrics", headers=user["headers"])
    assert metrics.status_code == 200
    assert metrics.json()["users"] == 1
    assert metrics.json()["trusted_devices"] == 1
    assert metrics.json()["intent_accuracy"] is None


def test_cancel_is_persisted_and_cannot_be_reversed_by_late_result(client, registered_user):
    user = registered_user()
    planned = client.post(
        "/api/v1/agent/run",
        headers=user["headers"],
        json={"user_input": "Ouvre Maps", "device_identifier": user["device_identifier"]},
    ).json()
    cancelled = client.post(
        f"/api/v1/agent/runs/{planned['run_id']}/cancel",
        headers=user["headers"],
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "CANCELLED"

    late_result = client.post(
        f"/api/v1/agent/runs/{planned['run_id']}/steps/{planned['steps'][0]['step_id']}/result",
        headers=user["headers"],
        json={"status": "verified", "result": {"verified": True, "opened": True}},
    )
    assert late_result.status_code == 409
