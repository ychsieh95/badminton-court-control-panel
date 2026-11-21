# Play Store screenshots

English | [繁體中文（台灣）](README.zh-TW.md)

These scripts capture real emulator pixels from the app's existing screens, then frame them as Play Store screenshots. All courts, players, messages, and accounts are fictional.

## How it works

- `fixture_server.py` runs the real website and JSON API (`Web/app.py`) against a throwaway database in a temporary directory. It seeds fictional courts, players, and message-board threads through `/api/v1`, so the app receives exactly what it gets in production. It never touches `Web/instance/` or any real server. Each locale gets its own data set, and court dates are relative to today so every court stays upcoming.
- `capture.py` clears the app on the emulator, then writes its DataStore directly with `run-as` (debug builds only): the fixture server address (`http://10.0.2.2:PORT`), light theme (the default palette), a remembered join name, and a sign-in token for the fictional organizer `coach_amy`. The app therefore never contacts the production server and no login screen needs to be scripted. It then opens each scenario with intents and taps located in the UI tree, and saves validated 1080 × 2400 portrait PNGs.
- `capture.sh` is the entry point. It selects or boots an emulator (never a physical device), builds and installs the debug APK, switches the system to light mode, puts the status bar in System UI demo mode (current host time, full battery and Wi-Fi, no notification icons), runs the fixture server and `capture.py` for each locale, and restores the emulator settings afterwards.
- `render_store.py` composes the finished store panels from the captures.

| Scenario | Screen | Output |
| --- | --- | --- |
| `courts` | All courts list | `01-courts.png` |
| `court-detail` | Court page, top | `02-court-detail.png` |
| `members-levels` | Members, price, and level guide | `03-members-levels.png` |
| `join` | Join sheet with a username and hidden PIN | `04-join.png` |
| `messages` | Message board with organizer replies | `05-messages.png` |
| `organize` | My courts (organizer dashboard) | `06-organize.png` |
| `court-form` | Edit court form | `07-court-form.png` |

## Requirements

- Android SDK with platform tools, an emulator, and an AVD on API 33 or later (per-app languages). A Pixel 7 profile at 1080 × 2400 matches the existing output.
- JDK 17–21 for the build. The script uses Android Studio's JBR at `/opt/android-studio/jbr` when `JAVA_HOME` is unset.
- `app/google-services.json` (see `Android/README.md`).
- The website virtualenv at `Web/.venv` (see `Web/README.md`), and Python 3 with Pillow and NumPy for `render_store.py`.
- Noto Sans CJK fonts at `/usr/share/fonts/opentype/noto/`.

## Capture

From the repository root:

```bash
Android/docs/store-listing/screenshots/capture.sh --avd Pixel_7_API_36d0
```

To use a running emulator:

```bash
Android/docs/store-listing/screenshots/capture.sh --serial emulator-5560 --no-start
```

By default both locales are written to `closed-testing/alpha/app/en-US/` and `closed-testing/alpha/app/zh-TW/`. Use `--locale en-US` or `--locale zh-TW` for one language, `--scenarios join,messages` for a subset, `--output DIR` for another track, `--no-build` to reinstall the existing APK, and `--port` if 5055 is taken. Run `capture.sh --help` for every option.

The capture clears the app's data on the emulator (it shares the release application ID), and clears it again at the end so no fixture sign-in or local server address is left behind. Sign in again afterwards if you use that emulator for other testing.

## Store panels

```bash
python3 Android/docs/store-listing/screenshots/render_store.py \
  --input  Android/docs/store-listing/screenshots/closed-testing/alpha/app \
  --output Android/docs/store-listing/screenshots/closed-testing/alpha/store
```

Each visual treatment has its own directory under `closed-testing/alpha/store/`, with `en-US/`, `zh-TW/`, and `source/` (the procedurally drawn background panorama, at half size, that the seven panels are cut from). The backgrounds are drawn in code; no third-party artwork is used.

| Style | Look |
| --- | --- |
| `court-green` | Deep green with gold court lines and accents |
| `shuttle-ivory` | Warm ivory with amber and gold shuttle-flight arcs |
| `night-arena` | Navy arena with overhead light and an amber floor glow |

Panel copy lives in `COPY` in `render_store.py`. Keep the English and Traditional Chinese meaning aligned, keep each title to one line (the script stops if the copy pushes into the phone frame), and describe only features the app has. Pass `--styles court-green` to render one style. Inspect every image before uploading.

## Troubleshooting

- **A scenario times out waiting for a label:** the labels in `LABELS` in `capture.py` must match `res/values*/strings.xml`. Update them after changing wording.
- **Sections are clipped after scrolling:** adjust the `top` target in `Runner.scroll_top`.
- **Port in use:** pass `--port`.
- **Fixture server exits:** the script prints its log. Make sure `Web/.venv` has the website's requirements installed.
