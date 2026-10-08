import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:koras_mobile/main.dart';
import 'package:koras_mobile/domain/models/agent_models.dart';
import 'package:koras_mobile/features/confirmation/screens/confirmation_sheet.dart';
import 'package:koras_mobile/features/conversation/widgets/voice_orb.dart';

void main() {
  testWidgets('KORAS app launches smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: KorasApp()));
    await tester.pumpAndSettle();
    expect(find.textContaining('KORAS'), findsWidgets);
  });

  testWidgets('voice control describes and triggers an explicit session', (
    WidgetTester tester,
  ) async {
    var started = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: VoiceOrb(
            isListening: false,
            isActive: false,
            onPressed: () => started = true,
          ),
        ),
      ),
    );

    expect(find.byTooltip('Démarrer une session vocale'), findsOneWidget);
    await tester.tap(find.byTooltip('Démarrer une session vocale'));
    expect(started, isTrue);
  });

  testWidgets('confirmation preserves action details and safety controls', (
    WidgetTester tester,
  ) async {
    final step = PlannedStepModel(
      stepId: 'step-1',
      toolId: 'transfer_money',
      toolName: 'Transfert',
      parameters: const {'amount': 5000, 'currency': 'XOF'},
      riskLevel: 4,
      requiresApproval: true,
      requiresBiometric: true,
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ConfirmationSheet(
            step: step,
            onConfirm: () async => false,
            onCancel: () {},
          ),
        ),
      ),
    );

    expect(find.text('ACTION CRITIQUE'), findsOneWidget);
    expect(find.text('Transfert'), findsOneWidget);
    expect(find.text('5000'), findsOneWidget);
    expect(find.text('XOF'), findsOneWidget);
    expect(find.text('Montant'), findsOneWidget);
    expect(find.text('Confirmer avec biométrie'), findsOneWidget);
    expect(find.text('Annuler'), findsOneWidget);
    expect(
      find.text('Cette action ne peut pas être annulée une fois exécutée.'),
      findsOneWidget,
    );
  });
}
