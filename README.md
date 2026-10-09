# KORAS

KORAS est un prototype en développement composé d’une application Android
(Flutter/Kotlin), d’une API FastAPI, d’un portail d’administration Next.js et
d’un serveur MCP. L’application permet d’exprimer des demandes par texte ou
voix et de préparer certaines actions Android avec des confirmations selon le
risque.

**Ce dépôt ne fournit ni API hébergée, ni compte de démonstration, ni service de
production.** Pour utiliser l’application, il faut démarrer ou déployer son
propre backend et configurer l’URL correspondante dans le build mobile. Les
connecteurs financiers restent désactivés. L’utilisation réelle des permissions
et des actions Android doit être vérifiée sur un appareil; les tests automatisés
ne sont pas une certification de sécurité ni un test E2E complet.

## Composants

- `mobile/flutter/` : client Android Flutter et intégrations natives Kotlin.
- `backend/` : API FastAPI et logique d’agent; SQLite est la base locale par
  défaut.
- `admin/` : portail d’administration Next.js.
- `mcp/` : serveur MCP en transport stdio.
- `tests/backend/` et `mobile/flutter/test/` : tests automatisés backend et
  Flutter.
- `docker-compose.yml` : configuration de développement PostgreSQL, Redis,
  API et portail admin.

Redis est configuré dans Docker Compose; cela ne signifie pas que toutes les
fonctionnalités de l’API en dépendent. En mode local, le backend utilise SQLite.

## Prérequis

- Python compatible avec `backend/requirements.txt`
- Flutter et Android SDK (pour le client Android)
- Node.js et npm (pour le portail admin)
- Docker Compose uniquement si l’on choisit le démarrage Docker

## Tests

Depuis la racine du dépôt :

```powershell
python -m pip install -r backend/requirements.txt
python .\run_koras.py test
```

Pour les tests Flutter :

```powershell
Set-Location .\mobile\flutter
flutter pub get
flutter test
```

Ces tests sont automatisés; ils ne remplacent pas les essais des permissions,
services Android, actions sur appareil ou du parcours complet client/API.

## Démarrer l’API localement

Depuis la racine du dépôt :

```powershell
$env:KORAS_HOST = "127.0.0.1"
$env:KORAS_PORT = "8016"
python .\run_koras.py backend
```

Le lancement local écoute sur la boucle locale pour éviter d’exposer l’API au
réseau. Le port par défaut est `8000`; `KORAS_HOST` et `KORAS_PORT` permettent
de choisir une adresse et un port disponibles. L’API est accessible sur
`http://127.0.0.1:8016`, sa documentation de développement sur
`http://127.0.0.1:8016/docs` et son contrôle de santé sur
`http://127.0.0.1:8016/health`. Le chemin `/health` vérifie également l’accès à
la base.

La base SQLite locale est créée dans `backend/koras.db`. Ne partagez pas cette
base : elle peut contenir des comptes et des données locales. Pour une
installation durable ou multi-utilisateur, configurez une base et des secrets
adaptés au déploiement au lieu d’utiliser la configuration de développement.

## Connecter l’application Android

Une compilation Android utilise par défaut `http://10.0.2.2:8000/api/v1`,
adresse réservée à l’émulateur Android; elle ne convient pas à un téléphone
physique. Le build mobile ne contient pas d’URL de backend hébergée par KORAS.

### Émulateur Android

Démarrez le backend, puis lancez l’application en remplaçant `8016` par le port
choisi :

```powershell
Set-Location .\mobile\flutter
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8016/api/v1
```

### Téléphone physique relié en USB

Le tunnel ADB transfère uniquement le port local du PC vers le téléphone; il
nécessite que le backend tourne et que le téléphone reste relié en USB :

```powershell
adb reverse tcp:8016 tcp:8016
Set-Location .\mobile\flutter
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8016/api/v1
```

Pour générer un APK de développement avec cette configuration :

```powershell
flutter build apk --release --dart-define=API_BASE_URL=http://127.0.0.1:8016/api/v1
```

Une URL `127.0.0.1` dans l’APK ne fonctionne que lorsqu’un tunnel local approprié
est actif. Pour distribuer l’application sans tunnel, déployez vous-même une
API joignable par les utilisateurs, configurez son URL HTTPS dans
`API_BASE_URL`, puis reconstruisez l’application. Ne publiez pas de secrets
dans le dépôt et n’exposez pas le serveur de développement directement à
Internet.

Guide mobile détaillé : [mobile/flutter/README.md](mobile/flutter/README.md).
État fonctionnel et limites : [docs/mvp-coverage.md](docs/mvp-coverage.md).

## Docker Compose

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Remplacez POSTGRES_PASSWORD et SECRET_KEY par des valeurs aléatoires distinctes.
docker compose up --build
```

Ne publiez pas le fichier `.env`. Le service API Compose publie le port `8000`;
vérifiez qu’il est libre avant le démarrage. Les valeurs d’exemple ne sont pas
des secrets utilisables en production.

## Portail d’administration et MCP

Le portail se trouve dans `admin/`; consultez son `package.json` pour les
commandes disponibles. Le serveur MCP stdio se lance depuis la racine avec :

```powershell
python .\run_koras.py mcp
```

## État et limites

- Le dépôt inclut des implémentations et tests automatisés, mais aucun backend
  public prêt à l’emploi.
- L’inscription, la connexion et les demandes qui nécessitent l’API ne
  fonctionnent que si l’URL du backend configurée dans le client est accessible.
- La session vocale commence après une action explicite et affiche une
  notification Android; la continuité de la reconnaissance vocale quand
  l’application est en arrière-plan dépend du système et reste à tester sur
  appareil.
- Les appels et SMS ouverts via une intention Android ne prouvent pas qu’un
  appel a abouti ou qu’un message a été livré.
- Les connecteurs financiers ne sont pas activés.
