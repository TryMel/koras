from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database.session import get_db
from app.database.models.models import Device, User, AuditLog, Session as AuthSession
from app.core.dependencies import get_current_user, get_authenticated_session

router = APIRouter(prefix="/devices", tags=["Devices"])

class DeviceRegistrationRequest(BaseModel):
    device_identifier: str = Field(min_length=1, max_length=128)
    platform: str = Field(default="android", min_length=1, max_length=32)
    android_version: Optional[str] = Field(default="14", max_length=32)
    app_version: str = Field(default="1.0.0", min_length=1, max_length=32)

class DeviceResponse(BaseModel):
    id: str
    device_identifier: str
    platform: str
    android_version: Optional[str]
    app_version: str
    trust_status: str

@router.post("/register", response_model=DeviceResponse)
async def register_device(
    req: DeviceRegistrationRequest,
    current_user: User = Depends(get_current_user),
    auth_session: AuthSession = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Device).where(Device.device_identifier == req.device_identifier))
    existing = res.scalars().first()
    if existing:
        if existing.user_id != current_user.id:
            raise HTTPException(status_code=409, detail="Cet identifiant d'appareil est déjà associé à un autre compte.")
        if existing.trust_status != "trusted":
            raise HTTPException(status_code=409, detail="Cet appareil n'est pas approuvé et ne peut pas être réactivé ici.")
        existing.last_seen_at = datetime.now(timezone.utc)
        existing.platform = req.platform
        existing.android_version = req.android_version
        existing.app_version = req.app_version
        auth_session.device_id = existing.id
        db.add(AuditLog(
            user_id=current_user.id,
            device_id=existing.id,
            event_type="DEVICE_REGISTERED",
            resource_type="device",
            resource_id=existing.id,
        ))
        await db.commit()
        await db.refresh(existing)
        return existing

    device = Device(
        user_id=current_user.id,
        device_identifier=req.device_identifier,
        platform=req.platform,
        android_version=req.android_version,
        app_version=req.app_version,
        trust_status="trusted"
    )
    db.add(device)
    try:
        await db.flush()
        auth_session.device_id = device.id
        db.add(AuditLog(
            user_id=current_user.id,
            device_id=device.id,
            event_type="DEVICE_REGISTERED",
            resource_type="device",
            resource_id=device.id,
        ))
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Cet appareil est déjà enregistré.") from exc
    await db.refresh(device)
    return device

@router.get("", response_model=List[DeviceResponse])
async def list_user_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Device).where(Device.user_id == current_user.id))
    return res.scalars().all()

@router.post("/{device_id}/revoke")
async def revoke_device(
    device_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Device).where(Device.id == device_id, Device.user_id == current_user.id))
    device = res.scalars().first()
    if not device:
        raise HTTPException(status_code=404, detail="Appareil non trouvé.")

    device.trust_status = "revoked"
    sessions_result = await db.execute(
        select(AuthSession).where(AuthSession.device_id == device.id, AuthSession.status == "active")
    )
    revoked_at = datetime.now(timezone.utc)
    for auth_session in sessions_result.scalars().all():
        auth_session.status = "terminated"
        auth_session.ended_at = revoked_at

    audit = AuditLog(
        user_id=current_user.id,
        device_id=device_id,
        event_type="DEVICE_REVOKED",
        resource_type="device",
        resource_id=device_id
    )
    db.add(audit)
    await db.commit()
    return {"message": "Appareil révoqué avec succès. Toutes les actions sensibles sont désormais bloquées."}
