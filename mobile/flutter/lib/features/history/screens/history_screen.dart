import 'package:flutter/material.dart';
import 'package:dio/dio.dart';

import '../../../domain/repositories/conversation_repository.dart';

/// Displays persisted API history; no sample actions are shown as real data.
class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});
  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  final _repository = ConversationRepository();
  late Future<List<Map<String, dynamic>>> _history;
  @override
  void initState() {
    super.initState();
    _history = _repository.list();
  }

  Future<void> _refresh() async {
    setState(() => _history = _repository.list());
    await _history;
  }

  Future<void> _openConversation(String id) async {
    try {
      final conversation = await _repository.get(id);
      if (!mounted) return;
      await showModalBottomSheet<void>(
        context: context,
        isScrollControlled: true,
        backgroundColor: const Color(0xFF1A1A2E),
        builder: (context) {
          final messages = conversation['messages'] as List? ?? [];
          return SafeArea(
            child: SizedBox(
              height: MediaQuery.sizeOf(context).height * 0.75,
              child: Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Text(
                      conversation['title']?.toString() ?? 'Conversation',
                      style: const TextStyle(color: Colors.white, fontSize: 20),
                    ),
                  ),
                  Expanded(
                    child: ListView.builder(
                      padding: const EdgeInsets.all(16),
                      itemCount: messages.length,
                      itemBuilder: (context, index) {
                        final message = Map<String, dynamic>.from(
                          messages[index] as Map,
                        );
                        return ListTile(
                          title: Text(
                            message['role'] == 'user' ? 'Vous' : 'KORAS',
                            style: const TextStyle(color: Color(0xFF9D97FF)),
                          ),
                          subtitle: Text(
                            message['content']?.toString() ?? '',
                            style: const TextStyle(color: Colors.white),
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      );
    } on DioException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              error.response?.data['detail']?.toString() ??
                  'Conversation indisponible.',
            ),
          ),
        );
      }
    }
  }

  Future<void> _deleteConversation(String id) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Supprimer cette conversation ?'),
        content: const Text('Cette suppression est définitive.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Annuler'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Supprimer'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _repository.delete(id);
      await _refresh();
    } on DioException catch (error) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              error.response?.data['detail']?.toString() ??
                  'Suppression impossible.',
            ),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    backgroundColor: const Color(0xFF0D0D0D),
    appBar: AppBar(
      backgroundColor: const Color(0xFF1A1A2E),
      title: const Text('Historique'),
    ),
    body: FutureBuilder<List<Map<String, dynamic>>>(
      future: _history,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done)
          return const Center(child: CircularProgressIndicator());
        if (snapshot.hasError)
          return Center(
            child: Text(
              'Historique indisponible : ${snapshot.error}',
              style: const TextStyle(color: Colors.white70),
            ),
          );
        final items = snapshot.data ?? [];
        if (items.isEmpty)
          return const Center(
            child: Text(
              'Aucune action enregistrée.',
              style: TextStyle(color: Colors.white70),
            ),
          );
        return RefreshIndicator(
          onRefresh: _refresh,
          child: ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: items.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (_, index) {
              final item = items[index];
              return ListTile(
                tileColor: const Color(0xFF1A1A2E),
                leading: const Icon(Icons.history, color: Color(0xFF6C63FF)),
                title: Text(
                  item['title']?.toString() ?? 'Conversation',
                  style: const TextStyle(color: Colors.white),
                ),
                subtitle: Text(
                  item['updated_at']?.toString() ?? '',
                  style: const TextStyle(color: Colors.white54),
                ),
                onTap: () => _openConversation(item['id'] as String),
                trailing: IconButton(
                  tooltip: 'Supprimer la conversation',
                  icon: const Icon(
                    Icons.delete_outline,
                    color: Colors.redAccent,
                  ),
                  onPressed: () => _deleteConversation(item['id'] as String),
                ),
              );
            },
          ),
        );
      },
    ),
  );
}
