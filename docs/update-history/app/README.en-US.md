# App update history

Changes that people using the website or the Android app can notice. Website changes released before November 2026 are listed on the site's `/updates` page, from `web/data/update_history.json`.

## Unreleased

### Android app

Adds a native Android app (Android 8.0 or later) built on the website's JSON API, in English and Traditional Chinese. Players can browse, filter, and open courts from shared links, join or leave with a nickname and PIN, and follow courts for notifications through Firebase Cloud Messaging. Organizers can create, edit, duplicate, archive, and delete courts and run roll call and clearing, and administrators can moderate courts, players, users, and contact messages. The app uses the website's palettes, with Yellow as the default, and can be pointed at any deployment from App settings.

### Court form readability in the Android app

Keeps court form labels on one line so empty fields stay the same height as their neighbours, shows only the level number in the half-width level fields with the level name underneath, gives the leave-deadline date more room than the time, and keeps section descriptions from pushing their badge aside.

### Court information file chooser

Restyles the file chooser for importing `court_info.md` on the court form so it matches the other form controls.

### Court message board

Each court now has a message board on the website and in the Android app. Players who joined a court can ask questions and reply with the nickname and PIN they joined with, and the court's organizer and administrators post as their account and can delete messages with their replies. The board refreshes itself while the page is open, and organizers and people who posted are notified of new messages and replies. Messages are limited to 500 characters and five posts per IP per court every 10 minutes, and archived courts accept no new posts.

### JSON API

Adds a versioned JSON API under `/api/v1` for courts, joining and leaving, organizer tools, accounts, contact, and administration. It signs in with expiring bearer tokens, of which only hashes are stored, and members can see and sign out their signed-in devices. The website and the API share the same validation, throttling, and permission rules.

### Message board hint spacing

Removes the stray space between the two sentences of the message board hint in Traditional Chinese.
