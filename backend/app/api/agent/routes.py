from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database.session import get_db
from app.database.models.models import (
    User, Device, Session as AuthSession, Conversation, Message, Intent, AgentRun,
    Action, Approval, AuditLog,
)
from app.core.dependencies import get_current_user, get_authenticated_session
from app.agent.agent_runtime import AgentRuntime, AgentRunOutput, AgentState
from app.core.security import sanitize_untrusted_input

router = APIRouter(prefix="/agent", tags=["Agent Execution"])

class AgentRunRequest(BaseModel):
    user_input: str = Field(min_length=1, max_length=8000)
    conversation_id: Optional[str] = Field(default=None, max_length=36)
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)
    device_identifier: Optional[str] = Field(default=None, max_length=128)

class ConfirmStepRequest(BaseModel):
    step_id: str = Field(min_length=1, max_length=36)
    biometric_authenticated: bool = False
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)

class StepResultRequest(BaseModel):
    """Observation returned by the trusted Android client after a tool call."""
    status: str = Field(pattern="^(verified|failed|unknown)$")
    result: Dict[str, Any] = Field(default_factory=dict, max_length=100)
    error: Optional[str] = Field(default=None, max_length=1000)

async def _load_owned_run(
    db: AsyncSession,
    run_id: str,
    current_user: User,
) -> tuple[AgentRun, AgentRunOutput, Dict[str, Any]]:
    result = await db.execute(
        select(AgentRun)
        .join(Intent, AgentRun.intent_id == Intent.id)
        .join(Conversation, Intent.conversation_id == Conversation.id)
        .where(AgentRun.id == run_id, Conversation.user_id == current_user.id)
    )
    run = result.scalars().first()
    if not run:
        raise HTTPException(status_code=404, detail="Exécution introuvable.")

    stored = run.execution_plan or {}
    if not isinstance(stored, dict):
        raise HTTPException(status_code=500, detail="État d'exécution persistant invalide.")
    output_data = stored.get("output")
    if not isinstance(output_data, dict):
        raise HTTPException(status_code=500, detail="État d'exécution persistant invalide.")
    return run, AgentRunOutput.model_validate(output_data), stored

def _require_run_session(stored: Dict[str, Any], auth_session: AuthSession) -> None:
    if stored.get("session_id") != auth_session.id:
        raise HTTPException(status_code=403, detail="Cette exécution appartient à une autre session.")
    if not stored.get("device_id") or stored.get("device_id") != auth_session.device_id:
        raise HTTPException(status_code=403, detail="Appareil de cette exécution non autorisé.")

def _store_run_output(
    run: AgentRun,
    output: AgentRunOutput,
    stored: Dict[str, Any],
) -> None:
    run.status = output.state.value
    run.execution_plan = {
        "version": 1,
        "session_id": stored["session_id"],
        "device_id": stored["device_id"],
        "output": output.model_dump(mode="json"),
    }
    if output.is_terminal:
        run.completed_at = datetime.now(timezone.utc)

async def _sync_action_state(db: AsyncSession, output: AgentRunOutput) -> None:
    for step in output.steps:
        result = await db.execute(select(Action).where(Action.id == step.step_id))
        action = result.scalars().first()
        if action:
            action.status = {
                "waiting_approval": "waiting_approval",
                "ready": "pending",
                "verified": "verified",
                "failed": "failed",
                "unknown": "unknown",
                "cancelled": "cancelled",
            }.get(step.status, step.status)
            action.output_payload = step.result
            if step.status in {"verified", "failed", "unknown", "cancelled"}:
                action.completed_at = datetime.now(timezone.utc)

