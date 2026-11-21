# Badminton Court Control Panel

[![Last commit](https://img.shields.io/github/last-commit/ychsieh95/badminton-court-control-panel)](https://github.com/ychsieh95/badminton-court-control-panel/commits/main) [![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/) [![Flask 3.1](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/) [![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](Web/docker/compose.yaml) [![Android 8.0+](https://img.shields.io/badge/Android-8.0%2B%20(API%2026)-34A853?logo=android&logoColor=white)](https://developer.android.com/) [![Kotlin 2.2](https://img.shields.io/badge/Kotlin-2.2-7F52FF?logo=kotlin&logoColor=white)](https://kotlinlang.org/) [![Jetpack Compose](https://img.shields.io/badge/Jetpack%20Compose-Material%203-4285F4?logo=jetpackcompose&logoColor=white)](https://developer.android.com/compose) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) ![Languages](https://img.shields.io/badge/i18n-en--US%20%7C%20zh--TW-blue?logo=googletranslate&logoColor=white)

**English** · [繁體中文](README.zh-TW.md)

Badminton Court Control Panel is a bilingual (English / Traditional Chinese) system for organizing badminton events. Organizers publish and manage courts. Players find a court and join or leave it with a nickname and a 6-digit PIN, without creating an account, and can ask questions on each court's message board.

The project has two parts that share one server:

| Directory | What it is | Documentation |
| --- | --- | --- |
| [`Web/`](Web/) | Flask website and the `/api/v1` JSON API, with Docker files and tests | [README](Web/README.md) · [API reference](Web/API.md) |
| [`Android/`](Android/) | Native Android app (Kotlin, Jetpack Compose) built on the JSON API | [README](Android/README.md) |

## Highlights

- **Players:** browse and filter courts, join or leave with a nickname and PIN, join a waiting list when a court is full, post on the message board, and turn on notifications for a court.
- **Organizers:** create, edit, duplicate, and archive courts with halls, levels, prices, reserved places, photos, and videos; reply to messages; run roll call and payment clearing.
- **Administrators:** moderate every court and message, manage members and roles, and read contact messages.
- **Notifications:** browser notifications through Web Push and Android notifications through Firebase Cloud Messaging, both optional.
- **Languages and themes:** English and Traditional Chinese, with several color palettes in light and dark modes.

## Quick start

Run the website locally:

```bash
cd Web
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/flask --app app run --debug
```

Open <http://127.0.0.1:5000> and sign in with the development administrator `admin` / `change-me`. See [Web/README.md](Web/README.md) for configuration, optional integrations, and Docker deployment.

Build the Android app (requires JDK 17–21, the Android SDK, and `Android/app/google-services.json`):

```bash
cd Android
./gradlew :app:installDebug
```

To point the app at your local server, open **Account → App settings** and enter `http://10.0.2.2:5000` from the emulator. See [Android/README.md](Android/README.md) for details.

## Tests

```bash
(cd Web && .venv/bin/pytest -q)
(cd Android && ./gradlew :app:testDebugUnitTest)
```

## Working on both parts

- The Android app uses only the JSON API. When the API changes, update `Web/api.py`, `Web/API.md`, and `Web/tests/test_api.py` together, then the app's model classes and test fixtures.
- Interface text is shared. The website's `TRANSLATIONS` table in `Web/app.py` is the source; the Android string resources are generated from it with `python3 tools/gen_strings.py` in `Android/`.
- Secrets such as `.env`, Firebase files, and signing keys stay local and are ignored by Git.

## License

Released under the [MIT License](LICENSE). Bundled third-party assets, such as the Noto Sans TC font and the shuttlecock icon, keep their own licenses; see [Web/README.md](Web/README.md#attribution-and-licenses).
