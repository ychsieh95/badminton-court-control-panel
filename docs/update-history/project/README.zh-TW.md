# 專案更新記錄

工具、測試、持續整合與文件的變更。

## 未發行

### Android 字串產生

兩個 `strings.xml` 檔案改由 `Android/tools/gen_strings.py` 從網站的 `TRANSLATIONS` 表產生，應用程式專用字串則放在 `Android/tools/extra_strings.json`。原本手動加入的留言板字串改由產生器處理，之後應用程式改用網站的 `court_message_*` 字串，並移除 21 個重複字串，畫面上的文字沒有變化。

### 程式開發代理指示

新增 `Android/AGENTS.md` 與 `Android/CLAUDE.md`，內容涵蓋應用程式架構與僅使用 API 的規則、產生的字串、機密資料與虛構測試資料、驗證方式及發行流程，並新增根目錄的 `CLAUDE.md` 說明提交訊息規則。`Android/CLAUDE.md` 也加入同一條提交訊息規則。Android 的 Claude Code 技能改記錄於 `Android/.claude/skills.lock.json`，並提供下載腳本，不再直接提交。

### 持續整合

新增 GitHub Actions 工作流程。`web.yml` 會在 `Web/` 變更時，以 Python 3.10 與 3.13 執行 pytest 及 Node 瀏覽器控制項測試。`android.yml` 會在 `Android/` 或 `Web/app.py` 變更時，先檢查產生的字串是否為最新，再執行單元測試與偵錯版建置，並使用 `GOOGLE_SERVICES_JSON` 儲存庫密鑰。

### 貢獻、隱私、安全性與 UI 文件

為本專案重寫 `docs/CONTRIBUTING.md`、`docs/PRIVACY.md`、`docs/SECURITY.md`、`docs/UI_BRIEF.md` 與本更新記錄，取代沿用自無關應用程式的內容。內容現涵蓋貢獻者的網站與 Android 檢查、API 與翻譯規則及機密資料；伺服器、瀏覽器與應用程式儲存的資料及相關第三方服務；帳號、工作階段、API 權杖、上傳檔案與應用程式的信任邊界；以及應用程式的分層、狀態合約、畫面與主題。

### 排除追蹤的機密資料與儲存庫結構

將網站移至 `Web/`，與新的 `Android/` 目錄並列，並排除追蹤憑證、金鑰庫、Firebase 服務帳戶金鑰、`google-services.json`、`.env` 檔案與 `tmp/`。

### Play 商店螢幕截圖

在 `Android/docs/store-listing/screenshots/` 新增工具，會建置偵錯版應用程式、以填入虛構資料的暫時資料庫執行網站、在模擬器上以英文與繁體中文擷取各情境畫面，再將擷取畫面排版成商店展示圖。其 README 說明 `capture.sh` 的所有選項。

### README 與授權

以英文與繁體中文重寫根目錄、`Web/` 與 `Android/` 的 README，加入狀態徽章，並以 MIT 授權發布專案。隨附的第三方素材仍沿用各自的授權。README 會連結貢獻、隱私、安全性與 UI 文件及更新記錄，並說明各個 CI 工作流程的檢查內容。

### 發行版簽署

Android 發行版改用從未追蹤的 `Android/keystore.properties` 讀取的上傳金鑰簽署。沒有該檔案時，發行版會維持未簽署。

### 測試場次日期

將測試場次日期從 2026 年改為月曆相同的 2099 年，讓測試中的場次不再過期，星期檢查也仍然成立。
