from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.database.session import get_db
from app.database.models.models import User, Session
from app.core.security import decode_token

security = HTTPBearer(auto_error=False)

async def get_authenticated_session(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Session:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentification requise.")

    payload = decode_token(credentials.credentials)
    if not payload or not payload.get("sub") or not payload.get("sid"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session invalide ou expirée.")

    result = await db.execute(
        select(Session).where(
            Session.id == payload["sid"],
            Session.user_id == payload["sub"],
            Session.status == "active",
            Session.ended_at.is_(None),
        )
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session révoquée ou expirée.")
    return session

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not credentials:
        return None
    token = credentials.credentials
    payload = decode_token(token)
    if not payload or not payload.get("sub") or not payload.get("sid"):
        return None
    user_id = payload["sub"]
    session_result = await db.execute(
        select(Session.id).where(
            Session.id == payload["sid"],
            Session.user_id == user_id,
            Session.status == "active",
            Session.ended_at.is_(None),
        )
    )
    if session_result.scalar_one_or_none() is None:
        return None
    res = await db.execute(select(User).where(User.id == user_id, User.status == "active"))
    return res.scalars().first()

async def get_current_user(
    session: Session = Depends(get_authenticated_session),
    db: AsyncSession = Depends(get_db),
) -> User:
    result = await db.execute(select(User).where(User.id == session.user_id, User.status == "active"))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Compte inactif ou introuvable.")
    return user

async def get_current_admin(
    user: User = Depends(get_current_user)
) -> User:
    if user.role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès restreint à l'administration."
        )
    return user
