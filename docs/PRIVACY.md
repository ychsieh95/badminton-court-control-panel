# Privacy

This page describes how Badminton Court Control Panel's own code handles data, on the website, the JSON API, and the Android app. It is written for contributors and self-hosting operators. The policy shown to visitors is the website's `/privacy` page; operators must add anything specific to their deployment, such as server logs, backups, hosting region, or extra services.

The project has no analytics, advertising, tracking pixels, or crash reporting, in either the website or the app.

## What the server stores

Everything is kept on the server that runs the website, under `instance/`: the SQLite database, profile pictures, court photos and videos, and cached preview images.

- **Players** (no account needed): the nickname used to join a court, a hash of their 6-digit PIN, and their place on the confirmed or waiting list.
- **Join and leave history:** nickname, action, and time. Administrators also see the client IP and a broad device type (iOS, Android, Mobile, Web). Full User-Agent strings and device fingerprints are not kept, and failed attempts are not added to the history.
- **Message board:** each post's text, nickname or account, time, and IP address. The IP is shown only to administrators.
- **Members:** username, password hash, role, profile picture, time format, saved halls, and the courts they organize. API tokens are stored as hashes with a device name, creation time, last-used time, and expiry.
- **Contact messages:** the message and the reply details the sender gives, visible only to administrators.
- **Notifications:** Web Push endpoints and keys, and FCM device tokens, linked to the courts someone follows. They are used only to deliver notifications people turned on and are never shown.
- **Abuse protection:** short-lived counters of failed sign-in, leave, and message-board PIN attempts per username or nickname and IP.

Deleting a record removes its files. Members can delete their own account on the website or in the Android app; this removes their profile and sign-in access, while courts they published stay available for administrators to manage. Administrators can also archive or delete members.

Exports are limited on purpose. `court_info.md` holds reusable court settings and reserved nicknames only, without registrations, PINs, history, messages, media, ownership, or the court's GUID. The administrator CSV export excludes PINs and join/leave history.

## What the browser stores

- The session cookie (`HttpOnly`, `SameSite=Lax`) for signed-in members and CSRF protection.
- `court_lang`, the language a visitor chose by hand, for one year.
- `court_section_*` cookies remembering which court page sections are collapsed, for one year.
- `court-theme` and `court-palette` in `localStorage`, and `court-introduction-prompt-seen-v1`, a flag that the first-visit introduction was shown.

## Third-party services

Each of these is used only when the operator configures it, except Google Fonts.

| Service | When it is contacted | What it receives |
| --- | --- | --- |
| Google Fonts (`fonts.googleapis.com`, `fonts.gstatic.com`) | Every website page view, by the visitor's browser | The visitor's IP and browser details |
| Google Maps JavaScript API and Places API | On the court form, when `GOOGLE_MAPS_API_KEY` is set | The organizer's hall search |
| Google Maps links | Only when someone taps a map link | The hall name or address |
| Cloudflare Turnstile (`challenges.cloudflare.com`) | Sign-up, sign-in, and the contact form, when both Turnstile keys are set; also in the Android app's sign-in WebView | What Turnstile collects to tell people from bots |
| The browser's push service | When a visitor turns on notifications for a court | Encrypted notification payloads |
| Firebase Cloud Messaging (`fcm.googleapis.com`) | When the server notifies Android devices, if `FCM_SERVICE_ACCOUNT_FILE` is set | The device token and the notification text |
| Discord webhook and Telegram Bot API | For each new contact message, when configured | The contact message and its reply details |

The visitor's country, used only to choose the default language, comes from a header set by a trusted proxy (such as Cloudflare's `CF-IPCountry`) or a local MaxMind database. No external lookup is made.

## The Android app

The app talks only to the server it is set to (`https://badminton.holey.cc` by default, changeable in **Account → App settings**), plus Firebase Cloud Messaging and, when the server enables it, Cloudflare Turnstile during sign-in. Images and videos are loaded from that server.

On the device, app-private DataStore holds the sign-in token and signed-in user, the server address, theme and palette, the last nickname used to join a court (to prefill the next form), and the FCM token. Android backup is disabled. Signing out clears the token, and uninstalling the app removes everything.

The app requests two permissions: **Internet**, to reach the server, and **Notifications** (Android 13 and later), for court notifications the user turns on. Photos are chosen through the system picker, so the app needs no storage permission.

## Inspecting the code

The source is public, so these behaviors can be checked. If this page and the code disagree, the code is right and this page should be fixed.
