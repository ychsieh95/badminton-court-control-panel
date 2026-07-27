# badminton-court-control-panel｜羽球場控面板

[English（預設）](README.md) · **繁體中文**

Badminton Court Control Panel 是一套支援雙語的 Flask 羽球活動管理系統。主辦者可以發布與管理場次，球友不需要建立帳號，就能搜尋、加入或退出活動。

## 功能特色

### 球友功能

- 瀏覽開放場次，並依關鍵字、建立者、日期範圍、球員程度、男女程度範圍、名額及活動狀態篩選。
- 使用暱稱及私密 6 位數 PIN 碼加入或退出場次，不需要註冊會員。
- 正式名額額滿時，自動依加入順序進入候補名單。
- 可針對個別場次開啟系統推播通知，在場次資訊或球友名單變更時收到通知。
- 查看日期、星期、時間、球館、地點、費用、用球、程度、主辦者、備註、球友名單及活動媒體。
- 在行動裝置上透過浮動按鈕開啟無障礙加入視窗。

### 主辦者功能

- 建立會員帳號，並從 `/my-courts` 管理自己的活動。
- 設定選填的活動名稱與羽球團名稱，並取得 `https://your-domain.example/<GUID>` 格式的永久 UUID 連結。
- 設定日期、24 小時制起訖時間、Google 地點球館、場地編號、人數範圍、預訂名額、男女程度範圍、費用、用球及備註。
- 建立活動時儲存常用球館地點，日後無須搜尋即可重複使用，並可在個人資料頁刪除。
- 記錄預訂球友的暱稱，並決定是否向訪客顯示。
- 最多上傳 12 個 JPEG、PNG、WebP、MP4 或 WebM 檔案；第一張圖片會作為場次卡片封面。
- 編輯、複製、封存、恢復或刪除自己建立的活動。
- 啟動「點名與結清」，將活動切換為唯讀，並記錄出席及費用結清狀態。

### 管理員功能

- 建立、編輯、複製、封存、恢復及刪除任何場次。
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
- 提供黑白、綠色與萊姆、紫色及黃色配色，每種配色皆支援系統、淺色及深色模式。
- 新訪客預設使用「黃色 · 淺色」；已儲存的偏好設定會優先套用。
- 內建台灣羽球推廣協會 1～18 級程度分級參考。

## 主要路由

| 路由 | 用途 |
| --- | --- |
| `/` | 首頁與即將開始的場次 |
| `/introduction` | 公開網站介紹 |
| `/courts` | 可篩選的公開場次列表 |
| `/courts/new` | 會員與管理員共用的新增場次表單 |
| `/<GUID>` | 公開場次詳情及報名 |
| `/signup` | 會員註冊 |
| `/login` | 會員及管理員登入 |
| `/my-courts` | 主辦者管理面板 |
| `/account/profile` | 會員個人資料與頭像 |
| `/admin` | 管理後台 |
| `/admin/users` | 會員管理 |
| `/licenses` | 素材授權及開發協助說明 |

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
| `HCAPTCHA_SITE_KEY` | 空白 | 公開的 hCaptcha 網站金鑰；與私密金鑰同時設定後保護註冊及登入。 |
| `HCAPTCHA_SECRET_KEY` | 空白 | hCaptcha 私密驗證金鑰；不可傳送至瀏覽器。 |
| `HCAPTCHA_VERIFY_TIMEOUT` | `5` | 伺服器端 hCaptcha 驗證逾時秒數。 |
| `COURT_DATABASE` | `instance/courts.sqlite` | SQLite 資料庫位置。 |
| `GOOGLE_MAPS_API_KEY` | 空白 | 啟用 Google Places 球館自動完成。 |
| `WEB_PUSH_PUBLIC_KEY` | 空白 | 提供給瀏覽器的 VAPID 公開應用伺服器金鑰。 |
| `WEB_PUSH_PRIVATE_KEY` | 空白 | 私密 VAPID 金鑰內容或 PEM 檔案路徑。 |
| `WEB_PUSH_SUBJECT` | 空白 | VAPID 聲明使用的營運者聯絡 URI，例如 `mailto:admin@example.com`。 |
| `WEB_PUSH_TIMEOUT` | `5` | 每個推播接收者的傳送逾時秒數。 |
| `SESSION_COOKIE_SECURE` | `0` | 網站完全透過 HTTPS 提供時設為 `1`。 |
| `TRUST_PROXY_HEADERS` | `0` | 信任 `X-Forwarded-For` 的第一個位址；僅能在會覆寫此標頭的可信任反向代理後啟用。 |
| `GEOIP_COUNTRY_DB` | 空白 | 選用的本機 MaxMind GeoIP2／GeoLite2 國家資料庫。 |
| `DEFAULT_COUNTRY_CODE` | 空白 | 選用的兩碼備用國家代碼；未知地區訪客預設使用英文。 |
| `LOGIN_MAX_ATTEMPTS` | `5` | 暫時鎖定前允許的登入失敗次數。 |
| `LOGIN_LOCKOUT_SECONDS` | `900` | 暫時鎖定秒數。 |

