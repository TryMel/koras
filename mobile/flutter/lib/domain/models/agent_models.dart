/// Section 30 — All possible KORAS agent states
enum AgentState {
  idle,
  listening,
  understanding,
  thinking,
  waitingForClarification,
  waitingForConfirmation,
  executing,
  verifying,
  success,
  partialSuccess,
  failed,
  unknown,
  offline,
  permissionDenied,
  cancelled,
  timedOut,
}

/// Section 18 — Risk levels
enum RiskLevel {
  level0Read,
  level1LocalReversible,
  level2External,
  level3Sensitive,
  level4Critical,
}

class PlannedStepModel {
  final String stepId;
  final String toolId;
  final String toolName;
  final Map<String, dynamic> parameters;
  final int riskLevel;
  final bool requiresApproval;
  final bool requiresBiometric;
  final String? idempotencyKey;
  final String status;
  final Map<String, dynamic>? result;
  final String? error;

  const PlannedStepModel({
    required this.stepId,
    required this.toolId,
    required this.toolName,
    required this.parameters,
    required this.riskLevel,
    required this.requiresApproval,
    this.requiresBiometric = false,
    this.idempotencyKey,
    this.status = 'pending',
    this.result,
    this.error,
  });

  factory PlannedStepModel.fromJson(Map<String, dynamic> json) {
    return PlannedStepModel(
      stepId: json['step_id'] as String,
      toolId: json['tool_id'] as String,
      toolName: json['tool_name'] as String,
      parameters: Map<String, dynamic>.from(json['parameters'] as Map),
      riskLevel: json['risk_level'] as int,
      requiresApproval: json['requires_approval'] as bool,
      requiresBiometric: json['requires_biometric'] as bool? ?? false,
      idempotencyKey: json['idempotency_key'] as String?,
      status: json['status'] as String? ?? 'pending',
      result: json['result'] != null
          ? Map<String, dynamic>.from(json['result'] as Map)
          : null,
      error: json['error'] as String?,
    );
  }
}

class AgentRunResult {
  final String runId;
  final AgentState state;
  final String spokenResponse;
  final Map<String, dynamic> visualFeedback;
  final List<PlannedStepModel> steps;
  final String? conversationId;
  final String? clarificationQuestion;
  final String? awaitingConfirmationStepId;
  final bool isTerminal;

  const AgentRunResult({
    required this.runId,
    required this.state,
    required this.spokenResponse,
    required this.visualFeedback,
    this.steps = const [],
    this.conversationId,
    this.clarificationQuestion,
    this.awaitingConfirmationStepId,
    this.isTerminal = false,
  });

  factory AgentRunResult.fromJson(Map<String, dynamic> json) {
    final stateStr = json['state'] as String;
    final state = _parseState(stateStr);

    final stepsRaw = json['steps'] as List? ?? [];
    final steps = stepsRaw
        .map((s) => PlannedStepModel.fromJson(s as Map<String, dynamic>))
        .toList();

    return AgentRunResult(
      runId: json['run_id'] as String,
      state: state,
      spokenResponse: json['spoken_response'] as String,
      visualFeedback: Map<String, dynamic>.from(json['visual_feedback'] as Map),
      steps: steps,
      conversationId: json['conversation_id'] as String?,
      clarificationQuestion: json['clarification_question'] as String?,
      awaitingConfirmationStepId:
          json['awaiting_confirmation_step_id'] as String?,
      isTerminal: json['is_terminal'] as bool? ?? false,
    );
  }

  static AgentState _parseState(String s) {
    switch (s) {
      case 'RECEIVED':
        return AgentState.understanding;
      case 'UNDERSTANDING':
        return AgentState.understanding;
      case 'PLANNING':
        return AgentState.thinking;
      case 'WAITING_FOR_CLARIFICATION':
        return AgentState.waitingForClarification;
      case 'WAITING_FOR_CONFIRMATION':
        return AgentState.waitingForConfirmation;
      case 'READY_TO_EXECUTE':
        return AgentState.executing;
      case 'EXECUTING':
        return AgentState.executing;
      case 'VERIFYING':
        return AgentState.verifying;
      case 'SUCCESS':
        return AgentState.success;
      case 'FAILED':
        return AgentState.failed;
      case 'CANCELLED':
        return AgentState.cancelled;
      case 'UNKNOWN':
        return AgentState.unknown;
      default:
        return AgentState.idle;
    }
  }
}
