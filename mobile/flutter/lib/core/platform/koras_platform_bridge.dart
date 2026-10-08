import 'package:flutter/services.dart';

import '../config/app_config.dart';

/// Bridge Flutter → Kotlin via Platform Channels (Section 10.1 & 12)
class KorasPlatformBridge {
  static const MethodChannel _methodChannel = MethodChannel(
    AppConfig.methodChannelName,
  );
  static const EventChannel _eventChannel = EventChannel(
    AppConfig.eventChannelName,
  );
  static const MethodChannel _accessibilityChannel = MethodChannel(
    AppConfig.accessibilityChannelName,
  );
  static const MethodChannel _audioChannel = MethodChannel(
    AppConfig.audioChannelName,
  );

  static Stream<Map<String, dynamic>> get backgroundSessionEvents =>
      _eventChannel.receiveBroadcastStream().map(
        (event) => Map<String, dynamic>.from(event as Map),
      );

  static Future<void> startBackgroundVoiceSession() async {
    final started = await _methodChannel.invokeMethod<bool>(
      'startBackgroundVoiceSession',
    );
    if (started != true) {
      throw StateError('Le service vocal Android n’a pas démarré.');
    }
  }

  static Future<void> stopBackgroundVoiceSession() async {
    final stopped = await _methodChannel.invokeMethod<bool>(
      'stopBackgroundVoiceSession',
    );
    if (stopped != true) {
      throw StateError('Le service vocal Android ne s’est pas arrêté.');
    }
  }

  // ─── PHONE CALLS ────────────────────────────────────────────────────────────

  /// Initiate a phone call to a resolved number (Section 35 - N1)
  static Future<bool> callContact({
    required String contactName,
    String? phoneNumber,
  }) async {
    final result = await _methodChannel.invokeMethod<bool>('callContact', {
      'contactName': contactName,
      if (phoneNumber != null) 'phoneNumber': phoneNumber,
    });
    return result ?? false;
  }

  // ─── SMS ────────────────────────────────────────────────────────────────────

  /// Sends an SMS after user confirmation (Section 35 - N2)
  static Future<bool> sendSms({
    required String contactName,
    required String message,
    String? phoneNumber,
  }) async {
    final result = await _methodChannel.invokeMethod<bool>('sendSms', {
      'contactName': contactName,
      'message': message,
      if (phoneNumber != null) 'phoneNumber': phoneNumber,
    });
    return result ?? false;
  }

  // ─── APP LAUNCHER ────────────────────────────────────────────────────────────

  static Future<bool> openApp({
    required String appName,
    String? packageName,
  }) async {
    final result = await _methodChannel.invokeMethod<bool>('openApp', {
      'appName': appName,
      if (packageName != null) 'packageName': packageName,
    });
    return result ?? false;
  }

  // ─── MAPS / NAVIGATION ───────────────────────────────────────────────────────

  static Future<bool> openMaps({required String destination}) async {
    final result = await _methodChannel.invokeMethod<bool>('openMaps', {
      'destination': destination,
    });
    return result ?? false;
  }

  static Future<bool> openUrl({required String url}) async {
    return await _methodChannel.invokeMethod<bool>('openUrl', {'url': url}) ??
        false;
  }

  static Future<bool> searchWeb({required String query}) async {
    return await _methodChannel.invokeMethod<bool>('searchWeb', {
          'query': query,
        }) ??
        false;
  }

  // ─── NOTIFICATIONS ───────────────────────────────────────────────────────────

