import 'package:flutter/foundation.dart';

class AppConfig {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: kIsWeb
        ? 'http://127.0.0.1:8000/api/v1'
        : 'http://10.0.2.2:8000/api/v1',
  );

  static const String appName = 'KORAS';
  static const String version = '1.0.0';

  // Agent constraints (mirrors backend Section 66)
  static const int maxAgentStepTimeoutMs = 60000;
  static const double clarificationThreshold = 0.50;
  static const double confidenceThreshold = 0.75;

  // Platform channels (matching Kotlin side)
  static const String methodChannelName = 'com.koras.koras_mobile/methods';
  static const String eventChannelName = 'com.koras.koras_mobile/events';
  static const String accessibilityChannelName =
      'com.koras.koras_mobile/accessibility';
  static const String audioChannelName = 'com.koras.koras_mobile/audio';
}
