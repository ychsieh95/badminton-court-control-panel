# JSON API v1

Base path: `/api/v1`. Request and response bodies are JSON (`Content-Type: application/json`) unless noted.

## Authentication

1. `POST /auth/login` (or `/auth/signup`) returns a bearer token:

   ```json
   {"token": "bccp_…", "token_type": "Bearer", "expires_at": "2027-02-18T10:00:00", "user": {…}}
   ```

2. Send it on later requests: `Authorization: Bearer bccp_…`.

- Tokens last `API_TOKEN_TTL_DAYS` (default 90) days. Only a SHA-256 hash is stored on the server.
- An unknown, revoked, or expired token returns `401 invalid_token`. Sign in again when that happens.
- Changing the password revokes every other token on the account. Admin-set temporary passwords revoke all of the user's tokens.
- When `user.must_change_password` is `true`, only `GET /me`, `POST /me/password`, and `POST /auth/logout` work. Every other member endpoint returns `403 temporary_password_required`.
- The API never reads the website's session cookie, so no CSRF token is needed.
- When Cloudflare Turnstile is enabled (see `GET /meta`), `signup`, `login`, and `contact` require a `turnstile_token` field.

## Language

Error messages are localized. Set the language with `?lang=zh-tw|en-us` or `Accept-Language`.

## Errors

```json
{"error": {"code": "duplicate_username", "message": "That username has already joined this court.", "fields": {"end_time": "End time must be later"}}}
```

`fields` appears only on validation errors. Branch on `code`, not on `message`.

| Status | Typical codes |
| --- | --- |
| 400 | `bad_request`, `invalid_username`, `invalid_pin`, `password_too_short`, `unknown_member` |
| 401 | `unauthorized`, `invalid_token`, `invalid_credentials` |
| 403 | `forbidden`, `temporary_password_required`, `leave_failed`, `court_message_auth_failed`, `account_banned`, `turnstile_required` |
| 404 | `not_found`, `participant_not_found`, `court_message_reply_missing`, `court_message_missing` |
| 409 | `court_closed`, `court_expired`, `court_read_only`, `leave_deadline_passed`, `duplicate_username`, `username_taken`, `court_not_read_only`, `court_message_closed` |
| 413 | `payload_too_large`, `avatar_too_large` |
| 422 | `invalid_form`, `contact_form_invalid` (see `fields`) |
| 429 | `login_locked`, `leave_locked`, `court_message_locked`, `court_message_rate_limited` |

## Objects

**Court** (list items and detail):

```json
{
  "guid": "…", "event_name": "", "badminton_name": "", "court_date": "2026-12-01",
  "start_time": "19:00", "end_time": "21:00", "hall_name": "", "location": "",
  "google_place_id": "", "latitude": null, "longitude": null, "court_id": "A1",
  "creator_username": "", "created_at": "…",
  "status": "open | full | read_only | expired | archived",
  "archived": false, "expired": false, "roll_clearing_locked": false,
  "leave_deadline": {"enabled": false, "at": null, "passed": false},
  "members": {"min": 4, "max": 8, "reserved": 0, "signed_up": 3, "waiting": 0, "confirmed_total": 3},
  "levels": {"male": {"min": 1, "max": 18}, "female": {"min": 1, "max": 18}},
  "prices": {"male": 0, "female": 0},
  "shuttlecock_info": "", "remark": "", "reserved_names_visible": true,
  "cover_image_url": null, "web_url": "…", "thumbnail_url": "…"
}
```

**Court detail** adds:

- `participants` and `waiting_participants`: `{id, username, joined_at}`. Managers also get `roll_called` and `cleared`.
- `reserved_members`
- `media`: `{id, media_type, mime_type, original_name, url}`
- `participation_history`: admins also get `ip_address` and `device_information`.
- `viewer`: `{is_owner, is_admin, can_manage}`
- For managers only: `form_values` and `reserved_nicknames`, in the same shape that `PATCH /courts/<guid>` accepts.
- For the owner only: `owner_notifications` (bool), whether the organizer gets change notifications for this court.

List responses include `pagination: {total, limit, offset}`. Use `?limit=` (1–200, default 100) and `?offset=`.

## Endpoints

### Public

