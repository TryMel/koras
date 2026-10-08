import 'package:dio/dio.dart';

import '../../core/network/api_client.dart';
import '../models/agent_models.dart';

class AgentRepository {
  final Dio _dio = ApiClient.instance.dio;

  /// Sends a text or voice-transcribed command to the KORAS Agent Runtime
  Future<AgentRunResult> runAgent({
    required String userInput,
    String? conversationId,
    Map<String, dynamic>? context,
    String? deviceIdentifier,
    String? language,
  }) async {
    final response = await _dio.post(
      '/agent/run',
      data: {
        'user_input': userInput,
        if (conversationId != null) 'conversation_id': conversationId,
        'context': {...?context, if (language != null) 'language': language},
        if (deviceIdentifier != null) 'device_identifier': deviceIdentifier,
      },
    );
    return AgentRunResult.fromJson(response.data as Map<String, dynamic>);
  }

  /// Confirms a specific step (user tapped "Confirmer")
  Future<AgentRunResult> confirmStep({
    required String runId,
    required String stepId,
    required bool biometricAuthenticated,
    Map<String, dynamic>? context,
  }) async {
    final response = await _dio.post(
      '/agent/runs/$runId/confirm',
      data: {
        'step_id': stepId,
        'biometric_authenticated': biometricAuthenticated,
        'context': context ?? {},
      },
    );
    return AgentRunResult.fromJson(response.data as Map<String, dynamic>);
  }

  /// Cancels an active run (Section 36 - A4)
  Future<AgentRunResult> cancelRun(String runId) async {
    final response = await _dio.post('/agent/runs/$runId/cancel');
    return AgentRunResult.fromJson(response.data as Map<String, dynamic>);
  }

  /// Gets run status (for polling unknown state - Section 103)
  Future<AgentRunResult> getRunStatus(String runId) async {
    final response = await _dio.get('/agent/runs/$runId');
    return AgentRunResult.fromJson(response.data as Map<String, dynamic>);
  }

  /// Reports the observable result returned by the Android tool. The backend
  /// will only announce success after this verified report.
  Future<AgentRunResult> reportStepResult({
    required String runId,
    required String stepId,
    required String status,
    Map<String, dynamic> result = const {},
    String? error,
  }) async {
    final response = await _dio.post(
      '/agent/runs/$runId/steps/$stepId/result',
      data: {
        'status': status,
        'result': result,
        if (error != null) 'error': error,
      },
    );
    return AgentRunResult.fromJson(response.data as Map<String, dynamic>);
  }

  /// Transaction preview (Section 19)
  Future<Map<String, dynamic>> previewTransaction({
    required double amount,
    required String currency,
    required String recipient,
    String provider = 'wave',
  }) async {
    final response = await _dio.post(
      '/transactions/preview',
      data: {
        'amount': amount,
        'currency': currency,
        'recipient': recipient,
        'provider': provider,
      },
    );
    return response.data as Map<String, dynamic>;
  }
}
