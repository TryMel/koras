import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../core/network/api_client.dart';
import '../../../domain/repositories/auth_repository.dart';
import '../../../core/platform/koras_platform_bridge.dart';

/// Section 32 & 62 — Paramètres et mode utilisateur vulnérable
class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen>
    with WidgetsBindingObserver {
  bool _vulnerableMode = false;
  bool _voiceFeedbackAlways = true;
  double _voiceSpeed = 0.85;
  String _selectedLanguage = 'Français (Côte d\'Ivoire)';
  bool _loading = true;
  bool _saving = false;
  bool _notificationListenerConnected = false;
  bool _accessibilityServiceConnected = false;
  String? _deviceId;
  String? _error;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _loadSettings();
    _refreshAndroidServices();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _refreshAndroidServices();
  }

  Future<void> _refreshAndroidServices() async {
    try {
      final status = await Future.wait([
        KorasPlatformBridge.isNotificationListenerConnected(),
        KorasPlatformBridge.isAccessibilityServiceConnected(),
      ]);
      if (mounted) {
        setState(() {
          _notificationListenerConnected = status[0];
          _accessibilityServiceConnected = status[1];
        });
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('État des services indisponible : $error')),
        );
      }
    }
  }

  Future<void> _openAndroidServiceSettings(
    Future<bool> Function() openSettings,
  ) async {
    try {
      if (!await openSettings() && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Impossible d’ouvrir les réglages Android.'),
          ),
        );
      }
    } catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ouverture des réglages impossible : $error')),
        );
      }
    }
  }

  Future<void> _loadSettings() async {
    try {
      final results = await Future.wait([
        AuthRepository().getProfile(),
        AuthRepository().listDevices(),
        KorasPlatformBridge.getDeviceInfo(),
        SharedPreferences.getInstance(),
      ]);
      final profile = results[0] as Map<String, dynamic>;
      final devices = results[1] as List<Map<String, dynamic>>;
      final deviceInfo = results[2] as Map<String, dynamic>;
      final preferences = results[3] as SharedPreferences;
      final locale = profile['locale'] as String? ?? 'fr';
      final matchingDevices = devices.where(
        (item) => item['device_identifier'] == deviceInfo['device_identifier'],
      );
      if (!mounted) return;
      setState(() {
        _vulnerableMode = profile['vulnerable_mode'] as bool? ?? false;
        _selectedLanguage = locale == 'en'
            ? 'English'
            : 'Français (Côte d\'Ivoire)';
        _deviceId = matchingDevices.isEmpty
            ? null
            : matchingDevices.first['id'] as String;
        _voiceFeedbackAlways =
            preferences.getBool('koras_voice_feedback') ?? true;
        _voiceSpeed = preferences.getDouble('koras_voice_speed') ?? 0.85;
      });
    } catch (error) {
      if (mounted) setState(() => _error = 'Paramètres indisponibles : $error');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _saveProfile(Map<String, dynamic> changes) async {
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await AuthRepository().updateProfile(changes);
    } catch (error) {
      if (mounted)
        setState(() => _error = 'Enregistrement impossible : $error');
      rethrow;
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D0D0D),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A1A2E),
        title: const Text('Paramètres', style: TextStyle(color: Colors.white)),
        elevation: 0,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_loading)
            const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: CircularProgressIndicator(),
              ),
            ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                _error!,
                style: const TextStyle(color: Colors.redAccent),
              ),
            ),
          if (_saving) const LinearProgressIndicator(),
          _buildSectionHeader('Session vocale'),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF1A1A2E),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white12),
            ),
            child: const Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.mic_none_rounded, color: Color(0xFFC3B9FF)),
                SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Écoute à la demande',
                        style: TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      SizedBox(height: 6),
                      Text(
                        'Le microphone ne s’active que lorsque vous appuyez sur le bouton vocal. Une notification reste visible pendant la session; utilisez-la pour arrêter l’écoute.',
                        style: TextStyle(
                          color: Colors.white54,
                          fontSize: 13,
                          height: 1.4,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          // Section Accessibilité & Vulnérabilité
          _buildSectionHeader('Accessibilité & Protection'),
          _buildActionTile(
            title: 'Accès aux notifications',
            subtitle: _notificationListenerConnected
                ? 'Autorisé — KORAS peut lire les notifications récentes.'
                : 'Non autorisé — requis pour demander les notifications récentes.',
            icon: Icons.notifications_active,
            color: _notificationListenerConnected
                ? Colors.greenAccent
                : Colors.white70,
            onTap: () => _openAndroidServiceSettings(
              KorasPlatformBridge.openNotificationListenerSettings,
            ),
          ),
          const SizedBox(height: 12),
          _buildActionTile(
            title: 'Service d’accessibilité',
            subtitle: _accessibilityServiceConnected
                ? 'Activé — la lecture d’écran assistée est disponible.'
                : 'Désactivé — requis pour les fonctions d’assistance à l’écran.',
            icon: Icons.accessibility_new,
            color: _accessibilityServiceConnected
                ? Colors.greenAccent
                : Colors.white70,
            onTap: () => _openAndroidServiceSettings(
              KorasPlatformBridge.openAccessibilitySettings,
            ),
          ),
          const SizedBox(height: 12),

          // Switch Mode Vulnérable (Section 62)
          SwitchListTile(
            title: const Text(
              'Mode protection renforcée',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w600,
              ),
            ),
            subtitle: const Text(
              'Vocabulaire simplifié, confirmation systématique même pour les actions mineures et délais allongés.',
              style: TextStyle(color: Colors.white54, fontSize: 13),
            ),
            value: _vulnerableMode,
            activeColor: const Color(0xFF6C63FF),
            tileColor: const Color(0xFF1A1A2E),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            onChanged: _loading
                ? null
                : (val) async {
                    final previous = _vulnerableMode;
                    setState(() => _vulnerableMode = val);
                    try {
                      await _saveProfile({'vulnerable_mode': val});
                    } catch (_) {
                      if (mounted) setState(() => _vulnerableMode = previous);
                    }
                  },
          ),
          const SizedBox(height: 12),

          // Switch Retour vocal permanent
          SwitchListTile(
            title: const Text(
              'Retour vocal systématique',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w600,
              ),
            ),
            subtitle: const Text(
              'KORAS lit oralement chaque résultat et étape d\'action.',
              style: TextStyle(color: Colors.white54, fontSize: 13),
            ),
            value: _voiceFeedbackAlways,
            activeColor: const Color(0xFF6C63FF),
            tileColor: const Color(0xFF1A1A2E),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
            onChanged: (val) async {
              setState(() => _voiceFeedbackAlways = val);
              final preferences = await SharedPreferences.getInstance();
              await preferences.setBool('koras_voice_feedback', val);
            },
          ),
          const SizedBox(height: 24),

          // Section Voix & Langue
          _buildSectionHeader('Voix et Langue'),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFF1A1A2E),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Langue d\'interaction',
                  style: TextStyle(color: Colors.white70, fontSize: 14),
                ),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  value: _selectedLanguage,
                  dropdownColor: const Color(0xFF1E1E2E),
                  style: const TextStyle(color: Colors.white, fontSize: 16),
                  decoration: InputDecoration(
                    filled: true,
                    fillColor: Colors.white10,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: BorderSide.none,
                    ),
                  ),
                  items: const [
                    DropdownMenuItem(
                      value: 'Français (Côte d\'Ivoire)',
                      child: Text('Français (Côte d\'Ivoire)'),
                    ),
                    DropdownMenuItem(value: 'English', child: Text('English')),
                  ],
                  onChanged: (val) async {
                    if (val == null) return;
                    final previous = _selectedLanguage;
                    setState(() => _selectedLanguage = val);
                    try {
                      await _saveProfile({
                        'locale': val == 'English' ? 'en' : 'fr',
                      });
                      final preferences = await SharedPreferences.getInstance();
                      await preferences.setString(
                        'koras_locale',
                        val == 'English' ? 'en' : 'fr',
                      );
                    } catch (_) {
                      if (mounted) setState(() => _selectedLanguage = previous);
                    }
                  },
                ),
                const SizedBox(height: 16),
                Text(
                  'Vitesse de la voix : ${(_voiceSpeed * 100).toInt()}%',
                  style: const TextStyle(color: Colors.white70, fontSize: 14),
                ),
                Slider(
                  value: _voiceSpeed,
                  min: 0.5,
                  max: 1.2,
                  divisions: 7,
                  activeColor: const Color(0xFF6C63FF),
                  onChanged: (val) async {
                    setState(() => _voiceSpeed = val);
                    final preferences = await SharedPreferences.getInstance();
                    await preferences.setDouble('koras_voice_speed', val);
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Section Sécurité & Confidentialité (Section 73 & 75)
          _buildSectionHeader('Sécurité & Appareil'),
          _buildActionTile(
            title: 'Révoquer cet appareil',
            subtitle:
                'Déconnecte la session et bloque toutes les actions sensibles.',
            icon: Icons.phonelink_erase,
            color: Colors.orange,
            onTap: _deviceId == null
                ? null
                : () {
                    _showRevokeDialog(context);
                  },
          ),
          const SizedBox(height: 12),
          _buildActionTile(
            title: 'Supprimer mes données KORAS',
            subtitle: 'Suppression définitive de l\'historique et des préférences (Section 75).',
            icon: Icons.delete_forever,
            color: Colors.red,
            onTap: () {
              _showDeleteDataDialog(context);
            },
          ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10, left: 4),
      child: Text(
        title.toUpperCase(),
        style: const TextStyle(
          color: Color(0xFF6C63FF),
          fontSize: 13,
          fontWeight: FontWeight.bold,
          letterSpacing: 0.8,
        ),
      ),
    );
  }

  Widget _buildActionTile({
    required String title,
    required String subtitle,
    required IconData icon,
    required Color color,
    required VoidCallback? onTap,
  }) {
    return ListTile(
      leading: CircleAvatar(
        backgroundColor: color.withOpacity(0.15),
        child: Icon(icon, color: color, size: 22),
      ),
      title: Text(
        title,
        style: TextStyle(color: color, fontWeight: FontWeight.w600),
      ),
      subtitle: Text(
        subtitle,
        style: const TextStyle(color: Colors.white54, fontSize: 12),
      ),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: color.withOpacity(0.3)),
      ),
      tileColor: const Color(0xFF1A1A2E),
      onTap: onTap,
    );
  }

  void _showRevokeDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E1E2E),
        title: const Text(
          'Révoquer l\'appareil ?',
          style: TextStyle(color: Colors.white),
        ),
        content: const Text(
          'Toutes les autorisations locales et les clés de chiffrement de cet appareil seront révoquées.',
          style: TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text(
              'Annuler',
              style: TextStyle(color: Colors.white54),
            ),
          ),
          ElevatedButton(
            onPressed: _saving
                ? null
                : () async {
                    Navigator.pop(ctx);
                    try {
                      await AuthRepository().revokeDevice(_deviceId!);
                      await ApiClient.instance.clearToken();
                      if (context.mounted) context.go('/auth');
                    } catch (error) {
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text('Révocation impossible : $error'),
                          ),
                        );
                      }
                    }
                  },
            style: ElevatedButton.styleFrom(backgroundColor: Colors.orange),
            child: const Text('Révoquer'),
          ),
        ],
      ),
    );
  }

  void _showDeleteDataDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1E1E2E),
        title: const Text(
          'Supprimer toutes les données ?',
          style: TextStyle(color: Colors.white),
        ),
        content: const Text(
          'Conformément à la politique de confidentialité (Section 75), toutes vos conversations, historiques et consentements seront effacés.',
          style: TextStyle(color: Colors.white70),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text(
              'Annuler',
              style: TextStyle(color: Colors.white54),
            ),
          ),
          ElevatedButton(
            onPressed: _saving
                ? null
                : () async {
                    Navigator.pop(ctx);
                    try {
                      await AuthRepository().deleteAccount();
                      if (context.mounted) context.go('/auth');
                    } catch (error) {
                      if (context.mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text('Suppression impossible : $error'),
                          ),
                        );
                      }
                    }
                  },
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('Supprimer définitivement'),
          ),
        ],
      ),
    );
  }
}