| Method | Path | Body / query | Notes |
| --- | --- | --- | --- |
| GET | `/version` | | `{app_version, api_version, last_updated}`. `app_version` comes from `APP_VERSION`, or the newest update-history date if unset |
| GET | `/status` | | `{status: ok \| degraded, checks: {database}, server_time, started_at, uptime_seconds, …version}`. `503` when a check fails |
| GET | `/meta` | | API version, Turnstile settings, `push: {fcm}`, input limits, default court values |
| GET | `/courts` | `q, date_from, date_to, level, gender, status, show_expired=1, limit, offset` | Same filters as the `/courts` page |
| GET | `/courts/<guid>` | | Court detail |
| POST | `/courts/<guid>/join` | `{username, pin}` (6-digit PIN) | `201 {court, waitlisted}` |
| POST | `/courts/<guid>/leave` | `{username, pin}` | `200 {court}`. Throttled per court |
| GET | `/courts/<guid>/messages` | `version?` | Message board. `{changed: true, messages, count, version}`; with the current `version`, just `{changed: false, version}` |
| POST | `/courts/<guid>/messages` | `{username, pin, message, parent_id?, fcm_token?}` | `201 {message_id, thread_id, changed, messages, count, version}`. See below |
| DELETE | `/courts/<guid>/messages/<id>` | | Organizer or admin. Removes the message and its replies; returns the board |
| POST | `/contact` | `{sender_name, reply_contact?, subject, message, client?, turnstile_token?}` | `201 {sent: true}`. `client: {platform, app_version, os_version, device_model}` (strings, each ≤ 60 characters) is added to the Telegram/Discord report |

### Message board

`messages` lists threads newest first: `{id, author_name, author_kind: participant | organizer, message, posted_at, ip_address (admins only), replies: [...]}`, with replies oldest first. Replies to a reply attach to the top-level message.

- **Who can post.** A player must have joined the court and sends the `username` and `pin` they joined with. Wrong PINs count toward a lockout (`court_message_locked`). A signed-in organizer of the court, or an administrator, posts as their account with `author_kind: organizer` and needs no PIN.
- **Limits.** `message` is 1–500 characters. Five posts per IP per court in 10 minutes (`court_message_rate_limited`). Archived courts reject posts (`court_message_closed`).
- **Notifications.** The organizer gets one for each new message or reply; the thread's author gets one for each reply. Payloads use `type: court_changed` with `change: message | reply` and no message text. Send `fcm_token` to get reply notifications on a device that follows the court (it is ignored otherwise); signed-in authors are reached through their account's devices.

### Push notifications (Android, FCM)

The Android app subscribes its Firebase Cloud Messaging registration token per court, the same way the website subscribes a Web Push endpoint. No account is needed. These endpoints need `FCM_SERVICE_ACCOUNT_FILE` on the server; `GET /meta` reports it as `push.fcm`.

| Method | Path | Body | Notes |
| --- | --- | --- | --- |
| POST | `/courts/<guid>/push/status` | `{token}` | `{subscribed}` |
| PUT | `/courts/<guid>/push` | `{token}` | `{subscribed: true}`. Saves the request language for notification text. `503 push_unavailable` when FCM is off |
| DELETE | `/courts/<guid>/push` | `{token}` | `{subscribed: false}` |
| PUT | `/push/token` | `{previous_token, token}` | Moves all subscriptions to a refreshed token. `{subscriptions}` |

Each court change (edit, archive, restore, roll call started, editing restored, delete, member list change) sends a high-priority **data** message with string fields `type: "court_changed"`, `guid`, `change`, `audience` (`subscription` or `owner`), `title`, `body` (localized) and `url`. The app builds the notification itself. Tokens FCM reports as unregistered are removed.

**Organizer notifications.** A signed-in app links its FCM token to its bearer token with `PUT /me/push-token`. Changes to a court then also reach every device its owner is signed in on (`audience: "owner"`), unless the owner made the change or turned `owner_notifications` off for that court. A device that is both subscribed and the owner's gets one message. Signing out drops the link.

| Method | Path | Body | Notes |
| --- | --- | --- | --- |
| PUT | `/me/push-token` | `{token}` | `{registered: true}`. Saves the request language. A token belongs to one sign-in at a time |
| DELETE | `/me/push-token` | | `{registered: false}` |

### Account

