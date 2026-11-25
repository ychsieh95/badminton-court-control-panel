# Badminton Court Control Panel — Web

[![Web CI](https://github.com/ychsieh95/badminton-court-control-panel/actions/workflows/web.yml/badge.svg)](https://github.com/ychsieh95/badminton-court-control-panel/actions/workflows/web.yml) [![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/) [![Flask 3.1](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/) [![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/) [![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](docker/compose.yaml) [![JSON API](https://img.shields.io/badge/JSON%20API-%2Fapi%2Fv1-FF6F00?logo=json&logoColor=white)](API.md) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE) ![Languages](https://img.shields.io/badge/i18n-en--US%20%7C%20zh--TW-blue?logo=googletranslate&logoColor=white)

**English** · [繁體中文](README.zh-TW.md)

The website and JSON API for Badminton Court Control Panel, a bilingual (English / Traditional Chinese) Flask application for organizing badminton events. Organizers publish and manage courts. Players find a court and join or leave it with a nickname and a 6-digit PIN, without creating an account. The same server provides the `/api/v1` JSON API used by the [Android app](../android/README.md).

## Contents

- [Features](#features)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [Optional integrations](#optional-integrations)
- [Deployment with Docker](#deployment-with-docker)
- [Data and storage](#data-and-storage)
- [Security and privacy](#security-and-privacy)
- [Development](#development)
- [Attribution and licenses](#attribution-and-licenses)

## Features

### Players

- Browse upcoming courts and filter by keyword, organizer, date range, player level, gender level range, capacity, and status.
- Join or leave with a nickname and a private 6-digit PIN. No account is needed. When the confirmed places are full, new players go onto a first-in, first-out waiting list.
- See the organizer's leave deadline before joining. After it passes, players can no longer remove themselves.
- Read the schedule, hall and map location, prices, shuttlecock, level ranges, remarks, player lists, and event photos and videos.
- Ask questions on the court's **message board**. Players who joined the court post and reply with the nickname and PIN they joined with. The board refreshes itself while the page is open.
- Turn on browser notifications for a court to hear about edits, archiving, players joining or leaving, and replies to their messages.
- Share a court link with a 1200×630 social preview, or download that preview as a JPEG.
- Collapse court sections and jump between them with a draggable section navigator.

### Organizers

- Sign up and manage your events from **My courts** (`/my-courts`). Each court has a permanent link of the form `https://your-domain.example/<GUID>`.
- Set the date and time, a Google Places hall, court number, capacity and reserved places, male and female level ranges, prices, shuttlecock, remarks, and an optional leave deadline.
- Reserve places by nickname and choose whether visitors can see those names. Save frequently used halls and reuse them later.
- Upload up to 12 photos or videos (JPEG, PNG, WebP, MP4, WebM). The first image becomes the court card cover.
- Reply to messages as the organizer, delete messages, and get a notification for each new message or reply.
- Edit, duplicate, archive, restore, or delete your courts. Export a court as `court_info.md` and import it later to prefill a new one.
- Start **Roll call & clearing** to make a court read-only and record attendance and payment for each player.
- Choose 12-hour or 24-hour time on your profile.

### Administrators

- Manage every court, including archived and expired ones, with the same filters as the public listing. Export all courts as a UTF-8 CSV file.
- Rename players, reset their PINs, or remove them from a court. See join/leave history with IP addresses and broad device types, and the IP address of each message.
- Manage members: assign roles (member, sub-admin, admin, super-admin; only super-admins change roles), ban, archive, delete, set a temporary password, or reset failed sign-in lockouts.
- Read contact messages in a protected inbox and choose how many courts the homepage shows.

### Language and appearance

- English (`en-US`) and Traditional Chinese (`zh-TW`). Visitors detected in Taiwan start in Traditional Chinese; others start in English. A language chosen by hand is kept in a cookie.
- Monochrome, Green & Lime, Purple, and Yellow palettes, each in system, light, and dark modes. New visitors get **Yellow · Light**.
- Includes the Taiwan Badminton Promotion Association 1–18 level guide, a public introduction, an update history, a privacy policy, and a contact page.

### Main routes

| Route | Purpose |
| --- | --- |
| `/` | Homepage with upcoming courts |
| `/courts` | Filterable court listing |
| `/courts/new` | New court form (signed-in members and administrators) |
| `/<GUID>` | Court page: details, joining, and the message board |
| `/<GUID>/thumbnail.jpg` | The court's current 1200×630 preview image |
| `/<GUID>/court_info.md` | Court settings export (organizers only) |
| `/signup`, `/login` | Member sign-up; sign-in for members and administrators |
| `/my-courts` | Organizer dashboard |
| `/account/profile` | Profile, avatar, time format, saved halls |
| `/admin`, `/admin/users`, `/admin/messages` | Administrator dashboard, member management, contact inbox |
| `/admin/courts/export.csv` | CSV export of every court (administrators only) |
| `/introduction`, `/updates`, `/privacy`, `/contact`, `/licenses`, `/android` | Public information pages |
| `/healthz` | Health check; returns `{"status": "ok"}` after a database probe |
| `/api/v1/...` | JSON API (see [API.md](API.md)) |

## Quick start

Requires Python 3.10 or newer. Run every command in this document from the `web/` directory.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/flask --app app run --debug
```

Open <http://127.0.0.1:5000> and sign in at `/login`. Members land on `/my-courts`; administrators land on `/admin`.

On a database without a super-admin, the app creates one from `ADMIN_USERNAME` and `ADMIN_PASSWORD` (development defaults: `admin` / `change-me`). Changing these variables later does not change an existing super-admin's password; use the account password page instead. Replace `SECRET_KEY`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD` before the first production start.

## Configuration

Settings are read from `.env`. Variables already set in the process environment take precedence. [`.env.example`](.env.example) lists every variable with comments.

| Variable | Default | Description |
| --- | --- | --- |
| `SECRET_KEY` | Development value | Signs sessions and CSRF tokens. Use a long random value in production. |
| `ADMIN_USERNAME` | `admin` | Username of the first super-admin. |
| `ADMIN_PASSWORD` | `change-me` | Initial password of the first super-admin. |
| `COURT_DATABASE` | `instance/courts.sqlite` | SQLite database path. |
| `SESSION_COOKIE_SECURE` | `0` | Set to `1` when the site is served only over HTTPS. |
| `TRUST_PROXY_HEADERS` | `0` | Trust forwarded client-IP and scheme headers. Enable only behind a trusted proxy that replaces them. |
| `TURNSTILE_SITE_KEY` | Empty | Cloudflare Turnstile site key. |
| `TURNSTILE_SECRET_KEY` | Empty | Cloudflare Turnstile secret key. Never sent to browsers. |
| `TURNSTILE_VERIFY_TIMEOUT` | `5` | Turnstile verification timeout, in seconds. |
| `GOOGLE_MAPS_API_KEY` | Empty | Enables Google Places hall search on the court form. |
| `WEB_PUSH_PUBLIC_KEY` | Empty | VAPID application-server key shown to browsers. |
| `WEB_PUSH_PRIVATE_KEY` | Empty | VAPID private key, as a value or a PEM file path. |
| `WEB_PUSH_SUBJECT` | Empty | VAPID contact URI, such as `mailto:admin@example.com`. |
| `WEB_PUSH_TIMEOUT` | `5` | Web Push delivery timeout per recipient, in seconds. |
| `FCM_SERVICE_ACCOUNT_FILE` | Empty | Firebase service account JSON path. Enables Android app notifications. |
| `FCM_TIMEOUT` | `5` | FCM delivery timeout per recipient, in seconds. |
| `SOCIAL_THUMBNAIL_FFMPEG` | Bundled executable | FFmpeg override, used to take a preview frame from a video. |
| `SOCIAL_THUMBNAIL_FONT` | Bundled Noto Sans TC | Font override for generated preview images. |
| `GEOIP_COUNTRY_DB` | Empty | Local MaxMind GeoIP2/GeoLite2 country database, used to pick the default language. |
| `DEFAULT_COUNTRY_CODE` | Empty | Two-letter fallback country when the visitor's country is unknown. |
| `PRIVACY_OPERATOR_NAME` | Empty | Operator name shown on `/privacy` and `/contact`. |
| `PRIVACY_DATA_REGION` | Empty | Hosting region shown on `/privacy`. |
| `PRIVACY_CONTACT` | Empty | `mailto:` or HTTP(S) contact shown on `/privacy`. |
| `ADMIN_CONTACT` | Empty | `mailto:` or HTTP(S) support contact shown on `/contact`. |
| `ADMIN_CONTACT_DISCORD` | Empty | Discord invite code; `/contact` links to `discord.gg`. |
| `ADMIN_CONTACT_LINE` | Empty | LINE Official Account ID, with or without `@`. |
| `ADMIN_CONTACT_TELEGRAM` | Empty | Telegram public username, with or without `@`. |
| `CONTACT_DISCORD_WEBHOOK_URL` | Empty | Discord incoming webhook for new contact messages. An administrator turns it on in `/admin/messages`. |
| `CONTACT_TELEGRAM_BOT_TOKEN` | Empty | Telegram bot token. With the chat ID, every new contact message is reported to Telegram. |
| `CONTACT_TELEGRAM_CHAT_ID` | Empty | Telegram numeric chat ID or public `@channel` that receives reports. |
| `CONTACT_NOTIFICATION_TIMEOUT` | `5` | Discord/Telegram delivery timeout, in seconds. |
| `ANDROID_APP_URL` | Empty | HTTPS download link (such as a Google Play listing) shown on `/android`. |
| `LOGIN_MAX_ATTEMPTS` | `5` | Failed sign-ins allowed before a temporary lockout. |
| `LOGIN_LOCKOUT_SECONDS` | `900` | Sign-in lockout length, in seconds. |
| `LEAVE_MAX_ATTEMPTS` | `5` | Wrong nickname/PIN leave attempts allowed per court, nickname, and IP before a lockout. |
| `LEAVE_LOCKOUT_SECONDS` | `900` | Leave lockout length, in seconds. |
| `API_TOKEN_TTL_DAYS` | `90` | Lifetime of JSON API bearer tokens, in days. |
| `APP_VERSION` | Newest date in `data/update_history.json` | Version string reported by the API. |

## Optional integrations

Every integration is off until it is configured. The site works without any of them.

### Cloudflare Turnstile

Create a [Turnstile widget](https://developers.cloudflare.com/turnstile/get-started/) for your hostname and set both `TURNSTILE_SITE_KEY` and `TURNSTILE_SECRET_KEY`. Turnstile then protects sign-up, sign-in, and the contact form. The server checks each token and its action (`signup`, `login`, or `contact_message`) before handling the request, and rejects missing, expired, reused, or mismatched tokens. Turnstile is off when either key is empty or Flask debug mode is on. Cloudflare's [test keys](https://developers.cloudflare.com/turnstile/troubleshooting/testing/) are for testing only; never deploy them.

### Google hall search

Set `GOOGLE_MAPS_API_KEY` to a browser key with **Maps JavaScript API** and **Places API (New)** enabled, in a Google Cloud project with billing. Restrict it by **Websites (HTTP referrers)** to your domain, plus these for local development:

```text
http://127.0.0.1:5000/*
http://localhost:5000/*
```

Without a key, the court form still works and offers a Google Maps search link instead.

### Browser notifications (Web Push)

Each court page has a notification switch. Notifications go out when the organizer edits, archives, restores, locks, unlocks, or deletes the court; when a player joins, joins the waiting list, or leaves; and for new messages and replies on the message board (to the organizer, and to the author of the thread). Failed join or leave attempts and roll-call changes do not send notifications.

Generate one VAPID key pair and keep it:

```bash
mkdir -p instance/web-push
cd instance/web-push
../../.venv/bin/vapid --gen --applicationServerKey
```

The command prints the application-server key and writes `private_key.pem`. Then set:

```text
WEB_PUSH_PUBLIC_KEY=<printed application-server key>
WEB_PUSH_PRIVATE_KEY=instance/web-push/private_key.pem
WEB_PUSH_SUBJECT=mailto:your-contact@example.com
```

Replacing the key pair cancels every existing browser subscription. Browsers require HTTPS for push, except on localhost. If any VAPID setting is missing, the switch stays disabled. Subscriptions that the push service reports as gone (`404` or `410`) are removed automatically.

### Android app notifications (FCM)

The Android app receives the same notifications through Firebase Cloud Messaging. In the Firebase console, open **Project settings → Service accounts**, generate a private key, save it somewhere persistent, and point the server at it:

```text
FCM_SERVICE_ACCOUNT_FILE=instance/firebase-service-account.json
```

With Docker, put the file in the `/instance` volume and use `/instance/firebase-service-account.json`. Without this setting, the app hides its notification switch. Tokens that FCM reports as unregistered are removed automatically.

### Contact message alerts

Contact messages are always saved to the database first; alerts are extra. With both Telegram variables set, every new message from the website or the Android app is reported to that chat, including the sender, reply contact, account, source (website and device type, or app version, Android version, and device model), language, and an inbox link. Discord is optional: set `CONTACT_DISCORD_WEBHOOK_URL`, then turn it on in `/admin/messages`. Webhook URLs and bot tokens are validated, stay on the server, and are never shown in the inbox. A delivery failure is logged without the secret and never loses the stored message.

## Deployment with Docker

The image runs the app with uWSGI behind Nginx on port `8080`, as UID `1654` by default.

```bash
docker compose -f docker/compose.yaml up -d --build   # start
docker compose -f docker/compose.yaml down            # stop, keeping data
```

Compose loads `web/.env`, publishes port `8080`, and mounts the named volume `badminton-court-control-data` at `/instance`, so the database, avatars, and court media survive container rebuilds. Set the `APP_UID` build argument if the volume needs another owner.

To build and run without Compose:

```bash
docker build --build-arg APP_UID=1654 -f docker/Dockerfile -t badminton-court-control-panel .
docker run --rm --name badminton-court-control-panel --env-file .env \
  -p 8080:8080 -v badminton-court-control-data:/instance badminton-court-control-panel
```

If an older image that ran as root created the volume, fix its ownership once before starting the new image (replace `1654` if you changed `APP_UID`):

```bash
docker run --rm --user 0 --entrypoint chown \
  -v badminton-court-control-data:/instance \
  badminton-court-control-panel:local -R 1654:0 /instance
```

### Health check

The image's `HEALTHCHECK` requests `/healthz` every 30 seconds (5-second timeout, 20-second start period, 3 retries). The endpoint runs `SELECT 1` against the database, needs no sign-in, and returns no personal data, so uptime monitors and proxies can use it too.

```bash
docker compose -f docker/compose.yaml ps
docker inspect --format '{{.State.Health.Status}}' <container>
```

### Behind a reverse proxy

Behind another Nginx, the container sees the Docker gateway (often `172.18.0.1`) instead of the visitor. To record real client addresses, set `TRUST_PROXY_HEADERS=1` and have the public-facing proxy replace, not append, the forwarded headers:

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Reload Nginx and recreate the container so it picks up `.env`:

```bash
sudo nginx -t && sudo systemctl reload nginx
docker compose -f docker/compose.yaml up -d --force-recreate app
docker compose -f docker/compose.yaml exec app printenv TRUST_PROXY_HEADERS   # must print 1
```

Enable this only when the app is reachable exclusively through that proxy. If another proxy, such as Cloudflare, sits in front of Nginx, configure Nginx's real-IP module with that provider's address ranges first.

### Production checklist

- Set a strong `SECRET_KEY` and the bootstrap administrator credentials before the first start.
- Serve over HTTPS and set `SESSION_COOKIE_SECURE=1`.
- Set `TRUST_PROXY_HEADERS=1` only behind a trusted proxy that replaces forwarded headers.
- Persist and back up the `instance` directory, including the VAPID private key and Firebase service account file.
- Add the deployed domain to the Google Maps key's allowed referrers.
- Review `/privacy` and set `PRIVACY_OPERATOR_NAME`, `PRIVACY_DATA_REGION`, and `PRIVACY_CONTACT`.
- Point monitoring at `/healthz`.

FFmpeg and the Noto Sans TC font used for preview images are bundled, both in and outside Docker.

## Data and storage

- Courts expire after their date and end time. Expired courts are read-only and hidden from default listings. A leave deadline, if set, applies earlier: players can still join but can no longer leave on their own.
- Archived courts stay reachable by direct link and from the organizer and administrator dashboards, but their message boards accept no new posts.
- Everything is stored under `instance/`: the SQLite database (`courts.sqlite`, unless `COURT_DATABASE` is set), avatars (`avatars/`), court media (`court_media/`), and cached preview images (`social_thumbnails/`). Replacing or deleting records removes their files.
- `court_info.md` exports hold reusable court settings and reserved nicknames as a JSON block. They exclude registrations, PINs, history, messages, media, ownership, and the original GUID. Imports are limited to 64 KB, only prefill the form, and pass normal validation on save.
- The administrator CSV export (UTF-8 with BOM) has one row per court, including archived and expired ones. It excludes PINs and join/leave history.

## Security and privacy

- Passwords and PINs are stored as password hashes. Repeated failed sign-ins, leave attempts, and message-board PIN attempts lock that username and IP temporarily.
- Message-board posts are 1–500 characters and limited to five per IP per court every 10 minutes. Only players who joined the court, its organizer, and administrators can post.
- State-changing forms are protected against CSRF. API requests use bearer tokens and never the session cookie.
- Join/leave history records the nickname, action, and time. Administrators also see the validated IP and a broad device type (iOS, Android, Mobile, Web). Full User-Agent strings and device fingerprints are not kept. Failed attempts are not added to the history.
- Push endpoints, keys, and FCM tokens are stored only to deliver the notifications people turned on, and are never shown.
- Contact messages and their reply details are visible only to administrators.
- Banning a member blocks their sign-in and organizer tools without deleting their courts. Joining courts by nickname and PIN stays open to everyone.
- The public policy at `/privacy` covers the app's own data handling. Self-hosting operators must add anything deployment-specific, such as server logs, backups, or extra services.

See [docs/PRIVACY.md](../docs/PRIVACY.md) for the full list of stored data and third-party services. Report vulnerabilities privately as described in [docs/SECURITY.md](../docs/SECURITY.md).

## Development

Read [docs/CONTRIBUTING.md](../docs/CONTRIBUTING.md) before you open a pull request.

### Tests

```bash
.venv/bin/pytest -q
node tests/test_court_controls.cjs     # browser-control logic, no packages needed
node tests/test_court_navigation.cjs
```

The [`web.yml`](../.github/workflows/web.yml) workflow runs these tests on Python 3.10 and 3.13 when `web/` changes.

### JSON API

`/api/v1` exposes player, organizer, account, and administrator functions as JSON. Clients sign in with `POST /api/v1/auth/login` and send `Authorization: Bearer <token>`. The API shares validation, throttling, and permission rules with the HTML pages. See [API.md](API.md) for the endpoint reference. When the API changes, update `api.py`, `API.md`, and `tests/test_api.py` together.

### Translations

All interface text lives in the `TRANSLATIONS` table in `app.py`, with matching `en-us` and `zh-tw` keys. The Android app generates its string resources from this table, so run `python3 tools/gen_strings.py` in `android/` after changing shared wording.

### Update history

The `/updates` timeline comes from `data/update_history.json`, newest entry first. Each entry needs `date`, `date_label`, `title`, `summary`, and a non-empty `items` list, each in both `en-us` and `zh-tw`. The app validates the file at startup and refuses to start if it is malformed, incomplete, or out of order.

## Attribution and licenses

The source code is released under the [MIT License](../LICENSE). Bundled third-party assets keep their own licenses.

The favicon, [`static/shuttlecock.png`](static/shuttlecock.png), is based on the [Shuttlecock icon by Flaticon](https://www.flaticon.com/free-icon/shuttlecock_9719863). Preview images use the bundled [Noto Sans TC](https://github.com/notofonts/noto-cjk) font under the SIL Open Font License 1.1. Attribution and license links are also shown at `/licenses`.

Badminton Court Control Panel was developed with support from [OpenAI Codex](https://openai.com/codex/) for implementation, review, and testing. Responsibility for the website, its operation, and its content remains with the project owner; this acknowledgment does not imply OpenAI endorsement or ownership.
