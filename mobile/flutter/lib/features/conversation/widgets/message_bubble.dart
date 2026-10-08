import 'package:flutter/material.dart';

import '../providers/conversation_provider.dart';

class MessageBubble extends StatelessWidget {
  final ChatMessage message;

  const MessageBubble({super.key, required this.message});

  bool get _isUser => message.role == 'user';

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: _isUser
          ? 'Vous avez dit: ${message.content}'
          : 'KORAS a dit: ${message.content}',
      child: Align(
        alignment: _isUser ? Alignment.centerRight : Alignment.centerLeft,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 6),
          constraints: BoxConstraints(
            maxWidth: MediaQuery.of(context).size.width * 0.78,
          ),
          decoration: BoxDecoration(
            color: _isUser ? const Color(0xFF7464E8) : const Color(0xFF1B1C2B),
            borderRadius: BorderRadius.only(
              topLeft: const Radius.circular(20),
              topRight: const Radius.circular(20),
              bottomLeft: const Radius.circular(20),
              bottomRight: _isUser
                  ? const Radius.circular(7)
                  : const Radius.circular(20),
            ),
            border: _isUser
                ? null
                : Border.all(color: Colors.white.withOpacity(0.07)),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (!_isUser)
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    CircleAvatar(
                      radius: 10,
                      backgroundColor: const Color(0xFF7464E8),
                      child: const Icon(
                        Icons.auto_awesome,
                        color: Colors.white,
                        size: 11,
                      ),
                    ),
                    const SizedBox(width: 7),
                    Text(
                      'KORAS',
                      style: TextStyle(
                        color: const Color(0xFFC3B9FF),
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 0.8,
                      ),
                    ),
                  ],
                ),
              if (!_isUser) const SizedBox(height: 6),
              Text(
                message.content,
                style: TextStyle(
                  color: const Color(0xFFF0EFF7),
                  fontSize: 16,
                  height: 1.55,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                _formatTime(message.createdAt),
                style: const TextStyle(color: Color(0xFF9897AA), fontSize: 11),
              ),
            ],
          ),
        ),
      ),
    );
  }

  String _formatTime(DateTime dt) {
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }
}
