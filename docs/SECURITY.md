# Security Policy

## Supported version

Security fixes are provided for the latest version of the website on `main` and the latest published Android app.

## Reporting a vulnerability

Use the repository's private GitHub Security Advisory reporting flow. Do not post a working exploit, API tokens, session cookies, PINs, passwords, `.env` values, Firebase or VAPID keys, or real player data in a public issue. If a reproduction needs a request or response, redact tokens, PINs, IP addresses, and account names first, and use a local server rather than a live deployment.

## Trust boundary

**Accounts and PINs.** Member passwords and players' 6-digit PINs are stored only as Werkzeug password hashes. Repeated failed sign-ins lock the username and IP temporarily (`LOGIN_MAX_ATTEMPTS`, `LOGIN_LOCKOUT_SECONDS`). Wrong leave attempts are counted per court, nickname, and IP (`LEAVE_MAX_ATTEMPTS`, `LEAVE_LOCKOUT_SECONDS`), and wrong PINs on the message board count toward the same kind of lockout. A temporary password set by an administrator must be changed at the next sign-in. Banning a member blocks sign-in and organizer tools without deleting their courts.

**Roles.** Members, sub-admins, admins, and super-admins have separate permissions. Organizers manage only their own courts; moderation tools are limited to administrators, and only super-admins change roles. The first super-admin is created from `ADMIN_USERNAME` and `ADMIN_PASSWORD` only when none exists. Deployments must replace the development defaults and `SECRET_KEY` before the first start.

**Website sessions.** Sessions are signed with `SECRET_KEY` and use `HttpOnly`, `SameSite=Lax` cookies, with `Secure` when `SESSION_COOKIE_SECURE=1`. Every state-changing form carries a CSRF token. Cloudflare Turnstile, when configured, protects sign-up, sign-in, and the contact form; the server checks each token and its expected action before handling the request.

**JSON API.** `/api/v1` authenticates with `Authorization: Bearer` tokens and never reads the session cookie, so it needs no CSRF token. Tokens are random, only their SHA-256 hashes are stored, and they expire after `API_TOKEN_TTL_DAYS` (90 by default). Signed-in members can list and revoke their tokens as signed-in devices. Changing a password revokes every other token on the account, and an administrator-set temporary password revokes all of them. A rejected token returns `401 invalid_token`. The API reuses the website's validation, throttling, and permission helpers rather than its own copies.

**Client IP and proxies.** Forwarded client-IP and scheme headers are ignored unless `TRUST_PROXY_HEADERS=1`. Enable it only behind a proxy that replaces those headers, otherwise visitors can spoof the IP used for lockouts, rate limits, and history.

**Message board.** Posts are 1–500 characters and limited to five per IP per court every 10 minutes. Only players who joined the court (with their nickname and PIN), its organizer, and administrators can post. Archived and expired courts accept no new posts. Message text is escaped by the server's templates, including in the board's live refresh, and shown as plain text in the app.

**Uploads.** Court media is limited to 12 files per court: JPEG, PNG, or WebP up to 8 MB and MP4 or WebM up to 50 MB. Profile pictures are JPEG, PNG, or WebP up to 2 MB. Uploaded files are saved under random names in `instance/`, and `court_info.md` imports are limited to 64 KB, only prefill the form, and pass normal validation on save.

**Push and outbound requests.** Web Push uses VAPID keys and FCM uses a Firebase service account; neither private key is ever sent to browsers or the app. Push endpoints, keys, and FCM tokens are stored only to deliver notifications people turned on and are never shown. Turnstile, Web Push, FCM, and Discord/Telegram contact notifications each use a short delivery timeout.

**Android app.** The bearer token and FCM token are kept in app-private DataStore, and Android backup is disabled. A `401 invalid_token` response signs the app out, and changing the server address signs the user out, because a token is only valid on the server that issued it. Debug builds log only request lines, with the `Authorization` header redacted; release builds log nothing. Cleartext `http://` is allowed so the app can reach LAN and emulator servers; public servers should use `https://`, which is checked against the system trust store. The launcher activity is exported so it can be launched and receive shared court links, which it only parses for a court ID. The FCM service is not exported.

**Self-hosting.** Operators are responsible for HTTPS, `SESSION_COOKIE_SECURE=1`, a long random `SECRET_KEY`, keeping `.env` and `instance/` out of public reach, and backups. The Docker image runs as a non-root user and stores data in a named volume.
