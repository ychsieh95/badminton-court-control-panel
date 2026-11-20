# badminton-court-control-panel｜羽球場控面板

Badminton Court Control Panel is a bilingual (English / Traditional Chinese) system for organizing badminton events. Organizers publish and manage courts. Players can find, join, or leave an event without creating an account.

Badminton Court Control Panel 是一套支援中英雙語的羽球活動管理系統。主揪可以發布與管理場次，球友不需要建立帳號，就能搜尋、加入或退出活動。

## Repository layout｜目錄結構

| Directory | Contents | 內容 |
| --- | --- | --- |
| [`Web/`](Web/) | Flask website, JSON API, Docker files, and tests | Flask 網站、JSON API、Docker 設定與測試 |
| [`Android/`](Android/) | Android app (Kotlin, Jetpack Compose), built on the JSON API | Android App（Kotlin、Jetpack Compose），使用 JSON API |

## Documentation｜文件

- Web setup, configuration, and deployment: [Web/README.md](Web/README.md) · [繁體中文](Web/README.zh-TW.md)
- JSON API reference (`/api/v1`): [Web/API.md](Web/API.md)
- Android app build and setup: [Android/README.md](Android/README.md)

## Quick start｜快速開始

```bash
cd Web
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
.venv/bin/flask --app app run --debug
```

Run tests from `Web/` with `.venv/bin/pytest -q`.

測試請在 `Web/` 目錄執行 `.venv/bin/pytest -q`。
