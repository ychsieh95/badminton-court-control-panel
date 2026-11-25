# Contributing

Issues and pull requests are welcome. Coding agents and human contributors follow the same rules. The Android rules are written down in [android/AGENTS.md](../android/AGENTS.md); this page summarizes them and adds the website's.

The repository has two parts that share one server: the Flask website and `/api/v1` JSON API in [`web/`](../web/), and the native Android app in [`android/`](../android/), which talks only to that API.

## Requirements

- **Website:** Python 3.10 or newer, and Node.js for the browser-control tests (no npm packages needed).
- **Android app:** JDK 17–21 (Android Studio's bundled JBR works), the Android SDK with platform 36, and `android/app/google-services.json`, which is not committed. Download it from the Firebase console for the package `cc.holey.badmintoncourtcontrolpanel`.
- An Android 8.0 (API 26) or later device or emulator for manual testing.

Use the Gradle wrapper in `android/`. Do not upgrade Gradle, the Android Gradle Plugin, Kotlin, or other dependencies as part of an unrelated change; add dependencies through `android/gradle/libs.versions.toml`.

## Before submitting a change

```sh
# Website (from web/)
.venv/bin/pytest -q
node tests/test_court_controls.cjs
node tests/test_court_navigation.cjs

# Android app (from android/)
python3 tools/gen_strings.py          # if TRANSLATIONS or extra_strings.json changed
./gradlew :app:testDebugUnitTest
./gradlew :app:assembleDebug
```

GitHub Actions runs the same checks on pushes and pull requests to `main`. [`web.yml`](../.github/workflows/web.yml) runs on Python 3.10 and 3.13. [`android.yml`](../.github/workflows/android.yml) also fails if the generated string resources are out of date, and runs whenever `web/app.py` changes, because the app's strings come from it.

For UI changes, check the affected page or screen in both English and Traditional Chinese and in light and dark themes. For the app, run a local server from `web/` (`.venv/bin/flask --app app run`), install with `./gradlew :app:installDebug`, and set **Account → App settings** to `http://10.0.2.2:5000` from the emulator.

## Guidelines

- **Keep changes focused** and add or update tests for behavior changes: `web/tests/` for the website and API, `android/app/src/test/` for the app.
- **The app uses only the JSON API.** Do not scrape HTML pages or call website form endpoints from the app. When the API changes, update `web/api.py`, `web/API.md`, and `web/tests/test_api.py` together, then the app's model classes in `core/model/`, the JSON fixtures in `app/src/test/resources/fixtures/`, and `ApiContractTest`.
- **Share rules between the pages and the API.** Validation, throttling, and permission checks live in shared helpers in `web/app.py` so the HTML pages and `/api/v1` behave the same. Do not reimplement them in a single route.
- **Respect the app's architecture.** Keep the split into `core/model`, `core/network`, `core/data`, `core/push`, `core/di`, `core/ui`, `feature/<area>`, and `navigation/`. Each screen exposes one immutable `UiState` as a `StateFlow`, and one-off events go through a `Channel`. Repositories return `Result<T>` and map failures to `DataError`. See [UI_BRIEF.md](UI_BRIEF.md) for the UI conventions.
- **Keep translations in sync.** All interface text lives in `TRANSLATIONS` in `web/app.py`, with matching `en-us` and `zh-tw` keys. The app's `strings.xml` files are generated from it, plus app-only strings in `android/tools/extra_strings.json`; never edit the XML by hand. Do not hard-code user-visible text in Kotlin or templates. Keep each README pair (`README.md` and `README.zh-TW.md`) in step.
- **Do not hard-wrap prose** in README, agent instruction, or `docs/` files. Keep each paragraph on one line.
- **Do not add tracking.** No analytics, crash reporting, ads, or new third-party services, libraries, or Android permissions without a maintainer's agreement. Every integration must stay optional, and the site must work with none configured.
- **Record user-visible website changes** in `web/data/update_history.json`, which feeds the `/updates` page. Each entry needs both languages, and the app refuses to start if the file is malformed or out of order.
- **Record every change** in the right bilingual history pair under [update-history/](update-history/): `app/` for changes that people using the website or Android app can notice, `project/` for tooling, tests, CI, and documentation. Add entries under the `Unreleased` (`未發行`) group, sorted alphabetically by English title, with matching Traditional Chinese entries in the same order.

## Credentials, secrets, and test data

- Never commit `.env`, `google-services.json`, Firebase service account files, VAPID private keys, `local.properties`, keystores, or `keystore.properties`. They are ignored by Git; keep it that way, and never paste their contents into code, documentation, issues, or commit messages.
- Use fictional names, PINs, courts, and messages in tests, fixtures, previews, and screenshots. Do not copy real data from a production database.
- Point manual testing at a local server. Do not create, change, or delete data on the production server (`https://badminton.holey.cc`) while developing.
- Test court dates use 2099 so they never expire. Keep new fixtures in the future the same way.

## Releases

- **Website:** the version reported by the API defaults to the newest date in `web/data/update_history.json`, or `APP_VERSION` when set. See [web/README.md](../web/README.md) for Docker deployment.
- **Android app:** set `versionCode` and `versionName` in `android/app/build.gradle.kts`, then build with `./gradlew :app:bundleRelease`. Release bundles are signed with the upload key described by the untracked `android/keystore.properties`; without it the bundle is unsigned and cannot be uploaded to Google Play.
- Commit messages follow Conventional Commits with a `web` or `android` scope where it applies, for example `feat(android): …` or `fix(web): …`.
