#!/usr/bin/env python3
"""Run the real website and JSON API against a throwaway database of fictional courts.

Used by capture.sh so store screenshots show deterministic, fictional data. Every
record is created through the public JSON API (/api/v1), so the data has exactly the
shape the app receives in production. Nothing touches Web/instance or any real server.

Run with the website's virtualenv from the repository root:

    Web/.venv/bin/python Android/docs/store-listing/screenshots/fixture_server.py \
        --locale en-US --port 5055 --data-dir /tmp/bccp-fixtures

The script prints "fixture-server-ready" once seeding has finished and keeps serving
until it is stopped. Court dates are relative to today so every court stays upcoming.
"""
from __future__ import annotations

import argparse
import io
import json
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "Web"))

ORGANIZER = {"username": "coach_amy", "password": "fictional-pass-2026"}
PIN = "246810"

# Each locale gets its own independent fictional data set.
FIXTURES = {
    "en-US": {
        "courts": [
            {
                "key": "friday",
                "days": 2,
                "event_name": "Friday Night Doubles",
                "badminton_name": "Shuttle Social Club",
                "start_time": "19:00", "end_time": "22:00",
                "hall_name": "Riverside Sports Center",
                "location": "12 Riverside Road, Maple District",
                "court_id": "3 & 4",
                "member_min": 8, "member_max": 16, "ordered_count": 2,
                "reserved_nicknames": ["Coach Amy", "Ben"],
                "male_level_min": 6, "male_level_max": 12,
                "female_level_min": 4, "female_level_max": 10,
                "male_price": 280, "female_price": 240,
                "shuttlecock_info": "Feather shuttles, speed 77",
                "remark": "Doubles rotation every 15 minutes. Bring indoor shoes and a water bottle. Shuttles are included in the fee.",
                "leave_deadline": (1, "18:00"),
                "players": ["Mia Chen", "Leo Park", "Chloe Wu", "Noah Lin", "Ava Huang",
                            "Ethan Ho", "Zoe Tsai", "Lucas Yang", "Ivy Kao", "Owen Lee"],
                "waiting": [],
                "media": True,
                "messages": [
                    ("Mia Chen", "Is there parking near the hall?",
                     "Yes, the riverside lot is free after 6 PM."),
                    ("Leo Park", "Can I bring a friend who plays at level 8?",
                     "Sure, ask them to join here so I can keep count."),
                ],
            },
            {
                "key": "sunday",
                "days": 4,
                "event_name": "Sunday Morning Rally",
                "badminton_name": "Early Birds Badminton",
                "start_time": "08:00", "end_time": "10:00",
                "hall_name": "Northgate Community Gym",
                "location": "5 Northgate Lane, Cedar Town",
                "court_id": "1",
                "member_min": 4, "member_max": 8, "ordered_count": 0,
                "reserved_nicknames": [],
                "male_level_min": 3, "male_level_max": 9,
                "female_level_min": 3, "female_level_max": 9,
                "male_price": 200, "female_price": 200,
                "shuttlecock_info": "Nylon shuttles provided",
                "remark": "Friendly games for all ages.",
                "players": ["Grace Liu", "Henry Chou", "Ella Su", "Ryan Kuo",
                            "Lily Hsu", "Daniel Wang", "Sophie Lai", "Jack Tseng"],
                "waiting": ["Emma Fang", "Max Peng"],
            },
            {
                "key": "clinic",
                "days": 6,
                "event_name": "Beginner Footwork Clinic",
                "badminton_name": "Shuttle Social Club",
                "start_time": "14:00", "end_time": "16:00",
                "hall_name": "Lakeside Arena",
                "location": "300 Lakeside Avenue, Willow Bay",
                "court_id": "6",
                "member_min": 4, "member_max": 10, "ordered_count": 0,
                "reserved_nicknames": [],
                "male_level_min": 1, "male_level_max": 5,
                "female_level_min": 1, "female_level_max": 5,
                "male_price": 350, "female_price": 350,
                "shuttlecock_info": "Rackets available to borrow",
                "remark": "Coached drills for new players.",
                "players": ["Nina Cho", "Sam Lo", "Kai Hung"],
                "waiting": [],
            },
            {
                "key": "smash",
                "days": 9,
                "event_name": "Lunchtime Smash",
                "badminton_name": "Downtown Office League",
                "start_time": "12:00", "end_time": "13:30",
                "hall_name": "Central Sports Hall",
                "location": "77 Harbor Street, Downtown",
                "court_id": "2",
                "member_min": 4, "member_max": 12, "ordered_count": 0,
                "reserved_nicknames": [],
                "male_level_min": 5, "male_level_max": 14,
                "female_level_min": 5, "female_level_max": 14,
                "male_price": 150, "female_price": 150,
                "shuttlecock_info": "",
                "remark": "Quick games over the lunch break.",
                "players": ["Ruby Tang", "Felix Chu", "Iris Yeh", "Adam Kang", "Mila Pan"],
                "waiting": [],
            },
        ],
    },
    "zh-TW": {
        "courts": [
            {
                "key": "friday",
                "days": 2,
                "event_name": "週五夜間雙打",
                "badminton_name": "羽你同樂俱樂部",
                "start_time": "19:00", "end_time": "22:00",
                "hall_name": "河濱運動中心",
                "location": "楓林區河濱路 12 號",
                "court_id": "3、4",
                "member_min": 8, "member_max": 16, "ordered_count": 2,
                "reserved_nicknames": ["小雅教練", "阿斌"],
                "male_level_min": 6, "male_level_max": 12,
                "female_level_min": 4, "female_level_max": 10,
                "male_price": 280, "female_price": 240,
                "shuttlecock_info": "羽毛球，速度 77",
                "remark": "每 15 分鐘輪換雙打。請攜帶室內運動鞋與水壺，場地費已含用球。",
                "leave_deadline": (1, "18:00"),
                "players": ["陳小雨", "朴立安", "吳可薇", "林諾亞", "黃艾琳",
                            "何以森", "蔡若希", "楊路克", "高依婷", "李歐文"],
                "waiting": [],
                "media": True,
                "messages": [
                    ("陳小雨", "請問球館附近有停車場嗎？", "有的，河濱停車場晚上六點後免費。"),
                    ("朴立安", "可以帶一位程度 8 的朋友來嗎？", "可以，請他在這裡報名，方便我統計人數。"),
                ],
            },
            {
                "key": "sunday",
                "days": 4,
                "event_name": "週日晨間對打",
                "badminton_name": "早鳥羽球團",
                "start_time": "08:00", "end_time": "10:00",
                "hall_name": "北門社區體育館",
                "location": "杉木鎮北門巷 5 號",
                "court_id": "1",
                "member_min": 4, "member_max": 8, "ordered_count": 0,
                "reserved_nicknames": [],
                "male_level_min": 3, "male_level_max": 9,
                "female_level_min": 3, "female_level_max": 9,
                "male_price": 200, "female_price": 200,
                "shuttlecock_info": "提供尼龍球",
                "remark": "歡迎各年齡層一起友誼賽。",
                "players": ["劉恩典", "周亨利", "蘇艾拉", "郭睿恩",
                            "許莉莉", "王丹尼", "賴蘇菲", "曾傑克"],
                "waiting": ["方艾瑪", "彭麥斯"],
            },
            {
                "key": "clinic",
                "days": 6,
                "event_name": "新手步法教學",
                "badminton_name": "羽你同樂俱樂部",
                "start_time": "14:00", "end_time": "16:00",
                "hall_name": "湖畔體育館",
                "location": "柳灣市湖畔大道 300 號",
                "court_id": "6",
                "member_min": 4, "member_max": 10, "ordered_count": 0,
                "reserved_nicknames": [],
                "male_level_min": 1, "male_level_max": 5,
                "female_level_min": 1, "female_level_max": 5,
                "male_price": 350, "female_price": 350,
                "shuttlecock_info": "可借用球拍",
                "remark": "教練帶領新手練習。",
                "players": ["卓妮娜", "羅山姆", "洪凱"],
                "waiting": [],
            },
            {
                "key": "smash",
                "days": 9,
                "event_name": "午休殺球團",
                "badminton_name": "市中心上班族聯盟",
                "start_time": "12:00", "end_time": "13:30",
                "hall_name": "中央運動館",
                "location": "市中心港灣街 77 號",
                "court_id": "2",
                "member_min": 4, "member_max": 12, "ordered_count": 0,
                "reserved_nicknames": [],
                "male_level_min": 5, "male_level_max": 14,
                "female_level_min": 5, "female_level_max": 14,
                "male_price": 150, "female_price": 150,
                "shuttlecock_info": "",
                "remark": "利用午休時間快速打幾局。",
                "players": ["唐露比", "朱菲力", "葉艾莉", "康亞當", "潘米拉"],
                "waiting": [],
            },
        ],
    },
}