  static Future<List<Map<String, dynamic>>> readNotifications({
    int limit = 3,
  }) async {
    final result = await _methodChannel.invokeMethod<List>(
      'readNotifications',
      {'limit': limit},
    );
    if (result == null) return [];
    return result.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  static Future<bool> isNotificationListenerConnected() async {
    return await _methodChannel.invokeMethod<bool>(
          'isNotificationListenerConnected',
        ) ??
        false;
  }

  static Future<bool> openNotificationListenerSettings() async {
    return await _methodChannel.invokeMethod<bool>(
          'openNotificationListenerSettings',
        ) ??
        false;
  }

  // ─── REMINDERS ───────────────────────────────────────────────────────────────

  static Future<bool> createReminder({
    required String title,
    String? time,
  }) async {
    final result = await _methodChannel.invokeMethod<bool>('createReminder', {
      'title': title,
      if (time != null) 'time': time,
    });
    return result ?? false;
  }

  static Future<bool> createEvent({
    required String title,
    String? description,
  }) async {
    return await _methodChannel.invokeMethod<bool>('createEvent', {
          'title': title,
          if (description != null) 'description': description,
        }) ??
        false;
  }

  // ─── CONTACTS ────────────────────────────────────────────────────────────────

  static Future<List<Map<String, dynamic>>> searchContacts(String query) async {
    final result = await _methodChannel.invokeMethod<List>('searchContacts', {
      'query': query,
    });
    if (result == null) return [];
    return result.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  // ─── ACCESSIBILITY ────────────────────────────────────────────────────────────

  /// Reads visible screen content via AccessibilityService (Section 21 & 22)
  static Future<Map<String, dynamic>> readScreenContent() async {
    final result = await _accessibilityChannel.invokeMethod<Map>(
      'readScreenContent',
    );
    if (result == null) return {};
    return Map<String, dynamic>.from(result);
  }

  static Future<bool> performAccessibilityClick(String label) async {
    return await _accessibilityChannel.invokeMethod<bool>(
          'performClickByLabel',
          {'label': label},
        ) ??
        false;
  }

  static Future<bool> openAccessibilitySettings() async {
    return await _methodChannel.invokeMethod<bool>(
          'openAccessibilitySettings',
        ) ??
        false;
  }

  static Future<bool> isAccessibilityServiceConnected() async {
    return await _methodChannel.invokeMethod<bool>(
          'isAccessibilityServiceConnected',
        ) ??
        false;
  }

  // ─── AUDIO ───────────────────────────────────────────────────────────────────

  static Future<void> startListening() async {
    await _audioChannel.invokeMethod('startListening');
  }

  static Future<void> stopListening() async {
    await _audioChannel.invokeMethod('stopListening');
  }

  static Future<void> speak(String text, {String language = 'fr-FR'}) async {
    await _audioChannel.invokeMethod('speak', {
      'text': text,
      'language': language,
    });
  }

  static Future<void> stopSpeaking() async {
    await _audioChannel.invokeMethod('stopSpeaking');
  }

  // ─── BIOMETRIC ───────────────────────────────────────────────────────────────

  /// Trigger biometric authentication for critical actions (Section 24)
  static Future<bool> authenticateBiometric({
    String reason = 'Confirmer cette action',
  }) async {
    final result = await _methodChannel.invokeMethod<bool>(
      'authenticateBiometric',
      {'reason': reason},
    );
    return result ?? false;
  }

  // ─── DEVICE INFO ─────────────────────────────────────────────────────────────

  static Future<Map<String, dynamic>> getDeviceInfo() async {
    final result = await _methodChannel.invokeMethod<Map>('getDeviceInfo');
    if (result == null) return {};
    return Map<String, dynamic>.from(result);
  }

  static Future<int> getBatteryLevel() async {
    final result = await _methodChannel.invokeMethod<int>('getBatteryLevel');
    return result ?? 100;
  }

  static Future<bool> isNetworkAvailable() async {
    final result = await _methodChannel.invokeMethod<bool>(
      'isNetworkAvailable',
    );
    return result ?? true;
  }

  // ─── EVENT STREAM ────────────────────────────────────────────────────────────

  /// Stream for real-time Kotlin events (voice detection, accessibility, etc.)
  static Stream<Map<String, dynamic>> get eventStream {
    return backgroundSessionEvents;
  }
}