async def _record_assistant_update(db: AsyncSession, output: AgentRunOutput, user_id: str) -> None:
    if not output.conversation_id:
        return
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == output.conversation_id,
            Conversation.user_id == user_id,
        )
    )
    conversation = result.scalars().first()
    if conversation:
        conversation.updated_at = datetime.now(timezone.utc)
        language_result = await db.execute(
            select(Message.language)
            .where(Message.conversation_id == conversation.id)
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        db.add(Message(
            conversation_id=conversation.id,
            role="assistant",
            content=output.spoken_response,
            content_type="text",
            language=language_result.scalar_one_or_none() or "fr",
        ))

@router.post("/run", response_model=AgentRunOutput)
async def run_agent(
    req: AgentRunRequest,
    current_user: User = Depends(get_current_user),
    auth_session: AuthSession = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db)
):
    safe_input = sanitize_untrusted_input(req.user_input).strip()
    if not safe_input:
        raise HTTPException(status_code=422, detail="La commande ne peut pas être vide.")
    if not req.device_identifier or not auth_session.device_id:
        raise HTTPException(status_code=403, detail="Une session liée à un appareil approuvé est requise.")

    device_result = await db.execute(
        select(Device).where(
            Device.id == auth_session.device_id,
            Device.user_id == current_user.id,
            Device.device_identifier == req.device_identifier,
        )
    )
    device = device_result.scalars().first()
    if not device or device.trust_status != "trusted":
        raise HTTPException(status_code=403, detail="Appareil absent, révoqué ou non approuvé.")
    device.last_seen_at = datetime.now(timezone.utc)

    ctx = req.context or {}
    ctx["user_id"] = current_user.id
    run_output = AgentRuntime.process_request(
        user_input=safe_input,
        context=ctx,
        user_vulnerable_mode=current_user.vulnerable_mode,
        device_trusted=True,
    )

    if req.conversation_id:
        conversation_result = await db.execute(
            select(Conversation).where(
                Conversation.id == req.conversation_id,
                Conversation.user_id == current_user.id,
            )
        )
        conversation = conversation_result.scalars().first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation introuvable.")
    else:
        conversation = Conversation(user_id=current_user.id, title=safe_input[:80] or "Nouvelle conversation")
        db.add(conversation)
        await db.flush()

    conversation.updated_at = datetime.now(timezone.utc)
    conversation.session_id = auth_session.id
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=safe_input,
        content_type="text",
        language=ctx.get("language", "fr"),
    )
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=run_output.spoken_response,
        content_type="text",
        language=ctx.get("language", "fr"),
    )
    db.add_all([user_message, assistant_message])
    await db.flush()
    run_output.conversation_id = conversation.id

    first_step = run_output.steps[0] if run_output.steps else None
    intent = Intent(
        conversation_id=conversation.id,
        message_id=user_message.id,
        intent_name=first_step.tool_id if first_step else str(run_output.visual_feedback.get("intent", "unresolved")),
        parameters=first_step.parameters if first_step else run_output.visual_feedback.get("partial_parameters", {}),
        confidence=1.0 if first_step else 0.0,
        status="ambiguous" if run_output.state == AgentState.WAITING_FOR_CLARIFICATION else (
            "rejected" if run_output.state == AgentState.FAILED else "resolved"
        ),
    )
    db.add(intent)
    await db.flush()

    run = AgentRun(
        id=run_output.run_id,
        intent_id=intent.id,
        status=run_output.state.value,
        completed_at=datetime.now(timezone.utc) if run_output.is_terminal else None,
        execution_plan={
            "version": 1,
            "session_id": auth_session.id,
            "device_id": device.id,
            "output": run_output.model_dump(mode="json"),
        },
    )
    db.add(run)
    for step in run_output.steps:
        action = Action(
            id=step.step_id,
            agent_run_id=run.id,
            tool_id=step.tool_id,
            risk_level=step.risk_level,
            status="waiting_approval" if step.requires_approval and step.status == "waiting_approval" else "pending",
            input_payload=step.parameters,
            idempotency_key=step.idempotency_key,
        )
        db.add(action)
        if step.requires_approval:
            db.add(Approval(action_id=step.step_id, required=True, status="pending"))

    db.add(AuditLog(
        user_id=current_user.id,
        actor_type="user",
        actor_id=current_user.id,
        event_type="AGENT_RUN_INITIATED",
        resource_type="agent_run",
        resource_id=run_output.run_id,
        metadata_json={
            "state": run_output.state.value,
            "steps_count": len(run_output.steps),
            "conversation_id": conversation.id,
        }
    ))
    if run_output.visual_feedback.get("type") == "policy_denial":
        db.add(AuditLog(
            user_id=current_user.id,
            device_id=device.id,
            actor_type="system",
            event_type="POLICY_DENIAL",
            resource_type="agent_run",
            resource_id=run_output.run_id,
            metadata_json={"reason": run_output.visual_feedback.get("reason")},
        ))
    await db.commit()

    return run_output