def court_photo() -> bytes:
    """A drawn, fictional top-down badminton court (no real photo)."""
    from PIL import Image, ImageDraw

    w, h = 1200, 800
    im = Image.new("RGB", (w, h), "#2f6f57")
    d = ImageDraw.Draw(im)
    for y in range(h):  # soft vertical light falloff
        shade = int(18 * (1 - abs(y - h / 2) / (h / 2)))
        d.line((0, y, w, y), fill=(47 + shade, 111 + shade, 87 + shade))
    line = (238, 241, 236)
    x0, y0, x1, y1 = 140, 120, 1060, 680
    d.rectangle((x0, y0, x1, y1), outline=line, width=8)
    d.line((x0, y0 + 50, x1, y0 + 50), fill=line, width=6)
    d.line((x0, y1 - 50, x1, y1 - 50), fill=line, width=6)
    cx = (x0 + x1) // 2
    d.line((cx, y0 - 30, cx, y1 + 30), fill=(250, 250, 250), width=10)  # net
    for x in (cx - 180, cx + 180):
        d.line((x, y0, x, y1), fill=line, width=6)
    d.line((x0, (y0 + y1) // 2, cx - 180, (y0 + y1) // 2), fill=line, width=6)
    d.line((cx + 180, (y0 + y1) // 2, x1, (y0 + y1) // 2), fill=line, width=6)
    d.line((x0 + 70, y0, x0 + 70, y1), fill=line, width=6)
    d.line((x1 - 70, y0, x1 - 70, y1), fill=line, width=6)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    return buf.getvalue()


def seed(client, locale: str) -> dict:
    lang = {"Accept-Language": "zh-TW" if locale == "zh-TW" else "en-US"}
    counter = iter(range(10, 250))

    def call(method, path, *, token=None, ip=None, **kwargs):
        headers = dict(lang)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        # Spread fixture traffic over fictional addresses so per-IP limits do not trip.
        environ = {"REMOTE_ADDR": ip or f"192.0.2.{next(counter)}"}
        response = getattr(client, method)(f"/api/v1{path}", headers=headers,
                                           environ_base=environ, **kwargs)
        if response.status_code >= 400:
            raise SystemExit(f"{method.upper()} {path} -> {response.status_code}: {response.get_data(as_text=True)}")
        return response.get_json(silent=True) or {}

    auth = call("post", "/auth/signup", json={
        **ORGANIZER, "confirm_password": ORGANIZER["password"], "device_name": "Pixel 7",
    })
    token = auth["token"]
    call("patch", "/me", token=token, json={"time_format": "24h"})

    guids: dict[str, str] = {}
    today = date.today()
    # Create the farthest court first so the newest-first list reads in a natural order.
    for spec in sorted(FIXTURES[locale]["courts"], key=lambda c: -c["days"]):
        body = {k: v for k, v in spec.items()
                if k not in {"key", "days", "players", "waiting", "media", "messages", "leave_deadline"}}
        body["court_date"] = (today + timedelta(days=spec["days"])).isoformat()
        if "leave_deadline" in spec:
            before, at = spec["leave_deadline"]
            body["leave_deadline_enabled"] = True
            body["leave_deadline_at"] = f"{(today + timedelta(days=spec['days'] - before)).isoformat()}T{at}"
        body["save_location"] = True
        if spec.get("media"):
            data = {"court": json.dumps(body),
                    "media": (io.BytesIO(court_photo()), "court.jpg", "image/jpeg")}
            court = call("post", "/courts", token=token, data=data,
                         content_type="multipart/form-data")["court"]
        else:
            court = call("post", "/courts", token=token, json=body)["court"]
        guid = court["guid"]
        guids[spec["key"]] = guid
        for name in spec["players"] + spec["waiting"]:
            call("post", f"/courts/{guid}/join", json={"username": name, "pin": PIN})
        for author, question, answer in spec.get("messages", []):
            posted = call("post", f"/courts/{guid}/messages",
                          json={"username": author, "pin": PIN, "message": question})
            call("post", f"/courts/{guid}/messages", token=token,
                 json={"message": answer, "parent_id": posted["message_id"]})
    user = call("get", "/me", token=token)
    return {"courts": guids, "token": token, "user": user.get("user", user)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--locale", choices=sorted(FIXTURES), required=True)
    parser.add_argument("--port", type=int, default=5055)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--data-dir", type=Path, required=True,
                        help="Throwaway directory; it is wiped and recreated.")
    parser.add_argument("--state-file", type=Path,
                        help="Write the court GUIDs and the organizer's token and user here as JSON.")
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    if data_dir == (ROOT / "Web" / "instance").resolve():
        raise SystemExit("refusing to use the real Web/instance directory")
    shutil.rmtree(data_dir, ignore_errors=True)
    data_dir.mkdir(parents=True)

    import app as core  # Web/app.py

    application = core.create_app({
        "TESTING": False,
        "DATABASE": str(data_dir / "courts.sqlite"),
        "AVATAR_FOLDER": str(data_dir / "avatars"),
        "COURT_MEDIA_FOLDER": str(data_dir / "court_media"),
        "SOCIAL_THUMBNAIL_FOLDER": str(data_dir / "social_thumbnails"),
        "TURNSTILE_SITE_KEY": "", "TURNSTILE_SECRET_KEY": "",
        "FCM_SERVICE_ACCOUNT_FILE": "",
        "WEB_PUSH_PUBLIC_KEY": "", "WEB_PUSH_PRIVATE_KEY": "",
        "CONTACT_DISCORD_WEBHOOK_URL": "", "CONTACT_TELEGRAM_BOT_TOKEN": "",
        "ADMIN_PASSWORD": "fictional-admin-2026",
        "GEOIP_COUNTRY_DB": "",
    })
    seeded = seed(application.test_client(), args.locale)
    if args.state_file:
        args.state_file.write_text(json.dumps(seeded, ensure_ascii=False))
    print("fixture-server-ready", json.dumps(seeded["courts"]), flush=True)
    application.run(host=args.host, port=args.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
