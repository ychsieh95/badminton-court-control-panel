# 羽球場控面板

[![Web CI](https://github.com/ychsieh95/badminton-court-control-panel/actions/workflows/web.yml/badge.svg)](https://github.com/ychsieh95/badminton-court-control-panel/actions/workflows/web.yml) [![Android CI](https://github.com/ychsieh95/badminton-court-control-panel/actions/workflows/android.yml/badge.svg)](https://github.com/ychsieh95/badminton-court-control-panel/actions/workflows/android.yml) [![Last commit](https://img.shields.io/github/last-commit/ychsieh95/badminton-court-control-panel)](https://github.com/ychsieh95/badminton-court-control-panel/commits/main) [![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/) [![Flask 3.1](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/) [![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](Web/docker/compose.yaml) [![Android 8.0+](https://img.shields.io/badge/Android-8.0%2B%20(API%2026)-34A853?logo=android&logoColor=white)](https://developer.android.com/) [![Kotlin 2.2](https://img.shields.io/badge/Kotlin-2.2-7F52FF?logo=kotlin&logoColor=white)](https://kotlinlang.org/) [![Jetpack Compose](https://img.shields.io/badge/Jetpack%20Compose-Material%203-4285F4?logo=jetpackcompose&logoColor=white)](https://developer.android.com/compose) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) ![Languages](https://img.shields.io/badge/i18n-en--US%20%7C%20zh--TW-blue?logo=googletranslate&logoColor=white)

[English](README.md) · **繁體中文**

羽球場控面板（Badminton Court Control Panel）是一套支援中英雙語的羽球活動管理系統。主揪可以發布與管理場次；球友不需要建立帳號，只要使用暱稱與 6 位數 PIN 碼就能加入或退出場次，也可以在每個場次的留言板提問。

本專案由共用同一台伺服器的兩個部分組成：

| 目錄 | 內容 | 文件 |
| --- | --- | --- |
| [`Web/`](Web/) | Flask 網站與 `/api/v1` JSON API，包含 Docker 設定與測試 | [說明文件](Web/README.zh-TW.md) · [API 參考](Web/API.md) |
| [`Android/`](Android/) | 以 JSON API 為基礎的原生 Android App（Kotlin、Jetpack Compose） | [說明文件](Android/README.zh-TW.md) |

## 特色

- **球友**：瀏覽與篩選場次、使用暱稱與 PIN 碼加入或退出、額滿時進入候補名單、在留言板留言，並為場次開啟通知。
- **主揪**：建立、編輯、複製與封存場次，設定球館、程度、費用、預訂名額、相片與影片；回覆留言；進行點名與費用結清。
- **管理員**：管理所有場次與留言、管理會員與角色，以及閱讀聯絡留言。
- **通知**：透過 Web Push 提供瀏覽器通知，透過 Firebase 雲端通訊提供 Android 通知，兩者皆為選用。
- **語言與主題**：支援英文與繁體中文，並提供多種配色及淺色、深色模式。

## 快速開始

在本機執行網站：

```bash
cd Web
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/flask --app app run --debug
```

開啟 <http://127.0.0.1:5000>，並以開發用管理員帳號 `admin` / `change-me` 登入。環境設定、選用整合服務與 Docker 部署請見 [Web/README.zh-TW.md](Web/README.zh-TW.md)。

建置 Android App（需要 JDK 17～21、Android SDK 與 `Android/app/google-services.json`）：

```bash
cd Android
./gradlew :app:installDebug
```

若要讓 App 連線至本機伺服器，請開啟「帳號 → App 設定」，並在模擬器中輸入 `http://10.0.2.2:5000`。詳細說明請見 [Android/README.zh-TW.md](Android/README.zh-TW.md)。

## 測試

```bash
(cd Web && .venv/bin/pytest -q)
(cd Android && ./gradlew :app:testDebugUnitTest)
```

推送或發出 Pull Request 至 `main` 時，GitHub Actions 會執行相同的檢查：[`web.yml`](.github/workflows/web.yml) 在 Python 3.10 與 3.13 上執行，[`android.yml`](.github/workflows/android.yml) 另外會檢查產生的字串資源是否為最新。Android 工作流程需要儲存庫密鑰 `GOOGLE_SERVICES_JSON`，內容為以 `base64 -w0` 編碼的 `app/google-services.json`。

## 同時開發兩個部分

- Android App 只使用 JSON API。API 變更時，請同時更新 `Web/api.py`、`Web/API.md` 與 `Web/tests/test_api.py`，再更新 App 的模型類別與測試範例資料。
- 介面文字為共用。來源是 `Web/app.py` 中網站的 `TRANSLATIONS` 表，Android 字串資源則在 `Android/` 中以 `python3 tools/gen_strings.py` 產生。
- `.env`、Firebase 檔案與簽署金鑰等機密只保留在本機，並已被 Git 忽略。
- 每項變更都要記錄在 [`docs/update-history/`](docs/update-history/) 下對應的雙語檔案：使用網站或 App 的人能察覺的變更記錄在 `app/`，工具、測試、CI 與文件的變更記錄在 `project/`。

## 文件

| 文件 | 內容 |
| --- | --- |
| [CONTRIBUTING.md](docs/CONTRIBUTING.md) | 環境需求、要執行的檢查、API 與翻譯規則，以及機密資料。 |
| [PRIVACY.md](docs/PRIVACY.md) | 伺服器、瀏覽器與 App 儲存的資料，以及涉及的第三方服務。 |
| [SECURITY.md](docs/SECURITY.md) | 支援的版本、私下回報漏洞的方式與信任邊界。 |
| [UI_BRIEF.md](docs/UI_BRIEF.md) | Android App 的分層、狀態約定、畫面與主題。 |
| [更新紀錄](docs/update-history/) | 自上次發行以來的 App 與專案變更。 |

## 授權

本專案以 [MIT 授權條款](LICENSE)釋出。內附的第三方素材（例如 Noto Sans TC 字型與羽毛球圖示）仍適用其各自的授權，請見 [Web/README.zh-TW.md](Web/README.zh-TW.md#素材來源與授權)。