@router.post("/runs/{run_id}/confirm", response_model=AgentRunOutput)
async def confirm_run_step(
    run_id: str,
    req: ConfirmStepRequest,
    current_user: User = Depends(get_current_user),
    auth_session: AuthSession = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db)
):
    run, run_output, stored = await _load_owned_run(db, run_id, current_user)
    _require_run_session(stored, auth_session)
    device_result = await db.execute(select(Device).where(Device.id == stored["device_id"]))
    device = device_result.scalars().first()
    if not device or device.trust_status != "trusted":
        raise HTTPException(status_code=403, detail="L'appareil de cette exécution n'est plus approuvé.")
    if (
        run_output.state != AgentState.WAITING_FOR_CONFIRMATION
        or run_output.awaiting_confirmation_step_id != req.step_id
    ):
        raise HTTPException(status_code=409, detail="Cette étape n'attend pas de confirmation.")
    step = next((s for s in run_output.steps if s.step_id == req.step_id), None)
    if not step:
        raise HTTPException(status_code=404, detail="Étape à confirmer introuvable.")

    if step.requires_biometric and not req.biometric_authenticated:
        raise HTTPException(
            status_code=403,
            detail="Authentification biométrique requise pour cette action financière."
        )

    updated_step = AgentRuntime.confirm_and_execute_step(step, req.context)
    run_output.state = AgentState.READY_TO_EXECUTE
    run_output.spoken_response = "Confirmation reçue. Exécution en cours sur votre téléphone."
    run_output.awaiting_confirmation_step_id = None
    run_output.is_terminal = False
    run_output.visual_feedback = {"type": "execution_requested", "step": updated_step.model_dump()}
    approval_result = await db.execute(select(Approval).where(Approval.action_id == step.step_id))
    approval = approval_result.scalars().first()
    if approval:
        approval.status = "approved"
        approval.method = "biometric" if step.requires_biometric else "voice_or_touch"
        approval.approved_at = datetime.now(timezone.utc)
        approval.approved_by_user_id = current_user.id

    _store_run_output(run, run_output, stored)
    await _sync_action_state(db, run_output)
    db.add(AuditLog(
        user_id=current_user.id,
        actor_type="user",
        actor_id=current_user.id,
        event_type="STEP_APPROVED",
        resource_type="action",
        resource_id=step.step_id,
        metadata_json={"tool_id": step.tool_id, "risk_level": step.risk_level},
    ))
    await _record_assistant_update(db, run_output, current_user.id)
    await db.commit()

    return run_output

