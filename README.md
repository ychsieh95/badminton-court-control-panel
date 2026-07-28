# badminton-court-control-panel

**English (default)** · [繁體中文](README.zh-TW.md)

Badminton Court Control Panel is a bilingual Flask application for organizing badminton events. Organizers can publish and manage courts, while players can discover, join, or leave an event without creating an account.

## Features

### For players

- Browse active courts and filter by keyword, creator, date range, player level, gender range, capacity, and event status.
- Join or leave with a nickname and private 6-digit PIN—no account required.
- Enter a FIFO waiting list automatically when confirmed places are full.
- Opt in to court-specific system push notifications when event information or the member list changes.
- View the schedule, weekday, hall, location, prices, shuttlecock, levels, organizer, remarks, participant lists, and event media.
- Share court links with a 1200×630 social preview generated from the first event photo, a frame from the first event video, or the event information when no media exists.
- Use a floating, accessible join dialog on mobile screens.

### For organizers

- Create an account and manage personal events from `/my-courts`.
- Publish optional event and badminton-group names with permanent UUID links in the form `https://your-domain.example/<GUID>`.
- Configure the date, 24-hour start/end time, Google Place hall, court ID, capacity range, reserved places, male/female level ranges, prices, shuttlecock, and remarks.
- Save frequently used hall locations while creating an event, reuse them without searching, and delete them from the profile page.
- Record reserved-player nicknames and choose whether visitors can see them.
- Upload up to 12 JPEG, PNG, WebP, MP4, or WebM files. The first image becomes the court-card cover.
- Edit, duplicate, archive, restore, or delete owned events.
- Start **Roll call & clearing** to make an event read-only and track attendance and payment-clearing status.

### For administrators

- Create, edit, duplicate, archive, restore, and delete any court.
- Use private, account-owned saved locations from the same new-event form as members.
- Assign member, sub-admin, admin, or super-admin roles; only super-admins can change roles.
- Filter all courts with the same controls available on the public listing, including archived and expired events.
- Configure the maximum number of courts displayed on the homepage.
- Archive, restore, ban, unban, or permanently delete eligible member accounts.
- Assign temporary passwords that require a password change after sign-in.
- View member last-login time and IP address.
- View each court event’s creation date and time from the administrator dashboard.
- Reset a member’s failed-login retries and active lockouts across all IP addresses.
- View join/leave history with timestamps, validated IP addresses, and broad device categories: iOS, Android, Mobile, or Web.

### Localization and appearance

- Interface languages: English (`en-US`) and Traditional Chinese (`zh-TW`).
- Visitors detected in Taiwan default to Traditional Chinese; other visitors default to English.
- A manually selected language is stored in a cookie and overrides country detection.
- First-time visitors can choose whether to open a brief introduction; their choice is remembered in the browser.
- Monochrome, Green & Lime, Purple, and Yellow palettes are available in system, light, and dark modes.
- New visitors use **Yellow · Light** by default. Saved preferences take precedence.
- Includes the Taiwan Badminton Promotion Association 1–18 grading reference.

## Main routes

| Route | Purpose |
| --- | --- |
| `/` | Homepage and upcoming courts |
| `/introduction` | Public product introduction |
| `/updates` | Public bilingual update history |
| `/courts` | Filterable public court listing |
| `/courts/new` | Shared new-event form for signed-in members and administrators |
| `/<GUID>` | Public court details and registration |
| `/signup` | Member registration |
| `/login` | Member and administrator sign-in |
| `/my-courts` | Organizer dashboard |
| `/account/profile` | Member profile and avatar |
| `/admin` | Administrator dashboard |
| `/admin/users` | Member administration |
| `/licenses` | Asset licenses and development acknowledgments |

## Local setup

Python 3.10 or newer is recommended.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Update `.env`, then start the development server:

```bash
flask --app app run --debug
```

Open <http://127.0.0.1:5000>. Members and administrators use the same `/login` form. Successful member sign-ins redirect to `/my-courts`; administrator roles redirect to `/admin`. The legacy `/admin/login` URL redirects to `/login`.

On a database without a super-admin, the application creates or promotes the configured `ADMIN_USERNAME` as the initial database-backed super-admin and hashes `ADMIN_PASSWORD`. Later environment changes do not overwrite an existing super-admin password; change it from the account password page instead.

