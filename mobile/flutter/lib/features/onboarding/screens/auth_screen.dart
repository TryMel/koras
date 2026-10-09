import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../../core/config/app_config.dart';
import '../../../domain/repositories/auth_repository.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({super.key});
  @override State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _form = GlobalKey<FormState>();
  final _phone = TextEditingController();
  final _name = TextEditingController();
  final _password = TextEditingController();
  bool _isRegister = false;
  bool _loading = false;

  @override void dispose() { _phone.dispose(); _name.dispose(); _password.dispose(); super.dispose(); }

  Future<void> _submit() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _loading = true);
    try {
      final repository = AuthRepository();
      if (_isRegister) {
        await repository.register(phone: _phone.text.trim(), name: _name.text.trim(), password: _password.text);
      } else {
        await repository.login(phone: _phone.text.trim(), password: _password.text);
      }
      if (mounted) context.go('/home');
    } on DioException catch (error) {
      final responseData = error.response?.data;
      final detail = responseData is Map
          ? responseData['detail'] ?? responseData['message']
          : null;
      final message = detail?.toString().trim();
      final errorMessage = error.type == DioExceptionType.cancel
          ? 'Connexion annulée.'
          : message != null && message.isNotEmpty
              ? message
              : error.response == null
                  ? 'Serveur KORAS inaccessible sur ${AppConfig.baseUrl}. Vérifiez que le backend fonctionne et que cette adresse est joignable par le téléphone.'
                  : 'Le serveur KORAS a répondu avec une erreur (HTTP ${error.response?.statusCode ?? 'inconnu'}).';
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(errorMessage)));
    } finally { if (mounted) setState(() => _loading = false); }
  }

  @override Widget build(BuildContext context) => Scaffold(
    backgroundColor: const Color(0xFF0D0D0D),
    appBar: AppBar(backgroundColor: const Color(0xFF1A1A2E), title: Text(_isRegister ? 'Créer mon compte' : 'Se connecter')),
    body: SafeArea(child: Padding(padding: const EdgeInsets.all(24), child: Form(
      key: _form, child: Column(children: [
        const SizedBox(height: 24),
        if (_isRegister) TextFormField(controller: _name, style: const TextStyle(color: Colors.white), decoration: const InputDecoration(labelText: 'Votre nom'), validator: (value) => value == null || value.trim().isEmpty ? 'Nom requis' : null),
        TextFormField(controller: _phone, keyboardType: TextInputType.phone, style: const TextStyle(color: Colors.white), decoration: const InputDecoration(labelText: 'Numéro de téléphone'), validator: (value) => value == null || value.trim().length < 6 ? 'Numéro invalide' : null),
        TextFormField(controller: _password, obscureText: true, style: const TextStyle(color: Colors.white), decoration: const InputDecoration(labelText: 'Mot de passe'), validator: (value) => value == null || value.length < 8 ? '8 caractères minimum' : null),
        const SizedBox(height: 24),
        SizedBox(width: double.infinity, child: ElevatedButton(onPressed: _loading ? null : _submit, child: Text(_loading ? 'Veuillez patienter…' : (_isRegister ? 'Créer le compte' : 'Se connecter')))),
        TextButton(onPressed: () => setState(() => _isRegister = !_isRegister), child: Text(_isRegister ? 'J’ai déjà un compte' : 'Créer un compte')),
      ]),
    ))),
  );
}
