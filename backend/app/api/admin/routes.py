from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.database.session import get_db
from app.database.models.models import User, Device, AuditLog, Transaction, Session
from app.core.dependencies import get_current_admin
from app.agent.agent_runtime import AgentRuntime, AgentRunOutput

router = APIRouter(
    prefix="/admin",
    tags=["Admin Portal"],
    dependencies=[Depends(get_current_admin)],
)

class SimulationRequest(BaseModel):
    simulated_query: str
    vulnerable_user: bool = False
    device_trusted: bool = True
    battery_level: int = 80
    is_offline: bool = False

@router.get("/metrics")
async def get_metrics(db: AsyncSession = Depends(get_db)):
    users = await db.scalar(select(func.count(User.id)))
    devices = await db.scalar(
        select(func.count(Device.id)).where(Device.trust_status == "trusted")
    )
    blocked_actions = await db.scalar(
        select(func.count(AuditLog.id)).where(AuditLog.event_type == "POLICY_DENIAL")
    )
    return {
        "users": users or 0,
        "trusted_devices": devices or 0,
        "policy_denials": blocked_actions or 0,
        "intent_accuracy": None,
        "false_action_rate": None,
        "metrics_note": "Les métriques de précision nécessitent un jeu d'évaluation annoté.",
    }

@router.get("/users")
async def get_all_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(User).offset(skip).limit(limit))
    users = res.scalars().all()
    return [{"id": u.id, "phone": u.phone, "display_name": u.display_name, "status": u.status, "role": u.role} for u in users]

@router.get("/devices")
async def get_all_devices(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Device).offset(skip).limit(limit))
    devices = res.scalars().all()
    return [{
        "id": d.id, "user_id": d.user_id, "device_identifier": d.device_identifier,
        "platform": d.platform, "trust_status": d.trust_status, "last_seen_at": str(d.last_seen_at)
    } for d in devices]

@router.post("/devices/{device_id}/revoke")
async def revoke_device(device_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalars().first()
    if not device:
        raise HTTPException(status_code=404, detail="Appareil introuvable.")
    if device.trust_status == "revoked":
        return {"device_id": device.id, "trust_status": "revoked"}

    device.trust_status = "revoked"
    revoked_at = datetime.now(timezone.utc)
    sessions = await db.execute(
        select(Session).where(Session.device_id == device.id, Session.status == "active")
    )
    for auth_session in sessions.scalars().all():
        auth_session.status = "terminated"
        auth_session.ended_at = revoked_at

    db.add(AuditLog(
        user_id=device.user_id,
        device_id=device.id,
        actor_type="admin",
        event_type="DEVICE_REVOKED",
        resource_type="device",
        resource_id=device.id,
    ))
    await db.commit()
    return {"device_id": device.id, "trust_status": "revoked"}

@router.get("/audit")
async def get_audit_logs(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(AuditLog).order_by(desc(AuditLog.created_at)).offset(skip).limit(limit))
    logs = res.scalars().all()
    return [{
        "id": l.id,
        "user_id": l.user_id,
        "actor_type": l.actor_type,
        "event_type": l.event_type,
        "resource_type": l.resource_type,
        "resource_id": l.resource_id,
        "metadata": l.metadata_json,
        "created_at": str(l.created_at)
    } for l in logs]

@router.get("/transactions")
async def get_transactions(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Transaction).order_by(desc(Transaction.created_at)).offset(skip).limit(limit))
    txs = res.scalars().all()
    return [{
        "id": t.id,
        "action_id": t.action_id,
        "provider": t.provider,
        "amount": t.amount,
        "currency": t.currency,
        "recipient": t.recipient,
        "idempotency_key": t.idempotency_key,
        "status": t.status,
        "provider_ref": t.provider_reference,
        "created_at": str(t.created_at)
    } for t in txs]

@router.post("/simulation/run", response_model=AgentRunOutput)
async def simulate_agent(req: SimulationRequest):
    """
    Section 69: Admin simulation environment.
    Runs simulated intent, planning, risk, and tool execution in a completely isolated sandbox.
    """
    sim_output = AgentRuntime.process_request(
        user_input=req.simulated_query,
        context={
            "battery_level": req.battery_level,
            "is_offline": req.is_offline,
            "is_simulation": True
        },
        user_vulnerable_mode=req.vulnerable_user,
        device_trusted=req.device_trusted
    )
    return sim_output