| Method | Path | Body | Notes |
| --- | --- | --- | --- |
| POST | `/auth/signup` | `{username, password, confirm_password?, device_name?, turnstile_token?}` | `201` token response |
| POST | `/auth/login` | `{username, password, device_name?, turnstile_token?}` | Token response. Throttled |
| POST | `/auth/logout` | | Revokes the current token. `204` |
| GET | `/auth/tokens` | | Signed-in devices. `current` marks this one |
| DELETE | `/auth/tokens/<id>` | | Sign out a device. `204` |
| GET | `/me` | | Current user |
| PATCH | `/me` | `{time_format: "12h" \| "24h"}` | |
| POST | `/me/password` | `{current_password, new_password, confirm_password?}` | |
| PUT | `/me/avatar` | multipart, `avatar` file (JPEG/PNG/WebP, ≤ 2 MB) | |
| DELETE | `/me/avatar` | | |
| GET | `/me/saved-locations` | | |
| DELETE | `/me/saved-locations/<id>` | | `204` |
| DELETE | `/me` | `{current_password}` | Delete account. Not allowed for admins. `204` |

### Organizer (owner, or any admin)

| Method | Path | Body | Notes |
| --- | --- | --- | --- |
| GET | `/me/courts` | `limit, offset` | Courts you own, including archived ones |
| POST | `/courts` | Court fields, `reserved_nicknames: [str]`, `save_location: bool`, `owner_notifications: bool` (default `true`) | `201 {court}`. Missing fields use `GET /meta` → `court_defaults` |
| PATCH | `/courts/<guid>` | Any court fields, `reserved_nicknames`, `remove_media_ids: [int]`, `owner_notifications` (owner only; ignored for admins editing someone else's court) | Partial update. `409 court_read_only` while roll call is running |
| DELETE | `/courts/<guid>` | | `204` |
| POST | `/courts/<guid>/archive` | | |
| POST | `/courts/<guid>/restore` | | |
| POST | `/courts/<guid>/roll-clearing` | | Start roll call and clearing (event becomes read-only) |
| PATCH | `/courts/<guid>/roll-clearing` | `{participants: [{id, roll_called?, cleared?}], reserved_members: [...]}` | Updates only the listed members and flags |
| DELETE | `/courts/<guid>/roll-clearing` | | Back to editing mode |

Court fields: `event_name, badminton_name, court_date (YYYY-MM-DD), start_time, end_time (HH:MM, 24h), hall_name, location, google_place_id, latitude, longitude, court_id, remark, shuttlecock_info, male_price, female_price, member_min, member_max, ordered_count, male_level_min, male_level_max, female_level_min, female_level_max, reserved_names_visible (bool), leave_deadline_enabled (bool), leave_deadline_at (YYYY-MM-DDTHH:MM)`.

**Uploading media:** send `multipart/form-data` to `POST /courts` or `PATCH /courts/<guid>`. Put the JSON body in a `court` form field and attach files as `media` parts. The limit is 12 files per court: images ≤ 8 MB, videos ≤ 50 MB.

### Admin

`sub_admin` and above can use the court-moderation endpoints. `admin` and `super_admin` can use the account and site endpoints. Only `super_admin` can change roles.

| Method | Path | Body | Role |
| --- | --- | --- | --- |
| GET | `/admin/courts` | Filters as `/courts`, plus `status=archived` | sub_admin+ |
| PATCH | `/courts/<guid>/participants/<id>` | `{username?, pin?}` | sub_admin+ |
| DELETE | `/courts/<guid>/participants/<id>` | | sub_admin+ |
| GET | `/admin/users` | | admin+ |
| POST | `/admin/users/<id>/archive` · `restore` · `ban` · `unban` · `reset-login-retries` | | admin+ |
| POST | `/admin/users/<id>/temporary-password` | `{temporary_password}` | admin+ |
| DELETE | `/admin/users/<id>` | Account must be archived first | admin+ |
| PUT | `/admin/users/<id>/role` | `{role: member \| sub_admin \| admin \| super_admin}` | super_admin |
| GET | `/admin/messages` | `status=all\|unread\|read, page` | admin+ |
| PATCH | `/admin/messages/<id>` | `{read: bool}` | admin+ |
| GET / PATCH | `/admin/settings` | `{homepage_court_limit?: 1–100, contact_notifications_enabled?: bool}` | admin+ |

## Not in the API

- **CSV and `court_info.md` export/import:** the court detail's `form_values` and `reserved_nicknames` already cover duplicating an event.
- **Static pages:** introduction, updates, privacy, and licenses stay web-only.
