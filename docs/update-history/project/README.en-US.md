# Project update history

Changes to tooling, tests, CI, and documentation.

## Unreleased

### Android string generation

Generates both `strings.xml` files with `android/tools/gen_strings.py` from the website's `TRANSLATIONS` table, plus app-only strings in `android/tools/extra_strings.json`. Moves the message board strings that had been added by hand into the generator, then switches the app to the website's `court_message_*` strings and drops 21 duplicates, with no visible wording change.

### Coding-agent instructions

Adds `android/AGENTS.md` and `android/CLAUDE.md`, covering the app's architecture and API-only rule, generated strings, secrets and fictional test data, verification, and release handling (including one `android/build/outputs/version-<versionCode> (<versionName>)/` folder per release instead of per track), and a root `CLAUDE.md` for commit message rules. Repeats the commit message rule in `android/CLAUDE.md`. Records the Android Claude Code skills in `android/.claude/skills.lock.json` with a script that downloads them, instead of committing them.

### Continuous integration

Adds GitHub Actions workflows. `web.yml` runs pytest on Python 3.10 and 3.13 and the Node browser-control tests when `web/` changes. `android.yml` checks that the generated strings are up to date, then runs the unit tests and a debug build when `android/` or `web/app.py` changes, using the `GOOGLE_SERVICES_JSON` repository secret.

### Contributor, privacy, security, and UI documentation

Rewrites `docs/CONTRIBUTING.md`, `docs/PRIVACY.md`, `docs/SECURITY.md`, `docs/UI_BRIEF.md`, and this update history for this project, replacing content carried over from an unrelated app. They now cover the website and Android checks, API and translation rules, and secrets for contributors; the data the server, browser, and app store and the third-party services involved; the account, session, API token, upload, and app trust boundary; and the app's layers, state contract, screens, and theme.

### Ignored secrets and repository layout

Moves the website into `web/` next to the new `android/` directory (both originally capitalized, as `Web/` and `Android/`), and ignores credentials, keystores, Firebase service account keys, `google-services.json`, `.env` files, and `tmp/`.

### Play Store screenshots

Adds tooling under `android/docs/store-listing/screenshots/` that builds the debug app, runs the website against a throwaway database seeded with fictional data, captures each scenario on an emulator in English and Traditional Chinese, and frames the captures as store panels. Screenshots are stored per app version in `version-<versionCode> (<versionName>)/`, read from `android/app/build.gradle.kts`, rather than per Google Play track. Its README documents every `capture.sh` option.

### READMEs and license

Rewrites the root, `web/`, and `android/` READMEs, each in English and Traditional Chinese, with status badges, and licenses the project under MIT. Bundled third-party assets keep their own licenses. The READMEs link the contributor, privacy, security, and UI docs and the update history, and describe what each CI workflow checks.

### Release signing

Signs Android release builds with an upload key read from the untracked `android/keystore.properties`. Without it, release builds stay unsigned.

### Test court dates

Moves test court dates from 2026 to 2099, which has the same calendar, so courts in the tests no longer expire and weekday checks still hold.