The development bootstrap credentials are `admin` / `change-me`. Always replace `SECRET_KEY`, `ADMIN_USERNAME`, and `ADMIN_PASSWORD` before the first production startup.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `SECRET_KEY` | Development value | Flask session and CSRF signing secret. Use a long random production value. |
| `ADMIN_USERNAME` | `admin` | Username used to bootstrap the first database super-admin. |
| `ADMIN_PASSWORD` | `change-me` | Initial bootstrap super-admin password. |
| `TURNSTILE_SITE_KEY` | Empty | Public Cloudflare Turnstile site key; set with the secret key to protect signup and login. |
| `TURNSTILE_SECRET_KEY` | Empty | Private Turnstile Siteverify secret; never expose it to browsers. |
| `TURNSTILE_VERIFY_TIMEOUT` | `5` | Server-side Turnstile verification timeout in seconds. |
| `COURT_DATABASE` | `instance/courts.sqlite` | SQLite database location. |
| `GOOGLE_MAPS_API_KEY` | Empty | Enables Google Places hall autocomplete. |
| `WEB_PUSH_PUBLIC_KEY` | Empty | Public VAPID application-server key shown to browsers. |
| `WEB_PUSH_PRIVATE_KEY` | Empty | Secret VAPID private key value or PEM-file path. |
| `WEB_PUSH_SUBJECT` | Empty | Operator contact URI used in VAPID claims, such as `mailto:admin@example.com`. |
| `WEB_PUSH_TIMEOUT` | `5` | Per-recipient push delivery timeout in seconds. |
| `SOCIAL_THUMBNAIL_FFMPEG` | Bundled executable | Optional FFmpeg executable override used to extract the preview frame when the first event-media item is a video. |
| `SOCIAL_THUMBNAIL_FONT` | Bundled Noto Sans TC | Optional path to a TrueType/OpenType font that overrides the bundled font used for generated information thumbnails. |
| `SESSION_COOKIE_SECURE` | `0` | Set to `1` when the site is served exclusively over HTTPS. |
| `TRUST_PROXY_HEADERS` | `0` | Trust forwarded client-IP and URL-scheme headers. Enable only behind a trusted proxy that replaces them. |
| `GEOIP_COUNTRY_DB` | Empty | Optional local MaxMind GeoIP2/GeoLite2 country database. |
| `DEFAULT_COUNTRY_CODE` | Empty | Optional two-letter fallback country. Unknown visitors otherwise use English. |
| `LOGIN_MAX_ATTEMPTS` | `5` | Failed sign-ins allowed before temporary lockout. |
| `LOGIN_LOCKOUT_SECONDS` | `900` | Lockout duration in seconds. |

Values already present in the process environment take precedence over `.env`.

## Cloudflare Turnstile

