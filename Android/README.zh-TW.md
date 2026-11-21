# 羽球場控面板 — Android

[![Android CI](https://github.com/ychsieh95/badminton-court-control-panel/actions/workflows/android.yml/badge.svg)](https://github.com/ychsieh95/badminton-court-control-panel/actions/workflows/android.yml) [![Android 8.0+](https://img.shields.io/badge/Android-8.0%2B%20(API%2026)-34A853?logo=android&logoColor=white)](https://developer.android.com/) [![Target API 36](https://img.shields.io/badge/target%20API-36-34A853?logo=android&logoColor=white)](https://developer.android.com/about/versions) [![Kotlin 2.2](https://img.shields.io/badge/Kotlin-2.2-7F52FF?logo=kotlin&logoColor=white)](https://kotlinlang.org/) [![Jetpack Compose](https://img.shields.io/badge/Jetpack%20Compose-Material%203-4285F4?logo=jetpackcompose&logoColor=white)](https://developer.android.com/compose) [![Firebase Cloud Messaging](https://img.shields.io/badge/Firebase-Cloud%20Messaging-DD2C00?logo=firebase&logoColor=white)](https://firebase.google.com/docs/cloud-messaging) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE) ![Languages](https://img.shields.io/badge/i18n-en--US%20%7C%20zh--TW-blue?logo=googletranslate&logoColor=white)

[English](README.md) · **繁體中文**

羽球場控面板（Badminton Court Control Panel）的原生 Android App，支援英文與繁體中文。App 只透過伺服器的 JSON API（`/api/v1`，請見 [../Web/API.md](../Web/API.md)）存取資料，並提供網站透過該 API 可使用的所有功能。

- 套件名稱：`cc.holey.badmintoncourtcontrolpanel`
- 需要 Android 8.0（API 26）以上；目標 API 36
- Kotlin、Jetpack Compose（Material 3）、Hilt、Retrofit、kotlinx.serialization、DataStore、Coil、Firebase 雲端通訊（FCM）

## 功能特色

| 類別 | 功能 |
| --- | --- |
| 場次 | 瀏覽與搜尋場次；依日期範圍、程度、性別、狀態或是否過期篩選；從分享或貼上的連結開啟場次 |
| 場次頁 | 狀態、時間、名額、相片與影片、費用、含分級圖表的程度說明、備註、預訂球友、球友名單、候補名單及加入／退出紀錄。可分享、複製連結、以瀏覽器或地圖開啟，以及下載分享圖片 |
| 球友 | 使用暱稱與 6 位數 PIN 碼加入或退出場次，不需要帳號。額滿時自動進入候補名單，並遵守退出期限 |
| 留言板 | 閱讀場次留言；以加入時的暱稱與 PIN 碼留言及回覆，或登入後以團主身分留言。團主與管理員可刪除留言 |
| 通知 | 追蹤場次後，可在場次變更、球友加入或退出，以及有人回覆你的留言時收到通知；團主會收到新留言通知。點選留言通知會直接開啟該場次的留言板 |
| 主揪 | 我的場次；建立、編輯、複製場次（已儲存球館、預訂暱稱、退出期限、相片與影片上傳）；封存、恢復、刪除；點名與結清 |
| 帳號 | 註冊、登入、大頭貼、12／24 小時制、已儲存球館、變更密碼（管理員設定臨時密碼後必須變更）、已登入裝置、刪除帳號 |
| 管理 | 管理所有場次（包含已封存場次）；重新命名球友、重設其 PIN 碼、移除球友；管理使用者（角色、停權、封存、臨時密碼、重設登入失敗、刪除）；聯絡留言；首頁與通知設定 |
| 其他 | 聯絡表單；伺服器啟用時支援 Cloudflare Turnstile；淺色與深色主題；與網站相同的配色（預設為黃色），以及裝置本身的色彩 |

以下功能因 API 未提供而無法使用（請見 `API.md` 的「Not in the API」）：CSV 匯出、`court_info.md` 匯入與匯出，以及網站的靜態頁面。

## 建置與執行

需要：

- JDK 17～21（可使用 Android Studio 內附的 JBR）
- 含 platform 36 的 Android SDK
- `app/google-services.json`（未納入版本控制）。請從 Firebase 主控台（「專案設定 → 你的應用程式」，套件名稱 `cc.holey.badmintoncourtcontrolpanel`）下載，並存放至 `Android/app/`。

```bash
cd Android
./gradlew :app:assembleDebug        # APK 位於 app/build/outputs/apk/debug/
./gradlew :app:installDebug         # 安裝至已連線的裝置或模擬器
./gradlew :app:testDebugUnitTest    # 單元測試
```

也可以直接用 Android Studio 開啟 `Android/`。

### 選擇伺服器

App 預設連線至 `https://badminton.holey.cc`。若要使用其他部署，請開啟「帳號 → App 設定」，輸入伺服器位址（例如 `https://courts.example.com`）後點選「儲存」。變更伺服器會登出，因為登入權杖只在核發它的伺服器上有效。

本機開發時，請在 `Web/` 啟動網站（`.venv/bin/flask --app app run`），並在模擬器中使用 `http://10.0.2.2:5000`。為了方便區域網路與模擬器測試，App 允許使用 `http://`；公開伺服器請使用 `https://`。

### 正式版建置

正式版會經過程式碼縮減，並以 `Android/keystore.properties` 所指定的上傳金鑰簽署。此檔案及其指向的金鑰庫只保留在本機，且已被 Git 忽略：

```properties
storeFile=/path/to/upload-keystore.jks
storePassword=…
keyAlias=…
keyPassword=…
```

```bash
./gradlew :app:bundleRelease        # AAB 位於 app/build/outputs/bundle/release/
```

沒有 `keystore.properties` 時，正式版不會簽署，也無法上傳至 Google Play。每次發布前，請先在 `app/build.gradle.kts` 設定 `versionCode` 與 `versionName`。

## 專案結構

單一 `:app` 模組，套件為 `io.github.ychsieh95.bccp`：

```text
app/src/main/java/io/github/ychsieh95/bccp/
├── core/
│   ├── model/      API 物件（kotlinx.serialization，snake_case）
│   ├── network/    Retrofit 服務；攔截器負責加上伺服器網址、Bearer 權杖與語言
│   ├── data/       Repository（錯誤邊界，轉換為 DataError）、登入狀態與設定儲存
│   ├── push/       FCM 服務與通知
│   ├── di/         Hilt 模組
│   └── ui/         主題（網站配色）、共用元件、日期與時間格式
├── feature/        courts、courtdetail、courtform、auth、account、admin、contact、settings
└── navigation/     路由、底部導覽列、NavHost
```

- 每個畫面都有一個不可變的 `UiState`，以 `StateFlow` 提供；一次性事件（導覽、Snackbar）透過 `Channel` 傳遞。
- Repository 回傳 `Result<T>`。伺服器錯誤會轉為 `DataError.Api`，包含伺服器已在地化的 `message` 與各欄位的 `fields`，表單會將其顯示在對應欄位下方。
- 伺服器依 `Accept-Language` 標頭在地化訊息，因此錯誤訊息會與 App 語言一致。
- Bearer 權杖保存在 App 私有的 DataStore 中。收到 `401 invalid_token` 回應時，App 會自動登出。
- `app/src/test/` 的單元測試會以 `app/src/test/resources/fixtures/` 中的 JSON 範例檢查 API 契約。API 變更時請一併更新。

程式碼遵循 Claude Code 技能 `android-dev`、`compose`、`android-ux`、`android-retrofit` 與 `android-data-layer` 的慣例。這些技能未納入版本控制；[`.claude/skills.lock.json`](.claude/skills.lock.json) 記錄其來源，可使用 `.claude/update-skills.py update --force` 下載至 `.claude/skills/`。程式開發代理（coding agent）也請閱讀 [AGENTS.md](AGENTS.md)。

### 字串

`res/values/strings.xml` 與 `res/values-zh-rTW/strings.xml` 為自動產生，讓 App 與網站使用相同的用語。請勿手動編輯：

```bash
python3 tools/gen_strings.py
```

共用文字來自 `Web/app.py` 的 `TRANSLATIONS`；App 專用字串放在 `tools/extra_strings.json`，格式為 `["English", "繁體中文"]`。

### 圖示

啟動器與通知圖示由 `tools/gen_launcher_icon.py` 從 `Web/static/shuttlecock.png` 產生。需要更新時請重新執行此腳本，不要直接編輯 PNG。

### 商店截圖

[`docs/store-listing/screenshots/`](docs/store-listing/screenshots/README.zh-TW.md) 會在模擬器上連線至含虛構資料的本機伺服器擷取 Google Play 截圖，再將其排版為商店圖片。

## 授權

本專案以 [MIT 授權條款](../LICENSE)釋出。啟動器圖示改作自網站的羽毛球圖示，其來源說明請見 [Web/README.zh-TW.md](../Web/README.zh-TW.md#素材來源與授權)。
