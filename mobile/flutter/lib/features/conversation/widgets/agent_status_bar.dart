import 'package:flutter/material.dart';

import '../../../domain/models/agent_models.dart';

class AgentStatusBar extends StatelessWidget {
  final AgentState state;

  const AgentStatusBar({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    final config = _configFor(state);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      color: const Color(0xFF1B1C2B),
      child: Semantics(
        label: 'État de KORAS: ${config.label}',
        liveRegion: true,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(config.icon, color: config.color, size: 16),
            const SizedBox(width: 8),
            Text(
              config.label,
              style: TextStyle(
                color: config.color,
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
            if (config.showPulse) ...[
              const Spacer(),
              _PulseIndicator(color: config.color),
            ],
          ],
        ),
      ),
    );
  }

  _StatusConfig _configFor(AgentState state) {
    switch (state) {
      case AgentState.idle:
        return _StatusConfig(
          const Color(0xFFB3B2C1),
          Icons.radio_button_unchecked,
          'Prêt',
        );
      case AgentState.listening:
        return _StatusConfig(
          const Color(0xFFFF929C),
          Icons.mic,
          'À l\'écoute…',
          showPulse: true,
        );
      case AgentState.understanding:
        return _StatusConfig(
          const Color(0xFF91B9FF),
          Icons.psychology,
          'Analyse de la demande…',
          showPulse: true,
        );
      case AgentState.thinking:
        return _StatusConfig(
          const Color(0xFFB8A7FF),
          Icons.auto_awesome,
          'Planification…',
          showPulse: true,
        );
      case AgentState.waitingForClarification:
        return _StatusConfig(
          const Color(0xFFFFC078),
          Icons.help_outline,
          'Précision requise',
        );
      case AgentState.waitingForConfirmation:
        return _StatusConfig(
          const Color(0xFFFFD479),
          Icons.verified_user_outlined,
          'En attente de confirmation',
        );
      case AgentState.executing:
        return _StatusConfig(
          const Color(0xFF7DD3E8),
          Icons.play_circle_outline,
          'Exécution en cours…',
          showPulse: true,
        );
      case AgentState.verifying:
        return _StatusConfig(
          const Color(0xFF78D9D0),
          Icons.check_circle_outline,
          'Vérification…',
          showPulse: true,
        );
      case AgentState.success:
        return _StatusConfig(
          const Color(0xFF88D6B0),
          Icons.check_circle,
          'Succès',
        );
      case AgentState.partialSuccess:
        return _StatusConfig(
          const Color(0xFFC4D889),
          Icons.check_circle_outline,
          'Succès partiel',
        );
      case AgentState.failed:
        return _StatusConfig(
          const Color(0xFFFF929C),
          Icons.error_outline,
          'Échec',
        );
      case AgentState.unknown:
        return _StatusConfig(
          const Color(0xFFB3B2C1),
          Icons.help,
          'État inconnu',
        );
      case AgentState.offline:
        return _StatusConfig(
          const Color(0xFFFFC078),
          Icons.wifi_off,
          'Hors ligne',
        );
      case AgentState.permissionDenied:
        return _StatusConfig(
          const Color(0xFFFF929C),
          Icons.block,
          'Permission refusée',
        );
      case AgentState.cancelled:
        return _StatusConfig(
          const Color(0xFFB3B2C1),
          Icons.cancel_outlined,
          'Annulé',
        );
      case AgentState.timedOut:
        return _StatusConfig(
          const Color(0xFFFFA57D),
          Icons.timer_off,
          'Délai dépassé',
        );
    }
  }
}

class _StatusConfig {
  final Color color;
  final IconData icon;
  final String label;
  final bool showPulse;

  const _StatusConfig(
    this.color,
    this.icon,
    this.label, {
    this.showPulse = false,
  });
}

class _PulseIndicator extends StatefulWidget {
  final Color color;
  const _PulseIndicator({required this.color});

  @override
  State<_PulseIndicator> createState() => _PulseIndicatorState();
}

class _PulseIndicatorState extends State<_PulseIndicator>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat(reverse: true);
    _anim = Tween<double>(begin: 0.3, end: 1.0).animate(_ctrl);
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _anim,
      child: Container(
        width: 8,
        height: 8,
        decoration: BoxDecoration(color: widget.color, shape: BoxShape.circle),
      ),
    );
  }
}
