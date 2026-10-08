from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database.session import get_db
from app.database.models.models import Conversation, Message, User
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/conversations", tags=["Conversations"])

class CreateConversationRequest(BaseModel):
    title: Optional[str] = Field(default="Nouvelle conversation", max_length=256)

class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=8000)
    content_type: str = Field(default="text", pattern="^(text|audio_transcript|system_notice)$")
    language: str = Field(default="fr", min_length=2, max_length=16)

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    content_type: str
    language: str
    created_at: str

class ConversationResponse(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    messages: List[MessageResponse] = Field(default_factory=list)

@router.post("", response_model=ConversationResponse)
async def create_conversation(
    req: CreateConversationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    conv = Conversation(
        user_id=current_user.id,
        title=req.title or "Nouvelle conversation"
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        created_at=str(conv.created_at),
        updated_at=str(conv.updated_at),
        messages=[]
    )

@router.post("/{conversation_id}/messages")
async def add_message(
    conversation_id: str,
    req: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conv = res.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")

    message = Message(
        conversation_id=conversation_id,
        role="user",
        content=req.content,
        content_type=req.content_type,
        language=req.language
    )
    conv.updated_at = datetime.now(timezone.utc)
    db.add(message)
    await db.commit()
    await db.refresh(message)

    return MessageResponse(
        id=message.id,
        role=message.role,
        content=message.content,
        content_type=message.content_type,
        language=message.language,
        created_at=str(message.created_at)
    )

@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conv = res.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")

    msgs_res = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    msgs = msgs_res.scalars().all()

    return ConversationResponse(
        id=conv.id,
        title=conv.title,
        created_at=str(conv.created_at),
        updated_at=str(conv.updated_at),
        messages=[
            MessageResponse(
                id=m.id,
                role=m.role,
                content=m.content,
                content_type=m.content_type,
                language=m.language,
                created_at=str(m.created_at)
            ) for m in msgs
        ]
    )

@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == current_user.id)
        .order_by(desc(Conversation.updated_at))
        .offset(skip)
        .limit(limit)
    )
    convs = res.scalars().all()
    return [
        ConversationResponse(
            id=c.id,
            title=c.title,
            created_at=str(c.created_at),
            updated_at=str(c.updated_at)
        )
        for c in convs
    ]

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Section 75 - Droit à la suppression des données."""
    res = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == current_user.id
        )
    )
    conv = res.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation introuvable.")
    await db.delete(conv)
    await db.commit()
    return {"message": "Conversation et tous ses messages supprimés."}