@router.post("/runs/{run_id}/steps/{step_id}/result", response_model=AgentRunOutput)
async def report_step_result(
    run_id: str,
    step_id: str,
    req: StepResultRequest,
    current_user: User = Depends(get_current_user),
    auth_session: AuthSession = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db),
):
    """Accept a verified observation from the device; never infer success."""
    run, output, stored = await _load_owned_run(db, run_id, current_user)
    _require_run_session(stored, auth_session)
    device_result = await db.execute(select(Device).where(Device.id == stored["device_id"]))
    device = device_result.scalars().first()
    if not device or device.trust_status != "trusted":
        raise HTTPException(status_code=403, detail="L'appareil de cette exécution n'est plus approuvé.")
    if output.is_terminal or output.state == AgentState.CANCELLED:
        raise HTTPException(status_code=409, detail="Cette exécution est déjà terminée.")

    step = next((item for item in output.steps if item.step_id == step_id), None)
    if not step:
        raise HTTPException(status_code=404, detail="Étape introuvable.")
    if any(item.status != "verified" for item in output.steps[:output.steps.index(step)]):
        raise HTTPException(status_code=409, detail="Les étapes précédentes doivent être vérifiées d'abord.")
    if step.requires_approval or step.status == "waiting_approval":
        raise HTTPException(status_code=409, detail="L'étape doit être confirmée avant son exécution.")
    if step.status in {"verified", "failed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Le résultat de cette étape a déjà été enregistré.")
    if step.status not in {"ready", "unknown"}:
        raise HTTPException(status_code=409, detail="Cette étape n'est pas prête à recevoir un résultat.")

    if req.status == "verified":
        if req.result.get("verified") is not True:
            raise HTTPException(status_code=422, detail="Une réussite doit contenir une observation vérifiée.")
    elif req.status == "failed" and not req.error:
        raise HTTPException(status_code=422, detail="Une erreur est requise pour signaler un échec.")

    step.status, step.result, step.error = req.status, req.result, req.error
    if req.status == "verified":
        if all(item.status == "verified" for item in output.steps):
            output.state = AgentState.SUCCESS
            output.spoken_response = AgentRuntime._generate_success_speech(output.steps)
            output.is_terminal = True
            output.awaiting_confirmation_step_id = None
            output.visual_feedback = {"type": "success", "steps": [item.model_dump() for item in output.steps]}
        else:
            next_approval = next(
                (
                    item for index, item in enumerate(output.steps)
                    if item.status == "waiting_approval"
                    and all(previous.status == "verified" for previous in output.steps[:index])
                ),
                None,
            )
            if next_approval:
                output.state = AgentState.WAITING_FOR_CONFIRMATION
                output.awaiting_confirmation_step_id = next_approval.step_id
                output.spoken_response = f"Voulez-vous exécuter {next_approval.tool_name} ?"
                output.visual_feedback = {
                    "type": "confirmation_sheet",
                    "step_id": next_approval.step_id,
                    "tool": next_approval.tool_name,
                    "parameters": next_approval.parameters,
                    "risk_level": next_approval.risk_level,
                    "requires_biometric": next_approval.requires_biometric,
                }
            else:
                output.state = AgentState.READY_TO_EXECUTE
                output.spoken_response = "Action suivante prête sur votre téléphone."
    elif req.status == "unknown":
        output.state, output.is_terminal = AgentState.UNKNOWN, False
        output.spoken_response = "L'action a été demandée, mais son résultat n'est pas encore confirmé."
        output.visual_feedback = {"type": "unknown", "step": step.model_dump()}
    else:
        output.state, output.is_terminal = AgentState.FAILED, True
        output.awaiting_confirmation_step_id = None
        output.spoken_response = f"Je n'ai pas pu effectuer l'opération : {req.error or 'erreur inconnue'}."
        output.visual_feedback = {"type": "step_failure", "step": step.model_dump()}
        for later_step in output.steps[output.steps.index(step) + 1:]:
            if later_step.status not in {"verified", "failed"}:
                later_step.status = "cancelled"

    db.add(AuditLog(
        user_id=current_user.id if current_user else None,
        actor_type="device",
        actor_id=None,
        event_type="STEP_RESULT_REPORTED",
        resource_type="action",
        resource_id=step_id,
        metadata_json={"tool_id": step.tool_id, "status": req.status, "error": req.error},
    ))
    if req.status == "failed":
        await db.flush()
        recent = await db.execute(select(AuditLog).where(
            AuditLog.user_id == current_user.id,
            AuditLog.event_type == "STEP_RESULT_REPORTED",
        ).order_by(desc(AuditLog.created_at)).limit(3))
        recent_logs = recent.scalars().all()
        if len(recent_logs) == 3 and all(log.metadata_json.get("status") == "failed" for log in recent_logs):
            db.add(AuditLog(
                user_id=current_user.id, actor_type="system", event_type="ANOMALY_SUSPECTED",
                resource_type="agent_run", resource_id=run_id,
                metadata_json={"reason": "three_consecutive_failed_device_actions"},
            ))
    _store_run_output(run, output, stored)
    await _sync_action_state(db, output)
    await _record_assistant_update(db, output, current_user.id)
    await db.commit()
    return output

@router.post("/runs/{run_id}/cancel", response_model=AgentRunOutput)
async def cancel_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    auth_session: AuthSession = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db)
):
    run, run_output, stored = await _load_owned_run(db, run_id, current_user)
    _require_run_session(stored, auth_session)
    if run_output.is_terminal:
        raise HTTPException(status_code=409, detail="Cette exécution est déjà terminée.")

    run_output.state = AgentState.CANCELLED
    run_output.spoken_response = "Opération annulée à votre demande."
    run_output.awaiting_confirmation_step_id = None
    run_output.is_terminal = True
    run_output.visual_feedback = {"type": "cancelled"}
    for step in run_output.steps:
        if step.status not in {"verified", "failed"}:
            step.status = "cancelled"

    audit = AuditLog(
        user_id=current_user.id,
        actor_type="user",
        actor_id=current_user.id,
        event_type="ACTION_CANCELLED",
        resource_type="agent_run",
        resource_id=run_id
    )
    db.add(audit)
    _store_run_output(run, run_output, stored)
    await _sync_action_state(db, run_output)
    await _record_assistant_update(db, run_output, current_user.id)
    await db.commit()

    return run_output

@router.get("/runs/{run_id}", response_model=AgentRunOutput)
async def get_run_status(
    run_id: str,
    current_user: User = Depends(get_current_user),
    auth_session: AuthSession = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db),
):
    _, output, stored = await _load_owned_run(db, run_id, current_user)
    _require_run_session(stored, auth_session)
    return output
