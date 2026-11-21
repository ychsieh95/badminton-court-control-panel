# Badminton Court Control Panel — Android

[![Android 8.0+](https://img.shields.io/badge/Android-8.0%2B%20(API%2026)-34A853?logo=android&logoColor=white)](https://developer.android.com/) [![Target API 36](https://img.shields.io/badge/target%20API-36-34A853?logo=android&logoColor=white)](https://developer.android.com/about/versions) [![Kotlin 2.2](https://img.shields.io/badge/Kotlin-2.2-7F52FF?logo=kotlin&logoColor=white)](https://kotlinlang.org/) [![Jetpack Compose](https://img.shields.io/badge/Jetpack%20Compose-Material%203-4285F4?logo=jetpackcompose&logoColor=white)](https://developer.android.com/compose) [![Firebase Cloud Messaging](https://img.shields.io/badge/Firebase-Cloud%20Messaging-DD2C00?logo=firebase&logoColor=white)](https://firebase.google.com/docs/cloud-messaging) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE) ![Languages](https://img.shields.io/badge/i18n-en--US%20%7C%20zh--TW-blue?logo=googletranslate&logoColor=white)

**English** · [繁體中文](README.zh-TW.md)

The native Android app for Badminton Court Control Panel, in English and Traditional Chinese. It talks only to the server's JSON API (`/api/v1`, see [../Web/API.md](../Web/API.md)) and offers everything the website does through that API.

- Package: `cc.holey.badmintoncourtcontrolpanel`
- Android 8.0 (API 26) or later; targets API 36
- Kotlin, Jetpack Compose (Material 3), Hilt, Retrofit, kotlinx.serialization, DataStore, Coil, Firebase Cloud Messaging

## Features

| Area | What you can do |
| --- | --- |
| Courts | Browse and search courts; filter by date range, level, gender, status, or expired; open a court from a shared or pasted link |
| Court page | Status, schedule, capacity, photos and videos, prices, level guide with the grading chart, remark, reserved players, players, waiting list, and join/leave history. Share, copy the link, open in a browser or in Maps, download the share image |
| Players | Join or leave with a nickname and 6-digit PIN, no account needed. Full courts put you on the waiting list. Leave deadlines are enforced |
| Message board | Read a court's messages; post and reply with the nickname and PIN you joined with, or as the organizer when signed in. Organizers and admins can delete messages |
| Notifications | Follow a court to be notified about changes, players joining or leaving, and replies to your messages. Organizers are notified of new messages. A message notification opens the court at its message board |
| Organizers | My courts; create, edit, and duplicate courts (saved halls, reserved nicknames, leave deadline, photo and video upload); archive, restore, delete; roll call and clearing |
| Account | Sign up, sign in, profile picture, 12/24-hour time, saved halls, change password (required after an admin sets a temporary one), signed-in devices, delete account |
| Admin | Moderate all courts, including archived ones; rename players, reset their PINs, remove players; manage users (role, ban, archive, temporary password, reset failed sign-ins, delete); contact messages; homepage and notification settings |
| Other | Contact form; Cloudflare Turnstile when the server enables it; light and dark themes; the website's palettes (Yellow by default) plus the device's own colors |

Not available, because the API does not provide them (see "Not in the API" in `API.md`): the CSV export, `court_info.md` import and export, and the website's static pages.

## Build and run

You need:

- JDK 17–21 (Android Studio's bundled JBR works)
- The Android SDK with platform 36
- `app/google-services.json`, which is not committed. Download it from the Firebase console (**Project settings → Your apps**, package `cc.holey.badmintoncourtcontrolpanel`) and save it to `Android/app/`.

```bash
cd Android
./gradlew :app:assembleDebug        # APK in app/build/outputs/apk/debug/
./gradlew :app:installDebug         # install on a connected device or emulator
./gradlew :app:testDebugUnitTest    # unit tests
```

You can also open `Android/` in Android Studio.

### Choosing a server

The app starts with `https://badminton.holey.cc`. To use another deployment, open **Account → App settings**, enter its address (for example `https://courts.example.com`), and tap **Save**. Changing the server signs you out, because a sign-in token only works on the server that issued it.

For local development, run the website from `Web/` (`.venv/bin/flask --app app run`) and use `http://10.0.2.2:5000` from the emulator. Plain `http://` is allowed for LAN and emulator setups; use `https://` for public servers.

### Release builds

Release builds are minified and signed with the upload key described in `Android/keystore.properties`. That file, and the keystore it points to, stay local and are ignored by Git:

```properties
storeFile=/path/to/upload-keystore.jks
storePassword=…
keyAlias=…
keyPassword=…
```

```bash
./gradlew :app:bundleRelease        # AAB in app/build/outputs/bundle/release/
```

Without `keystore.properties`, the release build is unsigned and cannot be uploaded to Google Play. Set `versionCode` and `versionName` in `app/build.gradle.kts` before each release.

## Project layout

A single `:app` module under the package `io.github.ychsieh95.bccp`:

```text
app/src/main/java/io/github/ychsieh95/bccp/
├── core/
│   ├── model/      API objects (kotlinx.serialization, snake_case)
│   ├── network/    Retrofit service; interceptor adds the server URL, bearer token, and language
│   ├── data/       Repositories (the error boundary, mapping to DataError), session and settings stores
│   ├── push/       FCM service and notifications
│   ├── di/         Hilt module
│   └── ui/         Theme (web palettes), shared components, date and time formatting
├── feature/        courts, courtdetail, courtform, auth, account, admin, contact, settings
└── navigation/     Routes, bottom navigation, NavHost
```

- Each screen has one immutable `UiState`, exposed as a `StateFlow`. One-off events (navigation, snackbars) go through a `Channel`.
- Repositories return `Result<T>`. Server errors become `DataError.Api`, carrying the server's localized `message` and per-field `fields`, which forms show under each input.
- The server localizes its messages from the `Accept-Language` header, so errors match the app language.
- The bearer token is kept in app-private DataStore. A `401 invalid_token` response signs the app out.
- Unit tests in `app/src/test/` check the API contract against JSON fixtures in `app/src/test/resources/fixtures/`. Update them when the API changes.

The code follows the conventions of the Claude Code skills `android-dev`, `compose`, `android-ux`, `android-retrofit`, and `android-data-layer`. The skills are not committed; [`.claude/skills.lock.json`](.claude/skills.lock.json) records their sources, and `.claude/update-skills.py update --force` downloads them into `.claude/skills/`. Coding agents should also read [AGENTS.md](AGENTS.md).

### Strings

`res/values/strings.xml` and `res/values-zh-rTW/strings.xml` are generated, so the app uses the same wording as the website. Don't edit them by hand:

```bash
python3 tools/gen_strings.py
```

Shared wording comes from `TRANSLATIONS` in `Web/app.py`. App-only strings are in `tools/extra_strings.json` as `["English", "繁體中文"]` pairs.

### Icons

Launcher and notification icons are generated from `Web/static/shuttlecock.png` by `tools/gen_launcher_icon.py`. Rerun the script instead of editing the PNGs.

### Store screenshots

[`docs/store-listing/screenshots/`](docs/store-listing/screenshots/README.md) captures Google Play screenshots from an emulator against a local server seeded with fictional data, then frames them as store panels.

## License

Released under the [MIT License](../LICENSE). The launcher icon is derived from the website's shuttlecock icon; see [Web/README.md](../Web/README.md#attribution-and-licenses) for its attribution.
