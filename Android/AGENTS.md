# Android app instructions for coding agents

These instructions apply to everything under `Android/`. Codex reads this file directly; Claude Code imports it through `CLAUDE.md`. The website and JSON API live in `../Web/` and are outside the scope of this file, but changes here often depend on them.

## Project context

- This is the native Android client for Badminton Court Control Panel, written in Kotlin with Jetpack Compose (Material 3), Hilt, Retrofit, kotlinx.serialization, DataStore, Coil, and Firebase Cloud Messaging. App source and resources are in `app/src/main/`; local unit tests and JSON fixtures are in `app/src/test/`.
- Read `README.md` for features, build requirements, server configuration, and the project layout. Read `../Web/API.md` before touching networking code.
- The app is a single `:app` module under the package `io.github.ychsieh95.bccp`. Keep the existing split: `core/model` (API objects), `core/network` (Retrofit service and interceptor), `core/data` (repositories, session and settings stores), `core/di`, `core/ui` (theme, shared components, formatting), `feature/<area>` (screens and view models), and `navigation/` (routes and NavHost).
- Do not hard-wrap prose in `README.md`, `AGENTS.md`, or `CLAUDE.md`. Keep each paragraph on one source line, regardless of length. Preserve Markdown structure, including separate headings, list items, table rows, blank lines, and code-block formatting.
- Keep changes focused and preserve existing user work. Do not edit generated build output (`build/`, `.gradle/`, `.kotlin/`) as source files.

## Architecture rules

- The app talks only to the JSON API under `/api/v1`. Do not scrape HTML pages or call website form endpoints. If a feature needs data or an action the API does not provide, say so; extend the API only when the user asks, and then update `../Web/api.py`, `../Web/API.md`, and `../Web/tests/test_api.py` in the same change.
- Model API objects with kotlinx.serialization using the server's snake_case field names. When the API contract changes, update the matching fixtures in `app/src/test/resources/fixtures/` and `ApiContractTest`.
- Each screen exposes one immutable `UiState` as a `StateFlow` from its view model; one-off events such as navigation and snackbars go through a `Channel`.
- Repositories are the error boundary: they return `Result<T>` and map failures to `DataError`. Show the server's localized `message` and per-field `fields` from `DataError.Api` instead of inventing client-side wording for server errors.
- The bearer token stays in app-private DataStore. Keep the existing behavior where `401 invalid_token` signs the app out and changing the server address signs the user out.
- Do not add new third-party runtime libraries, permissions, analytics, or tracking without an explicit user request. Add dependencies through `gradle/libs.versions.toml`.
- Follow the conventions of the Claude Code skills listed in `.claude/skills.lock.json` (notably `android-dev`, `compose`, `android-ux`, `android-retrofit`, and `android-data-layer`). The skills are not committed; if `.claude/skills/` is missing, download them with `.claude/update-skills.py update --force`.

## Strings and localization

- The app ships in English (`res/values/strings.xml`) and Traditional Chinese, Taiwan (`res/values-zh-rTW/strings.xml`). Every user-visible string must exist in both, with the same meaning and placeholders.
- Both XML files are generated. Never edit them by hand. Shared wording comes from `TRANSLATIONS` in `../Web/app.py`; app-only strings go in `tools/extra_strings.json` as `["English", "繁體中文"]`. Regenerate with `python3 tools/gen_strings.py` from `Android/` and commit the regenerated XML with the source change.
- Do not hard-code user-visible text in Kotlin. Use string resources, including for content descriptions.
- Launcher and notification icons are generated from `../Web/static/shuttlecock.png` by `tools/gen_launcher_icon.py`. Regenerate them with that script instead of editing the PNGs.

## Secrets and private data

- `app/google-services.json`, `local.properties`, keystores, and signing properties are local-only and ignored by Git. Never commit, print, or copy their contents into source, documentation, or commit messages.
- Use fictional names, PINs, courts, and messages in tests, fixtures, previews, and screenshots. Do not use real user data from the production server.
- Point verification builds at a local or test server where possible. Do not create, modify, or delete data on the production server (`https://badminton.holey.cc`) without an explicit user request.

## Verification and completion

- Run Gradle through the wrapper from `Android/`: `./gradlew`. Use JDK 17–21; Android Studio's bundled JBR works.
- After Kotlin or resource changes, run `./gradlew :app:testDebugUnitTest` and `./gradlew :app:assembleDebug`. Both must pass before the task is complete.
- After changes to `../Web/`, also run `.venv/bin/pytest -q` from `Web/`.
- For UI changes, when an emulator or device is available, install with `./gradlew :app:installDebug` and check the affected screen in both English and Traditional Chinese and in light and dark themes. A local Flask dev server is reachable from the emulator at `http://10.0.2.2:5000`.
- If a check cannot run (for example, no Android SDK, no `google-services.json`, or no emulator), say so explicitly. Report what changed, which checks passed, and which could not run.

## Release builds

- Before preparing a release, use the version name and version code supplied by the user. If either is missing or ambiguous, ask before changing `versionName` or `versionCode` in `app/build.gradle.kts` or building artifacts.
- Release bundles must be signed with the existing upload key. Never present an unsigned bundle as upload-ready, and never commit signing material.
- Collect each release's files in `build/outputs/version-<versionCode> (<versionName>)/` under `Android/`, for example `build/outputs/version-1 (1.0.0)/`: the signed bundle `bccp-<versionName>-<versionCode>.aab`, the matching APK `bccp-<versionName>-<versionCode>.apk`, and the R8 `mapping.txt` (from `app/build/outputs/mapping/release/`). Use one folder per version, not per Google Play track: the same build moves from closed testing to open testing to production, so do not create `closed-testing/`, `open-testing/`, or `production/` subfolders. Never overwrite an existing version folder; a new upload needs a new `versionCode`.
- After completing a release, provide a Git commit message that follows the style of previous commits (Conventional Commits with an `android` scope, for example `feat(android): …`).
