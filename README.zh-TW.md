# badminton-court-control-panel｜羽球場控面板

[English（預設）](README.md) · **繁體中文**

Badminton Court Control Panel 是一套支援雙語的 Flask 羽球活動管理系統。主辦者可以發布與管理場次，球友不需要建立帳號，就能搜尋、加入或退出活動。

## 功能特色

### 球友功能

- 瀏覽開放場次，並依關鍵字、建立者、日期範圍、球員程度、男女程度範圍、名額及活動狀態篩選。
- 使用暱稱及私密 6 位數 PIN 碼加入或退出場次，不需要註冊會員。
- 加入或退出前可查看主辦者設定的退出期限；期限過後將無法自行退出場次。
- 正式名額額滿時，自動依加入順序進入候補名單。
- 可針對個別場次開啟系統推播通知，在場次資訊或球友名單變更時收到通知。
- 查看日期、星期、時間、球館、地點、費用、用球、程度、主辦者、備註、球友名單及活動媒體。
- 分享場次網址時提供 1200×630 社群預覽；依序使用第一個活動相片、第一個活動影片的畫面，或在沒有媒體時使用活動資訊產生圖片。
- 在行動裝置上透過浮動按鈕開啟無障礙加入視窗。

### 主辦者功能

- 建立會員帳號，並從 `/my-courts` 管理自己的活動。
- 設定選填的活動名稱與羽球團名稱，並取得 `https://your-domain.example/<GUID>` 格式的永久 UUID 連結。
- 設定日期、24 小時制起訖時間、Google 地點球館、場地編號、人數範圍、預訂名額、男女程度範圍、費用、用球及備註。
- 可選擇設定精確的本地日期及明確的 24 小時制 `HH:MM` 時間，超過後球友無法自行退出活動；此限制預設停用。
- 可在個人資料頁選擇並保存 12 小時制（AM/PM）或 24 小時制顯示格式；場次時間、退出期限、登入時間及稽核時間會依登入會員的偏好顯示。
- 建立活動時儲存常用球館地點，日後無須搜尋即可重複使用，並可在個人資料頁刪除。
- 建立或編輯活動時可逐一新增或刪除預訂球友暱稱欄位，並決定是否向訪客顯示這些暱稱。
- 最多上傳 12 個 JPEG、PNG、WebP、MP4 或 WebM 檔案；第一張圖片會作為場次卡片封面。
- 將管理中的場次匯出為 `court_info.md`，並在新增場次表單匯入，以預填另一個活動。
- 編輯、複製、封存、恢復或刪除自己建立的活動。
- 啟動「點名與結清」，將活動切換為唯讀，並記錄出席及費用結清狀態。

### 管理員功能

- 建立、編輯、複製、封存、恢復及刪除任何場次。
- 將所有現有場次（包含已封存與已過期活動）匯出為 UTF-8 CSV 檔案。
- 直接在場次頁重新命名球友、重設其 6 位數 PIN 碼，或將球友移出場次。
- 與會員共用新增場次表單，並使用各管理員帳號私有的已儲存地點。
- 指派會員、副管理員、管理員或最高管理員角色；只有最高管理員可變更角色。
- 使用與公開場次列表相同的篩選器管理所有場次，並可查詢已封存與已過期活動。
- 設定首頁最多顯示的場次數量。
- 封存、恢復、停權、解除停權，或永久刪除符合條件的會員帳號。
- 設定臨時密碼，要求會員登入後立即變更密碼。
- 查看會員最後登入時間與 IP 位址。
- 從管理後台查看每個球場活動的建立日期與時間。
- 重設會員在所有 IP 位址的登入失敗次數及暫時鎖定。
- 查看加入／退出紀錄的時間、已驗證 IP 位址及概略裝置類型：iOS、Android、行動裝置或網頁。

### 語言與外觀

