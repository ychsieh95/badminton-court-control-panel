# Android app

A native Android client for Badminton Court Control Panel. It talks only to the JSON API (`/api/v1`, see [../Web/API.md](../Web/API.md)) and covers everything the website does through that API, in English and Traditional Chinese.

## Features

| Area | What you can do |
| --- | --- |
| Courts | Browse and search courts; filter by date range, level, gender, status, or expired; open a court from a pasted or shared link |
| Court page | Status, schedule, capacity, gallery (photos and videos), prices, level guide with the grading chart, remark, reserved players, players, waiting list, and join/leave history. Share, copy link, open in browser, open in Maps, download the share thumbnail |
| Players | Join or leave with a username and 6-digit PIN, no account needed. Full courts add you to the waiting list. Leave deadlines are respected |
| Organizers | My courts; create, edit, and duplicate courts (saved locations, reserved nicknames, leave deadline, photo and video upload); archive, restore, delete; roll call and clearing |
| Account | Sign up, sign in, profile picture, 12/24-hour time, saved locations, change password (forced after an admin sets a temporary password), signed-in devices, delete account |
| Admin | Moderate all courts (including archived ones); rename players, reset their PINs, remove players; manage users (role, ban, archive, temporary password, reset failed logins, delete); contact messages; homepage and notification settings |
| Other | Contact form; Cloudflare Turnstile when the server enables it; light/dark theme; the web's color palettes plus device colors |

Not available, because the API does not provide them (see "Not in the API" in `API.md`): CSV export, `court_info.md` import/export, and the static web pages.

## Build and run

Requirements: JDK 17–21 (Android Studio's bundled JBR works) and the Android SDK with platform 36.

The build also needs `app/google-services.json`, which is not committed. Download it from the Firebase console (**Project settings → Your apps**, Android package `cc.holey.badmintoncourtcontrolpanel`) and save it to `Android/app/`.

```bash
cd Android
./gradlew :app:assembleDebug        # APK in app/build/outputs/apk/debug/
./gradlew :app:installDebug         # install on a connected device or emulator
./gradlew :app:testDebugUnitTest    # unit tests
```

Or open `Android/` in Android Studio.

### Pointing the app at a server

The app starts with `https://badminton.holey.cc` and calls its JSON API under `/api/v1/`. To use another deployment, such as a local Flask dev server (`http://10.0.2.2:5000` from an emulator, after `flask --app app run` in `Web/`), open **Account → App settings**, enter its address (for example `https://courts.example.com`), and tap **Save**. Changing the server signs you out, because a token only works on the server that issued it.

Plain `http://` is allowed so LAN and emulator setups work. Use `https://` for public deployments.

## Project layout

Single `:app` module, Kotlin + Jetpack Compose (Material 3), following the conventions of the Claude Code skills `android-dev`, `compose`, `android-ux`, `android-retrofit`, and `android-data-layer`. The skills are not committed; [`.claude/skills.lock.json`](.claude/skills.lock.json) records their upstream sources. Download them with `.claude/update-skills.py update --force`, which installs the latest upstream versions into `.claude/skills/`.

```
app/src/main/java/io/github/ychsieh95/bccp/
├── core/
│   ├── model/      API objects (kotlinx.serialization, snake_case)
│   ├── network/    Retrofit service, interceptor (server URL, bearer token, language)
│   ├── data/       Repositories (the error boundary → DataError), session and settings stores
│   ├── di/         Hilt module
│   └── ui/         Theme (web palettes), shared components, date/time formatting
├── feature/        courts, courtdetail, courtform, auth, account, admin, contact, settings
└── navigation/     Routes, bottom navigation, NavHost
```

- One immutable `UiState` per screen as a `StateFlow`; one-off events (navigation, snackbars) go through a `Channel`.
- Repositories return `Result<T>`. Server errors become `DataError.Api` carrying the server's localized `message` and per-field `fields`, which forms show under each input.
- The bearer token is stored in app-private DataStore. A `401 invalid_token` response signs the app out.
- The server localizes its error messages from the `Accept-Language` header, so they match the app language.

### Strings

`res/values*/strings.xml` are generated from the website's translation table, so wording matches the site:

```bash
python3 tools/gen_strings.py
```

Shared wording comes from `TRANSLATIONS` in `Web/app.py`. App-only strings are in `tools/extra_strings.json`. Don't edit the XML by hand.
