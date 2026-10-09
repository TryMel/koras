# Application mobile KORAS

Client Android Flutter avec intégrations natives Kotlin. L’application a besoin
d’une API KORAS accessible pour l’inscription, la connexion et les fonctions
qui passent par le backend. **Aucun serveur public ni compte de démonstration
n’est fourni avec le dépôt.**

## Prérequis

- Flutter et Dart compatibles avec les contraintes indiquées dans `pubspec.yaml`
- Android SDK et un émulateur Android ou un téléphone Android
- Backend KORAS lancé ou déployé par l’utilisateur

```powershell
flutter pub get
flutter test
```

## Démarrer le backend local

Dans un autre terminal ouvert à la racine du dépôt :

```powershell
$env:KORAS_HOST = "127.0.0.1"
$env:KORAS_PORT = "8016"
python .\run_koras.py backend
```

Le backend reste actif dans ce terminal. Il utilise SQLite localement; ne
partagez pas sa base de données.

## Choisir l’URL de l’API

L’URL se configure à la compilation avec `--dart-define=API_BASE_URL=...`.
Sans cette option, le build Android utilise `http://10.0.2.2:8000/api/v1`,
accessible depuis l’émulateur Android lorsque le backend écoute sur le port
8000 du PC. Cette adresse ne désigne pas le PC depuis un téléphone physique.

### Émulateur

Depuis la racine du dépôt, lancez le backend local, puis :

```powershell
Set-Location .\mobile\flutter
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8016/api/v1
```

### Téléphone connecté en USB

Lancez d’abord le backend local sur le port choisi (exemple : `8016`) et
laissez-le actif. Puis, depuis la racine du dépôt :

```powershell
adb reverse tcp:8016 tcp:8016
Set-Location .\mobile\flutter
flutter run --dart-define=API_BASE_URL=http://127.0.0.1:8016/api/v1
```

Le tunnel fonctionne tant que le téléphone reste relié par ADB et que le
backend est actif. Pour créer un APK de développement :

```powershell
flutter build apk --release --dart-define=API_BASE_URL=http://127.0.0.1:8016/api/v1
```

N’installez pas cet APK comme une version autonome : sans tunnel ADB vers le
backend indiqué, il ne peut pas joindre cette adresse locale.

### Installation distribuable

Avant de distribuer une compilation, déployez une API KORAS avec TLS, configurez
son URL HTTPS complète (se terminant par `/api/v1`) dans `API_BASE_URL`, puis
reconstruisez l’application. La configuration locale HTTP est réservée aux
essais de développement; ne mettez ni clé, ni mot de passe, ni URL privée dans
le dépôt.

## Tests et limites connues

`flutter test` couvre les widgets présents dans `test/`; il ne simule pas
l’ensemble des appels réseau ou une session réelle sur téléphone. Vérifiez
séparément l’accès à l’API, l’inscription, les permissions et les intégrations
Android sur le matériel visé.

La session vocale nécessite une action explicite et utilise un service Android
de premier plan avec notification persistante. Le service de notification ne
garantit pas que la reconnaissance vocale pilotée par Flutter continue après
la mise en arrière-plan ou la destruction de l’activité; ce comportement doit
être testé sur l’appareil cible.
