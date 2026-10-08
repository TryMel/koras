import 'package:flutter/material.dart';

import '../../../domain/models/agent_models.dart';

/// Section 32 — Confirmation screen
/// Section 3.1 & 19 — LLM cannot bypass this screen for critical actions
class ConfirmationSheet extends StatefulWidget {
  final PlannedStepModel step;
  final Future<bool> Function() onConfirm;
  final VoidCallback onCancel;

  const ConfirmationSheet({
    super.key,
    required this.step,
    required this.onConfirm,
    required this.onCancel,
  });

  @override
  State<ConfirmationSheet> createState() => _ConfirmationSheetState();
}

class _ConfirmationSheetState extends State<ConfirmationSheet> {
  bool _isLoading = false;

  bool get _isCritical => widget.step.riskLevel >= 4;
  bool get _requiresBiometric => widget.step.requiresBiometric;

  Color get _riskColor {
    switch (widget.step.riskLevel) {
      case 4:
        return const Color(0xFFFF929C);
      case 3:
        return const Color(0xFFFFC078);
      case 2:
        return const Color(0xFFFFD479);
      default:
        return const Color(0xFF88D6B0);
    }
  }

  String get _riskLabel {
    switch (widget.step.riskLevel) {
      case 4:
        return 'ACTION CRITIQUE';
      case 3:
        return 'ACTION SENSIBLE';
      case 2:
        return 'CONFIRMATION REQUISE';
      default:
        return 'CONFIRMATION';
    }
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.step.parameters;

    return Semantics(
      label:
          'Fenêtre de confirmation. $_riskLabel. Vérifiez les détails avant de confirmer.',
      child: Container(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.9,
        ),
        decoration: const BoxDecoration(
          color: Color(0xFF191A29),
          borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
        ),
        padding: EdgeInsets.only(
          left: 24,
          right: 24,
          top: 20,
          bottom: MediaQuery.of(context).viewInsets.bottom + 32,
        ),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Handle
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: const Color(0xFF77788A),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 20),

              // Risk badge
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: _riskColor.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: _riskColor.withOpacity(0.42)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.shield_outlined, color: _riskColor, size: 16),
                    const SizedBox(width: 6),
                    Text(
                      _riskLabel,
                      style: TextStyle(
                        color: _riskColor,
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),

              // Action title
              Text(
                widget.step.toolName,
                style: const TextStyle(
                  color: const Color(0xFFF5F3FC),
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                ),
              ),
              const SizedBox(height: 20),

              // Parameters display
              _buildDetailsCard(p),
              const SizedBox(height: 24),

              // Biometric notice
              if (_requiresBiometric)
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFF34281D),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: const Color(0xFFFFC078).withOpacity(0.4),
                    ),
                  ),
                  child: const Row(
                    children: [
                      Icon(
                        Icons.fingerprint,
                        color: Color(0xFFFFC078),
                        size: 20,
                      ),
                      SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'Votre empreinte digitale ou Face ID sera requis pour confirmer.',
                          style: TextStyle(
                            color: Color(0xFFFFD6A1),
                            fontSize: 13,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

              if (_requiresBiometric) const SizedBox(height: 20),

              // Non-reversible warning
              if (_isCritical)
                const Padding(
                  padding: EdgeInsets.only(bottom: 20),
                  child: Row(
                    children: [
                      Icon(
                        Icons.warning_amber_rounded,
                        color: Color(0xFFFF929C),
                        size: 16,
                      ),
                      SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Cette action ne peut pas être annulée une fois exécutée.',
                          style: TextStyle(
                            color: Color(0xFFFFB8BE),
                            fontSize: 12,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

              // Cancel button
              SizedBox(
                width: double.infinity,
                height: 52,
                child: OutlinedButton(
                  onPressed: _isLoading
                      ? null
                      : () {
                          widget.onCancel();
                          Navigator.pop(context);
                        },
                  style: OutlinedButton.styleFrom(
                    foregroundColor: const Color(0xFFF5F3FC),
                    side: const BorderSide(color: Color(0xFF55566A)),
                    backgroundColor: const Color(0xFF222333),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  child: const Text('Annuler', style: TextStyle(fontSize: 16)),
                ),
              ),
              const SizedBox(height: 12),

              // Confirm button
              SizedBox(
                width: double.infinity,
                height: 56,
                child: ElevatedButton(
                  onPressed: _isLoading ? null : _handleConfirm,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: _isCritical
                        ? const Color(0xFFD9586D)
                        : const Color(0xFF7464E8),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                    textStyle: const TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  child: _isLoading
                      ? const SizedBox(
                          width: 24,
                          height: 24,
                          child: CircularProgressIndicator(
                            color: Colors.white,
                            strokeWidth: 2,
                          ),
                        )
                      : Text(
                          _requiresBiometric
                              ? 'Confirmer avec biométrie'
                              : 'Confirmer',
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDetailsCard(Map<String, dynamic> p) {
    final entries = p.entries
        .where((e) => e.value != null && e.value.toString().isNotEmpty)
        .toList();
    if (entries.isEmpty) return const SizedBox.shrink();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF222333),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.07)),
      ),
      child: Column(
        children: entries
            .map(
              (e) => _DetailRow(
                label: _labelFor(e.key),
                value: e.value.toString(),
              ),
            )
            .toList(),
      ),
    );
  }

  String _labelFor(String key) {
    const map = {
      'amount': 'Montant',
      'currency': 'Devise',
      'recipient': 'Destinataire',
      'provider': 'Opérateur',
      'contact_name': 'Contact',
      'message': 'Message',
      'destination': 'Destination',
      'title': 'Titre',
      'app_name': 'Application',
    };
    return map[key] ?? key;
  }

  Future<void> _handleConfirm() async {
    setState(() => _isLoading = true);
    try {
      final confirmed = await widget.onConfirm();
      if (confirmed && mounted) Navigator.pop(context);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;

  const _DetailRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: const TextStyle(color: Color(0xFFA5A5B7), fontSize: 14),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(
                color: const Color(0xFFF5F3FC),
                fontSize: 15,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
