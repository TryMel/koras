from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database.session import get_db
from app.database.models.models import Transaction, User, Action, AgentRun, Intent, Conversation
from app.core.dependencies import get_current_user
from app.core.security import generate_idempotency_key
from app.agent.agent_runtime import AgentRuntime
from app.core.logging import logger

router = APIRouter(prefix="/transactions", tags=["Transactions"])

class TransactionPreviewRequest(BaseModel):
    amount: float = Field(gt=0, allow_inf_nan=False)
    currency: str = Field(default="XOF", min_length=3, max_length=8)
    recipient: str = Field(min_length=1, max_length=128)
    provider: str = Field(default="wave", min_length=1, max_length=64)
    context: Optional[Dict[str, Any]] = None

    @field_validator("recipient")
    @classmethod
    def validate_recipient(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Destinataire requis.")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().upper()

class TransactionPreviewResponse(BaseModel):
    transaction_id: Optional[str] = None
    idempotency_key: str
    amount: float
    currency: str
    recipient: str
    provider: str
    estimated_fee: float = 0.0
    total_amount: float
    risk_level: int = 4
    requires_biometric: bool = True
    preview_message: str
    status: str = "preview"

@router.post("/preview", response_model=TransactionPreviewResponse)
async def preview_transaction(
    req: TransactionPreviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Section 19 - Génère un aperçu de la transaction avant toute exécution.
    Aucun fonds n'est déplacé à cette étape.
    """
    fee = 0.0
    total = req.amount
    idemp_key = generate_idempotency_key()

    preview_msg = (
        f"Aperçu non exécutable : {req.amount:,.0f} {req.currency} à {req.recipient} "
        f"via {req.provider}. Aucun frais réel n'est calculé et aucun fonds ne sera déplacé."
    )

    logger.info("Non-executable financial preview generated")

    return TransactionPreviewResponse(
        idempotency_key=idemp_key,
        amount=req.amount,
        currency=req.currency,
        recipient=req.recipient,
        provider=req.provider,
        estimated_fee=fee,
        total_amount=total,
        preview_message=preview_msg,
        status="preview_only"
    )

@router.post("/{idempotency_key}/confirm")
async def confirm_transaction(
    idempotency_key: str,
    biometric_authenticated: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reject execution until an approved financial connector is configured."""
    raise HTTPException(
        status_code=503,
        detail="Aucun connecteur financier agréé n'est activé. L'aperçu ne peut pas être confirmé.",
    )

@router.get("/{transaction_id}")
async def get_transaction(
    transaction_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Transaction)
        .join(Action, Transaction.action_id == Action.id)
        .join(AgentRun, Action.agent_run_id == AgentRun.id)
        .join(Intent, AgentRun.intent_id == Intent.id)
        .join(Conversation, Intent.conversation_id == Conversation.id)
        .where(Transaction.id == transaction_id, Conversation.user_id == current_user.id)
    )
    tx = res.scalars().first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction introuvable.")

    return {
        "id": tx.id,
        "provider": tx.provider,
        "amount": tx.amount,
        "currency": tx.currency,
        "recipient": tx.recipient,
        "idempotency_key": tx.idempotency_key,
        "status": tx.status,
        "provider_reference": tx.provider_reference,
        "created_at": str(tx.created_at),
        "updated_at": str(tx.updated_at)
    }
