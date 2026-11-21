#!/usr/bin/env python3
"""Drive the installed debug app through the store screenshot scenarios for one locale.

Called by capture.sh after the fixture server is running. It seeds the app's DataStore
(server address, light theme, the fictional organizer's sign-in), opens each scenario
with intents and taps found in the UI tree, and saves validated portrait PNGs.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from device import ACTIVITY, APP_ID, Device, prefs_for  # noqa: E402

SCENARIOS = {
    "courts": "01-courts.png",
    "court-detail": "02-court-detail.png",
    "members-levels": "03-members-levels.png",
    "join": "04-join.png",
    "messages": "05-messages.png",
    "organize": "06-organize.png",
    "court-form": "07-court-form.png",
}

# UI labels per locale. They must match res/values*/strings.xml.
LABELS = {
    "en-US": {
        "friday": "Friday Night Doubles", "join": "Join court", "pin": "6-digit PIN",
        "members": "MEMBERS", "board": "Message board", "organize": "Organize",
        "my_courts": "Your court events", "more": "More options", "edit": "Edit",
        "event_info": "Event information", "joiner": "Jamie Lo",
        "join_body": "Pick a username and a private 6-digit PIN.",
    },
    "zh-TW": {
        "friday": "週五夜間雙打", "join": "加入場次", "pin": "6 位數 PIN 碼",
        "members": "人數", "board": "留言板", "organize": "主辦",
        "my_courts": "你的球場活動", "more": "更多選項", "edit": "編輯",
        "event_info": "活動資訊", "joiner": "林小安",
        "join_body": "設定使用者名稱與私密的 6 位數 PIN 碼。",
    },
}

PIN = "135790"
SETTLE = 1.5


class Runner:
    def __init__(self, device: Device, locale: str, state: dict, server_url: str):
        self.d = device
        self.locale = locale
        self.state = state
        self.server_url = server_url
        self.t = LABELS[locale]

    def fresh(self) -> None:
        prefs = prefs_for(self.state, self.server_url)
        prefs["last_join_name"] = self.t["joiner"]
        self.d.reset_app(self.locale, prefs)

    def open_court(self, key: str) -> None:
        guid = self.state["courts"][key]
        self.d.shell(f"am force-stop {APP_ID}")
        self.d.shell(f"am start -W -n {ACTIVITY} -a android.intent.action.SEND "
                     f"-t text/plain --es android.intent.extra.TEXT {guid}")
        self.d.wait_for(self.t["friday"])

    def scroll_top(self, label: str) -> None:
        # Leave the section heading, with its eyebrow, just under the top app bar.
        self.d.scroll_to(label, top=400)

    # --- scenarios ---------------------------------------------------------------
    def courts(self) -> None:
        self.d.launch()
        self.d.wait_for(self.t["friday"])

    def court_detail(self) -> None:
        self.open_court("friday")

    def members_levels(self) -> None:
        self.open_court("friday")
        self.scroll_top(self.t["members"])

    def join(self) -> None:
        self.open_court("friday")
        self.d.tap(self.t["join"])
        self.d.tap(self.t["pin"])
        time.sleep(0.6)
        self.d.shell(f"input text {PIN}")
        time.sleep(0.4)
        self.d.hide_keyboard()
        # The BACK key switches the UI to keyboard-navigation mode, which draws a focus ring.
        # A tap on static sheet text returns it to touch mode.
        self.d.tap(self.t["join_body"])

    def messages(self) -> None:
        self.open_court("friday")
        self.scroll_top(self.t["board"])

    def organize(self) -> None:
        self.d.launch()
        self.d.tap(self.t["organize"])
        self.d.wait_for(self.t["my_courts"])

    def court_form(self) -> None:
        self.open_court("friday")
        self.d.tap(self.t["more"])
        self.d.tap(self.t["edit"])
        self.d.wait_for(self.t["event_info"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--serial", required=True)
    parser.add_argument("--adb", required=True)
    parser.add_argument("--locale", choices=sorted(LABELS), required=True)
    parser.add_argument("--state-file", type=Path, required=True)
    parser.add_argument("--server-url", required=True)
    parser.add_argument("--output", type=Path, required=True, help="Locale directory for the PNGs.")
    parser.add_argument("--scenarios", default=",".join(SCENARIOS))
    args = parser.parse_args()

    scenarios = [s for s in args.scenarios.split(",") if s]
    unknown = [s for s in scenarios if s not in SCENARIOS]
    if unknown:
        raise SystemExit(f"unsupported scenario: {', '.join(unknown)}")

    device = Device(args.serial, args.adb)
    runner = Runner(device, args.locale, json.loads(args.state_file.read_text()), args.server_url)
    for scenario in scenarios:
        runner.fresh()
        getattr(runner, scenario.replace("-", "_"))()
        time.sleep(SETTLE)
        path = args.output / SCENARIOS[scenario]
        size = device.screenshot(path)
        print(f"OK  {args.locale + '/' + scenario:28} {size}  {path}", flush=True)


if __name__ == "__main__":
    main()
