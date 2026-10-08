from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database.session import get_db
from app.database.models.models import User, Device, Session
from app.core.dependencies import get_authenticated_session
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.logging import logger

router = APIRouter(prefix="/auth", tags=["Authentication"])

class RegisterRequest(BaseModel):
    phone: str = Field(min_length=6, max_length=32)
    display_name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=128)
    device_identifier: str = Field(min_length=1, max_length=128)
    android_version: Optional[str] = Field(default="14", max_length=32)

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Le mot de passe ne peut pas dépasser 72 octets.")
        return value

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Numéro de téléphone requis.")
        return value

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Nom requis.")
        return value

class LoginRequest(BaseModel):
    phone: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=1, max_length=128)
    device_identifier: Optional[str] = Field(default=None, min_length=1, max_length=128)

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Le mot de passe ne peut pas dépasser 72 octets.")
        return value

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Numéro de téléphone requis.")
        return value

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    session_id: str
    phone: str
    display_name: Optional[str]
    vulnerable_mode: bool

@router.post("/register", response_model=AuthResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    res = await db.execute(select(User).where(User.phone == req.phone))
    existing = res.scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Ce numéro de téléphone est déjà enregistré.")

    user = User(
        phone=req.phone,
        display_name=req.display_name,
        hashed_password=get_password_hash(req.password),
        status="active"
    )
    try:
        db.add(user)
        await db.flush()
        device = Device(
            user_id=user.id,
            device_identifier=req.device_identifier,
            android_version=req.android_version,
            trust_status="trusted"
        )
        db.add(device)
        await db.flush()
        auth_session = Session(user_id=user.id, device_id=device.id, authentication_level="standard")
        db.add(auth_session)
        await db.flush()
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce numéro ou cet appareil est déjà enregistré.",
        ) from exc
    await db.refresh(user)

    token = create_access_token({"sub": user.id, "sid": auth_session.id, "role": user.role})
    logger.info("User registered successfully")
    return AuthResponse(
        access_token=token,
        user_id=user.id,
        session_id=auth_session.id,
        phone=user.phone,
        display_name=user.display_name,
        vulnerable_mode=user.vulnerable_mode
    )

@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.phone == req.phone))
    user = res.scalars().first()
    if not user or not user.hashed_password or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Identifiants incorrects.")

    if user.status != "active":
        raise HTTPException(status_code=403, detail="Ce compte est suspendu ou inactif.")

    device_id = None
    if req.device_identifier:
        device_res = await db.execute(select(Device).where(
            Device.user_id == user.id, Device.device_identifier == req.device_identifier
        ))
        device = device_res.scalars().first()
        if device and device.trust_status != "trusted":
            raise HTTPException(status_code=403, detail="Cet appareil n'est plus approuvé.")
        if device:
            device_id = device.id

    auth_session = Session(user_id=user.id, device_id=device_id, authentication_level="standard")
    db.add(auth_session)
    await db.commit()
    token = create_access_token({"sub": user.id, "sid": auth_session.id, "role": user.role})
    return AuthResponse(
        access_token=token,
        user_id=user.id,
        session_id=auth_session.id,
        phone=user.phone,
        display_name=user.display_name,
        vulnerable_mode=user.vulnerable_mode
    )

@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    auth_session: Session = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db),
):
    auth_session.status = "terminated"
    auth_session.ended_at = datetime.now(timezone.utc)
    await db.commit()
