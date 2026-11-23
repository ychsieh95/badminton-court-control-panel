# UI brief — Badminton Court Control Panel (Android)

This brief is for anyone changing the Android app's screens: what the app is, which layer owns what, the state contract screens build on, and the visual rules that keep the app consistent with the website. Read [Android/AGENTS.md](../Android/AGENTS.md) first for build, string, and verification rules.

## What the app is

A native client for the court system's `/api/v1` JSON API (see [Web/API.md](../Web/API.md)). It offers what the website offers through that API, in English and Traditional Chinese (Taiwan).

- **Players** browse and filter courts, open a court from a shared or pasted link, join or leave with a nickname and 6-digit PIN (no account), land on the waiting list when a court is full, read and post on the message board, and follow a court for notifications.
- **Organizers** sign in to create, edit, duplicate, archive, restore, and delete their courts, reply to messages, and run roll call and payment clearing.
- **Administrators** moderate every court, player, and message, manage users, and read contact messages.

Most people open the app to answer "is there a place for me, and when and where is it?", so court cards and the court page put status, schedule, capacity, and place first.

## Layers and ownership

The app is one `:app` module under `io.github.ychsieh95.bccp`.

| Layer | Package | UI work may change it? |
| --- | --- | --- |
| Screens and view models | `feature/<area>/` (`courts`, `courtdetail`, `courtform`, `auth`, `account`, `admin`, `contact`, `settings`) | Yes |
| Shared UI | `core/ui/component/`, `core/ui/theme/`, `core/ui/format/`, `core/ui/UiMessage.kt` | Yes, keeping existing callers working |
| Navigation | `navigation/` (`Routes.kt`, `BccpApp.kt`, `AppViewModel.kt`) | Yes, for new routes and tabs |
| Resources | `res/` | Yes, except `values*/strings.xml` and generated launcher and notification icons |
| Data | `core/data/`, `core/network/`, `core/model/`, `core/push/`, `core/di/` | Only when the screen needs data the layer does not yet expose |

If a screen needs something the API does not provide, say so rather than working around it. The API is extended only on request, together with `Web/api.py`, `Web/API.md`, `Web/tests/test_api.py`, the app's models, and the test fixtures.

## Contract to build against

- **One state per screen.** Each view model exposes a single immutable `UiState` data class as `StateFlow`, for example `CourtDetailUiState` (court, loading, not-found, error, busy flags, player and message forms, roll-call draft, push state, message board). Composables collect it with `collectAsStateWithLifecycle()` and never hold their own copy of server data.
- **One-off events go through a `Channel`.** Snackbars, sheet dismissal, and navigation after a delete are effects such as `CourtDetailEffect.Message`, `PlayerSheetDone`, and `Deleted`, collected once per screen.
- **Actions are an interface.** Where a screen has many actions, the view model implements a `@Stable` actions interface (such as `CourtDetailActions`) that is passed down instead of many lambdas.
- **Errors come from repositories.** Repositories return `Result<T>` and map failures to `DataError`. Show them through `UiMessage`: `Throwable.toUiMessage()` turns `DataError.Api` into the server's localized message (the server localizes from `Accept-Language`) and network or unexpected failures into app strings. Show `Throwable.fieldErrors` under the matching form fields. Do not invent client-side wording for server errors.
- **Session.** `SessionStore` holds the token and signed-in user. A `401 invalid_token` response signs the app out, and changing the server address signs the user out; screens react to the session rather than handling these cases themselves. The **Admin** tab appears only when `user.role.moderatesCourts` is true.
- **Settings.** `SettingsStore` provides the server URL, `ThemeMode` (System, Light, Dark), `Palette` (Mono, Green, Purple, Yellow, Dynamic; Yellow by default), and the last nickname used to join, which prefills the join and message forms.
- **Time format.** Use the helpers in `core/ui/format/Formatters.kt` (`clock`, `dateTime`, `courtSchedule`, `weekday`, `levelLabel`). They follow the member's 12- or 24-hour choice through `LocalUse12h`.

