import 'package:dio/dio.dart';

import '../../core/network/api_client.dart';
import '../../core/platform/koras_platform_bridge.dart';

class AuthRepository {
  final Dio _dio = ApiClient.instance.dio;

  Future<void> register({
    required String phone,
    required String name,
    required String password,
  }) async {
    final device = await KorasPlatformBridge.getDeviceInfo();
    final identifier = _requiredDeviceIdentifier(device);
    final response = await _dio.post(
      '/auth/register',
      data: {
        'phone': phone,
        'display_name': name,
        'password': password,
        'device_identifier': identifier,
        'android_version': device['android_version']?.toString() ?? '',
      },
    );
    await ApiClient.instance.saveToken(
      (response.data as Map<String, dynamic>)['access_token'] as String,
    );
  }

  Future<void> login({required String phone, required String password}) async {
    final device = await KorasPlatformBridge.getDeviceInfo();
    final identifier = _requiredDeviceIdentifier(device);
    final response = await _dio.post(
      '/auth/login',
      data: {
        'phone': phone,
        'password': password,
        'device_identifier': identifier,
      },
    );
    await ApiClient.instance.saveToken(
      (response.data as Map<String, dynamic>)['access_token'] as String,
    );
    await registerCurrentDevice();
  }

  Future<Map<String, dynamic>> registerCurrentDevice() async {
    final device = await KorasPlatformBridge.getDeviceInfo();
    final identifier = _requiredDeviceIdentifier(device);
    final response = await _dio.post(
      '/devices/register',
      data: {
        'device_identifier': identifier,
        'platform': 'android',
        'android_version': device['android_version']?.toString() ?? '',
        'app_version': '1.0.0',
      },
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> getProfile() async {
    final response = await _dio.get('/users/me');
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<Map<String, dynamic>> updateProfile(
    Map<String, dynamic> changes,
  ) async {
    final response = await _dio.patch('/users/me', data: changes);
    return Map<String, dynamic>.from(response.data as Map);
  }

  Future<List<Map<String, dynamic>>> listDevices() async {
    final response = await _dio.get('/devices');
    return (response.data as List)
        .map((item) => Map<String, dynamic>.from(item as Map))
        .toList();
  }

  Future<void> revokeDevice(String id) async {
    await _dio.post('/devices/$id/revoke');
  }

  Future<void> deleteAccount() async {
    await _dio.delete('/users/me');
    await ApiClient.instance.clearToken();
  }

  Future<void> logout() async {
    try {
      await _dio.post('/auth/logout');
    } finally {
      await ApiClient.instance.clearToken();
    }
  }

  String _requiredDeviceIdentifier(Map<String, dynamic> device) {
    final identifier = device['device_identifier'];
    if (identifier is! String ||
        identifier.isEmpty ||
        identifier == 'unknown') {
      throw StateError(
        'Identifiant Android indisponible; appareil non enregistré.',
      );
    }
    return identifier;
  }
}