- 介面支援英文（`en-US`）及繁體中文（`zh-TW`）。
- 偵測為台灣的訪客預設使用繁體中文，其他地區預設使用英文。
- 手動選擇的語言會儲存在 Cookie，並優先於國家／地區偵測。
- 初次造訪時可選擇是否查看網站介紹，選擇結果會記錄於瀏覽器。
- 公開雙語隱私權政策會說明應用程式的資料處理、可見範圍、保留方式、瀏覽器儲存及選用外部服務。
- 訪客可留下會儲存的支援留言，管理員可在受保護的收件匣中查看。
- 提供黑白、綠色與萊姆、紫色及黃色配色，每種配色皆支援系統、淺色及深色模式。
- 新訪客預設使用「黃色 · 淺色」；已儲存的偏好設定會優先套用。
- 內建台灣羽球推廣協會 1～18 級程度分級參考。

## 主要路由

| 路由 | 用途 |
| --- | --- |
| `/` | 首頁與即將開始的場次 |
| `/introduction` | 公開網站介紹 |
| `/updates` | 公開雙語更新紀錄 |
| `/contact` | 公開雙語網站管理員聯絡頁面 |
| `/privacy` | 公開雙語隱私權政策 |
| `/courts` | 可篩選的公開場次列表 |
| `/courts/new` | 會員與管理員共用的新增場次表單 |
| `/<GUID>` | 公開場次詳情及報名 |
| `/<GUID>/court_info.md` | 僅限主辦者使用的場次設定匯出 |
| `/signup` | 會員註冊 |
| `/login` | 會員及管理員登入 |
| `/my-courts` | 主辦者管理面板 |
| `/account/profile` | 會員個人資料與頭像 |
| `/admin` | 管理後台 |
| `/admin/messages` | 僅限管理員使用的聯絡留言收件匣與通知設定 |
| `/admin/courts/export.csv` | 僅限管理員匯出所有場次活動 |
| `/admin/users` | 會員管理 |
| `/licenses` | 素材授權及開發協助說明 |

## 更新紀錄內容

雙語 `/updates` 時間軸維護於 `data/update_history.json`，最新項目需放在最前面。每筆項目都必須提供 `date`、`date_label`、`title`、`summary`，以及 `en-us` 與 `zh-tw` 兩種語言的非空白 `items` 清單。應用程式啟動時會驗證此結構，格式錯誤、翻譯不完整、日期無效或排序不正確時會提早失敗，避免顯示不完整內容。

## 本機安裝

建議使用 Python 3.10 或更新版本。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

更新 `.env` 後，啟動開發伺服器：

```bash
flask --app app run --debug
```

開啟 <http://127.0.0.1:5000>。會員與管理員共用 `/login` 表單；會員登入後前往 `/my-courts`，管理員角色則前往 `/admin`。舊有 `/admin/login` 網址會重新導向 `/login`。

若資料庫尚無最高管理員，應用程式會建立或提升設定的 `ADMIN_USERNAME` 為第一個資料庫最高管理員，並雜湊儲存 `ADMIN_PASSWORD`。最高管理員建立後，修改環境變數不會覆寫其密碼；請改用帳號密碼頁變更。

開發環境的初始帳密為 `admin` / `change-me`。正式部署第一次啟動前，務必更換 `SECRET_KEY`、`ADMIN_USERNAME` 及 `ADMIN_PASSWORD`。

## 環境設定