處理程序環境中已存在的變數會優先於 `.env`。

## hCaptcha

同時設定 `HCAPTCHA_SITE_KEY` 及 `HCAPTCHA_SECRET_KEY` 後，`/signup` 與共用的 `/login` 頁面都會要求 hCaptcha。建立帳號或處理登入憑證前，伺服器會先向 hCaptcha 驗證瀏覽器回傳內容。缺少、遭拒、過期、重複使用、格式錯誤或無法驗證的回應都會被拒絕。

任一金鑰留空或 Flask 偵錯模式啟用時，hCaptcha 會自動停用。私密金鑰僅用於伺服器間驗證，不會輸出至 HTML。hCaptcha 官方服務可能拒絕 `localhost` 與 `127.0.0.1`；一般本機開發可不設定金鑰，或使用 hCaptcha 支援的開發主機名稱。

## Google 球館搜尋

將 `GOOGLE_MAPS_API_KEY` 設為已啟用 **Maps JavaScript API** 及 **Places API (New)** 的瀏覽器金鑰。Google Cloud 專案必須啟用帳單功能。

請在 **網站（HTTP 參照網址）** 中加入正式網域。本機開發請允許：

```text
http://127.0.0.1:5000/*
http://localhost:5000/*
```

未設定金鑰時，場次表單仍可正常使用，並會提供即時 Google 地圖搜尋連結。

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

## 安全性與隱私

- 會員密碼及球友 PIN 碼皆以安全密碼雜湊儲存。
- 同一使用者名稱與 IP 位址連續登入失敗時，會員及管理員登入會暫時鎖定。
- 設定 hCaptcha 後，註冊或處理登入憑證前會先完成人機驗證。
- 會員成功登入時會記錄本機時間及已驗證的用戶端 IP。
- 成功加入或退出場次時會記錄暱稱、動作及時間；管理員可額外查看已驗證 IP 及概略裝置類型。
- 推播訂閱端點與加密金鑰只用於傳送使用者已同意的場次更新，且不會公開顯示。
- 系統不保留完整瀏覽器 User-Agent 字串，也不建立裝置指紋。
- 加入或退出失敗不會寫入活動紀錄。
- 停權會員會阻擋帳號登入及會員專用主辦功能，但不會刪除場次；公開暱稱／PIN 報名仍不需要登入。
- 會變更狀態的表單皆有 CSRF 防護。

## 活動生命週期與儲存

- 活動會在設定日期及結束時間後自動過期；過期場次會變成唯讀，並從預設列表隱藏。
- 已封存活動仍可透過直接連結、主辦者面板或管理後台查看。
- 未設定 `COURT_DATABASE` 時，SQLite 資料儲存在 `instance/courts.sqlite`。
- 頭像儲存在 `instance/avatars`。
- 場次相片及影片儲存在 `instance/court_media`。
- 更換或刪除資料時，系統會在適用情況下清理相關上傳檔案。

## 正式環境

- 第一次啟動前設定高強度的 `SECRET_KEY`、初始管理員名稱及密碼。
- 使用 HTTPS 提供網站，並設定 `SESSION_COOKIE_SECURE=1`。
- 僅在可信任反向代理會覆寫 `X-Forwarded-For` 時設定 `TRUST_PROXY_HEADERS=1`。
- 持久化並備份設定的 SQLite 資料庫及 `instance` 上傳目錄。
- 將正式網域加入 Google Maps 瀏覽器金鑰允許的參照網址。

## 測試

在虛擬環境中執行完整測試：

```bash
.venv/bin/pytest -q
```

## 授權標示與致謝

網站圖示使用 [`static/shuttlecock.png`](static/shuttlecock.png)，其來源為 [Flaticon 的 Shuttlecock icon](https://www.flaticon.com/free-icon/shuttlecock_9719863?term=badminton&page=1&position=51&origin=search&related_id=9719863)。公開授權標示及授權連結可於 `/licenses` 查看。

Badminton Court Control Panel 在功能實作、程式碼檢查及測試過程中使用 [OpenAI Codex](https://openai.com/codex/) 協助。網站內容、營運及最終成果仍由專案擁有者負責；此說明不代表 OpenAI 對本網站提供背書或擁有權。
