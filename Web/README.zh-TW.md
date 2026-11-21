# 羽球場控面板 — 網站

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/) [![Flask 3.1](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/) [![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/) [![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](docker/compose.yaml) [![JSON API](https://img.shields.io/badge/JSON%20API-%2Fapi%2Fv1-FF6F00?logo=json&logoColor=white)](API.md) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](../LICENSE) ![Languages](https://img.shields.io/badge/i18n-en--US%20%7C%20zh--TW-blue?logo=googletranslate&logoColor=white)

[English](README.md) · **繁體中文**

羽球場控面板（Badminton Court Control Panel）的網站與 JSON API。這是一套支援中英雙語的 Flask 羽球活動管理系統：主揪可以發布與管理場次，球友不需要註冊帳號，只要使用暱稱與 6 位數 PIN 碼就能加入或退出場次。同一台伺服器也提供 [Android App](../Android/README.zh-TW.md) 使用的 `/api/v1` JSON API。

## 目錄

- [功能特色](#功能特色)
- [快速開始](#快速開始)
- [環境設定](#環境設定)
- [選用整合服務](#選用整合服務)
- [使用 Docker 部署](#使用-docker-部署)
- [資料與儲存](#資料與儲存)
- [安全性與隱私](#安全性與隱私)
- [開發](#開發)
- [素材來源與授權](#素材來源與授權)

## 功能特色

### 球友

- 瀏覽即將開始的場次，並依關鍵字、主揪、日期範圍、球員程度、男女程度範圍、名額及狀態篩選。
- 使用暱稱及私密 6 位數 PIN 碼加入或退出場次，不需要註冊。正式名額額滿時，新加入的球友會依先後順序進入候補名單。
- 加入前即可看到主揪設定的退出期限；期限過後，球友無法自行退出。
- 查看日期時間、球館與地圖位置、費用、用球、程度範圍、備註、球友名單，以及活動相片與影片。
- 在場次的**留言板**提問。已加入場次的球友使用加入時的暱稱與 PIN 碼留言及回覆；頁面開啟期間，留言板會自動更新。
- 為個別場次開啟瀏覽器通知，在場次被編輯、封存、有球友加入或退出，以及有人回覆自己的留言時收到通知。
- 分享場次連結時附帶 1200×630 社群預覽圖，也可以直接把預覽圖下載為 JPEG。
- 收合場次各區塊，並透過可拖曳的區塊導覽快速跳轉。

### 主揪

- 註冊後在**我的場次**（`/my-courts`）管理自己的活動。每個場次都有 `https://your-domain.example/<GUID>` 格式的永久連結。
- 設定日期時間、Google 地點球館、場地編號、人數與預訂名額、男女程度範圍、費用、用球、備註，以及選用的退出期限。
- 以暱稱保留預訂名額，並決定訪客是否看得到這些暱稱。可儲存常用球館，日後直接選用。
- 最多上傳 12 個相片或影片（JPEG、PNG、WebP、MP4、WebM），第一張圖片會作為場次卡片封面。
- 以團主身分回覆留言、刪除留言，並在每則新留言或回覆時收到通知。
- 編輯、複製、封存、恢復或刪除自己的場次。可將場次匯出為 `court_info.md`，日後匯入以預填新場次。
- 啟動「點名與結清」，將場次切換為唯讀，並記錄每位球友的出席與付款狀態。
- 在個人資料頁選擇 12 小時制或 24 小時制。

### 管理員

- 使用與公開列表相同的篩選器管理所有場次，包含已封存與已過期場次，並可將所有場次匯出為 UTF-8 CSV 檔案。
- 重新命名球友、重設其 PIN 碼或將其移出場次；查看含 IP 位址與概略裝置類型的加入／退出紀錄，以及每則留言的 IP 位址。
- 管理會員：指派角色（會員、副管理員、管理員、最高管理員；只有最高管理員可變更角色）、停權、封存、刪除、設定臨時密碼，或重設登入失敗鎖定。
- 在受保護的收件匣閱讀聯絡留言，並設定首頁顯示的場次數量。

### 語言與外觀

- 支援英文（`en-US`）與繁體中文（`zh-TW`）。偵測為台灣的訪客預設使用繁體中文，其他訪客預設使用英文；手動選擇的語言會記錄在 Cookie 中。
- 提供黑白、綠色與萊姆、紫色及黃色配色，每種配色皆支援系統、淺色及深色模式。新訪客預設為「黃色 · 淺色」。
- 內建台灣羽球推廣協會 1～18 級程度分級參考，以及網站介紹、更新紀錄、隱私權政策與聯絡頁面。

### 主要路由

| 路由 | 用途 |
| --- | --- |
| `/` | 首頁與即將開始的場次 |
| `/courts` | 可篩選的場次列表 |
| `/courts/new` | 新增場次表單（已登入會員與管理員） |
| `/<GUID>` | 場次頁：詳細資訊、報名及留言板 |
| `/<GUID>/thumbnail.jpg` | 場次目前的 1200×630 預覽圖 |
| `/<GUID>/court_info.md` | 場次設定匯出（僅限主揪） |
| `/signup`、`/login` | 會員註冊；會員與管理員登入 |
| `/my-courts` | 主揪管理面板 |
| `/account/profile` | 個人資料、頭像、時間格式、已儲存球館 |
| `/admin`、`/admin/users`、`/admin/messages` | 管理後台、會員管理、聯絡留言收件匣 |
| `/admin/courts/export.csv` | 匯出所有場次的 CSV（僅限管理員） |
| `/introduction`、`/updates`、`/privacy`、`/contact`、`/licenses`、`/android` | 公開資訊頁面 |
| `/healthz` | 健康檢查；通過資料庫探測後回傳 `{"status": "ok"}` |
| `/api/v1/...` | JSON API（請見 [API.md](API.md)） |

## 快速開始

需要 Python 3.10 或更新版本。本文件中的所有指令都請在 `Web/` 目錄執行。

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/flask --app app run --debug
```

開啟 <http://127.0.0.1:5000>，並在 `/login` 登入。會員登入後會前往 `/my-courts`，管理員則前往 `/admin`。

若資料庫中還沒有最高管理員，系統會以 `ADMIN_USERNAME` 與 `ADMIN_PASSWORD` 建立一位（開發預設值：`admin` / `change-me`）。之後修改這兩個變數不會變更既有最高管理員的密碼，請改用帳號密碼頁變更。正式環境第一次啟動前，務必更換 `SECRET_KEY`、`ADMIN_USERNAME` 及 `ADMIN_PASSWORD`。

## 環境設定

設定從 `.env` 讀取，處理程序環境中已存在的變數優先。[`.env.example`](.env.example) 列出所有變數及說明。

| 變數 | 預設值 | 說明 |
| --- | --- | --- |
| `SECRET_KEY` | 開發用值 | 簽署工作階段與 CSRF 權杖。正式環境請使用足夠長的隨機值。 |
| `ADMIN_USERNAME` | `admin` | 第一位最高管理員的使用者名稱。 |
| `ADMIN_PASSWORD` | `change-me` | 第一位最高管理員的初始密碼。 |
| `COURT_DATABASE` | `instance/courts.sqlite` | SQLite 資料庫路徑。 |
| `SESSION_COOKIE_SECURE` | `0` | 網站僅透過 HTTPS 提供時設為 `1`。 |
| `TRUST_PROXY_HEADERS` | `0` | 信任轉送的用戶端 IP 與通訊協定標頭。僅能在會覆寫這些標頭的可信任代理後方啟用。 |
| `TURNSTILE_SITE_KEY` | 空白 | Cloudflare Turnstile 網站金鑰。 |
| `TURNSTILE_SECRET_KEY` | 空白 | Cloudflare Turnstile 私密金鑰，不會傳送至瀏覽器。 |
| `TURNSTILE_VERIFY_TIMEOUT` | `5` | Turnstile 驗證逾時秒數。 |
| `GOOGLE_MAPS_API_KEY` | 空白 | 啟用場次表單的 Google Places 球館搜尋。 |
| `WEB_PUSH_PUBLIC_KEY` | 空白 | 提供給瀏覽器的 VAPID 應用伺服器金鑰。 |
| `WEB_PUSH_PRIVATE_KEY` | 空白 | VAPID 私密金鑰，可填入金鑰內容或 PEM 檔案路徑。 |
| `WEB_PUSH_SUBJECT` | 空白 | VAPID 聯絡 URI，例如 `mailto:admin@example.com`。 |
| `WEB_PUSH_TIMEOUT` | `5` | 每位接收者的 Web Push 傳送逾時秒數。 |
| `FCM_SERVICE_ACCOUNT_FILE` | 空白 | Firebase 服務帳戶 JSON 路徑。設定後啟用 Android App 通知。 |
| `FCM_TIMEOUT` | `5` | 每位接收者的 FCM 傳送逾時秒數。 |
| `SOCIAL_THUMBNAIL_FFMPEG` | 內附執行檔 | 覆寫從影片擷取預覽畫面所用的 FFmpeg。 |
| `SOCIAL_THUMBNAIL_FONT` | 內附 Noto Sans TC | 覆寫產生預覽圖所用的字型。 |
| `GEOIP_COUNTRY_DB` | 空白 | 本機 MaxMind GeoIP2／GeoLite2 國家資料庫，用於判斷預設語言。 |
| `DEFAULT_COUNTRY_CODE` | 空白 | 無法判斷訪客國家時使用的兩碼備用國家代碼。 |
| `PRIVACY_OPERATOR_NAME` | 空白 | 顯示於 `/privacy` 與 `/contact` 的營運者名稱。 |
| `PRIVACY_DATA_REGION` | 空白 | 顯示於 `/privacy` 的主機所在地區。 |
| `PRIVACY_CONTACT` | 空白 | 顯示於 `/privacy` 的 `mailto:` 或 HTTP(S) 聯絡方式。 |
| `ADMIN_CONTACT` | 空白 | 顯示於 `/contact` 的 `mailto:` 或 HTTP(S) 支援聯絡方式。 |
| `ADMIN_CONTACT_DISCORD` | 空白 | Discord 邀請碼；`/contact` 會連結至 `discord.gg`。 |
| `ADMIN_CONTACT_LINE` | 空白 | LINE 官方帳號 ID，可含或不含 `@`。 |
| `ADMIN_CONTACT_TELEGRAM` | 空白 | Telegram 公開使用者名稱，可含或不含 `@`。 |
| `CONTACT_DISCORD_WEBHOOK_URL` | 空白 | 新聯絡留言使用的 Discord Incoming Webhook；需由管理員在 `/admin/messages` 開啟。 |
| `CONTACT_TELEGRAM_BOT_TOKEN` | 空白 | Telegram Bot Token。與 Chat ID 一併設定後，每則新聯絡留言都會回報至 Telegram。 |
| `CONTACT_TELEGRAM_CHAT_ID` | 空白 | 接收回報的 Telegram 數字 Chat ID 或公開 `@channel`。 |
| `CONTACT_NOTIFICATION_TIMEOUT` | `5` | Discord／Telegram 傳送逾時秒數。 |
| `ANDROID_APP_URL` | 空白 | 顯示於 `/android` 的 HTTPS 下載連結（例如 Google Play 頁面）。 |
| `LOGIN_MAX_ATTEMPTS` | `5` | 暫時鎖定前允許的登入失敗次數。 |
| `LOGIN_LOCKOUT_SECONDS` | `900` | 登入鎖定秒數。 |
| `LEAVE_MAX_ATTEMPTS` | `5` | 每個場次、暱稱及 IP 在鎖定前允許的錯誤暱稱／PIN 碼退出次數。 |
| `LEAVE_LOCKOUT_SECONDS` | `900` | 退出鎖定秒數。 |
| `API_TOKEN_TTL_DAYS` | `90` | JSON API 存取權杖的有效天數。 |
| `APP_VERSION` | `data/update_history.json` 中最新的日期 | API 回報的版本字串。 |

## 選用整合服務

所有整合服務在設定前都不會啟用，網站不依賴任何一項也能正常運作。

### Cloudflare Turnstile

為網站主機名稱[建立 Turnstile 小工具](https://developers.cloudflare.com/turnstile/get-started/)，並同時設定 `TURNSTILE_SITE_KEY` 與 `TURNSTILE_SECRET_KEY`，即可保護註冊、登入與聯絡表單。伺服器處理請求前會驗證權杖及其動作（`signup`、`login` 或 `contact_message`），缺少、過期、重複使用或動作不符的權杖都會被拒絕。任一金鑰留空或 Flask 偵錯模式開啟時，Turnstile 會停用。Cloudflare 的[測試金鑰](https://developers.cloudflare.com/turnstile/troubleshooting/testing/)僅供測試，請勿部署至正式環境。

### Google 球館搜尋

將 `GOOGLE_MAPS_API_KEY` 設為已啟用 **Maps JavaScript API** 與 **Places API (New)** 的瀏覽器金鑰，所屬 Google Cloud 專案須啟用帳單。在「網站（HTTP 參照網址）」限制中加入正式網域，本機開發另外加入：

```text
http://127.0.0.1:5000/*
http://localhost:5000/*
```

未設定金鑰時，場次表單仍可使用，並改為提供 Google 地圖搜尋連結。

### 瀏覽器通知（Web Push）

每個場次頁都有通知開關。主揪編輯、封存、恢復、鎖定、解除鎖定或刪除場次；球友加入、進入候補或退出；以及留言板有新留言或回覆時（通知團主與該留言串的作者），都會送出通知。失敗的加入／退出嘗試與點名變更不會送出通知。

請產生一組固定使用的 VAPID 金鑰：

```bash
mkdir -p instance/web-push
cd instance/web-push
../../.venv/bin/vapid --gen --applicationServerKey
```

此指令會顯示應用伺服器金鑰並建立 `private_key.pem`，接著設定：

```text
WEB_PUSH_PUBLIC_KEY=<指令顯示的應用伺服器金鑰>
WEB_PUSH_PRIVATE_KEY=instance/web-push/private_key.pem
WEB_PUSH_SUBJECT=mailto:your-contact@example.com
```

更換金鑰會使所有既有瀏覽器訂閱失效。除了 localhost 以外，瀏覽器推播需要 HTTPS。缺少任一 VAPID 設定時，開關會保持停用。推播服務回報失效（`404` 或 `410`）的訂閱會自動移除。

### Android App 通知（FCM）

Android App 透過 Firebase 雲端通訊（FCM）接收相同的通知。在 Firebase 主控台開啟「專案設定 → 服務帳戶」，產生私密金鑰並存放在持久保存的位置，再讓伺服器指向該檔案：

```text
FCM_SERVICE_ACCOUNT_FILE=instance/firebase-service-account.json
```

使用 Docker 時，請將檔案放進 `/instance` 磁碟區，並改用 `/instance/firebase-service-account.json`。未設定時，App 會隱藏通知開關。FCM 回報為已失效的權杖會自動移除。

### 聯絡留言通知

聯絡留言一定會先儲存至資料庫，外部通知只是額外功能。兩個 Telegram 變數都設定後，網站或 Android App 送出的每則新留言都會回報至該聊天室，內容包含寄件者、回覆聯絡方式、帳號、來源（網站與裝置類型，或 App 版本、Android 版本與裝置型號）、語言及收件匣連結。Discord 為選用：設定 `CONTACT_DISCORD_WEBHOOK_URL` 後，在 `/admin/messages` 開啟。Webhook 網址與 Bot Token 會經過驗證、只保留在伺服器端，也不會顯示在收件匣。傳送失敗時只會記錄不含密鑰的錯誤，已儲存的留言不會遺失。

## 使用 Docker 部署

映像檔以 uWSGI 搭配 Nginx 在 `8080` 連接埠執行應用程式，預設以 UID `1654` 執行。

```bash
docker compose -f docker/compose.yaml up -d --build   # 啟動
docker compose -f docker/compose.yaml down            # 停止並保留資料
```

Compose 會載入 `Web/.env`、發布 `8080` 連接埠，並將具名磁碟區 `badminton-court-control-data` 掛載至 `/instance`，因此重新建立容器後，資料庫、頭像與場次媒體都會保留。若磁碟區需要其他擁有者，請設定 `APP_UID` 建置參數。

不使用 Compose 時：

```bash
docker build --build-arg APP_UID=1654 -f docker/Dockerfile -t badminton-court-control-panel .
docker run --rm --name badminton-court-control-panel --env-file .env \
  -p 8080:8080 -v badminton-court-control-data:/instance badminton-court-control-panel
```

若磁碟區是由舊版以 root 執行的映像檔建立，請在啟動新映像檔前執行一次擁有者修正（若變更過 `APP_UID`，請取代 `1654`）：

```bash
docker run --rm --user 0 --entrypoint chown \
  -v badminton-court-control-data:/instance \
  badminton-court-control-panel:local -R 1654:0 /instance
```

### 健康檢查

映像檔的 `HEALTHCHECK` 每 30 秒請求一次 `/healthz`（逾時 5 秒、啟動寬限 20 秒、重試 3 次）。此端點會對資料庫執行 `SELECT 1`，不需登入，也不回傳個人資料，因此外部監控與反向代理也可使用。

```bash
docker compose -f docker/compose.yaml ps
docker inspect --format '{{.State.Health.Status}}' <container>
```

### 反向代理

在另一個 Nginx 後方時，容器看到的是 Docker 閘道（通常是 `172.18.0.1`）而非訪客。若要記錄真實的用戶端位址，請設定 `TRUST_PROXY_HEADERS=1`，並讓對外的代理覆寫（而非附加）轉送標頭：

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

重新載入 Nginx，並重新建立容器以載入 `.env`：

```bash
sudo nginx -t && sudo systemctl reload nginx
docker compose -f docker/compose.yaml up -d --force-recreate app
docker compose -f docker/compose.yaml exec app printenv TRUST_PROXY_HEADERS   # 必須輸出 1
```

只有當應用程式完全只能透過該代理存取時才可啟用。若 Nginx 前方還有其他代理（例如 Cloudflare），請先以該服務的 IP 範圍設定 Nginx 的 real-IP 模組。

### 正式環境檢查清單

- 第一次啟動前設定高強度的 `SECRET_KEY` 及初始管理員帳密。
- 透過 HTTPS 提供服務，並設定 `SESSION_COOKIE_SECURE=1`。
- 只有在會覆寫轉送標頭的可信任代理後方，才設定 `TRUST_PROXY_HEADERS=1`。
- 持久保存並備份 `instance` 目錄，包含 VAPID 私密金鑰與 Firebase 服務帳戶檔案。
- 將正式網域加入 Google Maps 金鑰允許的參照網址。
- 檢視 `/privacy`，並設定 `PRIVACY_OPERATOR_NAME`、`PRIVACY_DATA_REGION` 與 `PRIVACY_CONTACT`。
- 讓監控服務檢查 `/healthz`。

產生預覽圖所需的 FFmpeg 與 Noto Sans TC 字型已內附於專案，無論是否使用 Docker 都可直接使用。

## 資料與儲存

- 場次在設定的日期與結束時間後過期，過期場次為唯讀，且不會顯示在預設列表中。若設定了退出期限，則會提早生效：球友仍可加入，但無法再自行退出。
- 已封存場次仍可透過直接連結及主揪與管理員面板存取，但留言板不再接受新留言。
- 所有資料都存放在 `instance/` 下：SQLite 資料庫（`courts.sqlite`，除非另設 `COURT_DATABASE`）、頭像（`avatars/`）、場次媒體（`court_media/`）及快取的預覽圖（`social_thumbnails/`）。替換或刪除資料時，相關檔案會一併清除。
- `court_info.md` 匯出檔以 JSON 區塊保存可重複使用的場次設定與預訂暱稱，不包含報名資料、PIN 碼、紀錄、留言、媒體、擁有者及原始 GUID。匯入上限為 64 KB，只會預填表單，儲存時仍會經過一般驗證。
- 管理員 CSV 匯出（UTF-8 含 BOM）每個場次一列，包含已封存與已過期場次，不包含 PIN 碼及加入／退出紀錄。

## 安全性與隱私

- 密碼與 PIN 碼皆以密碼雜湊儲存。重複登入失敗、退出失敗或留言板 PIN 碼錯誤，會暫時鎖定該使用者名稱與 IP。
- 留言長度為 1～500 個字元，每個 IP 在每個場次 10 分鐘內最多留言 5 則。只有已加入場次的球友、該場次的團主與管理員可以留言。
- 會變更狀態的表單皆有 CSRF 保護。API 請求使用 Bearer 權杖，不會使用工作階段 Cookie。
- 加入／退出紀錄會保存暱稱、動作與時間；管理員另可看到已驗證的 IP 與概略裝置類型（iOS、Android、行動裝置、網頁）。系統不保存完整的 User-Agent 字串或裝置指紋，失敗的嘗試也不會列入紀錄。
- 推播端點、金鑰與 FCM 權杖只用於傳送使用者自行開啟的通知，不會公開顯示。
- 聯絡留言及其回覆聯絡方式僅管理員可見。
- 停權會封鎖會員登入與主揪功能，但不會刪除其場次。以暱稱與 PIN 碼加入場次仍對所有人開放。
- `/privacy` 的公開政策說明應用程式本身的資料處理方式。自行架設者須補充部署環境特有的處理，例如伺服器紀錄、備份或其他服務。

## 開發

### 測試

```bash
.venv/bin/pytest -q
node tests/test_court_controls.cjs     # 瀏覽器控制邏輯，不需額外套件
node tests/test_court_navigation.cjs
```

### JSON API

`/api/v1` 以 JSON 提供球友、主揪、帳號與管理員功能。用戶端透過 `POST /api/v1/auth/login` 登入，並傳送 `Authorization: Bearer <token>`。API 與 HTML 頁面共用相同的驗證、次數限制與權限規則。端點說明請見 [API.md](API.md)。變更 API 時，請同時更新 `api.py`、`API.md` 與 `tests/test_api.py`。

### 翻譯

所有介面文字都放在 `app.py` 的 `TRANSLATIONS` 表中，`en-us` 與 `zh-tw` 的鍵值必須一致。Android App 的字串資源由此表產生，因此變更共用文字後，請在 `Android/` 執行 `python3 tools/gen_strings.py`。

### 更新紀錄

`/updates` 時間軸來自 `data/update_history.json`，最新項目在最前面。每筆項目都需要 `date`、`date_label`、`title`、`summary` 及非空白的 `items` 清單，且每項都要有 `en-us` 與 `zh-tw` 兩種語言。應用程式啟動時會驗證此檔案，格式錯誤、內容不完整或順序錯誤時將拒絕啟動。

## 素材來源與授權

原始碼以 [MIT 授權條款](../LICENSE)釋出。內附的第三方素材仍適用其各自的授權。

網站圖示 [`static/shuttlecock.png`](static/shuttlecock.png) 改作自 [Flaticon 的 Shuttlecock 圖示](https://www.flaticon.com/free-icon/shuttlecock_9719863)。預覽圖使用內附的 [Noto Sans TC](https://github.com/notofonts/noto-cjk) 字型，以 SIL Open Font License 1.1 授權。素材來源與授權連結也列於 `/licenses`。

羽球場控面板在開發過程中使用 [OpenAI Codex](https://openai.com/codex/) 協助實作、審查與測試。網站及其營運與內容仍由專案擁有者負責；此說明不代表 OpenAI 背書或擁有本專案。