| 變數 | 預設值 | 說明 |
| --- | --- | --- |
| `SECRET_KEY` | 開發用值 | Flask 工作階段及 CSRF 簽署密鑰；正式環境請使用足夠長的隨機值。 |
| `ADMIN_USERNAME` | `admin` | 建立第一個資料庫最高管理員時使用的名稱。 |
| `ADMIN_PASSWORD` | `change-me` | 最高管理員的初始密碼。 |
| `TURNSTILE_SITE_KEY` | 空白 | 公開的 Cloudflare Turnstile 網站金鑰；與私密金鑰同時設定後保護註冊及登入。 |
| `TURNSTILE_SECRET_KEY` | 空白 | Turnstile Siteverify 私密驗證金鑰；不可傳送至瀏覽器。 |
| `TURNSTILE_VERIFY_TIMEOUT` | `5` | 伺服器端 Turnstile 驗證逾時秒數。 |
| `COURT_DATABASE` | `instance/courts.sqlite` | SQLite 資料庫位置。 |
| `GOOGLE_MAPS_API_KEY` | 空白 | 啟用 Google Places 球館自動完成。 |
| `WEB_PUSH_PUBLIC_KEY` | 空白 | 提供給瀏覽器的 VAPID 公開應用伺服器金鑰。 |
| `WEB_PUSH_PRIVATE_KEY` | 空白 | 私密 VAPID 金鑰內容或 PEM 檔案路徑。 |
| `WEB_PUSH_SUBJECT` | 空白 | VAPID 聲明使用的營運者聯絡 URI，例如 `mailto:admin@example.com`。 |
| `WEB_PUSH_TIMEOUT` | `5` | 每個推播接收者的傳送逾時秒數。 |
| `SOCIAL_THUMBNAIL_FFMPEG` | 內附執行檔 | 第一個活動媒體是影片時，用來覆寫擷取預覽畫面的 FFmpeg 執行檔。 |
| `SOCIAL_THUMBNAIL_FONT` | 內附 Noto Sans TC | 可選用的 TrueType/OpenType 字型路徑，用來覆寫產生活動資訊縮圖時使用的內附字型。 |
| `SESSION_COOKIE_SECURE` | `0` | 網站完全透過 HTTPS 提供時設為 `1`。 |
| `TRUST_PROXY_HEADERS` | `0` | 信任轉送的用戶端 IP 與網址通訊協定標頭；僅能在會覆寫這些標頭的可信任反向代理後啟用。 |
| `GEOIP_COUNTRY_DB` | 空白 | 選用的本機 MaxMind GeoIP2／GeoLite2 國家資料庫。 |
| `DEFAULT_COUNTRY_CODE` | 空白 | 選用的兩碼備用國家代碼；未知地區訪客預設使用英文。 |
| `PRIVACY_OPERATOR_NAME` | 空白 | 顯示於 `/privacy` 與 `/contact` 的此部署網站公開營運者名稱。 |
| `PRIVACY_DATA_REGION` | 空白 | 顯示於 `/privacy` 的主要主機／資料地區公開說明。 |
| `PRIVACY_CONTACT` | 空白 | 顯示於 `/privacy` 的選用公開 `mailto:` 或 HTTP(S) 聯絡方式。 |
| `ADMIN_CONTACT` | 空白 | 顯示於 `/contact` 的選用公開 `mailto:` 或 HTTP(S) 管理員／支援聯絡方式。 |
| `ADMIN_CONTACT_DISCORD` | 空白 | 選用的 Discord 邀請碼；`/contact` 會自動組成官方 `discord.gg` 連結。 |
| `ADMIN_CONTACT_LINE` | 空白 | 選用的 LINE 官方帳號 ID（可含或不含 `@`）；`/contact` 會自動組成官方 `line.me` 連結。 |
| `ADMIN_CONTACT_TELEGRAM` | 空白 | 選用的 Telegram 公開使用者名稱（可含或不含 `@`）；`/contact` 會自動組成官方 `t.me` 連結。 |
| `CONTACT_DISCORD_WEBHOOK_URL` | 空白 | 啟用新留言通知時使用的私密 Discord Incoming Webhook 網址。 |
| `CONTACT_TELEGRAM_BOT_TOKEN` | 空白 | 啟用新留言通知時使用的私密 Telegram Bot API Token。 |
| `CONTACT_TELEGRAM_CHAT_ID` | 空白 | 接收通知的 Telegram 數字 Chat ID 或公開 `@channel` 使用者名稱。 |
| `CONTACT_NOTIFICATION_TIMEOUT` | `5` | Discord／Telegram 各服務的傳送逾時秒數。 |
| `LOGIN_MAX_ATTEMPTS` | `5` | 暫時鎖定前允許的登入失敗次數。 |
| `LOGIN_LOCKOUT_SECONDS` | `900` | 暫時鎖定秒數。 |
| `LEAVE_MAX_ATTEMPTS` | `5` | 每個場次、暱稱及用戶端 IP 在暫時鎖定前允許的錯誤暱稱／PIN 碼退出嘗試次數。 |
| `LEAVE_LOCKOUT_SECONDS` | `900` | 退出場次嘗試的暫時鎖定秒數。 |