Create a [Turnstile widget](https://developers.cloudflare.com/turnstile/get-started/), allow the deployed hostname, and set both `TURNSTILE_SITE_KEY` and `TURNSTILE_SECRET_KEY` to protect `/signup` and the shared `/login` page. The widget uses the `signup` or `login` action, and the server validates both the token and matching action with Cloudflare Siteverify before account creation or credential processing.

Missing, rejected, expired, reused, oversized, malformed, action-mismatched, and unverifiable tokens are denied. If either key is empty or Flask debug mode is active, Turnstile is disabled. The secret key is used only for server-to-server verification and is never rendered into HTML. Cloudflare provides [dedicated test sitekeys and secret keys](https://developers.cloudflare.com/turnstile/troubleshooting/testing/) for automated testing and localhost; never deploy those test credentials to production.

## Google hall search

Set `GOOGLE_MAPS_API_KEY` to a browser key with **Maps JavaScript API** and **Places API (New)** enabled. The Google Cloud project must have billing enabled.

Configure **Websites (HTTP referrers)** for the deployed domain. For local development, allow:

```text
http://127.0.0.1:5000/*
http://localhost:5000/*
```

Without a key, the court form remains usable and provides a live Google Maps search link.

## System push notifications

Each court page includes an opt-in switch for browser/system notifications. Notifications are sent when an organizer edits, archives, restores, locks/unlocks, or deletes that court, and when a player successfully joins, enters the waiting list, or leaves. Failed join/leave attempts and individual roll-call checkbox changes do not send pushes.

Generate one persistent VAPID key pair:

```bash
mkdir -p instance/web-push
cd instance/web-push
../../.venv/bin/vapid --gen --applicationServerKey
```

The command prints the application-server key and creates `private_key.pem`. Set:

```text
WEB_PUSH_PUBLIC_KEY=<printed application-server key>
WEB_PUSH_PRIVATE_KEY=instance/web-push/private_key.pem
WEB_PUSH_SUBJECT=mailto:your-contact@example.com
```

Keep the private key and the entire `instance` directory persistent across deployments. Changing the VAPID key pair invalidates existing browser subscriptions. Production push requires HTTPS and browser permission; localhost is treated as a secure development context by supporting browsers.

If any required VAPID setting is missing, the court-page switch remains disabled. Expired push-service endpoints are removed automatically after a `404` or `410` delivery response.

## Docker

Start the application with Docker Compose:

```bash
docker compose up -d --build
```

Compose loads `.env`, publishes port `8080`, and mounts the named volume `badminton-court-control-data` at `/instance`. The image links `/app/instance` to this directory, so the SQLite database, avatars, and court media persist when containers are recreated. Stop the service without deleting its data:

```bash
docker compose down
```

Build the image from the project root:

```bash
docker build -t badminton-court-control-panel .
```

Run it on port `8080`, load the production environment, and persist the SQLite database and uploads:

```bash
docker run --rm \
  --name badminton-court-control-panel \
  --env-file .env \
  -p 8080:8080 \
  -v badminton-court-control-data:/instance \
  badminton-court-control-panel
```

The image uses `app.py` as the uWSGI module and serves it through Nginx on port `8080`.

## Security and privacy

- Account passwords and participant PINs are stored using secure password hashes.
- Member and administrator sign-ins are temporarily locked after repeated failures from the same username and IP address.
- When configured, Cloudflare Turnstile is verified before signup or sign-in credentials are processed.
- Successful member sign-ins record the local timestamp and validated client IP.
- Successful court joins and leaves record the nickname, action, and timestamp. Administrators additionally see the validated IP and a broad device category.
- Push subscription endpoints and encryption keys are stored only to deliver opted-in court updates and are never displayed publicly.
- Complete browser User-Agent strings and device fingerprints are not retained.
- Failed join/leave attempts are not added to participation history.
- Banning a member blocks account sign-in and member-only organizer access without deleting courts. Public nickname/PIN registration remains login-free.
- CSRF protection is applied to state-changing forms.

## Event lifecycle and storage

- Events expire automatically after their configured date and end time. Expired events become read-only and are hidden from default listings.
- Archived events remain available through direct links and organizer or administrator dashboards.
- SQLite data is stored in `instance/courts.sqlite` unless `COURT_DATABASE` is configured.
- Avatars are stored under `instance/avatars`.
- Court photos and videos are stored under `instance/court_media`.
- Versioned social-sharing thumbnails are cached under `instance/social_thumbnails`.
- Replacing or deleting records cleans up associated uploaded files where applicable.

## Production

- Set a strong `SECRET_KEY`, bootstrap administrator username, and bootstrap password before the first startup.
- Serve the application over HTTPS and set `SESSION_COOKIE_SECURE=1`.
- Set `TRUST_PROXY_HEADERS=1` only when a trusted reverse proxy replaces the forwarded client-IP and URL-scheme headers.
- Persist and back up the configured SQLite database and `instance` upload directories.
- The project bundles the FFmpeg executable and Noto Sans TC variable font required to generate media and information thumbnails, both inside and outside Docker.
- Configure the deployed domain as an allowed Google Maps browser-key referrer.

## Tests

Run the complete test suite inside the virtual environment:

```bash
.venv/bin/pytest -q
```

## Attribution and licenses

The website favicon uses [`static/shuttlecock.png`](static/shuttlecock.png), based on the [Shuttlecock icon by Flaticon](https://www.flaticon.com/free-icon/shuttlecock_9719863?term=badminton&page=1&position=51&origin=search&related_id=9719863). Generated information thumbnails use the bundled [Noto Sans TC](https://github.com/notofonts/noto-cjk) variable font under the SIL Open Font License 1.1. Public attribution and license links are available at `/licenses`.

Badminton Court Control Panel was developed with support from [OpenAI Codex](https://openai.com/codex/) for implementation, review, and testing. Responsibility for the website, its operation, and its content remains with the project owner; this acknowledgment does not imply OpenAI endorsement or ownership.
