import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field

from app.agent.intent_resolver import IntentResolver, IntentResult
from app.policy.policy_engine import PolicyEngine, PolicyCheckResult
from app.risk.risk_engine import RiskEngine, RiskLevel
from app.tools.registry import tool_registry, ToolContract
from app.core.security import generate_idempotency_key

class AgentState(str, Enum):
    RECEIVED = "RECEIVED"
    UNDERSTANDING = "UNDERSTANDING"
    CONTEXT_ENRICHMENT = "CONTEXT_ENRICHMENT"
    PLANNING = "PLANNING"
    POLICY_CHECK = "POLICY_CHECK"
    RISK_ASSESSMENT = "RISK_ASSESSMENT"
    WAITING_FOR_CLARIFICATION = "WAITING_FOR_CLARIFICATION"
    WAITING_FOR_CONFIRMATION = "WAITING_FOR_CONFIRMATION"
    READY_TO_EXECUTE = "READY_TO_EXECUTE"
    EXECUTING = "EXECUTING"
    OBSERVING = "OBSERVING"
    VERIFYING = "VERIFYING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    UNKNOWN = "UNKNOWN"
    RECOVERY = "RECOVERY"

class PlannedStep(BaseModel):
    step_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_id: str
    tool_name: str
    parameters: Dict[str, Any]
    risk_level: int
    requires_approval: bool
    requires_biometric: bool = False
    idempotency_key: Optional[str] = None
    status: str = "pending"  # pending, waiting_approval, executing, verified, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class AgentRunOutput(BaseModel):
    run_id: str
    state: AgentState
    spoken_response: str
    visual_feedback: Dict[str, Any]
    conversation_id: Optional[str] = None
    steps: List[PlannedStep] = Field(default_factory=list)
    clarification_question: Optional[str] = None
    awaiting_confirmation_step_id: Optional[str] = None
    is_terminal: bool = False

