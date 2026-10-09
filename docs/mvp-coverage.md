# Couverture MVP KORAS

Ce document décrit les capacités présentes dans le code, pas une certification
ni la validation E2E de chaque parcours. Les tests API automatisés emploient
FastAPI `TestClient`; leur résultat ne prouve pas qu'une action a été exécutée
sur un téléphone.

| Exigence MVP | Implémentation |
| --- | --- |
| Voix, texte, langue, intention, paramètres, clarification, contexte | `speech_to_text`, saisie Flutter, préférence fr/en propagée au backend, `IntentResolver`, clarification multi-tour et contexte appareil/session |
| Ouvrir app, URL, Maps, navigation, web | Intent Android (`AppTool`) avec retour d’ouverture observé |
| Contacts, appel, SMS | recherche locale `ContactsContract`, permissions runtime, appel/SMS après confirmation backend |
| Notifications et messages | `NotificationListenerService` activé explicitement par l’utilisateur; les messages présents dans les notifications sont lus sans exfiltration |
| Rappels et événements | Intent calendrier Android prérempli; l’utilisateur confirme l’enregistrement dans l’application Calendrier |
| Informations système | batterie, réseau, modèle, version et identifiant Android collectés localement pour le contexte |
| Lecture/action accessible | `AccessibilityService` opt-in : lecture sémantique et clic strict par libellé, après confirmation |
| Historique, états, confirmation, annulation, répétition, erreurs, hors-ligne | API conversations/audit, états agent, feuille de confirmation, annulation, commande « répète » et erreurs typées; les nouvelles commandes sont refusées hors ligne sans prétendre à une exécution locale |
| Session vocale en arrière-plan | Écoute uniquement après appui explicite; service Android de premier plan avec notification persistante et action d’arrêt. Les permissions micro et notifications sont demandées à l’activation, pas au lancement de l’application. |
| Authentification, session, appareils | inscription/connexion JWT, sessions persistées, enregistrement/révocation d’appareil, trust check par identifiant Android |
| Permissions, validation, risque, audit, anomalie | permissions Android à l’exécution, validation des contrats d’outils, moteur de risque/politique, audit persistant et alerte après trois échecs consécutifs |

## Limites explicitement assumées par le MVP

- Les intégrations financières restent désactivées : elles sont prévues en V3 du
  CDC, après validation de partenaires autorisés.
- L’état « SMS remis » et « appel lancé » ne doit pas être interprété comme une
  livraison SMS ou une conversation effectivement aboutie. Android ne donne pas
  ces garanties via l’Intent d’appel; KORAS ne les annonce donc pas comme telles.
- La lecture des notifications et l’accessibilité exigent l’activation volontaire
  des services correspondants dans les réglages Android; l’écran Paramètres
  KORAS indique leur état et ouvre les pages Android nécessaires.
- La session vocale en arrière-plan n’est pas une écoute permanente ni un mot
  de réveil : elle démarre uniquement à la demande, affiche une notification
  persistante et peut être arrêtée depuis cette notification. Android et le
  moteur de reconnaissance peuvent interrompre une session (économie d’énergie,
  disponibilité du service vocal); le maintien garanti de l’agent ou des actions
  après la fin de la reconnaissance n’est pas couvert par ce MVP.

## Validation automatisée

- `python .\run_koras.py test` : 29 tests backend réussis lors de la dernière
  validation, couvrant l'agent, les routes API, l'authentification, les
  autorisations, le registre d'outils et le serveur MCP.
- `flutter test` : 3 tests widget réussis lors de la dernière validation.
- `flutter analyze` sur le client API et l'écran d'authentification : aucune
  erreur ni avertissement lors de la dernière validation.
- APK release ARM64 compilé avec l'URL locale `http://127.0.0.1:8016/api/v1`,
  installé par mise à jour et lancé sur un téléphone Samsung connecté en USB.
- Aucun E2E complet ni test de connexion utilisateur n'est déduit de ces
  résultats. Les permissions, intents, accès réseau depuis un téléphone,
  reconnaissance vocale en arrière-plan et actions Android doivent être
  vérifiés séparément sur un appareil.
- Un téléphone connecté en USB a reçu une réponse HTTP `200` de `/health` au
  travers d'un tunnel ADB vers l'API locale; cela valide le tunnel et la
  disponibilité de l'API, mais pas la connexion dans l'application ni
  l'inscription d'un utilisateur.
- Le portail admin et Docker Compose ne font pas partie de cette validation;
  leur démarrage et leur déploiement ne sont pas garantis par les résultats
  ci-dessus.

## Configuration réseau mobile

- Le défaut Android `10.0.2.2:8000` est destiné à l'émulateur, pas à un
  téléphone physique.
- Un téléphone Android connecté au PC par ADB peut accéder à un backend local
  via `adb reverse`; voir [le guide mobile](../mobile/flutter/README.md).
- Le dépôt ne publie pas de backend KORAS ni de compte de démonstration. Une
  utilisation sans tunnel local nécessite un backend déployé et une URL
  accessible configurée par l'utilisateur.