## Navigation and screens

Bottom navigation has **Courts**, **Organize**, **Admin** (moderators only), and **Account**. Routes are type-safe `@Serializable` objects in `navigation/Routes.kt`.

1. **Courts** (`CourtsRoute`): court cards with search and a filter sheet (date range, level, gender, status, expired). Pasting or sharing a court link into the app opens the court; `CourtLinks.guidFrom` accepts a URL, text containing one, or a bare GUID.
2. **Court page** (`CourtDetailRoute`, optionally `showMessages` to scroll to the board, as from a message notification): status, schedule, capacity, media, prices, level guide, remark, reserved players, players, waiting list, and join/leave history; share, copy link, open in browser or Maps, download the share image. Joining and leaving use the player sheet. After joining, offer to follow the court; after leaving, offer to stop. The message board shows threads, with a sheet for posting and replying. Organizers and administrators get the participant menu and the roll-call panel.
3. **Organize** (`OrganizeRoute`) and the court form (`CourtFormRoute`, editing with `guid` or prefilling from another court with `copyFrom`): saved halls, reserved nicknames, level ranges, prices, leave deadline, and photo and video upload through the system photo picker.
4. **Account** (`AccountRoute`): sign in and sign up (`AuthRoute`, with Turnstile when the server enables it), profile and picture (with delete account), change password (required after an administrator sets a temporary one), signed-in devices, contact, and app settings (server address with a connection test, theme, palette; Dynamic is offered only on Android 12 and later).
5. **Admin** (`AdminRoute` and its courts, users, and messages routes): moderation lists with the same filters as the public listing, user management, and the contact inbox.

Every screen handles loading (`LoadingPane`), error with retry (`ErrorPane`), and empty states (`MessagePane`).

## Visual direction

- **Match the website.** `core/ui/theme/Palettes.kt` copies the website stylesheet's CSS variables for each palette in light and dark (`WebTokens`), and `Theme.kt` maps them onto the Material 3 color scheme. Change colors there, in step with `Web/static/css/styles.css`, never inline in a screen. The **Dynamic** palette uses the device's colors on Android 12 and later and falls back to the Mono tokens.
- **Extra roles.** The website's warning color (expired courts) and lime accent highlight have no Material slot; read them from `LocalExtraColors`.
- **Shapes.** Use the theme's shape scale (6, 10, 18, 24, and 28 dp corners) rather than custom radii.
- **Shared components first.** Use `PanelCard`, `SectionHeader`, `PrimaryActionButton`, `TextInput`, `SecretInput` (PINs and passwords), `DropdownField`, `DateField`, `TimeField`, `SwitchRow`, `ConfirmDialog`, `CourtCard`, `StatusBadge`, `Pill`, `CountBadge`, `DateChip`, `IconLine`, and `UserAvatar` before adding a new one. Keep field labels to one line so neighbouring fields keep the same height.
- **Status is never color-only.** Court status, waiting-list position, and expired or archived states carry a label or icon as well as color.
- **Layout.** The app is edge-to-edge and uses `adjustResize` for forms. Confirm destructive actions (leave, delete, remove a player) with `ConfirmDialog`.
- **Text.** Every user-visible string, including content descriptions, comes from string resources. Shared wording is generated from `TRANSLATIONS` in `Web/app.py`; app-only wording goes in `Android/tools/extra_strings.json`. Regenerate with `python3 tools/gen_strings.py` and never edit `strings.xml` by hand. Check long Traditional Chinese and English strings at narrow widths.
- **Previews.** If you add `@Preview`s, use fictional courts, nicknames, and messages only.

## Done means

From `Android/`, `./gradlew :app:testDebugUnitTest` and `./gradlew :app:assembleDebug` succeed, and the generated strings are up to date. When a device or emulator is available, the changed screens have been checked in English and Traditional Chinese and in light and dark themes against a local server at `http://10.0.2.2:5000`.
