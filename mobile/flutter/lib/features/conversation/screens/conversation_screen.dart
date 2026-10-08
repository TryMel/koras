import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/conversation_provider.dart';
import '../../confirmation/screens/confirmation_sheet.dart';
import '../../../domain/models/agent_models.dart';
import '../widgets/message_bubble.dart';
import '../widgets/voice_orb.dart';
import '../widgets/agent_status_bar.dart';

/// Section 32 — Écran de conversation principal
class ConversationScreen extends ConsumerStatefulWidget {
  const ConversationScreen({super.key});

  @override
  ConsumerState<ConversationScreen> createState() => _ConversationScreenState();
}

class _ConversationScreenState extends ConsumerState<ConversationScreen> {
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  @override
  void dispose() {
    _textController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final conversationState = ref.watch(conversationProvider);
    final notifier = ref.read(conversationProvider.notifier);

    // Auto-scroll on new messages
    ref.listen(conversationProvider, (_, next) {
      if (next.messages.isNotEmpty) _scrollToBottom();

      // Show confirmation sheet when agent waits for approval
      if (next.agentState == AgentState.waitingForConfirmation &&
          next.lastResult?.awaitingConfirmationStepId != null) {
        _showConfirmationSheet(context, next, notifier);
      }
    });

    return Scaffold(
      backgroundColor: const Color(0xFF0D0D0D),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A1A2E),
        elevation: 0,
        title: const Text(
          'KORAS',
          style: TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.bold,
            fontSize: 22,
          ),
        ),
        actions: [
          // Online indicator (Section 29)
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Icon(
              conversationState.isOnline ? Icons.wifi : Icons.wifi_off,
              color: conversationState.isOnline ? Colors.green : Colors.red,
              semanticLabel: conversationState.isOnline
                  ? 'Connecté'
                  : 'Hors ligne',
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Agent Status Bar (Section 30)
            AgentStatusBar(state: conversationState.agentState),

            // Messages List
            Expanded(
              child: conversationState.messages.isEmpty
                  ? _buildEmptyState()
                  : ListView.builder(
                      controller: _scrollController,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 8,
                      ),
                      itemCount: conversationState.messages.length,
                      itemBuilder: (context, index) {
                        final msg = conversationState.messages[index];
                        return MessageBubble(message: msg);
                      },
                    ),
            ),

            // Live transcript while listening
            if (conversationState.currentTranscript?.isNotEmpty == true)
              Container(
                margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white10,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  conversationState.currentTranscript!,
                  style: const TextStyle(
                    color: Colors.white60,
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ),

            if (conversationState.error != null)
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 4,
                ),
                child: Semantics(
                  liveRegion: true,
                  child: Text(
                    conversationState.error!,
                    style: const TextStyle(color: Colors.orangeAccent),
                  ),
                ),
              ),

            // Voice Orb + Text Input Row
            _buildInputArea(conversationState, notifier),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Semantics(
        label: 'Écran principal KORAS. Appuyez sur le bouton microphone pour parler.',
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.mic_none, size: 80, color: Color(0xFF6C63FF)),
            const SizedBox(height: 24),
            const Text(
              'Bonjour,\nque souhaitez-vous faire ?',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 24,
                fontWeight: FontWeight.w600,
                color: Colors.white,
                height: 1.4,
              ),
            ),
            const SizedBox(height: 16),
            const Text(
              'Appuyez sur le microphone ou tapez votre demande',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white54, fontSize: 15),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInputArea(
    ConversationState state,
    ConversationNotifier notifier,
  ) {
    final isActive =
        state.agentState == AgentState.listening ||
        state.agentState == AgentState.understanding ||
        state.agentState == AgentState.thinking ||
        state.agentState == AgentState.executing;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: const BoxDecoration(
        color: Color(0xFF1A1A2E),
        border: Border(top: BorderSide(color: Colors.white12)),
      ),
      child: Row(
        children: [
          // Text input
          Expanded(
            child: TextField(
              controller: _textController,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                hintText: 'Tapez ou parlez…',
                hintStyle: const TextStyle(color: Colors.white38),
                filled: true,
                fillColor: Colors.white10,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: BorderSide.none,
                ),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 20,
                  vertical: 14,
                ),
              ),
              onChanged: (_) => setState(() {}),
              onSubmitted: (text) {
                if (text.trim().isNotEmpty) {
                  notifier.processInput(text.trim());
                  _textController.clear();
                }
              },
            ),
          ),
          const SizedBox(width: 12),

          // Send button (text)
          if (_textController.text.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.send_rounded, color: Color(0xFF6C63FF)),
              onPressed: () {
                notifier.processInput(_textController.text.trim());
                _textController.clear();
              },
              tooltip: 'Envoyer',
            ),

          // Voice Orb (Section 32)
          VoiceOrb(
            isListening: state.isListening,
            isActive: isActive,
            onPressed: () async {
              if (state.isListening) {
                await notifier.stopListening();
              } else {
                await notifier.startListening();
              }
            },
          ),
        ],
      ),
    );
  }

  void _showConfirmationSheet(
    BuildContext context,
    ConversationState state,
    ConversationNotifier notifier,
  ) {
    if (!mounted) return;
    final result = state.lastResult;
    if (result == null) return;

    final step = result.steps.firstWhere(
      (s) => s.stepId == result.awaitingConfirmationStepId,
      orElse: () => result.steps.first,
    );

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      isDismissible: false,
      builder: (_) => ConfirmationSheet(
        step: step,
        onConfirm: notifier.confirmCurrentStep,
        onCancel: () => notifier.cancelCurrentRun(),
      ),
    );
  }
}
