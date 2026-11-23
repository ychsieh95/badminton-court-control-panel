# Play 商店螢幕截圖

[English](README.md) | 繁體中文（台灣）

這些腳本會從模擬器擷取 App 現有畫面的真實像素，再製作成 Play 商店螢幕截圖。所有場次、球友、留言與帳號都是虛構的。

## 運作方式

- `fixture_server.py` 以暫存目錄中的一次性資料庫執行真正的網站與 JSON API（`Web/app.py`）。它透過 `/api/v1` 建立虛構的場次、球友與留言板討論串，因此 App 收到的資料與正式環境完全相同。它不會碰到 `Web/instance/` 或任何真實伺服器。每個語系各有一組資料，場次日期以今天為基準，所以每個場次都是即將舉行。
- `capture.py` 會清除模擬器上的 App 資料，再以 `run-as` 直接寫入 DataStore（僅限 debug 版本）：fixture 伺服器位址（`http://10.0.2.2:PORT`）、淺色主題（預設配色）、記住的報名名稱，以及虛構主辦人 `coach_amy` 的登入權杖。因此 App 不會連到正式伺服器，也不需要自動操作登入畫面。接著它以 intent 與從 UI 樹找到的位置點擊開啟各情境，並儲存經過驗證的 1080 × 2400 直向 PNG。
- `capture.sh` 是進入點。它會選擇或啟動模擬器（絕不使用實體裝置）、建置並安裝 debug APK、將系統切換為淺色模式、讓狀態列進入 System UI 示範模式（主機目前時間、滿格電量與 Wi-Fi、不顯示通知圖示）、為每個語系執行 fixture 伺服器與 `capture.py`，最後還原模擬器設定。
- `render_store.py` 以擷取的畫面製作完成的商店圖。

| 情境 | 畫面 | 輸出 |
| --- | --- | --- |
| `courts` | 所有場次列表 | `01-courts.png` |
| `court-detail` | 場次頁面頂部 | `02-court-detail.png` |
| `members-levels` | 人數、費用與程度說明 | `03-members-levels.png` |
| `join` | 已填入名稱與隱藏 PIN 的報名面板 | `04-join.png` |
| `messages` | 含主辦人回覆的留言板 | `05-messages.png` |
| `organize` | 我的場次（主辦人控制台） | `06-organize.png` |
| `court-form` | 編輯場次表單 | `07-court-form.png` |

## 需求

- Android SDK，包含 platform tools、模擬器，以及 API 33 以上的 AVD（App 個別語言設定）。Pixel 7 設定檔（1080 × 2400）與現有輸出相符。
- 建置需要 JDK 17–21。未設定 `JAVA_HOME` 時，腳本會使用 `/opt/android-studio/jbr` 的 Android Studio JBR。
- `app/google-services.json`（見 `Android/README.md`）。
- 位於 `Web/.venv` 的網站虛擬環境（見 `Web/README.md`），以及供 `render_store.py` 使用、已安裝 Pillow 與 NumPy 的 Python 3。
- 位於 `/usr/share/fonts/opentype/noto/` 的 Noto Sans CJK 字型。

## 擷取

在儲存庫根目錄執行：

```bash
Android/docs/store-listing/screenshots/capture.sh --avd Pixel_7_API_36d0
```

使用已在執行的模擬器：

```bash
Android/docs/store-listing/screenshots/capture.sh --serial emulator-5560 --no-start
```

預設會將兩種語系寫入 `closed-testing/alpha/app/en-US/` 與 `closed-testing/alpha/app/zh-TW/`。使用 `--locale en-US` 或 `--locale zh-TW` 只擷取一種語言，`--scenarios join,messages` 只擷取部分情境，`--output DIR` 用於其他測試軌，`--no-build` 重新安裝現有 APK，若 5055 已被占用則使用 `--port`。由腳本啟動的模擬器會在結束時關閉，傳入 `--keep-emulator` 可讓它繼續執行。`--timeout` 設定開機與就緒的等待時間，預設為 180 秒。執行 `capture.sh --help` 查看所有選項。

擷取時會清除模擬器上的 App 資料（它與正式版使用相同的應用程式 ID），結束時會再清除一次，不會留下 fixture 登入狀態或本機伺服器位址。若之後要用該模擬器進行其他測試，請重新登入。

## 商店圖

```bash
python3 Android/docs/store-listing/screenshots/render_store.py \
  --input  Android/docs/store-listing/screenshots/closed-testing/alpha/app \
  --output Android/docs/store-listing/screenshots/closed-testing/alpha/store
```

每種視覺風格在 `closed-testing/alpha/store/` 下各有一個目錄，內含 `en-US/`、`zh-TW/` 與 `source/`（以程式繪製、半尺寸的背景全景圖，七張圖由此裁切）。背景都以程式繪製，未使用任何第三方圖像。

| 風格 | 外觀 |
| --- | --- |
| `court-green` | 深綠色搭配金色球場線條與點綴 |
| `shuttle-ivory` | 暖象牙色搭配琥珀色與金色的羽球飛行弧線 |
| `night-arena` | 海軍藍球館搭配頂燈光束與琥珀色地面光暈 |

圖片文案位於 `render_store.py` 的 `COPY`。請保持英文與繁體中文意思一致、每個標題維持一行（文案若擠到手機框內，腳本會停止），並且只描述 App 實際具備的功能。傳入 `--styles court-green` 可只產生一種風格。上傳前請逐張檢查。

## 疑難排解

- **情境等待標籤逾時：** `capture.py` 中 `LABELS` 的文字必須與 `res/values*/strings.xml` 相符。修改用字後請一併更新。
- **捲動後區塊被裁切：** 調整 `Runner.scroll_top` 中的 `top` 目標位置。
- **連接埠被占用：** 傳入 `--port`。
- **Fixture 伺服器結束：** 腳本會印出它的記錄。請確認 `Web/.venv` 已安裝網站所需套件。