class AgentRuntime:
    @staticmethod
    def process_request(
        user_input: str,
        context: Optional[Dict[str, Any]] = None,
        user_vulnerable_mode: bool = False,
        device_trusted: bool = True
    ) -> AgentRunOutput:
        """
        Executes the controlled Agent State Machine from User Input to Plan & Verification.
        """
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        ctx = context or {}
        requested_language = ctx.get("language")
        ctx["language"] = requested_language if requested_language in {"en", "fr"} else (
            IntentResolver.detect_language(user_input)
        )
        battery = ctx.get("battery_level", 80)
        is_offline = ctx.get("is_offline", False)

        # 1. RECEIVED -> 2. UNDERSTANDING
        intents = IntentResolver.resolve(user_input, ctx)
        if not intents:
            return AgentRunOutput(
                run_id=run_id,
                state=AgentState.FAILED,
                spoken_response="Je n'ai pas pu analyser votre demande.",
                visual_feedback={"type": "error", "message": "Entrée vide ou non traitable"},
                is_terminal=True
            )

        # Check for ambiguity in any resolved intent
        for intent in intents:
            if intent.is_ambiguous or intent.confidence < 0.50:
                return AgentRunOutput(
                    run_id=run_id,
                    state=AgentState.WAITING_FOR_CLARIFICATION,
                    spoken_response=intent.clarification_question or "Pouvez-vous préciser votre demande ?",
                    visual_feedback={
                        "type": "clarification",
                        "intent": intent.intent_name,
                        "question": intent.clarification_question,
                        "partial_parameters": intent.parameters
                    },
                    clarification_question=intent.clarification_question,
                    is_terminal=False
                )

        # 3. CONTEXT_ENRICHMENT & 4. PLANNING
        planned_steps: List[PlannedStep] = []
        for intent in intents:
            tool = tool_registry.get(intent.tool_id)
            if not tool:
                return AgentRunOutput(
                    run_id=run_id,
                    state=AgentState.FAILED,
                    spoken_response=f"L'outil nécessaire '{intent.tool_id}' n'est pas disponible.",
                    visual_feedback={"type": "error", "tool": intent.tool_id},
                    is_terminal=True
                )

            validation_error = tool_registry.validate_parameters(tool, intent.parameters)
            if validation_error:
                return AgentRunOutput(
                    run_id=run_id, state=AgentState.FAILED,
                    spoken_response=f"Je ne peux pas préparer cette action : {validation_error}",
                    visual_feedback={"type": "validation_error", "tool": intent.tool_id, "reason": validation_error},
                    is_terminal=True,
                )

            # 5. POLICY_CHECK
            policy_res: PolicyCheckResult = PolicyEngine.evaluate(
                action_name=intent.tool_id,
                parameters=intent.parameters,
                device_trusted=device_trusted,
                battery_level=battery,
                is_offline=is_offline,
                user_vulnerable_mode=user_vulnerable_mode
            )

            if not policy_res.allowed:
                return AgentRunOutput(
                    run_id=run_id,
                    state=AgentState.FAILED,
                    spoken_response=f"Opération refusée : {policy_res.reason}",
                    visual_feedback={"type": "policy_denial", "reason": policy_res.reason},
                    is_terminal=True
                )

            # 6. RISK_ASSESSMENT
            risk_level, risk_requires_conf, rationale = RiskEngine.assess_risk(
                tool_id=intent.tool_id,
                parameters=intent.parameters,
                user_vulnerable_mode=user_vulnerable_mode
            )

            requires_approval = policy_res.requires_approval or risk_requires_conf
            idemp_key = generate_idempotency_key() if tool.supports_idempotency else None

            step = PlannedStep(
                tool_id=intent.tool_id,
                tool_name=tool.name,
                parameters=intent.parameters,
                risk_level=risk_level.value,
                requires_approval=requires_approval,
                requires_biometric=policy_res.requires_biometric,
                idempotency_key=idemp_key,
                status="waiting_approval" if requires_approval else "ready"
            )
            planned_steps.append(step)

        # 7. Check if any planned step requires user approval
        first_approval_step = next((s for s in planned_steps if s.requires_approval), None)
        if first_approval_step:
            # Build human-friendly confirmation question
            p = first_approval_step.parameters
            if first_approval_step.tool_id == "transfer_money":
                spoken = f"Confirmez-vous l'envoi de {p.get('amount')} francs à {p.get('recipient')} ?"
            elif first_approval_step.tool_id == "call_contact":
                spoken = f"Voulez-vous appeler {p.get('contact_name')} ?"
            elif first_approval_step.tool_id == "send_sms":
                spoken = f"Voulez-vous envoyer ce SMS à {p.get('contact_name')} : « {p.get('message')} » ?"
            else:
                spoken = f"Voulez-vous exécuter {first_approval_step.tool_name} ?"

            return AgentRunOutput(
                run_id=run_id,
                state=AgentState.WAITING_FOR_CONFIRMATION,
                spoken_response=spoken,
                visual_feedback={
                    "type": "confirmation_sheet",
                    "step_id": first_approval_step.step_id,
                    "tool": first_approval_step.tool_name,
                    "parameters": p,
                    "risk_level": first_approval_step.risk_level,
                    "requires_biometric": first_approval_step.requires_biometric
                },
                steps=planned_steps,
                awaiting_confirmation_step_id=first_approval_step.step_id,
                is_terminal=False
            )

        # An Android tool is never executed by the model or by this API.  The
        # trusted mobile client executes the approved plan and reports an
        # observable result to /agent/runs/{run_id}/steps/{step_id}/result.
        # In particular, do not call a financial or device integration here.
        for step in planned_steps:
            step.status = "ready"
        return AgentRunOutput(
            run_id=run_id,
            state=AgentState.READY_TO_EXECUTE,
            spoken_response="Action prête. Exécution en cours sur votre téléphone.",
            visual_feedback={"type": "execution_requested", "language": ctx["language"], "steps": [s.model_dump() for s in planned_steps]},
            steps=planned_steps,
            is_terminal=False,
        )

    @staticmethod
    def confirm_and_execute_step(step: PlannedStep, context: Optional[Dict[str, Any]] = None) -> PlannedStep:
        """
        Called when the user clicks 'Confirmer' or gives verbal agreement / biometric auth.
        """
        step.requires_approval = False
        step.status = "ready"
        return step

    @staticmethod
    def _execute_step(step: PlannedStep, context: Dict[str, Any]) -> PlannedStep:
        """
        Deprecated safety guard. Device and partner actions are executed only by
        their approved connector, then reported through the API observation
        endpoint. Keeping an execution stub here prevents a future LLM/API path
        from silently simulating success.
        """
        step.status = "failed"
        step.error = "Exécution directe interdite : le connecteur approuvé doit rapporter le résultat observé."
        return step

    @staticmethod
    def _generate_success_speech(steps: List[PlannedStep]) -> str:
        if not steps:
            return "Aucune action n'a été exécutée."
        first = steps[0]
        if first.tool_id == "open_app":
            return f"Android a ouvert l'application {first.parameters.get('app_name')}."
        elif first.tool_id == "call_contact":
            return (
                f"Android a ouvert l'interface d'appel pour {first.parameters.get('contact_name')}. "
                "La connexion de l'appel n'est pas confirmée."
            )
        elif first.tool_id == "send_sms":
            return (
                f"Android a accepté la demande d'envoi du SMS à {first.parameters.get('contact_name')}. "
                "La livraison du message n'est pas confirmée."
            )
        elif first.tool_id == "open_maps":
            return f"Android a ouvert l'interface de navigation vers {first.parameters.get('destination')}."
        elif first.tool_id == "read_notification":
            notifs = first.result.get("notifications", [])
            if notifs:
                first_n = notifs[0]
                sender = first_n.get("sender") or first_n.get("title") or first_n.get("package") or "une application"
                text = first_n.get("text") or "sans contenu lisible"
                return f"Vous avez une notification de {sender} : {text}"
            return "Vous n'avez pas de nouvelle notification."
        elif first.tool_id == "search_contact":
            contacts = first.result.get("contacts", [])
            if contacts:
                return f"J'ai trouvé le contact {contacts[0].get('name', 'demandé')}."
            return "Je n'ai pas trouvé ce contact."
        elif first.tool_id == "create_reminder":
            return (
                f"Le formulaire de rappel « {first.parameters.get('title')} » est ouvert dans Calendrier. "
                "Enregistrez-le dans Calendrier pour le créer."
            )
        elif first.tool_id == "create_event":
            return (
                f"Le formulaire de l'événement « {first.parameters.get('title')} » est ouvert dans Calendrier. "
                "Enregistrez-le dans Calendrier pour le créer."
            )
        elif first.tool_id == "read_screen":
            return "L'écran affiche les commandes principales du téléphone."
        return "Le résultat observé par le téléphone a été enregistré."