處理程序環境中已存在的變數會優先於 `.env`。

## Cloudflare Turnstile

在 Cloudflare [建立 Turnstile 小工具](https://developers.cloudflare.com/turnstile/get-started/)、允許正式網站主機名稱，並同時設定 `TURNSTILE_SITE_KEY` 及 `TURNSTILE_SECRET_KEY`，即可保護 `/signup`、共用的 `/login` 頁面及 `/contact` 留言表單。小工具會使用 `signup`、`login` 或 `contact_message` 動作；處理請求前，伺服器會驗證權杖及對應動作。

缺少、遭拒、過期、重複使用、過長、格式錯誤、動作不符或無法驗證的權杖都會被拒絕。任一金鑰留空或 Flask 偵錯模式啟用時，Turnstile 會自動停用。私密金鑰僅用於伺服器間驗證，不會輸出至 HTML。Cloudflare 提供適用於自動化測試及 localhost 的[專用測試金鑰](https://developers.cloudflare.com/turnstile/troubleshooting/testing/)；不可將測試憑證部署至正式環境。

## 聯絡留言通知

公開留言一定會先寫入 SQLite，才嘗試傳送選用外部通知。設定 `CONTACT_DISCORD_WEBHOOK_URL`，及／或同時設定兩個 Telegram 變數後，管理員或最高管理員可在 `/admin/messages` 啟用通知。Discord 網址必須是官方 HTTPS Incoming Webhook；開關可用前也會驗證 Telegram Bot Token 與 Chat ID。Webhook 網址與 Bot Token 只保留在伺服器端，不會顯示於收件匣。傳送逾時或供應商錯誤只會記錄不含私密端點的錯誤類型，不會捨棄已儲存的留言。

## Google 球館搜尋

將 `GOOGLE_MAPS_API_KEY` 設為已啟用 **Maps JavaScript API** 及 **Places API (New)** 的瀏覽器金鑰。Google Cloud 專案必須啟用帳單功能。

請在 **網站（HTTP 參照網址）** 中加入正式網域。本機開發請允許：

```text
http://127.0.0.1:5000/*
http://localhost:5000/*
```

未設定金鑰時，場次表單仍可正常使用，並會提供即時 Google 地圖搜尋連結。

## 場次資訊匯入與匯出

從場次頁的主辦者操作選單選擇「匯出」，即可下載名稱為 `yyyy-MM-dd_HHmm_HHmm_<名稱>.md` 的檔案；兩組時間依序為活動開始與結束時間。有活動名稱時使用活動名稱，否則使用球館名稱。在 `/courts/new` 頂端展開預設收合的「場次資訊檔」區塊並選擇該檔案，即可預填新活動。匯入只會填入表單；主辦者仍須檢查內容並儲存，系統才會建立場次。匯入發生錯誤時，此區塊會自動展開以供處理。

此版本化 Markdown 檔案以易讀的 JSON 區塊保存可重複使用的場次欄位及預訂球友暱稱，不包含報名資料、參加者 PIN 碼、加入／退出歷程、媒體檔案、擁有者及原始公開 GUID。匯入檔案上限為 64 KB，儲存前仍會套用一般場次驗證。

管理員也可在 `/admin` 選擇「匯出所有場次（CSV）」。此 UTF-8 BOM 檔案會為每個現有活動輸出一列，包含已封存與已過期場次，以及活動設定、主辦者／狀態資訊、人數、預訂球友暱稱、媒體數量與公開網址；不會匯出參加者 PIN 碼及加入／退出歷程。

## 系統推播通知

每個場次頁面都有可自行開啟的瀏覽器／系統通知開關。主辦者編輯、封存、重新開放、鎖定／解除鎖定或刪除該場次，以及球友成功加入、進入候補或退出時，都會送出通知；失敗的加入／退出及個別點名勾選變更不會送出推播。

請產生一組固定使用的 VAPID 金鑰：

```bash
mkdir -p instance/web-push
cd instance/web-push
../../.venv/bin/vapid --gen --applicationServerKey
```

此指令會顯示應用伺服器金鑰，並建立 `private_key.pem`。請設定：

```text
WEB_PUSH_PUBLIC_KEY=<指令顯示的應用伺服器金鑰>
WEB_PUSH_PRIVATE_KEY=instance/web-push/private_key.pem
WEB_PUSH_SUBJECT=mailto:your-contact@example.com
```

私密金鑰與整個 `instance` 目錄都必須跨部署持久保存。更換 VAPID 金鑰會使既有瀏覽器訂閱失效。正式環境推播需要 HTTPS 及瀏覽器通知權限；支援的瀏覽器會將 localhost 視為安全的開發環境。

若缺少任何必要的 VAPID 設定，場次頁面的通知開關會保持停用。推播服務回覆 `404` 或 `410` 時，系統會自動移除失效端點。

## Docker

使用 Docker Compose 啟動應用程式：

```bash
docker compose up -d --build
```

Compose 會載入 `.env`、發布 `8080` 連接埠，並將具名磁碟區 `badminton-court-control-data` 掛載至 `/instance`。映像檔會將 `/app/instance` 連結至此目錄，因此重新建立容器時，SQLite 資料庫、頭像及場次媒體都會保留。停止服務但保留資料：

```bash
docker compose down
```

從專案根目錄建立映像檔：

```bash
docker build -t badminton-court-control-panel .
```

在 `8080` 連接埠執行、載入正式環境設定，並持久化 SQLite 資料庫及上傳檔案：

```bash
docker run --rm \
  --name badminton-court-control-panel \
  --env-file .env \
  -p 8080:8080 \
  -v badminton-court-control-data:/instance \
  badminton-court-control-panel
```

映像檔使用 `app.py` 作為 uWSGI 模組，並透過 Nginx 的 `8080` 連接埠提供服務。

### Nginx 反向代理與用戶端 IP 位址

另一個 Nginx 執行個體反向代理至 Docker 發布的連接埠時，容器會將 Docker 橋接閘道（通常是 `172.18.0.1`）視為直接連線來源。若要記錄訪客位址，請在 `.env` 設定 `TRUST_PROXY_HEADERS=1`，並讓對外且可信任的代理覆寫轉送標頭，而不是將不可信任的輸入附加在後方：

```nginx
location / {
    proxy_pass http://127.0.0.1:8080;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

驗證並重新載入 Nginx，再重新建立應用程式容器，讓 Compose 重新讀取 `.env`：

```bash
sudo nginx -t
sudo systemctl reload nginx
docker compose up -d --force-recreate app
docker compose exec app printenv TRUST_PROXY_HEADERS
```

最後一個指令必須顯示 `1`。只有應用程式完全透過會覆寫這些標頭的可信任代理存取時，才能啟用此設定。若 Nginx 前方另有 Cloudflare 或其他代理，請先使用該供應商的可信任位址範圍設定 Nginx real-IP 模組。

## 安全性與隱私

- `/privacy` 的公開雙語政策會說明應用程式內建的資料處理。自行架設的營運者必須檢查內容、設定 `PRIVACY_OPERATOR_NAME`、`PRIVACY_DATA_REGION` 與 `PRIVACY_CONTACT`，並揭露主機紀錄、備份、自訂服務或其他部署特有的處理。
- 會員密碼及球友 PIN 碼皆以安全密碼雜湊儲存。
- 同一使用者名稱與 IP 位址連續登入失敗時，會員及管理員登入會暫時鎖定。
- 設定 Cloudflare Turnstile 後，註冊、登入或送出聯絡留言前會先完成人機驗證。
- 聯絡留言會儲存在 SQLite，且只有管理員與最高管理員可以查看；選填回覆資訊不會公開。
- 會員成功登入時會記錄本機時間及已驗證的用戶端 IP。
- 成功加入或退出場次時會記錄暱稱、動作及時間；管理員可額外查看已驗證 IP 及概略裝置類型。
- 推播訂閱端點與加密金鑰只用於傳送使用者已同意的場次更新，且不會公開顯示。
- 系統不保留完整瀏覽器 User-Agent 字串，也不建立裝置指紋。
- 加入或退出失敗不會寫入活動紀錄。
- 停權會員會阻擋帳號登入及會員專用主辦功能，但不會刪除場次；公開暱稱／PIN 報名仍不需要登入。
- 會變更狀態的表單皆有 CSRF 防護。

## 活動生命週期與儲存

- 活動會在設定日期及結束時間後自動過期；過期場次會變成唯讀，並從預設列表隱藏。
- 啟用退出期限後，系統會在活動過期前獨立執行限制；球友仍可加入，但在設定的本地分鐘時間到達或超過後將無法自行退出。
- 已封存活動仍可透過直接連結、主辦者面板或管理後台查看。
- 未設定 `COURT_DATABASE` 時，SQLite 資料儲存在 `instance/courts.sqlite`。
- 頭像儲存在 `instance/avatars`。
- 場次相片及影片儲存在 `instance/court_media`。
- 具版本的社群分享縮圖快取於 `instance/social_thumbnails`。
- 更換或刪除資料時，系統會在適用情況下清理相關上傳檔案。

## 正式環境

- 第一次啟動前設定高強度的 `SECRET_KEY`、初始管理員名稱及密碼。
- 使用 HTTPS 提供網站，並設定 `SESSION_COOKIE_SECURE=1`。
- 僅在可信任反向代理會覆寫轉送的用戶端 IP 與網址通訊協定標頭時設定 `TRUST_PROXY_HEADERS=1`。
- 持久化並備份設定的 SQLite 資料庫及 `instance` 上傳目錄。
- 專案已內附產生媒體及活動資訊縮圖所需的 FFmpeg 執行檔與 Noto Sans TC 可變字型，無論是否使用 Docker 都可直接使用。
- 將正式網域加入 Google Maps 瀏覽器金鑰允許的參照網址。

## 測試

在虛擬環境中執行完整測試：

```bash
.venv/bin/pytest -q
```

## 授權標示與致謝

網站圖示使用 [`static/shuttlecock.png`](static/shuttlecock.png)，其來源為 [Flaticon 的 Shuttlecock icon](https://www.flaticon.com/free-icon/shuttlecock_9719863?term=badminton&page=1&position=51&origin=search&related_id=9719863)。產生活動資訊縮圖時使用內附的 [Noto Sans TC](https://github.com/notofonts/noto-cjk) 可變字型，並依 SIL Open Font License 1.1 授權。公開授權標示及授權連結可於 `/licenses` 查看。

Badminton Court Control Panel 在功能實作、程式碼檢查及測試過程中使用 [OpenAI Codex](https://openai.com/codex/) 協助。網站內容、營運及最終成果仍由專案擁有者負責；此說明不代表 OpenAI 對本網站提供背書或擁有權。
