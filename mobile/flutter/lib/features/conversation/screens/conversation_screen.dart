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
      backgroundColor: const Color(0xFF10111D),
      appBar: AppBar(
        backgroundColor: const Color(0xFF10111D),
        elevation: 0,
        titleSpacing: 20,
        title: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                gradient: const LinearGradient(
                  colors: [Color(0xFFB8A7FF), Color(0xFF7464E8)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
              ),
              child: const Icon(
                Icons.auto_awesome,
                color: Colors.white,
                size: 20,
              ),
            ),
            const SizedBox(width: 12),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'KORAS',
                  style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                    fontSize: 17,
                    letterSpacing: 1.2,
                  ),
                ),
                Text(
                  'Votre assistant',
                  style: TextStyle(color: Color(0xFF9B9BB0), fontSize: 12),
                ),
              ],
            ),
          ],
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Center(
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 7,
                ),
                decoration: BoxDecoration(
                  color: const Color(0xFF1B1C2B),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: Colors.white.withOpacity(0.08)),
                ),
                child: Row(
                  children: [
                    Icon(
                      conversationState.isOnline ? Icons.wifi : Icons.wifi_off,
                      color: conversationState.isOnline
                          ? const Color(0xFF88D6B0)
                          : const Color(0xFFFF9A9A),
                      size: 15,
                      semanticLabel: conversationState.isOnline
                          ? 'Connecté'
                          : 'Hors ligne',
                    ),
                    const SizedBox(width: 6),
                    Text(
                      conversationState.isOnline ? 'En ligne' : 'Hors ligne',
                      style: const TextStyle(
                        color: Color(0xFFD0D0DE),
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            AgentStatusBar(state: conversationState.agentState),
            Expanded(
              child: conversationState.messages.isEmpty
                  ? _buildEmptyState()
                  : ListView.builder(
                      controller: _scrollController,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 20,
                        vertical: 12,
                      ),
                      itemCount: conversationState.messages.length,
                      itemBuilder: (context, index) => MessageBubble(
                        message: conversationState.messages[index],
                      ),
                    ),
            ),
            if (conversationState.currentTranscript?.isNotEmpty == true)
              Container(
                margin: const EdgeInsets.fromLTRB(20, 0, 20, 8),
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: const Color(0xFF242239),
                  borderRadius: BorderRadius.circular(18),
                  border: Border.all(
                    color: const Color(0xFF8174E8).withOpacity(0.35),
                  ),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.graphic_eq, color: Color(0xFFB8A7FF)),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        conversationState.currentTranscript!,
                        style: const TextStyle(
                          color: Color(0xFFE6E3F5),
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            if (conversationState.error != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
                child: Semantics(
                  liveRegion: true,
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF3A2229),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Text(
                      conversationState.error!,
                      style: const TextStyle(color: Color(0xFFFFB8B8)),
                    ),
                  ),
                ),
              ),
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
            Container(
              width: 112,
              height: 112,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: const RadialGradient(
                  colors: [Color(0xFF393353), Color(0xFF1B1B2A)],
                ),
                boxShadow: [
                  BoxShadow(
                    color: const Color(0xFF8B7AF0).withOpacity(0.18),
                    blurRadius: 34,
                    spreadRadius: 4,
                  ),
                ],
              ),
              child: const Icon(
                Icons.auto_awesome,
                size: 42,
                color: Color(0xFFC7BCFF),
              ),
            ),
            const SizedBox(height: 30),
            const Text(
              'Bonjour, que souhaitez-vous faire ?',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 25,
                fontWeight: FontWeight.w600,
                color: Color(0xFFF5F3FC),
                height: 1.35,
                letterSpacing: -0.4,
              ),
            ),
            const SizedBox(height: 12),
            const Padding(
              padding: EdgeInsets.symmetric(horizontal: 40),
              child: Text(
                'Parlez naturellement ou écrivez votre demande. Je vous accompagne étape par étape.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Color(0xFFAAA9BB),
                  fontSize: 15,
                  height: 1.55,
                ),
              ),
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
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 18),
      decoration: const BoxDecoration(color: Color(0xFF10111D)),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _textController,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                hintText: 'Écrivez votre demande…',
                hintStyle: const TextStyle(color: Color(0xFF858598)),
                filled: true,
                fillColor: const Color(0xFF1B1C2B),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(22),
                  borderSide: BorderSide.none,
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(22),
                  borderSide: BorderSide(color: Colors.white.withOpacity(0.07)),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(22),
                  borderSide: const BorderSide(color: Color(0xFF8274E8)),
                ),
                contentPadding: const EdgeInsets.symmetric(
                  horizontal: 18,
                  vertical: 16,
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

          if (_textController.text.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(left: 8),
              child: IconButton.filled(
                style: IconButton.styleFrom(
                  backgroundColor: const Color(0xFF7464E8),
                  foregroundColor: Colors.white,
                  minimumSize: const Size(48, 48),
                ),
                icon: const Icon(Icons.arrow_upward_rounded),
                onPressed: () {
                  notifier.processInput(_textController.text.trim());
                  _textController.clear();
                },
                tooltip: 'Envoyer',
              ),
            ),

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
