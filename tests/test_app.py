import base64
import csv
import html
import io
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from PIL import Image
from werkzeug.security import check_password_hash

import app as app_module
from app import classify_device, create_app, get_db, verify_turnstile_response


@pytest.fixture()
def app(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.sqlite"),
            "SECRET_KEY": "test-secret",
            "ADMIN_USERNAME": "manager",
            "ADMIN_PASSWORD": "correct-horse",
            "GOOGLE_MAPS_API_KEY": "",
            "WEB_PUSH_PUBLIC_KEY": "",
            "WEB_PUSH_PRIVATE_KEY": "",
            "WEB_PUSH_SUBJECT": "",
            "WEB_PUSH_TIMEOUT": 1,
            "TURNSTILE_SITE_KEY": "",
            "TURNSTILE_SECRET_KEY": "",
            "TURNSTILE_VERIFY_TIMEOUT": 1,
            "AVATAR_FOLDER": str(tmp_path / "avatars"),
            "COURT_MEDIA_FOLDER": str(tmp_path / "court-media"),
            "SOCIAL_THUMBNAIL_FOLDER": str(
                tmp_path / "social-thumbnails"
            ),
            "SOCIAL_THUMBNAIL_FFMPEG": "ffmpeg",
            "SOCIAL_THUMBNAIL_FONT": "",
            "DEFAULT_COUNTRY_CODE": "TW",
            "PRIVACY_OPERATOR_NAME": "",
            "PRIVACY_DATA_REGION": "",
            "PRIVACY_CONTACT": "",
            "ADMIN_CONTACT": "",
            "ADMIN_CONTACT_DISCORD": "",
            "ADMIN_CONTACT_LINE": "",
            "ADMIN_CONTACT_TELEGRAM": "",
            "CONTACT_DISCORD_WEBHOOK_URL": "",
            "CONTACT_TELEGRAM_BOT_TOKEN": "",
            "CONTACT_TELEGRAM_CHAT_ID": "",
            "CONTACT_NOTIFICATION_TIMEOUT": 1,
            "TRUST_PROXY_HEADERS": False,
            "LEAVE_MAX_ATTEMPTS": 5,
            "LEAVE_LOCKOUT_SECONDS": 900,
        }
    )
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def csrf(client, path="/"):
    response = client.get(path)
    match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
    if match:
        return match.group(1).decode()
    with client.session_transaction() as session:
        return session["csrf_token"]


def test_health_check(client):
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_turnstile_widgets_render_on_signup_and_login_pages(client, app):
    app.config.update(
        TURNSTILE_SITE_KEY="test-site-key",
        TURNSTILE_SECRET_KEY="test-secret-key",
    )
    for path, action in (("/signup", b"signup"), ("/login", b"login")):
        response = client.get(path)
        assert b'class="cf-turnstile"' in response.data
        assert b'data-sitekey="test-site-key"' in response.data
        assert b'data-action="' + action + b'"' in response.data
        assert b'data-language="zh-tw"' in response.data
        assert b'data-size="flexible"' in response.data
        assert (
            b"https://challenges.cloudflare.com/turnstile/v0/api.js"
            in response.data
        )
        assert b"test-secret-key" not in response.data


def test_turnstile_is_disabled_in_debug_mode(client, app, monkeypatch):
    app.config.update(
        DEBUG=True,
        TURNSTILE_SITE_KEY="test-site-key",
        TURNSTILE_SECRET_KEY="test-secret-key",
    )
    verification_requested = False

    def unexpected_urlopen(*_args, **_kwargs):
        nonlocal verification_requested
        verification_requested = True
        raise AssertionError("Turnstile must not be contacted in debug mode")

    monkeypatch.setattr(app_module, "urlopen", unexpected_urlopen)
    page = client.get("/signup")
    assert b'class="cf-turnstile"' not in page.data
    assert b"challenges.cloudflare.com/turnstile" not in page.data

    created = client.post(
        "/signup",
        data={
            "csrf_token": csrf(client, "/signup"),
            "username": "debug-user",
            "password": "strong-pass",
            "confirm_password": "strong-pass",
        },
        follow_redirects=False,
    )
    assert created.status_code == 302
    assert verification_requested is False


@pytest.mark.parametrize(
    ("path", "data"),
    [
        (
            "/signup",
            {
                "username": "captcha-user",
                "password": "strong-pass",
                "confirm_password": "strong-pass",
            },
        ),
        (
            "/login",
            {"username": "manager", "password": "correct-horse"},
        ),
    ],
)
def test_turnstile_rejection_blocks_authentication(
    client, app, monkeypatch, path, data
):
    app.config.update(
        TURNSTILE_SITE_KEY="test-site-key",
        TURNSTILE_SECRET_KEY="test-secret-key",
    )
    monkeypatch.setattr(
        app_module, "verify_turnstile_response", lambda _action: False
    )
    response = client.post(
        path,
        data={"csrf_token": csrf(client, path), **data},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "請完成 Cloudflare Turnstile 人機驗證後再試一次。".encode() in response.data
    with client.session_transaction() as browser_session:
        assert "user_id" not in browser_session
        assert "admin" not in browser_session
    if path == "/signup":
        with app.app_context():
            assert get_db().execute(
                "SELECT 1 FROM users WHERE username_key = 'captcha-user'"
            ).fetchone() is None


def test_turnstile_server_verification_posts_expected_payload(
    app, monkeypatch
):
    app.config.update(
        TURNSTILE_SITE_KEY="expected-site-key",
        TURNSTILE_SECRET_KEY="private-secret",
        TURNSTILE_VERIFY_TIMEOUT=3,
    )
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit):
            return b'{"success": true, "action": "login"}'

    def fake_urlopen(verification_request, timeout):
        captured["request"] = verification_request
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(app_module, "urlopen", fake_urlopen)
    with app.test_request_context(
        "/login",
        method="POST",
        data={"cf-turnstile-response": "browser-token"},
        environ_base={"REMOTE_ADDR": "203.0.113.10"},
    ):
        assert verify_turnstile_response("login") is True
        assert verify_turnstile_response("signup") is False

    request_data = parse_qs(captured["request"].data.decode())
    assert (
        captured["request"].full_url
        == "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    )
    assert captured["request"].get_method() == "POST"
    assert captured["timeout"] == 3
    assert request_data == {
        "secret": ["private-secret"],
        "response": ["browser-token"],
        "remoteip": ["203.0.113.10"],
    }


def test_turnstile_rejects_oversized_token_without_verification_request(
    app, monkeypatch
):
    app.config.update(
        TURNSTILE_SITE_KEY="test-site-key",
        TURNSTILE_SECRET_KEY="test-secret-key",
    )

    def unexpected_urlopen(*_args, **_kwargs):
        raise AssertionError("Oversized Turnstile tokens must not be submitted")

    monkeypatch.setattr(app_module, "urlopen", unexpected_urlopen)
    with app.test_request_context(
        "/login",
        method="POST",
        data={"cf-turnstile-response": "x" * 2049},
    ):
        assert verify_turnstile_response("login") is False


@pytest.mark.parametrize(
    ("user_agent", "expected"),
    [
        (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
            "AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
            "ios",
        ),
        (
            "Mozilla/5.0 (Linux; Android 15; Pixel 9) "
            "AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36",
            "android",
        ),
        ("Mozilla/5.0 (Linux; U; Mobile) Opera Mini/9.80", "mobile"),
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/130.0 Safari/537.36",
            "web",
        ),
        ("", "web"),
    ],
)
def test_device_information_uses_broad_categories(user_agent, expected):
    assert classify_device(user_agent) == expected


def login(client):
    token = csrf(client, "/login")
    return client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "manager",
            "password": "correct-horse",
        },
        follow_redirects=True,
    )


def create_court(
    client,
    reserved_names_visible="1",
    media=None,
    event_name="",
    badminton_name="",
    save_location=False,
    leave_deadline_enabled="0",
    leave_deadline_at="",
    court_date="2026-08-20",
):
    token = csrf(client, "/courts/new")
    data = {
        "csrf_token": token,
        "event_name": event_name,
        "badminton_name": badminton_name,
        "court_date": court_date,
        "start_time": "19:00",
        "end_time": "21:00",
        "hall_name": "Taipei Sports Center",
        "location": "Taipei City",
        "google_place_id": "taipei-sports-center",
        "latitude": "25.0480",
        "longitude": "121.5160",
        "remark": "Bring your own racket.",
        "court_id": "A1",
        "male_price": "250",
        "female_price": "220",
        "shuttlecock_info": "YONEX AS-30",
        "reserved_names_visible": reserved_names_visible,
        "leave_deadline_enabled": leave_deadline_enabled,
        "leave_deadline_at": leave_deadline_at,
        "member_min": "4",
        "member_max": "8",
        "ordered_count": "2",
        "male_level_min": "6",
        "male_level_max": "12",
        "female_level_min": "4",
        "female_level_max": "10",
        "reserved_nickname": ["Coach Lin", "Mina"],
    }
    if leave_deadline_at and "T" in leave_deadline_at:
        deadline_date, deadline_time = leave_deadline_at.split("T", 1)
        data.pop("leave_deadline_at")
        data["leave_deadline_date"] = deadline_date
        data["leave_deadline_time"] = deadline_time
    if media:
        data["media"] = media
    if save_location:
        data["save_location"] = "1"
    response = client.post(
        "/courts/new",
        data=data,
        content_type="multipart/form-data" if media else None,
        follow_redirects=False,
    )
    assert response.status_code == 302
    return response.headers["Location"]


def test_owner_can_enable_leave_deadline_and_it_blocks_leaving(
    client, app
):
    login(client)
    future_deadline = (datetime.now() + timedelta(days=1)).strftime(
        "%Y-%m-%dT%H:%M"
    )
    location = create_court(
        client,
        leave_deadline_enabled="1",
        leave_deadline_at=future_deadline,
        court_date=(datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d"),
    )
    guid = location.rsplit("/", 1)[-1]

    with app.app_context():
        court = get_db().execute(
            "SELECT leave_deadline_enabled, leave_deadline_at FROM courts "
            "WHERE guid = ?",
            (guid,),
        ).fetchone()
        assert court["leave_deadline_enabled"] == 1
        assert court["leave_deadline_at"] == future_deadline

    detail = client.get(location)
    assert b'name="leave_deadline_enabled"' not in detail.data
    assert future_deadline.replace("T", " ").encode() in detail.data
    assert f'action="/{guid}/leave"'.encode() in detail.data

    edit_form = client.get(f"/admin/courts/{guid}/edit")
    deadline_date, deadline_time = future_deadline.split("T", 1)
    assert re.search(
        rb'name="leave_deadline_date"\s+value="'
        + re.escape(deadline_date.encode())
        + rb'"',
        edit_form.data,
    )
    assert re.search(
        rb'name="leave_deadline_time"\s+value="'
        + re.escape(deadline_time.encode())
        + rb'"',
        edit_form.data,
    )

    joined = client.post(
        f"/{guid}/join",
        data={
            "csrf_token": csrf(client, location),
            "username": "Deadline Player",
            "pin": "123456",
        },
        follow_redirects=False,
    )
    assert joined.status_code == 302

    with app.app_context():
        db = get_db()
        db.execute(
            "UPDATE courts SET leave_deadline_at = '2000-01-01T00:00' "
            "WHERE guid = ?",
            (guid,),
        )
        db.commit()

    closed_detail = client.get(location)
    assert "退出期限已過".encode() in closed_detail.data
    assert f'action="/{guid}/leave"'.encode() not in closed_detail.data

    blocked = client.post(
        f"/{guid}/leave",
        data={
            "csrf_token": csrf(client, location),
            "username": "Deadline Player",
            "pin": "123456",
        },
        follow_redirects=True,
    )
    assert "此場次的退出期限已過。".encode() in blocked.data
    with app.app_context():
        db = get_db()
        assert db.execute(
            "SELECT COUNT(*) FROM participants WHERE court_id = "
            "(SELECT id FROM courts WHERE guid = ?)",
            (guid,),
        ).fetchone()[0] == 1
        assert db.execute(
            "SELECT COUNT(*) FROM participation_history "
            "WHERE court_id = (SELECT id FROM courts WHERE guid = ?) "
            "AND event_type = 'leave'",
            (guid,),
        ).fetchone()[0] == 0


def test_leave_deadline_is_disabled_by_default_and_requires_valid_datetime(
    client, app
):
    login(client)
    form = client.get("/courts/new")
    assert b'name="leave_deadline_enabled"' in form.data
    assert b'data-leave-deadline-toggle' in form.data
    assert b'data-leave-deadline-date' in form.data
    assert b'data-leave-deadline-time' in form.data
    assert b'name="leave_deadline_date"' in form.data
    assert b'name="leave_deadline_time"' in form.data
    assert b'data-time24' in form.data
    assert rb'pattern="(?:[01]\d|2[0-3]):[0-5]\d"' in form.data
    assert not re.search(
        rb'name="leave_deadline_enabled"[^>]*checked', form.data
    )

    data = {
        "csrf_token": csrf(client, "/courts/new"),
        "court_date": "2026-08-20",
        "start_time": "19:00",
        "end_time": "21:00",
        "hall_name": "Taipei Sports Center",
        "location": "Taipei City",
        "court_id": "A1",
        "member_min": "4",
        "member_max": "8",
        "ordered_count": "0",
        "male_level_min": "1",
        "male_level_max": "18",
        "female_level_min": "1",
        "female_level_max": "18",
        "leave_deadline_enabled": "1",
        "leave_deadline_date": "2026-08-20",
        "leave_deadline_time": "07:00 PM",
    }
    invalid = client.post("/courts/new", data=data, follow_redirects=True)
    assert invalid.status_code == 200
    assert b"Use a valid date and time" in invalid.data
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM courts").fetchone()[0] == 0

    location = create_court(client)
    with app.app_context():
        court = get_db().execute(
            "SELECT leave_deadline_enabled, leave_deadline_at FROM courts"
        ).fetchone()
        assert court["leave_deadline_enabled"] == 0
        assert court["leave_deadline_at"] == ""


def test_organizer_can_export_and_import_court_info_markdown(client, app):
    login(client)
    location = create_court(
        client,
        reserved_names_visible="0",
        event_name="Friday Night 羽球",
        badminton_name="Shuttle Friends",
    )
    guid = location.rsplit("/", 1)[-1]

    detail = client.get(location)
    export_path = f"/{guid}/court_info.md"
    assert export_path.encode() in detail.data
    assert (
        'download="2026-08-20_1900_2100_Friday Night 羽球.md"'.encode()
        in detail.data
    )
    assert "匯出".encode() in detail.data

    exported = client.get(export_path)
    assert exported.status_code == 200
    assert exported.mimetype == "text/markdown"
    assert (
        "filename*=UTF-8''2026-08-20_1900_2100_"
        "Friday%20Night%20%E7%BE%BD%E7%90%83.md"
        in exported.headers["Content-Disposition"]
    )
    assert exported.headers["Cache-Control"] == "private, no-store"
    assert b"badminton-court-control-panel/court-info:v1" in exported.data
    assert "Friday Night 羽球".encode() in exported.data
    assert '"reserved_nicknames": ['.encode() in exported.data
    assert '"guid"'.encode() not in exported.data
    assert '"owner_id"'.encode() not in exported.data

    imported = client.post(
        "/courts/new",
        data={
            "csrf_token": csrf(client, "/courts/new"),
            "form_action": "import_court_info",
            "court_info_file": (io.BytesIO(exported.data), "court_info.md"),
        },
        content_type="multipart/form-data",
    )
    assert imported.status_code == 200
    assert "場次資訊已匯入".encode() in imported.data
    assert 'value="Friday Night 羽球"'.encode() in imported.data
    assert b'value="Shuttle Friends"' in imported.data
    assert b'value="Taipei Sports Center"' in imported.data
    assert b'value="Coach Lin"' in imported.data
    assert b'value="Mina"' in imported.data
    assert b'<option value="0" selected>' in imported.data
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM courts").fetchone()[0] == 1

    hall_location = create_court(client)
    hall_guid = hall_location.rsplit("/", 1)[-1]
    hall_export = client.get(f"/{hall_guid}/court_info.md")
    assert hall_export.headers["Content-Disposition"] == (
        'attachment; filename="2026-08-20_1900_2100_'
        'Taipei Sports Center.md"'
    )

    anonymous_client = app.test_client()
    unauthorized = anonymous_client.get(export_path)
    assert unauthorized.status_code == 302
    assert urlparse(unauthorized.headers["Location"]).path == "/login"

    client.post(
        "/logout",
        data={"csrf_token": csrf(client, location)},
    )
    signup(client, "unrelated-organizer")
    assert client.get(export_path).status_code == 404


def test_court_info_import_rejects_invalid_and_oversized_files(client, app):
    login(client)

    new_court_form = client.get("/courts/new")
    assert b'<details class="panel court-info-import" >' in new_court_form.data
    assert b'<details class="panel court-info-import" open>' not in new_court_form.data

    invalid = client.post(
        "/courts/new",
        data={
            "csrf_token": csrf(client, "/courts/new"),
            "form_action": "import_court_info",
            "court_info_file": (
                io.BytesIO(b"# unrelated markdown"),
                "court_info.md",
            ),
        },
        content_type="multipart/form-data",
    )
    assert invalid.status_code == 200
    assert "請選擇由本網站匯出的有效".encode() in invalid.data
    assert b'<details class="panel court-info-import" open>' in invalid.data

    oversized = client.post(
        "/courts/new",
        data={
            "csrf_token": csrf(client, "/courts/new"),
            "form_action": "import_court_info",
            "court_info_file": (
                io.BytesIO(b"x" * (app_module.MAX_COURT_INFO_BYTES + 1)),
                "court_info.md",
            ),
        },
        content_type="multipart/form-data",
    )
    assert oversized.status_code == 200
    assert "不可超過 64 KB".encode() in oversized.data
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM courts").fetchone()[0] == 0


def enable_web_push(app):
    public_key = base64.urlsafe_b64encode(b"\x04" + (b"\x01" * 64)).decode()
    app.config.update(
        WEB_PUSH_PUBLIC_KEY=public_key.rstrip("="),
        WEB_PUSH_PRIVATE_KEY="test-vapid-private-key",
        WEB_PUSH_SUBJECT="mailto:notifications@example.test",
        WEB_PUSH_TIMEOUT=1,
    )


def push_subscription_payload(endpoint=None):
    return {
        "endpoint": endpoint
        or "https://updates.push.services.mozilla.com/wpush/v2/test-endpoint",
        "keys": {
            "p256dh": base64.urlsafe_b64encode(
                b"\x04" + (b"\x03" * 64)
            ).decode().rstrip("="),
            "auth": base64.urlsafe_b64encode(
                b"\x02" * 16
            ).decode().rstrip("="),
        },
    }


def test_court_push_notification_control_and_service_worker(client):
    login(client)
    location = create_court(client)
    detail = client.get(location)
    assert b'class="panel push-notification-panel"' in detail.data
    assert b'data-push-notification-toggle' in detail.data
    assert b'data-push-enabled="false"' in detail.data
    assert "此網站尚未設定系統推播通知。".encode() in detail.data

    service_worker = client.get("/service-worker.js")
    assert service_worker.status_code == 200
    assert service_worker.mimetype == "application/javascript"
    assert service_worker.headers["Service-Worker-Allowed"] == "/"
    assert b"self.addEventListener('push'" in service_worker.data
    assert b"self.addEventListener('notificationclick'" in service_worker.data


def test_court_push_subscription_api_is_court_specific_and_csrf_protected(
    client, app
):
    enable_web_push(app)
    login(client)
    location = create_court(client)
    guid = location.rsplit("/", 1)[-1]
    token = csrf(client, location)
    headers = {"X-CSRF-Token": token}
    subscription = push_subscription_payload()

    detail = client.get(location)
    assert b'data-push-enabled="true"' in detail.data
    assert app.config["WEB_PUSH_PUBLIC_KEY"].encode() in detail.data

    rejected = client.post(
        f"/{guid}/push-subscription",
        json={"subscription": subscription},
    )
    assert rejected.status_code == 400

    invalid = client.post(
        f"/{guid}/push-subscription",
        json={
            "subscription": push_subscription_payload(
                "https://untrusted.example.test/push"
            )
        },
        headers=headers,
    )
    assert invalid.status_code == 400

    subscribed = client.post(
        f"/{guid}/push-subscription",
        json={"subscription": subscription},
        headers=headers,
    )
    assert subscribed.status_code == 200
    assert subscribed.get_json() == {"subscribed": True}
    with app.app_context():
        saved = get_db().execute(
            "SELECT endpoint, p256dh, auth, language FROM push_subscriptions"
        ).fetchone()
        assert saved["endpoint"] == subscription["endpoint"]
        assert saved["p256dh"] == subscription["keys"]["p256dh"]
        assert saved["auth"] == subscription["keys"]["auth"]
        assert saved["language"] == "zh-tw"

    status = client.post(
        f"/{guid}/push-subscription/status",
        json={"endpoint": subscription["endpoint"]},
        headers=headers,
    )
    assert status.get_json() == {"subscribed": True}

    removed = client.delete(
        f"/{guid}/push-subscription",
        json={"endpoint": subscription["endpoint"]},
        headers=headers,
    )
    assert removed.get_json() == {"subscribed": False}
    with app.app_context():
        assert get_db().execute(
            "SELECT COUNT(*) FROM push_subscriptions"
        ).fetchone()[0] == 0


def test_court_change_sends_localized_push_and_removes_stale_endpoint(
    client, app, monkeypatch
):
    enable_web_push(app)
    login(client)
    location = create_court(client, event_name="Original Event")
    guid = location.rsplit("/", 1)[-1]
    client.set_cookie("court_lang", "en-us")
    token = csrf(client, location)
    subscription = push_subscription_payload()
    subscribed = client.post(
        f"/{guid}/push-subscription",
        json={"subscription": subscription},
        headers={"X-CSRF-Token": token},
    )
    assert subscribed.status_code == 200

    delivered = []

    def fake_webpush(**kwargs):
        delivered.append(kwargs)

    monkeypatch.setattr(app_module, "webpush", fake_webpush)
    edited = client.post(
        f"/admin/courts/{guid}/edit",
        data={
            "csrf_token": csrf(client, f"/admin/courts/{guid}/edit"),
            "event_name": "Updated Event",
            "badminton_name": "",
            "court_date": "2026-08-21",
            "start_time": "20:00",
            "end_time": "22:00",
            "hall_name": "Updated Badminton Hall",
            "location": "New Taipei City",
            "google_place_id": "updated-hall",
            "latitude": "25.0123",
            "longitude": "121.4654",
            "remark": "Updated court notes.",
            "court_id": "B2",
            "male_price": "300",
            "female_price": "280",
            "shuttlecock_info": "Victor Master Ace",
            "reserved_names_visible": "1",
            "member_min": "6",
            "member_max": "10",
            "ordered_count": "0",
            "male_level_min": "7",
            "male_level_max": "13",
            "female_level_min": "5",
            "female_level_max": "11",
        },
        follow_redirects=False,
    )
    assert edited.status_code == 302
    assert len(delivered) == 1
    message = json.loads(delivered[0]["data"])
    assert message["title"] == "Updated Event updated"
    assert message["body"] == "The organizer changed this court event."
    assert message["url"].endswith(f"/{guid}")
    assert delivered[0]["subscription_info"] == subscription
    assert delivered[0]["vapid_private_key"] == "test-vapid-private-key"
    assert delivered[0]["vapid_claims"] == {
        "sub": "mailto:notifications@example.test"
    }
    assert delivered[0]["ttl"] == 86_400
    assert delivered[0]["timeout"] == 1

    class GoneResponse:
        status_code = 410

    def stale_webpush(**_kwargs):
        raise app_module.WebPushException(
            "subscription expired", response=GoneResponse()
        )

    monkeypatch.setattr(app_module, "webpush", stale_webpush)
    archived = client.post(
        f"/admin/courts/{guid}/archive",
        data={"csrf_token": csrf(client, location)},
        follow_redirects=False,
    )
    assert archived.status_code == 302
    with app.app_context():
        assert get_db().execute(
            "SELECT COUNT(*) FROM push_subscriptions"
        ).fetchone()[0] == 0


def test_successful_member_join_and_leave_send_generic_push_notifications(
    client, app, monkeypatch
):
    enable_web_push(app)
    login(client)
    location = create_court(client, event_name="Member Updates")
    guid = location.rsplit("/", 1)[-1]
    client.set_cookie("court_lang", "en-us")
    token = csrf(client, location)
    subscription = push_subscription_payload()
    client.post(
        f"/{guid}/push-subscription",
        json={"subscription": subscription},
        headers={"X-CSRF-Token": token},
    )

    delivered = []
    monkeypatch.setattr(
        app_module,
        "webpush",
        lambda **kwargs: delivered.append(json.loads(kwargs["data"])),
    )

    joined = client.post(
        f"/{guid}/join",
        data={
            "csrf_token": csrf(client, location),
            "username": "Private Player",
            "pin": "123456",
        },
        follow_redirects=False,
    )
    assert joined.status_code == 302
    assert len(delivered) == 1
    assert delivered[0]["body"] == (
        "The player or waiting list for this court event changed."
    )
    assert "Private Player" not in json.dumps(delivered[0])

    duplicate = client.post(
        f"/{guid}/join",
        data={
            "csrf_token": csrf(client, location),
            "username": "Private Player",
            "pin": "123456",
        },
        follow_redirects=False,
    )
    assert duplicate.status_code == 302
    assert len(delivered) == 1

    left = client.post(
        f"/{guid}/leave",
        data={
            "csrf_token": csrf(client, location),
            "username": "Private Player",
            "pin": "123456",
        },
        follow_redirects=False,
    )
    assert left.status_code == 302
    assert len(delivered) == 2
    assert delivered[1]["body"] == (
        "The player or waiting list for this court event changed."
    )


def test_optional_event_and_badminton_names_are_saved_and_displayed(client, app):
    login(client)
    location = create_court(
        client,
        event_name="Friday Smash Night",
        badminton_name="Taipei Shuttle Club",
    )

    detail = client.get(location)
    assert b"<h1>Friday Smash Night</h1>" in detail.data
    assert b"Taipei Shuttle Club" in detail.data
    assert b"Taipei Sports Center" in detail.data
    assert "星期四".encode() in detail.data

    homepage = client.get("/")
    assert b"<h3>Friday Smash Night</h3>" in homepage.data
    assert b"Taipei Shuttle Club" in homepage.data
    assert "星期四".encode() in homepage.data
    filtered = client.get("/courts?q=Shuttle+Club")
    assert b"Friday Smash Night" in filtered.data

    edit_form = client.get(f"/admin/courts/{location.rsplit('/', 1)[-1]}/edit")
    assert b'name="event_name" value="Friday Smash Night"' in edit_form.data
    assert b'name="badminton_name" value="Taipei Shuttle Club"' in edit_form.data
    assert b'data-court-weekday' in edit_form.data
    assert "星期四".encode() in edit_form.data
    with app.app_context():
        court = get_db().execute(
            "SELECT event_name, badminton_name FROM courts"
        ).fetchone()
        assert court["event_name"] == "Friday Smash Night"
        assert court["badminton_name"] == "Taipei Shuttle Club"


def test_court_media_gallery_card_cover_and_file_cleanup(client, app):
    login(client)
    location = create_court(
        client,
        media=[
            (io.BytesIO(b"\x00\x00\x00\x18ftypmp42video"), "walkthrough.mp4"),
            (io.BytesIO(b"\x89PNG\r\n\x1a\nfirst-image"), "court-one.png"),
            (
                io.BytesIO(b"RIFF\x10\x00\x00\x00WEBPsecond-image"),
                "court-two.webp",
            ),
        ],
    )
    guid = location.rsplit("/", 1)[-1]

    with app.app_context():
        media = get_db().execute(
            "SELECT id, filename, media_type, mime_type, position "
            "FROM court_media ORDER BY position"
        ).fetchall()
        assert [item["media_type"] for item in media] == [
            "video",
            "image",
            "image",
        ]
        assert [item["position"] for item in media] == [0, 1, 2]
        filenames = [item["filename"] for item in media]
        first_image = media[1]["filename"]

    detail = client.get(location)
    assert b'class="event-gallery"' in detail.data
    assert b'<details class="panel event-gallery-panel">' in detail.data
    assert b'<details class="panel event-gallery-panel" open>' not in detail.data
    assert detail.data.count(b"<video controls") == 1
    assert detail.data.count(b"<figure") == 3
    assert f"/court-media/{first_image}".encode() in client.get("/").data
    assert filenames[0].encode() not in client.get("/").data

    image_response = client.get(f"/court-media/{first_image}")
    assert image_response.status_code == 200
    assert image_response.mimetype == "image/png"
    video_response = client.get(f"/court-media/{filenames[0]}")
    assert video_response.status_code == 200
    assert video_response.mimetype == "video/mp4"

    removed_image_path = Path(app.config["COURT_MEDIA_FOLDER"]) / first_image
    token = csrf(client, f"/admin/courts/{guid}/edit")
    edited = client.post(
        f"/admin/courts/{guid}/edit",
        data={
            "csrf_token": token,
            "court_date": "2026-08-20",
            "start_time": "19:00",
            "end_time": "21:00",
            "hall_name": "Taipei Sports Center",
            "location": "Taipei City",
            "google_place_id": "taipei-sports-center",
            "latitude": "25.0480",
            "longitude": "121.5160",
            "remark": "Bring your own racket.",
            "court_id": "A1",
            "male_price": "250",
            "female_price": "220",
            "shuttlecock_info": "YONEX AS-30",
            "reserved_names_visible": "1",
            "member_min": "4",
            "member_max": "8",
            "ordered_count": "2",
            "male_level_min": "6",
            "male_level_max": "12",
            "female_level_min": "4",
            "female_level_max": "10",
            "reserved_nickname": ["Coach Lin", "Mina"],
            "remove_media": str(media[1]["id"]),
            "media": (
                io.BytesIO(b"\xff\xd8\xffnew-image"),
                "replacement.jpg",
            ),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert edited.status_code == 302
    assert not removed_image_path.exists()
    with app.app_context():
        remaining_media = get_db().execute(
            "SELECT filename, media_type FROM court_media ORDER BY position"
        ).fetchall()
        assert [item["media_type"] for item in remaining_media] == [
            "video",
            "image",
            "image",
        ]
        remaining_filenames = [item["filename"] for item in remaining_media]
    home = client.get("/")
    assert filenames[2].encode() in home.data
    assert remaining_filenames[-1].encode() not in home.data

    token = csrf(client, f"/admin/courts/{guid}/edit")
    deleted = client.post(
        f"/admin/courts/{guid}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert deleted.status_code == 302
    assert all(
        not (Path(app.config["COURT_MEDIA_FOLDER"]) / filename).exists()
        for filename in set(filenames + remaining_filenames)
    )
    assert client.get(f"/court-media/{first_image}").status_code == 404


def social_thumbnail_path(response):
    match = re.search(
        rb'<meta property="og:image" content="([^"]+)">',
        response.data,
    )
    assert match is not None
    return urlparse(html.unescape(match.group(1).decode())).path


def image_bytes(color, image_format="PNG"):
    output = io.BytesIO()
    Image.new("RGB", (1600, 900), color).save(output, format=image_format)
    return output.getvalue()


def test_court_social_thumbnail_metadata_and_information_fallback(
    client, app
):
    login(client)
    location = create_court(
        client,
        event_name="Friday Smash Night",
        badminton_name="Taipei Shuttle Club",
    )
    app.config["TRUST_PROXY_HEADERS"] = True
    detail = client.get(
        location,
        headers={
            "Host": "courts.example",
            "X-Forwarded-Proto": "https",
        },
    )
    thumbnail_path = social_thumbnail_path(detail)

    assert b'<meta property="og:type" content="website">' in detail.data
    assert (
        b'<meta property="og:title" content="Friday Smash Night">'
        in detail.data
    )
    assert b'<meta property="og:image:width" content="1200">' in detail.data
    assert b'<meta property="og:image:height" content="630">' in detail.data
    assert (
        b'<meta name="twitter:card" content="summary_large_image">'
        in detail.data
    )
    assert (
        b'<link rel="canonical" href="https://courts.example/'
        in detail.data
    )
    assert b'content="https://courts.example/' in detail.data
    assert thumbnail_path.endswith("/zh-tw.jpg")

    thumbnail = client.get(thumbnail_path)
    assert thumbnail.status_code == 200
    assert thumbnail.mimetype == "image/jpeg"
    assert thumbnail.headers["Cache-Control"] == (
        "public, max-age=31536000, immutable"
    )
    with Image.open(io.BytesIO(thumbnail.data)) as rendered:
        assert rendered.size == (1200, 630)
        assert rendered.format == "JPEG"

    with app.app_context():
        get_db().execute("UPDATE courts SET ordered_count = 3")
        get_db().commit()
    updated_detail = client.get(
        location,
        headers={
            "Host": "courts.example",
            "X-Forwarded-Proto": "https",
        },
    )
    updated_thumbnail_path = social_thumbnail_path(updated_detail)
    assert updated_thumbnail_path != thumbnail_path
    stale_response = client.get(thumbnail_path)
    assert stale_response.status_code == 302
    assert urlparse(stale_response.headers["Location"]).path == (
        updated_thumbnail_path
    )
    assert client.get(updated_thumbnail_path).status_code == 200
    cached_thumbnails = Path(app.config["SOCIAL_THUMBNAIL_FOLDER"]).glob(
        "*.jpg"
    )
    assert len(list(cached_thumbnails)) == 1

    guid = location.rsplit("/", 1)[-1]
    deleted = client.post(
        f"/admin/courts/{guid}/delete",
        data={"csrf_token": csrf(client, f"/admin/courts/{guid}/edit")},
        follow_redirects=False,
    )
    assert deleted.status_code == 302
    assert not list(
        Path(app.config["SOCIAL_THUMBNAIL_FOLDER"]).glob("*.jpg")
    )
    assert client.get(updated_thumbnail_path).status_code == 404


def test_court_thumbnail_can_be_downloaded_from_detail_page(client, app):
    login(client)
    location = create_court(
        client,
        event_name="Friday Night 羽球",
    )
    guid = location.rsplit("/", 1)[-1]
    public_client = app.test_client()
    detail = public_client.get(location)

    assert f'href="/{guid}/thumbnail.jpg"'.encode() in detail.data
    assert "下載縮圖".encode() in detail.data

    downloaded = public_client.get(f"/{guid}/thumbnail.jpg")
    assert downloaded.status_code == 200
    assert downloaded.mimetype == "image/jpeg"
    assert "attachment" in downloaded.headers["Content-Disposition"]
    assert (
        "filename*=UTF-8''2026-08-20_1900_2100_"
        "Friday%20Night%20%E7%BE%BD%E7%90%83.jpg"
        in downloaded.headers["Content-Disposition"]
    )
    assert downloaded.headers["Cache-Control"] == "private, no-store"
    with Image.open(io.BytesIO(downloaded.data)) as rendered:
        assert rendered.size == (1200, 630)
        assert rendered.format == "JPEG"


def test_court_social_thumbnail_uses_first_event_image(client):
    login(client)
    expected_color = (27, 83, 144)
    location = create_court(
        client,
        media=[
            (
                io.BytesIO(image_bytes(expected_color)),
                "first-event-photo.png",
            )
        ],
    )
    thumbnail = client.get(social_thumbnail_path(client.get(location)))
    assert thumbnail.status_code == 200
    with Image.open(io.BytesIO(thumbnail.data)) as rendered:
        assert rendered.size == (1200, 630)
        center = rendered.getpixel((600, 315))
        assert all(
            abs(actual - expected) <= 3
            for actual, expected in zip(center, expected_color)
        )


def test_court_social_thumbnail_extracts_first_event_video(
    client, app, monkeypatch
):
    login(client)
    location = create_court(
        client,
        media=[
            (
                io.BytesIO(b"\x00\x00\x00\x18ftypmp42video"),
                "first-event-video.mp4",
            ),
            (
                io.BytesIO(image_bytes((20, 180, 80))),
                "second-event-photo.png",
            ),
        ],
    )
    video_frame = image_bytes((190, 45, 60), "JPEG")
    captured = {}

    def fake_ffmpeg(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return SimpleNamespace(stdout=video_frame)

    monkeypatch.setattr(app_module.subprocess, "run", fake_ffmpeg)
    thumbnail = client.get(social_thumbnail_path(client.get(location)))
    assert thumbnail.status_code == 200
    assert captured["command"][0] == "ffmpeg"
    assert captured["command"][captured["command"].index("-i") + 1].endswith(
        ".mp4"
    )
    assert captured["kwargs"]["timeout"] == 12
    with Image.open(io.BytesIO(thumbnail.data)) as rendered:
        center = rendered.getpixel((600, 315))
        assert center[0] > center[1] * 3
        assert center[0] > center[2] * 2


def test_invalid_court_media_is_rejected(client, app):
    login(client)
    token = csrf(client, "/courts/new")
    response = client.post(
        "/courts/new",
        data={
            "csrf_token": token,
            "court_date": "2026-08-20",
            "start_time": "19:00",
            "end_time": "21:00",
            "hall_name": "Taipei Sports Center",
            "location": "Taipei City",
            "court_id": "A1",
            "male_price": "0",
            "female_price": "0",
            "shuttlecock_info": "",
            "reserved_names_visible": "1",
            "member_min": "4",
            "member_max": "8",
            "ordered_count": "0",
            "male_level_min": "1",
            "male_level_max": "18",
            "female_level_min": "1",
            "female_level_max": "18",
            "media": (io.BytesIO(b"<svg>not accepted</svg>"), "court.svg"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert "有效的 JPEG".encode() in response.data
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM courts").fetchone()[0] == 0
        assert get_db().execute("SELECT COUNT(*) FROM court_media").fetchone()[0] == 0


def signup(client, username="alice", password="strong-pass"):
    token = csrf(client, "/signup")
    return client.post(
        "/signup",
        data={
            "csrf_token": token,
            "username": username,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=True,
    )


def create_member_court(client, hall_name="Member Hall"):
    token = csrf(client, "/courts/new")
    response = client.post(
        "/courts/new",
        data={
            "csrf_token": token,
            "court_date": "2026-09-10",
            "start_time": "18:30",
            "end_time": "20:30",
            "hall_name": hall_name,
            "location": "Taipei City",
            "google_place_id": "",
            "latitude": "",
            "longitude": "",
            "court_id": "C3",
            "member_min": "4",
            "member_max": "8",
            "ordered_count": "1",
            "male_level_min": "5",
            "male_level_max": "12",
            "female_level_min": "4",
            "female_level_max": "11",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    return response.headers["Location"]


def test_member_can_save_reuse_and_delete_a_court_location(client, app):
    signup(client)
    empty_form = client.get("/courts/new")
    assert b"data-saved-location-select" in empty_form.data
    assert b"disabled" in empty_form.data
    assert b'name="save_location"' in empty_form.data

    token = csrf(client, "/courts/new")
    response = client.post(
        "/courts/new",
        data={
            "csrf_token": token,
            "court_date": "2026-09-10",
            "start_time": "18:30",
            "end_time": "20:30",
            "hall_name": "Saved Shuttle Hall",
            "location": "No. 8, Court Road, Taipei",
            "google_place_id": "saved-place-id",
            "latitude": "25.0478",
            "longitude": "121.5319",
            "court_id": "C3",
            "member_min": "4",
            "member_max": "8",
            "ordered_count": "0",
            "male_level_min": "5",
            "male_level_max": "12",
            "female_level_min": "4",
            "female_level_max": "11",
            "save_location": "1",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "此地點已儲存至你的個人資料。".encode() in response.data

    with app.app_context():
        saved = get_db().execute("SELECT * FROM saved_locations").fetchone()
        assert saved["hall_name"] == "Saved Shuttle Hall"
        assert saved["location"] == "No. 8, Court Road, Taipei"
        assert saved["google_place_id"] == "saved-place-id"
        assert saved["latitude"] == pytest.approx(25.0478)
        location_id = saved["id"]

    form = client.get("/courts/new")
    assert b'data-saved-location-select' in form.data
    assert b"Saved Shuttle Hall" in form.data
    assert b'name="save_location"' in form.data

    profile = client.get("/account/profile")
    assert "已儲存地點".encode() in profile.data
    assert b"No. 8, Court Road, Taipei" in profile.data

    token = csrf(client, "/account/profile")
    deleted = client.post(
        f"/account/profile/saved-locations/{location_id}/delete",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert deleted.status_code == 200
    assert "已刪除儲存的地點。".encode() in deleted.data
    with app.app_context():
        assert get_db().execute(
            "SELECT COUNT(*) FROM saved_locations"
        ).fetchone()[0] == 0


def test_member_cannot_delete_another_members_saved_location(client, app):
    signup(client, "alice")
    with app.app_context():
        alice_id = get_db().execute(
            "SELECT id FROM users WHERE username_key = 'alice'"
        ).fetchone()["id"]
        cursor = get_db().execute(
            "INSERT INTO saved_locations "
            "(user_id, hall_name, location, created_at) VALUES (?, ?, ?, ?)",
            (alice_id, "Alice Hall", "Taipei", "2026-07-27T12:00:00"),
        )
        location_id = cursor.lastrowid
        get_db().commit()

    client.post(
        "/logout",
        data={"csrf_token": csrf(client, "/my-courts")},
    )
    signup(client, "bob")
    response = client.post(
        f"/account/profile/saved-locations/{location_id}/delete",
        data={"csrf_token": csrf(client, "/account/profile")},
    )
    assert response.status_code == 404
    with app.app_context():
        assert get_db().execute(
            "SELECT COUNT(*) FROM saved_locations WHERE id = ?", (location_id,)
        ).fetchone()[0] == 1


def test_bootstrap_admin_is_database_backed_and_can_save_locations(client, app):
    login(client)
    with app.app_context():
        admin = get_db().execute(
            "SELECT id, role, password_hash FROM users "
            "WHERE username_key = 'manager'"
        ).fetchone()
        assert admin["role"] == "super_admin"
        assert check_password_hash(admin["password_hash"], "correct-horse")
        admin_id = admin["id"]

    form = client.get("/courts/new")
    assert b"data-saved-location-select" in form.data
    assert b'name="save_location"' in form.data

    create_court(client, save_location=True)
    with app.app_context():
        saved = get_db().execute(
            "SELECT hall_name, location FROM saved_locations WHERE user_id = ?",
            (admin_id,),
        ).fetchone()
        assert saved["hall_name"] == "Taipei Sports Center"
        assert saved["location"] == "Taipei City"
        court = get_db().execute(
            "SELECT owner_id FROM courts ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert court["owner_id"] == admin_id

    profile = client.get("/account/profile")
    assert profile.status_code == 200
    assert b"Taipei Sports Center" in profile.data


def test_super_admin_can_assign_sub_admin_role_with_limited_access(client, app):
    signup(client, "alice")
    client.post(
        "/logout",
        data={"csrf_token": csrf(client, "/my-courts")},
    )
    login(client)
    with app.app_context():
        alice_id = get_db().execute(
            "SELECT id FROM users WHERE username_key = 'alice'"
        ).fetchone()["id"]

    response = client.post(
        f"/admin/users/{alice_id}/role",
        data={"csrf_token": csrf(client, "/admin/users"), "role": "sub_admin"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "帳號角色已更新。".encode() in response.data

    client.post(
        "/admin/logout",
        data={"csrf_token": csrf(client, "/admin")},
    )
    signed_in = client.post(
        "/login",
        data={
            "csrf_token": csrf(client, "/login"),
            "username": "alice",
            "password": "strong-pass",
        },
        follow_redirects=False,
    )
    assert signed_in.headers["Location"] == "/admin"
    assert client.get("/admin").status_code == 200
    assert client.get("/admin/users").status_code == 403
    assert client.get("/admin/messages").status_code == 403
    court_form = client.get("/courts/new")
    assert court_form.status_code == 200
    assert b'name="save_location"' in court_form.data


def test_super_admin_cannot_change_own_role(client, app):
    login(client)
    with app.app_context():
        admin_id = get_db().execute(
            "SELECT id FROM users WHERE username_key = 'manager'"
        ).fetchone()["id"]
    response = client.post(
        f"/admin/users/{admin_id}/role",
        data={"csrf_token": csrf(client, "/admin/users"), "role": "member"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "你不能變更自己的管理員角色。".encode() in response.data
    with app.app_context():
        role = get_db().execute(
            "SELECT role FROM users WHERE id = ?", (admin_id,)
        ).fetchone()["role"]
        assert role == "super_admin"


def test_admin_can_create_archive_restore_and_delete(client, app):
    admin_page = login(client)
    assert admin_page.status_code == 200
    assert b'class="account-menu admin-account-menu"' in admin_page.data
    assert not re.search(
        rb'<a class="nav-link[^"]*" href="/admin">', admin_page.data
    )
    assert b'<a href="/admin">' in admin_page.data
    assert b'href="/admin/users"' in admin_page.data
    assert b'action="/admin/logout"' in admin_page.data
    assert admin_page.data.count(b'action="/admin/logout"') == 1
    location = create_court(client)
    guid = location.rsplit("/", 1)[-1]

    detail = client.get(location)
    assert detail.status_code == 200
    assert b'class="court-action-menu"' in detail.data
    assert b'class="account-menu-list court-action-list"' in detail.data
    assert f"/admin/courts/{guid}/edit".encode() in detail.data
    assert f"/admin/courts/{guid}/archive".encode() in detail.data
    assert f"/admin/courts/{guid}/delete".encode() in detail.data
    assert b'data-mobile-join-trigger' in detail.data
    assert b'data-mobile-join-dialog' in detail.data
    assert b'data-mobile-join-dialog-content' in detail.data
    assert b'data-join-panel' in detail.data
    assert b"Bring your own racket." in detail.data
    assert b"NT$ 250" in detail.data
    assert b"NT$ 220" in detail.data
    assert b"YONEX AS-30" in detail.data
    assert b'class="shuttle-icon"' in detail.data
    assert b'<details class="grading-chart">' in detail.data
    assert b'<details class="grading-chart" open>' not in detail.data
    assert b'src="/static/grading.webp"' in detail.data
    assert "台灣羽球推廣協會程度分級參考表".encode() in detail.data
    assert b"Coach Lin" in detail.data
    assert b"Mina" in detail.data
    assert b"Taipei Sports Center" in client.get("/").data

    token = csrf(client, f"/admin/courts/{guid}/edit")
    edited = client.post(
        f"/admin/courts/{guid}/edit",
        data={
            "csrf_token": token,
            "court_date": "2026-08-21",
            "start_time": "20:00",
            "end_time": "22:00",
            "hall_name": "Updated Badminton Hall",
            "location": "New Taipei City",
            "google_place_id": "updated-badminton-hall",
            "latitude": "25.0123",
            "longitude": "121.4654",
            "remark": "Updated court notes.",
            "court_id": "B2",
            "male_price": "300",
            "female_price": "280",
            "shuttlecock_info": "Victor Master Ace",
            "member_min": "6",
            "member_max": "10",
            "ordered_count": "3",
            "male_level_min": "7",
            "male_level_max": "13",
            "female_level_min": "5",
            "female_level_max": "11",
            "reserved_nickname": ["Captain Wu", "Ivy", "Leo"],
        },
        follow_redirects=True,
    )
    assert edited.status_code == 200
    assert b"Updated Badminton Hall" in edited.data
    assert b"Updated court notes." in edited.data
    assert guid.encode() in edited.request.path.encode()
    with app.app_context():
        saved = get_db().execute(
            "SELECT guid, hall_name, court_id, google_place_id, latitude, longitude, "
            "male_price, female_price, shuttlecock_info "
            "FROM courts"
        ).fetchone()
        assert saved["guid"] == guid
        assert saved["hall_name"] == "Updated Badminton Hall"
        assert saved["court_id"] == "B2"
        assert saved["google_place_id"] == "updated-badminton-hall"
        assert saved["latitude"] == pytest.approx(25.0123)
        assert saved["longitude"] == pytest.approx(121.4654)
        assert saved["male_price"] == 300
        assert saved["female_price"] == 280
        assert saved["shuttlecock_info"] == "Victor Master Ace"
        reserved = get_db().execute(
            "SELECT nickname FROM reserved_members WHERE court_id = "
            "(SELECT id FROM courts WHERE guid = ?) ORDER BY position",
            (guid,),
        ).fetchall()
        assert [row["nickname"] for row in reserved] == [
            "Captain Wu",
            "Ivy",
            "Leo",
        ]
        assert get_db().execute(
            "SELECT remark FROM courts WHERE guid = ?", (guid,)
        ).fetchone()["remark"] == "Updated court notes."

    token = csrf(client, "/admin")
    client.post(f"/admin/courts/{guid}/archive", data={"csrf_token": token})
    assert b"Updated Badminton Hall" not in client.get("/").data

    token = csrf(client, "/admin")
    client.post(f"/admin/courts/{guid}/restore", data={"csrf_token": token})
    assert b"Updated Badminton Hall" in client.get("/").data

    token = csrf(client, "/admin")
    client.post(f"/admin/courts/{guid}/delete", data={"csrf_token": token})
    assert client.get(location).status_code == 404


def test_admin_dashboard_displays_court_creation_datetime(client, app):
    login(client)
    create_court(client)
    with app.app_context():
        created_at = get_db().execute(
            "SELECT created_at FROM courts ORDER BY id DESC LIMIT 1"
        ).fetchone()["created_at"]
    expected = created_at.replace("-", "/").replace("T", " ")

    dashboard = client.get("/admin")
    assert "建立時間".encode() in dashboard.data
    assert expected.encode() in dashboard.data


def test_join_and_leave_with_six_digit_pin(client, app):
    login(client)
    location = create_court(client)
    client.post("/admin/logout", data={"csrf_token": csrf(client, "/admin")})

    public_detail = client.get(location)
    assert b"/admin/courts/" not in public_detail.data

    token = csrf(client, location)
    response = client.post(
        f"{location}/join",
        data={"csrf_token": token, "username": "Alice", "pin": "123456"},
        follow_redirects=True,
    )
    assert b"Alice" in response.data

    token = csrf(client, location)
    wrong = client.post(
        f"{location}/leave",
        data={"csrf_token": token, "username": "Alice", "pin": "000000"},
        follow_redirects=True,
    )
    assert b"Alice" in wrong.data

    token = csrf(client, location)
    left = client.post(
        f"{location}/leave",
        data={"csrf_token": token, "username": "Alice", "pin": "123456"},
        follow_redirects=True,
    )
    assert "你已離開此場次".encode() in left.data
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM participants").fetchone()[0] == 0


def test_failed_leave_credentials_are_limited_until_lockout_expires(
    client, app
):
    app.config.update(
        LEAVE_MAX_ATTEMPTS=3,
        LEAVE_LOCKOUT_SECONDS=120,
    )
    login(client)
    location = create_court(client)
    client.post("/admin/logout", data={"csrf_token": csrf(client, "/admin")})

    token = csrf(client, location)
    client.post(
        f"{location}/join",
        data={"csrf_token": token, "username": "Alice", "pin": "123456"},
    )

    unknown_name = client.post(
        f"{location}/leave",
        data={
            "csrf_token": csrf(client, location),
            "username": "Mallory",
            "pin": "123456",
        },
        follow_redirects=True,
    )
    assert "使用者名稱或 PIN 碼不正確，還可嘗試 2 次".encode() in (
        unknown_name.data
    )

    for remaining, pin in ((2, "12345"), (1, "000000")):
        denied = client.post(
            f"{location}/leave",
            data={
                "csrf_token": csrf(client, location),
                "username": "Alice",
                "pin": pin,
            },
            follow_redirects=True,
        )
        assert f"還可嘗試 {remaining} 次".encode() in denied.data

    locked = client.post(
        f"{location}/leave",
        data={
            "csrf_token": csrf(client, location),
            "username": "Alice",
            "pin": "000000",
        },
        follow_redirects=True,
    )
    assert "退出場次失敗次數過多，請在 2 分鐘後再試".encode() in locked.data

    correct_while_locked = client.post(
        f"{location}/leave",
        data={
            "csrf_token": csrf(client, location),
            "username": "Alice",
            "pin": "123456",
        },
        follow_redirects=True,
    )
    assert "退出場次失敗次數過多".encode() in correct_while_locked.data

    with app.app_context():
        db = get_db()
        court_id = db.execute(
            "SELECT id FROM courts WHERE guid = ?",
            (location.rsplit("/", 1)[-1],),
        ).fetchone()["id"]
        attempts = db.execute(
            "SELECT username_key, failed_count, locked_until "
            "FROM login_attempts WHERE scope = ? ORDER BY failed_count",
            (f"court_leave:{court_id}",),
        ).fetchall()
        assert [attempt["failed_count"] for attempt in attempts] == [1, 3]
        assert all(
            attempt["username_key"] not in {"alice", "mallory"}
            for attempt in attempts
        )
        assert attempts[-1]["locked_until"] is not None
        assert db.execute(
            "SELECT COUNT(*) FROM participants WHERE court_id = ?",
            (court_id,),
        ).fetchone()[0] == 1
        db.execute(
            "UPDATE login_attempts SET locked_until = '2000-01-01T00:00:00' "
            "WHERE scope = ? AND failed_count = 3",
            (f"court_leave:{court_id}",),
        )
        db.commit()

    accepted = client.post(
        f"{location}/leave",
        data={
            "csrf_token": csrf(client, location),
            "username": "Alice",
            "pin": "123456",
        },
        follow_redirects=True,
    )
    assert "你已離開此場次".encode() in accepted.data
    with app.app_context():
        db = get_db()
        assert db.execute(
            "SELECT COUNT(*) FROM participants WHERE court_id = ?",
            (court_id,),
        ).fetchone()[0] == 0
        remaining_attempts = db.execute(
            "SELECT failed_count FROM login_attempts WHERE scope = ?",
            (f"court_leave:{court_id}",),
        ).fetchall()
        assert [attempt["failed_count"] for attempt in remaining_attempts] == [
            1
        ]


def test_reserved_nicknames_can_be_hidden_from_public_viewers(client, app):
    login(client)
    location = create_court(client, reserved_names_visible="0")

    organizer_detail = client.get(location)
    assert b"Coach Lin" in organizer_detail.data
    assert "已對訪客隱藏".encode() in organizer_detail.data
    edit_form = client.get(
        f"/admin/courts/{location.rsplit('/', 1)[-1]}/edit"
    )
    assert b'value="0" selected' in edit_form.data

    token = csrf(client, "/admin")
    client.post("/admin/logout", data={"csrf_token": token})
    public_detail = client.get(location)
    assert b"Coach Lin" not in public_detail.data
    assert b"Mina" not in public_detail.data
    assert "2 已預訂".encode() in public_detail.data

    with app.app_context():
        visibility = get_db().execute(
            "SELECT reserved_names_visible FROM courts WHERE guid = ?",
            (location.rsplit("/", 1)[-1],),
        ).fetchone()["reserved_names_visible"]
        assert visibility == 0


def test_edit_court_can_reorder_and_delete_a_reserved_nickname(client, app):
    login(client)
    location = create_court(client)
    guid = location.rsplit("/", 1)[-1]
    edit_url = f"/admin/courts/{guid}/edit"

    edit_form = client.get(edit_url)
    assert edit_form.data.count(b"data-delete-reserved-nickname") == 2
    assert edit_form.data.count(b"data-drag-reserved-nickname") == 2
    assert edit_form.data.count(b'data-move-reserved-nickname="up"') == 2
    assert edit_form.data.count(b'data-move-reserved-nickname="down"') == 2
    assert b"data-delete-label=" in edit_form.data
    assert b"data-drag-label=" in edit_form.data
    assert b"data-move-up-label=" in edit_form.data
    assert b"data-move-down-label=" in edit_form.data
    assert b'id="reserved-nickname-0"' in edit_form.data
    javascript = client.get("/static/js/app.js")
    assert b"reservedNicknameList?.addEventListener('dragstart'" in javascript.data
    assert b"data-move-reserved-nickname" in javascript.data

    token = csrf(client, edit_url)
    form_data = {
        "csrf_token": token,
        "court_date": "2026-08-20",
        "start_time": "19:00",
        "end_time": "21:00",
        "hall_name": "Taipei Sports Center",
        "location": "Taipei City",
        "google_place_id": "taipei-sports-center",
        "latitude": "25.0480",
        "longitude": "121.5160",
        "remark": "Bring your own racket.",
        "court_id": "A1",
        "male_price": "250",
        "female_price": "220",
        "shuttlecock_info": "YONEX AS-30",
        "reserved_names_visible": "1",
        "member_min": "4",
        "member_max": "8",
        "ordered_count": "2",
        "male_level_min": "6",
        "male_level_max": "12",
        "female_level_min": "4",
        "female_level_max": "10",
        "reserved_nickname": ["Mina", "Coach Lin"],
    }
    reordered = client.post(
        edit_url,
        data=form_data,
        follow_redirects=False,
    )
    assert reordered.status_code == 302

    with app.app_context():
        court = get_db().execute(
            "SELECT id, ordered_count FROM courts WHERE guid = ?", (guid,)
        ).fetchone()
        reserved = get_db().execute(
            "SELECT position, nickname FROM reserved_members "
            "WHERE court_id = ? ORDER BY position",
            (court["id"],),
        ).fetchall()
        assert court["ordered_count"] == 2
        assert [(row["position"], row["nickname"]) for row in reserved] == [
            (0, "Mina"),
            (1, "Coach Lin"),
        ]

    detail = client.get(location)
    assert detail.data.index(b"Mina") < detail.data.index(b"Coach Lin")

    form_data["csrf_token"] = csrf(client, edit_url)
    form_data["ordered_count"] = "1"
    form_data["reserved_nickname"] = ["Mina"]
    saved = client.post(edit_url, data=form_data, follow_redirects=False)
    assert saved.status_code == 302

    with app.app_context():
        court = get_db().execute(
            "SELECT id, ordered_count FROM courts WHERE guid = ?", (guid,)
        ).fetchone()
        reserved = get_db().execute(
            "SELECT position, nickname FROM reserved_members "
            "WHERE court_id = ? ORDER BY position",
            (court["id"],),
        ).fetchall()
        assert court["ordered_count"] == 1
        assert [(row["position"], row["nickname"]) for row in reserved] == [
            (0, "Mina")
        ]


def test_rejects_duplicate_username_and_invalid_pin(client, app):
    login(client)
    location = create_court(client)
    token = csrf(client, location)

    invalid = client.post(
        f"{location}/join",
        data={"csrf_token": token, "username": "Alice", "pin": "12345"},
        follow_redirects=True,
    )
    assert b"Alice" not in invalid.data

    token = csrf(client, location)
    client.post(
        f"{location}/join",
        data={"csrf_token": token, "username": "Alice", "pin": "123456"},
    )
    token = csrf(client, location)
    client.post(
        f"{location}/join",
        data={"csrf_token": token, "username": "alice", "pin": "654321"},
    )
    with app.app_context():
        count = get_db().execute("SELECT COUNT(*) FROM participants").fetchone()[0]
    assert count == 1


def test_join_leave_history_limits_request_metadata_to_admin(client, app):
    login(client)
    location = create_court(client)

    token = csrf(client, location)
    joined = client.post(
        f"{location}/join",
        data={"csrf_token": token, "username": "Alice", "pin": "123456"},
        headers={
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) "
                "AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1"
            )
        },
        environ_base={"REMOTE_ADDR": "203.0.113.10"},
    )
    assert joined.status_code == 302

    token = csrf(client, location)
    left = client.post(
        f"{location}/leave",
        data={"csrf_token": token, "username": "Alice", "pin": "123456"},
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 15; Pixel 9) "
                "AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36"
            )
        },
        environ_base={"REMOTE_ADDR": "203.0.113.11"},
    )
    assert left.status_code == 302

    with app.app_context():
        history = get_db().execute(
            "SELECT username, event_type, occurred_at, ip_address, "
            "device_information FROM participation_history ORDER BY id"
        ).fetchall()
        assert [(event["username"], event["event_type"]) for event in history] == [
            ("Alice", "join"),
            ("Alice", "leave"),
        ]
        assert history[0]["ip_address"] == "203.0.113.10"
        assert history[0]["device_information"] == "ios"
        assert history[1]["ip_address"] == "203.0.113.11"
        assert history[1]["device_information"] == "android"
        displayed_times = [
            event["occurred_at"][:10].replace("-", "/").encode()
            for event in history
        ]

    admin_detail = client.get(location)
    assert "加入與退出紀錄".encode() in admin_detail.data
    assert "裝置類型".encode() in admin_detail.data
    assert b"203.0.113.10" in admin_detail.data
    assert b"iOS" in admin_detail.data
    assert b"203.0.113.11" in admin_detail.data
    assert b"Android" in admin_detail.data
    assert b"Mozilla/5.0" not in admin_detail.data
    for displayed_time in displayed_times:
        assert displayed_time in admin_detail.data

    with client.session_transaction() as user_session:
        user_session.clear()
    public_detail = client.get(location)
    assert "加入與退出紀錄".encode() in public_detail.data
    assert b"Alice" in public_detail.data
    assert "加入".encode() in public_detail.data
    assert "退出".encode() in public_detail.data
    assert "IP 位址".encode() not in public_detail.data
    assert "裝置類型".encode() not in public_detail.data
    assert b"203.0.113.10" not in public_detail.data
    assert b"iOS" not in public_detail.data
    for displayed_time in displayed_times:
        assert displayed_time in public_detail.data


def test_full_court_uses_fifo_waiting_list_and_promotes_after_leave(client, app):
    login(client)
    location = create_court(client)
    with app.app_context():
        get_db().execute(
            "UPDATE courts SET member_min = 1, member_max = 3 WHERE guid = ?",
            (location.rsplit("/", 1)[-1],),
        )
        get_db().commit()

    token = csrf(client, location)
    first = client.post(
        f"{location}/join",
        data={"csrf_token": token, "username": "Alice", "pin": "123456"},
        follow_redirects=True,
    )
    assert "你已加入此場次".encode() in first.data

    token = csrf(client, location)
    queued = client.post(
        f"{location}/join",
        data={"csrf_token": token, "username": "Bob", "pin": "654321"},
        follow_redirects=True,
    )
    assert "你已加入候補名單".encode() in queued.data
    assert "候補名單".encode() in queued.data

    with app.app_context():
        participants = get_db().execute(
            "SELECT username, waitlisted FROM participants ORDER BY joined_at, id"
        ).fetchall()
        assert [(row["username"], row["waitlisted"]) for row in participants] == [
            ("Alice", 0),
            ("Bob", 1),
        ]

    token = csrf(client, location)
    promoted = client.post(
        f"{location}/leave",
        data={"csrf_token": token, "username": "Alice", "pin": "123456"},
        follow_redirects=True,
    )
    assert b">Bob<" in promoted.data
    with app.app_context():
        bob = get_db().execute(
            "SELECT waitlisted FROM participants WHERE username = 'Bob'"
        ).fetchone()
        assert bob["waitlisted"] == 0


def test_admin_can_rename_reset_pin_and_delete_court_participants(
    client, app, monkeypatch
):
    login(client)
    location = create_court(client)
    guid = location.rsplit("/", 1)[-1]
    with app.app_context():
        db = get_db()
        db.execute(
            "UPDATE courts SET member_min = 1, member_max = 3 WHERE guid = ?",
            (guid,),
        )
        db.commit()

    for username, pin in (
        ("Alice", "123456"),
        ("Bob", "234567"),
        ("Charlie", "345678"),
    ):
        response = client.post(
            f"{location}/join",
            data={
                "csrf_token": csrf(client, location),
                "username": username,
                "pin": pin,
            },
        )
        assert response.status_code == 302

    with app.app_context():
        participants = get_db().execute(
            "SELECT id, username, waitlisted, pin_hash FROM participants "
            "WHERE court_id = (SELECT id FROM courts WHERE guid = ?) "
            "ORDER BY joined_at, id",
            (guid,),
        ).fetchall()
        alice_id, bob_id, charlie_id = [
            participant["id"] for participant in participants
        ]
        original_alice_pin_hash = participants[0]["pin_hash"]
        assert [
            (participant["username"], participant["waitlisted"])
            for participant in participants
        ] == [("Alice", 0), ("Bob", 1), ("Charlie", 1)]

    admin_detail = client.get(location)
    assert admin_detail.data.count(b"data-participant-admin-menu") == 3
    assert "重新命名球友".encode() in admin_detail.data
    assert (
        f"/admin/courts/{guid}/participants/{alice_id}/rename".encode()
        in admin_detail.data
    )
    assert (
        f"/admin/courts/{guid}/participants/{bob_id}/reset-pin".encode()
        in admin_detail.data
    )
    assert (
        f"/admin/courts/{guid}/participants/{charlie_id}/delete".encode()
        in admin_detail.data
    )

    public_client = app.test_client()
    public_detail = public_client.get(location)
    assert b"data-participant-admin-menu" not in public_detail.data
    assert f"/admin/courts/{guid}/participants/".encode() not in public_detail.data
    unauthorized = public_client.post(
        f"/admin/courts/{guid}/participants/{alice_id}/rename",
        data={
            "csrf_token": csrf(public_client, location),
            "username": "Intruder",
        },
    )
    assert unauthorized.status_code == 302
    assert unauthorized.headers["Location"].startswith("/login")

    missing_csrf = client.post(
        f"/admin/courts/{guid}/participants/{alice_id}/reset-pin",
        data={"pin": "654321"},
    )
    assert missing_csrf.status_code == 400

    delivered = []
    monkeypatch.setattr(
        app_module,
        "send_court_push_notifications",
        lambda court_guid, change_type: delivered.append(
            (court_guid, change_type)
        ),
    )

    renamed = client.post(
        f"/admin/courts/{guid}/participants/{alice_id}/rename",
        data={
            "csrf_token": csrf(client, location),
            "username": "Alicia",
        },
        follow_redirects=True,
    )
    assert "球友名稱已更新。".encode() in renamed.data
    assert delivered == [(guid, "members_changed")]

    duplicate = client.post(
        f"/admin/courts/{guid}/participants/{bob_id}/rename",
        data={
            "csrf_token": csrf(client, location),
            "username": "ALICIA",
        },
        follow_redirects=True,
    )
    assert "此使用者名稱已加入該場次。".encode() in duplicate.data
    assert delivered == [(guid, "members_changed")]

    invalid_pin = client.post(
        f"/admin/courts/{guid}/participants/{alice_id}/reset-pin",
        data={"csrf_token": csrf(client, location), "pin": "12345"},
        follow_redirects=True,
    )
    assert "PIN 碼必須正好為 6 位數字。".encode() in invalid_pin.data

    pin_reset = client.post(
        f"/admin/courts/{guid}/participants/{alice_id}/reset-pin",
        data={"csrf_token": csrf(client, location), "pin": "654321"},
        follow_redirects=True,
    )
    assert "球友 PIN 碼已重設。".encode() in pin_reset.data
    assert delivered == [(guid, "members_changed")]

    with app.app_context():
        db = get_db()
        renamed_participant = db.execute(
            "SELECT username, username_key, waitlisted, pin_hash "
            "FROM participants WHERE id = ?",
            (alice_id,),
        ).fetchone()
        bob = db.execute(
            "SELECT username FROM participants WHERE id = ?", (bob_id,)
        ).fetchone()
        assert tuple(renamed_participant)[:3] == ("Alicia", "alicia", 0)
        assert renamed_participant["pin_hash"] != original_alice_pin_hash
        assert check_password_hash(
            renamed_participant["pin_hash"], "654321"
        )
        assert not check_password_hash(
            renamed_participant["pin_hash"], "123456"
        )
        assert bob["username"] == "Bob"

    deleted = client.post(
        f"/admin/courts/{guid}/participants/{alice_id}/delete",
        data={"csrf_token": csrf(client, location)},
        follow_redirects=True,
    )
    assert "球友已移出場次。".encode() in deleted.data
    assert delivered == [
        (guid, "members_changed"),
        (guid, "members_changed"),
    ]
    with app.app_context():
        remaining = get_db().execute(
            "SELECT id, username, waitlisted FROM participants "
            "WHERE court_id = (SELECT id FROM courts WHERE guid = ?) "
            "ORDER BY joined_at, id",
            (guid,),
        ).fetchall()
        assert [
            (participant["username"], participant["waitlisted"])
            for participant in remaining
        ] == [("Bob", 0), ("Charlie", 1)]
        assert all(participant["id"] != alice_id for participant in remaining)
        get_db().execute(
            "UPDATE courts SET roll_clearing_locked = 1 WHERE guid = ?",
            (guid,),
        )
        get_db().commit()

    read_only_detail = client.get(location)
    assert b"data-participant-admin-menu" not in read_only_detail.data
    blocked_rename = client.post(
        f"/admin/courts/{guid}/participants/{bob_id}/rename",
        data={
            "csrf_token": csrf(client, location),
            "username": "Robert",
        },
        follow_redirects=True,
    )
    assert "此場次目前為唯讀。".encode() in blocked_rename.data
    with app.app_context():
        assert get_db().execute(
            "SELECT username FROM participants WHERE id = ?", (bob_id,)
        ).fetchone()["username"] == "Bob"
    assert delivered == [
        (guid, "members_changed"),
        (guid, "members_changed"),
    ]


def test_owner_can_finalize_court_and_record_roll_and_clearing(client, app):
    signup(client, "alice")
    location = create_member_court(client, "Finalized Court")

    token = csrf(client, location)
    client.post(
        f"{location}/join",
        data={"csrf_token": token, "username": "Bob", "pin": "123456"},
    )

    token = csrf(client, location)
    started = client.post(
        f"{location}/roll-clearing/start",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert "此場次目前為唯讀".encode() in started.data
    assert 'name="reserved_roll"'.encode() in started.data
    assert 'name="participant_roll"'.encode() in started.data
    assert b"Bob" in started.data

    guid = location.rsplit("/", 1)[-1]
    locked_edit = client.get(
        f"/my-courts/{guid}/edit", follow_redirects=False
    )
    assert locked_edit.status_code == 302
    assert locked_edit.headers["Location"] == location

    token = csrf(client, location)
    blocked_join = client.post(
        f"{location}/join",
        data={"csrf_token": token, "username": "Charlie", "pin": "654321"},
        follow_redirects=True,
    )
    assert "此場次目前為唯讀".encode() in blocked_join.data

    token = csrf(client, location)
    client.post(
        f"{location}/leave",
        data={"csrf_token": token, "username": "Bob", "pin": "123456"},
    )

    with app.app_context():
        db = get_db()
        court = db.execute(
            "SELECT id, roll_clearing_locked FROM courts WHERE guid = ?", (guid,)
        ).fetchone()
        participant = db.execute(
            "SELECT id FROM participants WHERE court_id = ? AND username = 'Bob'",
            (court["id"],),
        ).fetchone()
        reserved = db.execute(
            "SELECT id FROM reserved_members WHERE court_id = ?",
            (court["id"],),
        ).fetchone()
        assert court["roll_clearing_locked"] == 1
        assert participant is not None
        assert reserved is not None
        participant_id = participant["id"]
        reserved_id = reserved["id"]

    token = csrf(client, location)
    saved = client.post(
        f"{location}/roll-clearing/status",
        data={
            "csrf_token": token,
            "participant_roll": str(participant_id),
            "participant_cleared": str(participant_id),
            "reserved_roll": str(reserved_id),
        },
        follow_redirects=True,
    )
    assert "成員狀態已儲存".encode() in saved.data

    with app.app_context():
        participant_status = get_db().execute(
            "SELECT roll_called, cleared FROM participants WHERE id = ?",
            (participant_id,),
        ).fetchone()
        reserved_status = get_db().execute(
            "SELECT roll_called, cleared FROM reserved_members WHERE id = ?",
            (reserved_id,),
        ).fetchone()
        assert tuple(participant_status) == (1, 1)
        assert tuple(reserved_status) == (1, 0)
        assert get_db().execute(
            "SELECT COUNT(*) FROM participants WHERE court_id = ?",
            (court["id"],),
        ).fetchone()[0] == 1

    viewer = app.test_client()
    public_detail = viewer.get(location)
    assert 'name="participant_roll"'.encode() not in public_detail.data
    token = csrf(viewer, "/login")
    assert viewer.post(
        f"{location}/roll-clearing/status",
        data={"csrf_token": token},
    ).status_code == 404

    token = csrf(client, location)
    reopened = client.post(
        f"{location}/roll-clearing/edit",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert reopened.status_code == 302
    assert reopened.headers["Location"] == f"/my-courts/{guid}/edit"
    assert client.get(reopened.headers["Location"]).status_code == 200

    token = csrf(client, location)
    joined_after_reopen = client.post(
        f"{location}/join",
        data={"csrf_token": token, "username": "Charlie", "pin": "654321"},
        follow_redirects=True,
    )
    assert b"Charlie" in joined_after_reopen.data

    token = csrf(client, location)
    client.post(
        f"{location}/roll-clearing/start",
        data={"csrf_token": token},
    )
    with app.app_context():
        court_state = get_db().execute(
            "SELECT id, roll_clearing_locked FROM courts WHERE guid = ?", (guid,)
        ).fetchone()
        participant_status = get_db().execute(
            "SELECT roll_called, cleared FROM participants WHERE id = ?",
            (participant_id,),
        ).fetchone()
        reserved_status = get_db().execute(
            "SELECT roll_called, cleared FROM reserved_members "
            "WHERE court_id = ? AND position = 0",
            (court_state["id"],),
        ).fetchone()
        assert court_state["roll_clearing_locked"] == 1
        assert tuple(participant_status) == (1, 1)
        assert tuple(reserved_status) == (1, 0)


def test_language_uses_country_detection_until_user_selects_a_language(client):
    taiwan = client.get("/", headers={"CF-IPCountry": "TW"})
    assert "即將開打".encode() in taiwan.data

    overseas = client.get("/", headers={"CF-IPCountry": "US"})
    assert b"Upcoming courts" in overseas.data

    client.set_cookie("court_lang", "zh-tw")
    saved_zh = client.get("/", headers={"CF-IPCountry": "US"})
    assert "即將開打".encode() in saved_zh.data

    client.set_cookie("court_lang", "en-us")
    en = client.get("/", headers={"CF-IPCountry": "TW"})
    assert b"Upcoming courts" in en.data


def test_all_accounts_use_the_single_navigation_login(client):
    response = client.get("/")
    assert b'class="nav-link admin-link"' not in response.data
    assert b'href="/login"' in response.data
    assert b'href="/admin/login"' not in response.data
    legacy = client.get("/admin/login")
    assert legacy.status_code == 302
    assert legacy.headers["Location"] == "/login"


def test_introduction_page_is_bilingual_and_linked_from_footer(client):
    homepage = client.get("/")
    assert b'class="footer-introduction-link" href="/introduction"' in homepage.data

    introduction = client.get("/introduction")
    assert introduction.status_code == 200
    assert "管理場次，連結每一位球友。".encode() in introduction.data
    assert introduction.data.count(b'class="panel intro-feature-card"') == 6
    assert b'href="/courts"' in introduction.data
    assert b'href="/signup"' in introduction.data

    client.set_cookie("court_lang", "en-us")
    english = client.get("/introduction")
    assert b"Organize the court. Bring players together." in english.data
    assert b"Join without an account" in english.data
    assert b"Ready for your next game?" in english.data


def test_privacy_policy_is_bilingual_public_and_linked_from_footer(client, app):
    homepage = client.get("/")
    assert b'class="footer-privacy-link" href="/privacy"' in homepage.data

    privacy = client.get("/privacy")
    assert privacy.status_code == 200
    assert "隱私權政策".encode() in privacy.data
    assert b'<time datetime="2026-07-30">' in privacy.data
    assert privacy.data.count(b'class="panel privacy-section"') == 10
    assert "應用程式內建功能不含廣告或分析追蹤器".encode() in privacy.data
    assert "管理員 CSV 匯出".encode() in privacy.data
    assert "完整 User-Agent 或裝置指紋".encode() in privacy.data
    assert "Google Fonts".encode() in privacy.data
    assert "聯絡留言：訪客填寫的名稱".encode() in privacy.data
    assert "Discord Webhook 及／或 Telegram Bot".encode() in privacy.data
    assert "尚未設定專用的隱私權聯絡方式".encode() in privacy.data
    assert b"PRIVACY_CONTACT" not in privacy.data

    app.config.update(
        PRIVACY_OPERATOR_NAME="Example Badminton Association",
        PRIVACY_DATA_REGION="Taiwan",
        PRIVACY_CONTACT="mailto:privacy@example.test",
    )
    client.set_cookie("court_lang", "en-us")
    english = client.get("/privacy")
    assert b"Privacy policy" in english.data
    assert b"Scope and responsibility" in english.data
    assert b"The built-in application does not include advertising" in english.data
    assert b"Example Badminton Association" in english.data
    assert b"<dd>Taiwan</dd>" in english.data
    assert b'href="mailto:privacy@example.test"' in english.data
    assert b">privacy@example.test</a>" in english.data

    app.config["PRIVACY_CONTACT"] = "javascript:alert(1)"
    invalid_contact = client.get("/privacy")
    assert b"javascript:alert(1)" not in invalid_contact.data
    assert b"has not configured a dedicated privacy contact" in invalid_contact.data


def test_admin_contact_page_is_bilingual_public_and_linked_from_footer(client, app):
    homepage = client.get("/")
    assert b'class="footer-contact-link" href="/contact"' in homepage.data

    contact = client.get("/contact")
    assert contact.status_code == 200
    assert "聯絡網站管理員。".encode() in contact.data
    assert "網站管理員尚未設定公開聯絡方式".encode() in contact.data
    assert "請勿傳送密碼、管理員憑證或球友的 6 位數 PIN 碼".encode() in contact.data
    assert b"ADMIN_CONTACT" not in contact.data

    app.config.update(
        PRIVACY_OPERATOR_NAME="Example Badminton Association",
        ADMIN_CONTACT="mailto:admin@example.test",
        ADMIN_CONTACT_DISCORD="example-invite",
        ADMIN_CONTACT_LINE="@example.line",
        ADMIN_CONTACT_TELEGRAM="@example_bot",
    )
    client.set_cookie("court_lang", "en-us")
    english = client.get("/contact")
    assert b"Contact the site administrator." in english.data
    assert b"Example Badminton Association" in english.data
    assert b'href="mailto:admin@example.test"' in english.data
    assert (
        b'<span class="contact-method-value">admin@example.test</span>'
        in english.data
    )
    assert b'href="https://discord.gg/example-invite"' in english.data
    assert (
        b'href="https://line.me/R/ti/p/%40example.line"' in english.data
    )
    assert b'href="https://t.me/example_bot"' in english.data
    assert b">example-invite</span>" in english.data
    assert b">@example.line</span>" in english.data
    assert b">@example_bot</span>" in english.data
    assert english.data.count(b'class="contact-method-group ') == 2
    assert b'id="contact-method-group-email">Email</h3>' in english.data
    assert (
        b'id="contact-method-group-messaging">Messaging</h3>'
        in english.data
    )
    assert b'id="contact-method-group-other"' not in english.data
    assert english.data.count(b'class="contact-method-link"') == 4
    assert (
        english.data.index(b'id="contact-method-group-email"')
        < english.data.index(b">Email</span>")
        < english.data.index(b'id="contact-method-group-messaging"')
        < english.data.index(b">Discord</span>")
        < english.data.index(b">LINE</span>")
        < english.data.index(b">Telegram</span>")
    )
    assert b"Never send your password" in english.data

    app.config["ADMIN_CONTACT"] = "https://support.example.test"
    website_group = client.get("/contact")
    assert (
        b'id="contact-method-group-messaging">Messaging</h3>'
        in website_group.data
    )
    assert (
        b'id="contact-method-group-other">Other methods</h3>'
        in website_group.data
    )
    assert (
        website_group.data.index(b'id="contact-method-group-messaging"')
        < website_group.data.index(b'id="contact-method-group-other"')
        < website_group.data.index(b">Website</span>")
    )

    app.config["ADMIN_CONTACT"] = "https://t.me/example_bot"
    deduplicated_contact = client.get("/contact")
    assert deduplicated_contact.data.count(
        b'href="https://t.me/example_bot"'
    ) == 1

    app.config.update(
        ADMIN_CONTACT="",
        ADMIN_CONTACT_DISCORD="https://discord.com/invite/legacy-code",
        ADMIN_CONTACT_LINE="https://line.me/R/ti/p/%40legacy.line",
        ADMIN_CONTACT_TELEGRAM="https://telegram.me/legacy_bot",
    )
    legacy_links = client.get("/contact")
    assert (
        legacy_links.data.count(b'class="contact-method-group ') == 1
    )
    assert b'id="contact-method-group-email"' not in legacy_links.data
    assert b'id="contact-method-group-messaging"' in legacy_links.data
    assert b'id="contact-method-group-other"' not in legacy_links.data
    assert b'href="https://discord.gg/legacy-code"' in legacy_links.data
    assert (
        b'href="https://line.me/R/ti/p/%40legacy.line"'
        in legacy_links.data
    )
    assert b'href="https://t.me/legacy_bot"' in legacy_links.data

    app.config.update(
        ADMIN_CONTACT="javascript:alert(1)",
        ADMIN_CONTACT_DISCORD="https://example.com/not-discord",
        ADMIN_CONTACT_LINE="http://line.me/not-secure",
        ADMIN_CONTACT_TELEGRAM="https://example.com/not-telegram",
    )
    invalid_contact = client.get("/contact")
    assert b"javascript:alert(1)" not in invalid_contact.data
    assert b"not-discord" not in invalid_contact.data
    assert b"not-secure" not in invalid_contact.data
    assert b"not-telegram" not in invalid_contact.data
    assert b"has not configured a public contact method" in invalid_contact.data


def test_public_contact_message_is_validated_and_stored(client, app, monkeypatch):
    def unexpected_urlopen(*_args, **_kwargs):
        raise AssertionError("Notifications are disabled by default")

    monkeypatch.setattr(app_module, "urlopen", unexpected_urlopen)
    page = client.get("/contact")
    assert b'id="contact-form"' in page.data
    assert b'name="sender_name"' in page.data
    assert b'name="reply_contact"' in page.data
    assert b'name="subject"' in page.data
    assert b'name="message"' in page.data

    missing_csrf = client.post(
        "/contact",
        data={
            "sender_name": "Visitor",
            "subject": "Help",
            "message": "Please help.",
        },
    )
    assert missing_csrf.status_code == 400

    invalid = client.post(
        "/contact",
        data={
            "csrf_token": csrf(client, "/contact"),
            "sender_name": "",
            "reply_contact": "visitor@example.test",
            "subject": "",
            "message": "",
        },
    )
    assert invalid.status_code == 400
    assert "請填寫所有必填欄位".encode() in invalid.data

    oversized = client.post(
        "/contact",
        data={
            "csrf_token": csrf(client, "/contact"),
            "sender_name": "Visitor",
            "subject": "Oversized",
            "message": "x" * 17_000,
        },
    )
    assert oversized.status_code == 413

    submitted = client.post(
        "/contact",
        data={
            "csrf_token": csrf(client, "/contact"),
            "sender_name": "訪客 <One>",
            "reply_contact": "visitor@example.test",
            "subject": "帳號問題",
            "message": "登入時看到錯誤。\n請協助。",
        },
        follow_redirects=False,
    )
    assert submitted.status_code == 302
    assert submitted.headers["Location"] == "/contact#contact-form"
    with app.app_context():
        stored = get_db().execute(
            "SELECT sender_name, reply_contact, subject, message, language, "
            "submitted_at, read_at FROM contact_messages"
        ).fetchone()
        assert stored["sender_name"] == "訪客 <One>"
        assert stored["reply_contact"] == "visitor@example.test"
        assert stored["subject"] == "帳號問題"
        assert stored["message"] == "登入時看到錯誤。\n請協助。"
        assert stored["language"] == "zh-tw"
        assert stored["submitted_at"]
        assert stored["read_at"] is None


def test_contact_message_uses_turnstile_when_configured(
    client, app, monkeypatch
):
    app.config.update(
        TURNSTILE_SITE_KEY="contact-site-key",
        TURNSTILE_SECRET_KEY="contact-secret-key",
    )
    checked_actions = []

    def verify_action(action):
        checked_actions.append(action)
        return True

    monkeypatch.setattr(app_module, "verify_turnstile_response", verify_action)
    page = client.get("/contact")
    assert b'class="cf-turnstile"' in page.data
    assert b'data-action="contact_message"' in page.data
    assert b'data-sitekey="contact-site-key"' in page.data

    submitted = client.post(
        "/contact",
        data={
            "csrf_token": csrf(client, "/contact"),
            "sender_name": "Visitor",
            "subject": "Technical issue",
            "message": "The page did not load.",
        },
    )
    assert submitted.status_code == 302
    assert checked_actions == ["contact_message"]


def test_admin_can_view_and_mark_contact_messages(client, app):
    submitted = client.post(
        "/contact",
        data={
            "csrf_token": csrf(client, "/contact"),
            "sender_name": "Visitor <script>",
            "reply_contact": "@visitor",
            "subject": "Question <b>",
            "message": "Line one\nLine <two>",
        },
    )
    assert submitted.status_code == 302
    anonymous_inbox = client.get("/admin/messages")
    assert anonymous_inbox.status_code == 302
    assert "/login?next=/admin/messages" in anonymous_inbox.headers["Location"]

    login(client)
    inbox = client.get("/admin/messages")
    assert inbox.status_code == 200
    assert "聯絡留言".encode() in inbox.data
    assert b"Visitor &lt;script&gt;" in inbox.data
    assert b"Question &lt;b&gt;" in inbox.data
    assert b"Line &lt;two&gt;" in inbox.data
    assert b"CONTACT_TELEGRAM_BOT_TOKEN" not in inbox.data
    assert b"contact-secret" not in inbox.data
    assert "1 未讀留言".encode() in inbox.data

    updated = client.post(
        "/admin/messages/1/status",
        data={
            "csrf_token": csrf(client, "/admin/messages"),
            "read": "1",
            "status": "all",
            "page": "1",
        },
        follow_redirects=True,
    )
    assert updated.status_code == 200
    assert "留言狀態已更新".encode() in updated.data
    with app.app_context():
        message = get_db().execute(
            "SELECT read_at FROM contact_messages WHERE id = 1"
        ).fetchone()
        assert message["read_at"]

    unread = client.get("/admin/messages?status=unread")
    assert "此檢視目前沒有聯絡留言".encode() in unread.data


def test_contact_notifications_use_enabled_discord_and_telegram(
    client, app, monkeypatch
):
    bot_token = "123456789:abcdefghijklmnopqrstuvwxyzABCDE"
    app.config.update(
        CONTACT_DISCORD_WEBHOOK_URL=(
            "https://discord.com/api/webhooks/123456/"
            "abcdefghijklmnopqrstuvwxyz"
        ),
        CONTACT_TELEGRAM_BOT_TOKEN=bot_token,
        CONTACT_TELEGRAM_CHAT_ID="-1001234567890",
    )
    login(client)
    settings_page = client.get("/admin/messages")
    assert "Discord Webhook 已設定".encode() in settings_page.data
    assert "Telegram Bot 與聊天室已設定".encode() in settings_page.data
    assert b"abcdefghijklmnopqrstuvwxyz" not in settings_page.data
    assert bot_token.encode() not in settings_page.data

    enabled = client.post(
        "/admin/settings/contact-notifications",
        data={
            "csrf_token": csrf(client, "/admin/messages"),
            "enabled": "1",
        },
        follow_redirects=True,
    )
    assert "留言通知設定已儲存".encode() in enabled.data
    with app.app_context():
        assert get_db().execute(
            "SELECT setting_value FROM app_settings "
            "WHERE setting_key = 'contact_notifications_enabled'"
        ).fetchone()["setting_value"] == "1"

    captured_requests = []

    class FakeResponse:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit):
            return self.body

    def fake_urlopen(notification_request, timeout):
        captured_requests.append((notification_request, timeout))
        body = (
            b'{"ok": true}'
            if "api.telegram.org" in notification_request.full_url
            else b""
        )
        return FakeResponse(body)

    monkeypatch.setattr(app_module, "urlopen", fake_urlopen)
    submitted = client.post(
        "/contact",
        data={
            "csrf_token": csrf(client, "/contact"),
            "sender_name": "Notifier",
            "reply_contact": "notify@example.test",
            "subject": "Notification test",
            "message": "Please notify both channels.",
        },
    )
    assert submitted.status_code == 302
    assert len(captured_requests) == 2
    discord_request = next(
        item[0]
        for item in captured_requests
        if "discord.com" in item[0].full_url
    )
    discord_payload = json.loads(discord_request.data)
    assert discord_payload["allowed_mentions"] == {"parse": []}
    assert "Notification test" in discord_payload["content"]
    assert "notify@example.test" in discord_payload["content"]
    telegram_request = next(
        item[0]
        for item in captured_requests
        if "api.telegram.org" in item[0].full_url
    )
    telegram_payload = json.loads(telegram_request.data)
    assert telegram_payload["chat_id"] == "-1001234567890"
    assert "Please notify both channels." in telegram_payload["text"]
    assert all(timeout == 1 for _, timeout in captured_requests)

    def unavailable_urlopen(*_args, **_kwargs):
        raise app_module.URLError("offline")

    monkeypatch.setattr(app_module, "urlopen", unavailable_urlopen)
    still_stored = client.post(
        "/contact",
        data={
            "csrf_token": csrf(client, "/contact"),
            "sender_name": "Stored",
            "subject": "Delivery can fail",
            "message": "This must remain in SQLite.",
        },
    )
    assert still_stored.status_code == 302
    with app.app_context():
        assert get_db().execute(
            "SELECT COUNT(*) AS count FROM contact_messages"
        ).fetchone()["count"] == 2


def test_admin_cannot_enable_contact_notifications_without_a_channel(
    client, app
):
    login(client)
    response = client.post(
        "/admin/settings/contact-notifications",
        data={
            "csrf_token": csrf(client, "/admin/messages"),
            "enabled": "1",
        },
        follow_redirects=True,
    )
    assert "啟用通知前".encode() in response.data
    with app.app_context():
        assert get_db().execute(
            "SELECT 1 FROM app_settings "
            "WHERE setting_key = 'contact_notifications_enabled'"
        ).fetchone() is None


def test_update_history_page_is_bilingual_and_linked_from_footer(client):
    homepage = client.get("/")
    assert b'class="footer-updates-link" href="/updates"' in homepage.data

    updates = client.get("/updates")
    assert updates.status_code == 200
    assert "羽球場控面板，持續變得更好。".encode() in updates.data
    assert "場次縮圖可直接下載".encode() in updates.data
    assert "每個公開場次詳情頁都新增「下載縮圖」按鈕".encode() in updates.data
    assert "符合每位會員習慣的時間顯示".encode() in updates.data
    assert "退出期限編輯器拆分為日期及 24 小時制 HH:MM 欄位".encode() in updates.data
    assert "個人資料頁新增可保存的 12 小時制".encode() in updates.data
    assert "更清楚的退出規則與場次表單".encode() in updates.data
    assert "活動主辦者可啟用精確的本地退出期限".encode() in updates.data
    assert "場次資訊檔匯入工具預設收合".encode() in updates.data
    assert "每個預訂球友暱稱旁皆新增「刪除」操作".encode() in updates.data
    assert "更清楚的隱私權說明".encode() in updates.data
    assert "區分公開資訊、主辦者與管理員存取範圍".encode() in updates.data
    assert "部署網站營運者、主要資料地區".encode() in updates.data
    assert "新增網站管理員聯絡頁面".encode() in updates.data
    assert "訪客可留下儲存在 SQLite 的留言".encode() in updates.data
    assert "可攜式場次檔案與完整 CSV 匯出".encode() in updates.data
    assert "yyyy-MM-dd_HHmm_HHmm_&lt;活動或球館&gt;.md".encode() in updates.data
    assert "先預填並確認內容，再建立活動".encode() in updates.data
    assert "管理員可將所有現有場次".encode() in updates.data
    assert "每個場次連結都有豐富的社群預覽".encode() in updates.data
    assert "公開整理第三方素材授權資訊".encode() in updates.data
    assert "限制退出場次時重複輸入錯誤暱稱或 PIN 碼".encode() in updates.data
    assert "直接在場次頁管理球友".encode() in updates.data
    assert "系統會自動遞補最早加入的候補球友".encode() in updates.data
    assert "2026 年 7 月 28 日".encode() in updates.data
    assert updates.data.count(b'class="update-entry"') == 11
    assert updates.data.count(b'class="update-latest"') == 1
    assert b'<time datetime="2026-09-03">' in updates.data

    client.set_cookie("court_lang", "en-us")
    english = client.get("/updates")
    assert b"The control panel keeps getting better." in english.data
    assert b"Court thumbnails ready to download" in english.data
    assert b"Download thumbnail button to every public court" in english.data
    assert b"Time displays that fit each member" in english.data
    assert b"date and 24-hour HH:MM fields" in english.data
    assert b"persistent 12-hour (AM/PM) or 24-hour display preference" in english.data
    assert b"Clearer leave rules and cleaner event forms" in english.data
    assert b"event owner enable an exact local leave deadline" in english.data
    assert b"file importer by default" in english.data
    assert b"A clearer view of privacy" in english.data
    assert b"Distinguishes public information from organizer" in english.data
    assert b"configured deployment operator, primary data region" in english.data
    assert b"dedicated administrator-contact page" in english.data
    assert b"visitors leave messages stored in SQLite" in english.data
    assert b"Portable court files and complete CSV exports" in english.data
    assert b"yyyy-MM-dd_HHmm_HHmm_&lt;event-or-hall&gt;.md" in english.data
    assert b"prefill details for review before anything is created" in english.data
    assert b"Lets administrators export every existing court" in english.data
    assert b"Rich previews for every shared court" in english.data
    assert b"Organizes third-party asset licenses publicly" in english.data
    assert b"Safer access and court notifications" in english.data
    assert b"Limits repeated incorrect nickname/PIN attempts" in english.data
    assert b"Manage players without leaving the court page" in english.data
    assert b"automatically promoting the earliest waiting player" in english.data
    assert b"Changes in this update" in english.data


def test_update_history_is_loaded_and_validated_from_json(tmp_path):
    history_path = Path(app_module.__file__).with_name(
        "data"
    ) / "update_history.json"
    source_history = json.loads(history_path.read_text(encoding="utf-8"))
    assert tuple(source_history) == app_module.SITE_UPDATE_HISTORY
    assert app_module.SITE_UPDATE_HISTORY_PATH == history_path
    assert len(source_history) == 11

    invalid_history_path = tmp_path / "invalid-update-history.json"
    invalid_history_path.write_text(
        json.dumps(list(reversed(source_history))),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="newest first"):
        app_module.load_site_update_history(invalid_history_path)

    missing_translation = json.loads(json.dumps(source_history))
    del missing_translation[0]["title"]["zh-tw"]
    invalid_history_path.write_text(
        json.dumps(missing_translation),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="title translations"):
        app_module.load_site_update_history(invalid_history_path)


def test_first_visit_introduction_prompt_is_bilingual_and_remembered_in_browser(client):
    homepage = client.get("/")
    assert b'class="first-visit-tooltip"' in homepage.data
    assert b'data-first-visit-prompt' in homepage.data
    assert b'data-introduction-url="/introduction"' in homepage.data
    assert b'data-first-visit-accept' in homepage.data
    assert b'data-first-visit-decline' in homepage.data
    assert "第一次來嗎？先快速認識網站。".encode() in homepage.data
    assert "查看網站介紹".encode() in homepage.data
    assert "暫時不用".encode() in homepage.data

    client.set_cookie("court_lang", "en-us")
    english = client.get("/")
    assert b"New here? Take a quick tour." in english.data
    assert b"View introduction" in english.data
    assert b"Not now" in english.data

    javascript = client.get("/static/js/app.js")
    assert javascript.status_code == 200
    assert b"court-introduction-prompt-seen-v1" in javascript.data
    assert b"window.location.pathname === introductionUrl" in javascript.data
    assert b"firstVisitPrompt.hidden = false" in javascript.data


def test_homepage_shuttle_uses_vector_feathers_band_and_cork(client):
    response = client.get("/")
    assert b'class="brand-mark-shuttle"' in response.data
    assert b'<svg class="shuttle"' in response.data
    assert b'class="empty-icon-shuttle"' in response.data
    assert b'class="shuttle-skirt"' in response.data
    assert b'class="shuttle-ribs"' in response.data
    assert b'class="shuttle-band"' in response.data
    assert b'class="shuttle-cork"' in response.data
    not_found = client.get("/not-a-real-court-guid")
    assert not_found.status_code == 404
    assert b'class="empty-icon-shuttle"' in not_found.data


def test_social_thumbnail_uses_bundled_noto_font(app):
    expected_path = (
        Path(app_module.__file__).parent
        / "static"
        / "fonts"
        / "NotoSansTC-VF.ttf"
    ).resolve()

    with app.app_context():
        regular = app_module.social_thumbnail_font(48)
        bold = app_module.social_thumbnail_font(48, bold=True)

    assert Path(regular.path).resolve() == expected_path
    assert Path(bold.path).resolve() == expected_path
    assert regular.getbbox("羽球場")[2] > 0
    assert bytes(regular.getmask("羽")) != bytes(bold.getmask("羽"))


def test_theme_picker_includes_each_palette_and_appearance(client):
    response = client.get("/")
    assert b'<html lang="zh-tw" data-theme="light" data-palette="yellow">' in response.data
    assert b"localStorage.getItem('court-theme') || 'light'" in response.data
    assert b"localStorage.getItem('court-palette') || 'yellow'" in response.data
    assert response.data.count(b'class="preferences-menu"') == 1
    assert b'class="preferences-icon"' in response.data
    assert "<span>偏好設定</span>".encode() in response.data
    assert b'id="language-select"' in response.data
    assert b'id="theme-select"' in response.data
    assert b'class="select-compact"' not in response.data
    for palette in (b"mono", b"green", b"purple", b"yellow"):
        for mode in (b"system", b"light", b"dark"):
            assert b'value="' + palette + b":" + mode + b'"' in response.data


def test_shuttlecock_png_favicon_is_linked_and_served(client):
    response = client.get("/")
    assert (
        b'rel="icon" href="/static/shuttlecock.png" '
        b'type="image/png" sizes="512x512"' in response.data
    )
    assert b'rel="apple-touch-icon" href="/static/shuttlecock.png"' in response.data
    favicon = client.get("/static/shuttlecock.png")
    assert favicon.status_code == 200
    assert favicon.mimetype == "image/png"
    assert favicon.data.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(favicon.data) > 40_000


def test_license_page_credits_assets_and_codex_support(client):
    homepage = client.get("/")
    assert b'class="footer-license-link" href="/licenses"' in homepage.data

    license_page = client.get("/licenses")
    assert license_page.status_code == 200
    assert b'class="panel license-card"' in license_page.data
    assert b'src="/static/shuttlecock.png"' in license_page.data
    assert b"https://www.flaticon.com/free-icon/shuttlecock_9719863" in license_page.data
    assert b"https://media.flaticon.com/license/license.pdf" in license_page.data
    assert b"https://www.flaticon.com/terms-of-use" in license_page.data
    assert "本網站由 OpenAI Codex 協助開發".encode() in license_page.data
    assert "本網站之內容、營運與最終成果仍由專案擁有者負責".encode() in license_page.data
    assert b'href="https://openai.com/codex/"' in license_page.data
    assert b'class="codex-credit-mark"' in license_page.data
    assert "Noto Sans 繁體中文字型".encode() in license_page.data
    assert b'href="https://github.com/notofonts/noto-cjk"' in license_page.data
    assert b'href="/static/fonts/NotoSansTC-OFL.txt"' in license_page.data
    assert license_page.data.index(
        b'data-license-entry="flaticon"'
    ) < license_page.data.index(
        b'data-license-entry="noto"'
    )
    assert license_page.data.index(
        b'data-license-entry="noto"'
    ) < license_page.data.index(
        b'data-license-entry="codex"'
    )

    font_license = client.get("/static/fonts/NotoSansTC-OFL.txt")
    assert font_license.status_code == 200
    assert b"SIL OPEN FONT LICENSE Version 1.1" in font_license.data

    font = client.get("/static/fonts/NotoSansTC-VF.ttf")
    assert font.status_code == 200
    assert font.data.startswith(b"\x00\x01\x00\x00")
    assert len(font.data) > 11_000_000


def test_project_brand_and_grading_asset(client):
    client.set_cookie("court_lang", "en-us")
    english = client.get("/")
    assert b"Badminton Court Control Panel" in english.data
    assert b">Court Control Panel<" not in english.data

    client.set_cookie("court_lang", "zh-tw")
    assert "羽球場控面板".encode() in client.get("/").data

    grading = client.get("/static/grading.webp")
    assert grading.status_code == 200
    assert grading.mimetype == "image/webp"
    assert len(grading.data) > 300_000


def test_public_all_courts_page_lists_active_courts(client):
    login(client)
    court_location = create_court(client)
    listing = client.get("/courts")
    assert listing.status_code == 200
    assert "所有場次".encode() in listing.data
    assert b"Taipei Sports Center" in listing.data
    assert court_location.encode() in listing.data
    assert b'href="/courts"' in client.get("/").data
    assert b'name="q"' in listing.data
    assert b'name="date_from"' in listing.data
    assert b'name="date_to"' in listing.data
    assert b'name="level"' in listing.data
    assert b'name="gender"' in listing.data
    assert b'name="status"' in listing.data
    assert b'name="show_expired"' in listing.data
    assert b'data-date-from' in listing.data
    assert b'data-date-to' in listing.data
    assert b'placeholder="yyyy/mm/dd"' in listing.data
    assert b'class="nav-link active" href="/"' not in client.get("/").data


def test_admin_can_configure_homepage_court_limit(client, app):
    login(client)
    for _ in range(13):
        create_court(client)

    homepage = client.get("/")
    listing = client.get("/courts")
    assert homepage.data.count(b'class="court-card"') == 12
    assert listing.data.count(b'class="court-card"') == 13

    token = csrf(client, "/admin")
    saved = client.post(
        "/admin/settings/homepage",
        data={"csrf_token": token, "homepage_court_limit": "5"},
        follow_redirects=True,
    )
    assert "首頁設定已儲存".encode() in saved.data
    assert client.get("/").data.count(b'class="court-card"') == 5
    assert client.get("/courts").data.count(b'class="court-card"') == 13
    with app.app_context():
        setting = get_db().execute(
            "SELECT setting_value FROM app_settings "
            "WHERE setting_key = 'homepage_court_limit'"
        ).fetchone()
        assert setting["setting_value"] == "5"


def test_admin_can_export_every_court_as_utf8_csv(client, app):
    login(client)
    active_location = create_court(
        client,
        event_name="CSV 羽球",
        badminton_name="北區球團",
    )
    archived_location = create_court(client, event_name="Archived Event")
    expired_location = create_court(client, event_name="Temporary")
    active_guid = active_location.rsplit("/", 1)[-1]
    archived_guid = archived_location.rsplit("/", 1)[-1]
    expired_guid = expired_location.rsplit("/", 1)[-1]
    with app.app_context():
        db = get_db()
        db.execute(
            "UPDATE courts SET archived = 1, court_date = '2026-09-12' "
            "WHERE guid = ?",
            (archived_guid,),
        )
        db.execute(
            "UPDATE courts SET event_name = '=2+2', court_date = '2000-01-01', "
            "end_time = '09:00' WHERE guid = ?",
            (expired_guid,),
        )
        db.commit()

    dashboard = client.get("/admin")
    assert b'href="/admin/courts/export.csv"' in dashboard.data
    assert "匯出所有場次（CSV）".encode() in dashboard.data
    assert b"=2+2" not in dashboard.data

    exported = client.get("/admin/courts/export.csv")
    assert exported.status_code == 200
    assert exported.mimetype == "text/csv"
    assert exported.data.startswith(b"\xef\xbb\xbf")
    assert exported.headers["Cache-Control"] == "private, no-store"
    assert "_all_court_events.csv" in exported.headers["Content-Disposition"]

    rows = list(
        csv.DictReader(io.StringIO(exported.data.decode("utf-8-sig")))
    )
    assert len(rows) == 3
    rows_by_guid = {row["guid"]: row for row in rows}
    active = rows_by_guid[active_guid]
    assert active["event_name"] == "CSV 羽球"
    assert active["badminton_name"] == "北區球團"
    assert active["status"] == "open"
    assert active["reserved_nicknames"] == '["Coach Lin", "Mina"]'
    assert active["confirmed_signup_count"] == "0"
    assert active["total_confirmed_count"] == "2"
    assert active["public_url"].endswith(f"/{active_guid}")
    assert rows_by_guid[archived_guid]["status"] == "archived"
    assert rows_by_guid[expired_guid]["status"] == "expired"
    assert rows_by_guid[expired_guid]["event_name"] == "'=2+2"

    anonymous_client = app.test_client()
    unauthorized = anonymous_client.get("/admin/courts/export.csv")
    assert unauthorized.status_code == 302
    assert urlparse(unauthorized.headers["Location"]).path == "/login"


def test_admin_can_filter_all_courts(client, app):
    login(client)
    first_location = create_court(client)
    second_location = create_court(client)
    first_guid = first_location.rsplit("/", 1)[-1]
    second_guid = second_location.rsplit("/", 1)[-1]
    with app.app_context():
        db = get_db()
        db.execute(
            "UPDATE courts SET event_name = 'Morning Training', "
            "badminton_name = 'North Club', creator_name = 'manager', "
            "court_date = '2026-08-20' WHERE guid = ?",
            (first_guid,),
        )
        db.execute(
            "UPDATE courts SET event_name = 'Archived Social', "
            "badminton_name = 'South Club', creator_name = 'alice', "
            "court_date = '2026-09-12', archived = 1 WHERE guid = ?",
            (second_guid,),
        )
        db.commit()

    dashboard = client.get("/admin")
    assert b'<details class="panel court-filter-panel admin-court-filter-panel">' in dashboard.data
    assert b'name="q"' in dashboard.data
    assert b'name="date_from"' in dashboard.data
    assert b'name="date_to"' in dashboard.data
    assert b'name="level"' in dashboard.data
    assert b'name="gender"' in dashboard.data
    assert b'name="status"' in dashboard.data
    assert b'name="show_expired"' in dashboard.data
    assert b'<option value="archived"' in dashboard.data

    by_keyword = client.get("/admin?q=North+Club")
    assert b"Morning Training" in by_keyword.data
    assert b"Archived Social" not in by_keyword.data

    by_creator = client.get("/admin?q=alice")
    assert b"Archived Social" in by_creator.data
    assert b"Morning Training" not in by_creator.data
    assert b'value="alice"' in by_creator.data

    by_date = client.get(
        "/admin?date_from=2026%2F08%2F01&date_to=2026%2F08%2F31"
    )
    assert b"Morning Training" in by_date.data
    assert b"Archived Social" not in by_date.data
    assert b'value="2026/08/01"' in by_date.data

    archived = client.get("/admin?status=archived")
    assert b"Archived Social" in archived.data
    assert b"Morning Training" not in archived.data
    assert b'value="archived" selected' in archived.data

    by_level_and_gender = client.get("/admin?level=12&gender=male")
    assert b"Morning Training" in by_level_and_gender.data
    assert b'value="12" selected' in by_level_and_gender.data
    assert b'value="male" selected' in by_level_and_gender.data

    with app.app_context():
        get_db().execute(
            "UPDATE courts SET court_date = '2000-01-01', "
            "end_time = '09:00' WHERE guid = ?",
            (first_guid,),
        )
        get_db().commit()
    assert b"Morning Training" not in client.get("/admin").data
    show_expired = client.get("/admin?q=Morning&show_expired=1")
    assert b"Morning Training" in show_expired.data
    assert b'name="show_expired" type="checkbox" value="1" checked' in show_expired.data


def test_public_court_filters_and_creator_display(client):
    signup(client, "alice")
    court_location = create_member_court(client, "Alice Badminton Hall")

    homepage = client.get("/")
    detail = client.get(court_location)
    assert b"Alice Badminton Hall" in homepage.data
    assert b"alice" in homepage.data
    assert b"alice" in detail.data
    assert "活動建立者".encode() in detail.data

    by_creator = client.get("/courts?q=alice")
    assert b"Alice Badminton Hall" in by_creator.data
    assert b'value="alice"' in by_creator.data
    assert b'<details class="panel court-filter-panel">' in by_creator.data
    assert b'<details class="panel court-filter-panel" open>' not in by_creator.data

    by_date_and_level = client.get(
        "/courts?date_from=2026-09-01&date_to=2026-09-30"
        "&level=12&gender=male&status=open"
    )
    assert b"Alice Badminton Hall" in by_date_and_level.data
    assert b'value="2026/09/01"' in by_date_and_level.data
    assert b'value="2026/09/30"' in by_date_and_level.data
    assert b'value="12" selected' in by_date_and_level.data
    assert b'value="male" selected' in by_date_and_level.data
    assert b'value="open" selected' in by_date_and_level.data

    female_no_match = client.get("/courts?level=12&gender=female")
    assert b"Alice Badminton Hall" not in female_no_match.data

    both_match = client.get("/courts?level=10&gender=both")
    assert b"Alice Badminton Hall" in both_match.data
    assert b'value="both" selected' in both_match.data

    no_match = client.get(
        "/courts?date_from=2026-09-11&date_to=2026-09-30&level=18"
    )
    assert b"Alice Badminton Hall" not in no_match.data
    assert "目前沒有開放場次".encode() in no_match.data


def test_expired_courts_are_hidden_by_default_and_read_only(client, app):
    login(client)
    court_location = create_court(client)
    guid = court_location.rsplit("/", 1)[-1]
    with app.app_context():
        db = get_db()
        db.execute(
            "UPDATE courts SET court_date = '2000-01-01', "
            "start_time = '08:00', end_time = '09:00' WHERE guid = ?",
            (guid,),
        )
        db.commit()

    assert b"Taipei Sports Center" not in client.get("/").data
    assert b"Taipei Sports Center" not in client.get("/courts").data

    expired_listing = client.get("/courts?show_expired=1")
    assert b"Taipei Sports Center" in expired_listing.data
    assert "已過期".encode() in expired_listing.data
    assert b'name="show_expired" type="checkbox" value="1" checked' in expired_listing.data

    detail = client.get(court_location)
    assert "此場次已結束".encode() in detail.data
    assert b'class="status status-expired"' in detail.data

    token = csrf(client, court_location)
    rejected = client.post(
        f"/{guid}/join",
        data={"csrf_token": token, "username": "late-player", "pin": "123456"},
        follow_redirects=True,
    )
    assert "此場次已結束".encode() in rejected.data
    with app.app_context():
        assert get_db().execute(
            "SELECT COUNT(*) FROM participants"
        ).fetchone()[0] == 0


def test_admin_form_enforces_24_hour_time_and_loads_places_widget(client, app):
    app.config["GOOGLE_MAPS_API_KEY"] = "test-maps-key"
    login(client)
    form = client.get("/courts/new")
    assert b'data-time24' in form.data
    assert b'placeholder="19:00"' in form.data
    assert b'id="hall-autocomplete-host"' in form.data
    assert b'id="ordered-count"' in form.data
    assert b'id="reserved-nickname-list"' in form.data
    assert b"data-delete-label=" in form.data
    assert b"data-api-error=" in form.data
    assert b'name="google_place_id"' in form.data
    assert b'name="hall_name"' in form.data
    assert b"readonly" in form.data
    assert b"v=weekly" in form.data
    assert b"language=zh-TW" in form.data
    assert b"region=TW" in form.data
    assert b"callback=initPlacesAutocomplete" in form.data

    token = csrf(client, "/courts/new")
    invalid = client.post(
        "/courts/new",
        data={
            "csrf_token": token,
            "court_date": "2026-08-20",
            "start_time": "9:00",
            "end_time": "21:00",
            "hall_name": "Taipei Sports Center",
            "location": "Taipei City",
            "google_place_id": "test-place",
            "latitude": "25.0",
            "longitude": "121.5",
            "court_id": "A1",
            "member_min": "4",
            "member_max": "8",
            "ordered_count": "2",
            "male_level_min": "6",
            "male_level_max": "12",
            "female_level_min": "4",
            "female_level_max": "10",
        },
    )
    assert invalid.status_code == 200
    assert invalid.data.count(b"data-delete-reserved-nickname") == 2
    with app.app_context():
        count = get_db().execute("SELECT COUNT(*) FROM courts").fetchone()[0]
    assert count == 0


def test_member_signup_can_create_and_manage_only_owned_courts(client, app):
    registered = signup(client, "alice")
    assert registered.status_code == 200
    assert b"/courts/new" in registered.data
    assert b'class="account-menu"' in registered.data
    assert b'action="/logout"' in registered.data
    assert b'href="/account/password"' in registered.data

    location = create_member_court(client, "Alice Court")
    guid = location.rsplit("/", 1)[-1]
    detail = client.get(location)
    assert f"/my-courts/{guid}/edit".encode() in detail.data
    assert f"/my-courts/{guid}/duplicate".encode() in detail.data
    assert f"/my-courts/{guid}/archive".encode() in detail.data
    assert b"/admin/courts/" not in detail.data

    token = csrf(client, location)
    duplicated = client.post(
        f"/my-courts/{guid}/duplicate",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert duplicated.status_code == 302
    assert duplicated.headers["Location"] == f"/courts/new?duplicate={guid}"
    copied_form = client.get(duplicated.headers["Location"])
    assert b'value="Alice Court"' in copied_form.data

    with app.app_context():
        user = get_db().execute(
            "SELECT id, password_hash FROM users WHERE username_key = 'alice'"
        ).fetchone()
        court = get_db().execute(
            "SELECT owner_id FROM courts WHERE guid = ?", (guid,)
        ).fetchone()
        assert user["password_hash"] != "strong-pass"
        assert check_password_hash(user["password_hash"], "strong-pass")
        assert not check_password_hash(user["password_hash"], "wrong-password")
        assert "$" in user["password_hash"]
        assert court["owner_id"] == user["id"]
        assert get_db().execute("SELECT COUNT(*) FROM courts").fetchone()[0] == 1

    token = csrf(client, "/my-courts")
    client.post("/logout", data={"csrf_token": token})
    assert signup(client, "bob").status_code == 200
    assert b"Alice Court" not in client.get("/my-courts").data
    assert client.get(f"/my-courts/{guid}/edit").status_code == 404
    token = csrf(client, "/my-courts")
    assert client.post(
        f"/my-courts/{guid}/archive", data={"csrf_token": token}
    ).status_code == 404


def test_member_login_rejects_bad_password_and_duplicate_username(client):
    signup(client, "alice")
    token = csrf(client, "/my-courts")
    client.post("/logout", data={"csrf_token": token})

    duplicate = signup(client, "Alice")
    assert "已被使用".encode() in duplicate.data

    token = csrf(client, "/login")
    denied = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "alice",
            "password": "wrong-password",
        },
        follow_redirects=True,
    )
    assert "錯誤".encode() in denied.data

    token = csrf(client, "/login")
    accepted = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "alice",
            "password": "strong-pass",
        },
        follow_redirects=True,
    )
    assert accepted.status_code == 200
    assert b"/courts/new" in accepted.data


def test_member_login_locks_after_too_many_failures_and_resets_after_expiry(
    client, app
):
    signup(client, "alice")
    token = csrf(client, "/my-courts")
    client.post("/logout", data={"csrf_token": token})

    for remaining in (4, 3, 2, 1):
        token = csrf(client, "/login")
        denied = client.post(
            "/login",
            data={
                "csrf_token": token,
                "username": "alice",
                "password": "wrong-password",
            },
            follow_redirects=True,
        )
        assert f"\u9084\u53ef\u5617\u8a66 {remaining} \u6b21".encode() in denied.data

    token = csrf(client, "/login")
    locked = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "alice",
            "password": "wrong-password",
        },
        follow_redirects=True,
    )
    assert "\u8acb\u5728 15 \u5206\u9418\u5f8c\u518d\u8a66".encode() in locked.data

    token = csrf(client, "/login")
    still_locked = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "alice",
            "password": "strong-pass",
        },
        follow_redirects=True,
    )
    assert "\u8acb\u5728 15 \u5206\u9418\u5f8c\u518d\u8a66".encode() in still_locked.data
    assert b"/courts/new" not in still_locked.data

    with app.app_context():
        db = get_db()
        db.execute("UPDATE login_attempts SET locked_until = '2000-01-01T00:00:00'")
        db.commit()

    token = csrf(client, "/login")
    accepted = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "alice",
            "password": "strong-pass",
        },
        follow_redirects=True,
    )
    assert b"/courts/new" in accepted.data
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM login_attempts").fetchone()[0] == 0


def test_admin_can_reset_member_failed_login_retries(client, app):
    signup(client, "alice")
    token = csrf(client, "/my-courts")
    client.post("/logout", data={"csrf_token": token})

    for _ in range(5):
        token = csrf(client, "/login")
        locked = client.post(
            "/login",
            data={
                "csrf_token": token,
                "username": "alice",
                "password": "wrong-password",
            },
            environ_base={"REMOTE_ADDR": "203.0.113.70"},
            follow_redirects=True,
        )
    assert "請在 15 分鐘後再試".encode() in locked.data

    with app.app_context():
        db = get_db()
        user_id = db.execute(
            "SELECT id FROM users WHERE username_key = 'alice'"
        ).fetchone()["id"]
        attempt = db.execute(
            "SELECT scope, username_key, failed_count FROM login_attempts"
        ).fetchone()
        assert tuple(attempt) == ("member", "alice", 5)

    admin_client = app.test_client()
    login(admin_client)
    users_page = admin_client.get("/admin/users")
    reset_url = f"/admin/users/{user_id}/reset-login-retries"
    assert reset_url.encode() in users_page.data
    assert "重設登入失敗次數".encode() in users_page.data
    assert b'<span class="action-count">5</span>' in users_page.data

    token = csrf(admin_client, "/admin/users")
    reset = admin_client.post(
        reset_url,
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert "登入失敗次數已重設".encode() in reset.data
    assert reset_url.encode() not in reset.data

    with app.app_context():
        assert (
            get_db()
            .execute(
                "SELECT COUNT(*) FROM login_attempts "
                "WHERE scope = 'member' AND username_key = 'alice'"
            )
            .fetchone()[0]
            == 0
        )

    token = csrf(client, "/login")
    signed_in = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "alice",
            "password": "strong-pass",
        },
        environ_base={"REMOTE_ADDR": "203.0.113.70"},
        follow_redirects=True,
    )
    assert b"/courts/new" in signed_in.data


def test_regular_login_redirects_admin_credentials_to_admin_page(client):
    token = csrf(client, "/login")
    response = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "manager",
            "password": "correct-horse",
        },
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"] == "/admin"
    dashboard = client.get(response.headers["Location"])
    assert dashboard.status_code == 200
    assert b'class="account-menu admin-account-menu"' in dashboard.data


def test_admin_lockout_is_enforced_on_unified_login(client):
    for _ in range(5):
        token = csrf(client, "/login")
        response = client.post(
            "/login",
            data={
                "csrf_token": token,
                "username": "manager",
                "password": "wrong-password",
            },
            follow_redirects=True,
        )
    assert "請在 15 分鐘後再試".encode() in response.data

    token = csrf(client, "/login")
    blocked = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "manager",
            "password": "correct-horse",
        },
        follow_redirects=False,
    )
    assert blocked.status_code == 200
    assert "請在 15 分鐘後再試".encode() in blocked.data
    assert b'class="account-menu admin-account-menu"' not in blocked.data


def test_member_can_change_password(client):
    signup(client, "alice")
    token = csrf(client, "/account/password")
    changed = client.post(
        "/account/password",
        data={
            "csrf_token": token,
            "current_password": "strong-pass",
            "new_password": "new-strong-pass",
            "confirm_password": "new-strong-pass",
        },
        follow_redirects=True,
    )
    assert changed.status_code == 200
    assert "密碼已變更".encode() in changed.data

    token = csrf(client, "/my-courts")
    client.post("/logout", data={"csrf_token": token})
    token = csrf(client, "/login")
    old_password = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "alice",
            "password": "strong-pass",
        },
        follow_redirects=True,
    )
    assert "錯誤".encode() in old_password.data

    token = csrf(client, "/login")
    new_password = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "alice",
            "password": "new-strong-pass",
        },
        follow_redirects=True,
    )
    assert b"/courts/new" in new_password.data


def test_admin_can_set_temporary_password_and_archive_account(client, app):
    signup(client, "alice")
    with app.app_context():
        user_id = get_db().execute(
            "SELECT id FROM users WHERE username_key = 'alice'"
        ).fetchone()["id"]

    token = csrf(client, "/my-courts")
    client.post("/logout", data={"csrf_token": token})
    login(client)
    users_page = client.get("/admin/users")
    assert b"alice" in users_page.data
    assert b'id="temp-password-dialog"' in users_page.data
    assert (
        f'data-temp-password-url="/admin/users/{user_id}/temporary-password"'.encode()
        in users_page.data
    )

    token = csrf(client, "/admin/users")
    client.post(
        f"/admin/users/{user_id}/temporary-password",
        data={"csrf_token": token, "temporary_password": "temporary-pass"},
    )
    token = csrf(client, "/admin/users")
    client.post("/admin/logout", data={"csrf_token": token})

    token = csrf(client, "/login")
    temporary_login = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "alice",
            "password": "temporary-pass",
        },
        follow_redirects=False,
    )
    assert temporary_login.headers["Location"].endswith("/account/password")
    assert client.get("/my-courts").headers["Location"].endswith(
        "/account/password"
    )

    token = csrf(client, "/account/password")
    client.post(
        "/account/password",
        data={
            "csrf_token": token,
            "current_password": "temporary-pass",
            "new_password": "permanent-pass",
            "confirm_password": "permanent-pass",
        },
    )
    token = csrf(client, "/my-courts")
    client.post("/logout", data={"csrf_token": token})

    login(client)
    token = csrf(client, "/admin/users")
    client.post(
        f"/admin/users/{user_id}/archive", data={"csrf_token": token}
    )
    token = csrf(client, "/admin/users")
    client.post("/admin/logout", data={"csrf_token": token})

    token = csrf(client, "/login")
    archived_login = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "alice",
            "password": "permanent-pass",
        },
        follow_redirects=True,
    )
    assert "已被封存".encode() in archived_login.data


def test_admin_can_ban_unban_and_invalidate_member_access(client, app):
    signup(client, "alice")
    with app.app_context():
        user_id = get_db().execute(
            "SELECT id FROM users WHERE username_key = 'alice'"
        ).fetchone()["id"]

    admin_client = app.test_client()
    login(admin_client)
    users_page = admin_client.get("/admin/users")
    assert f"/admin/users/{user_id}/ban".encode() in users_page.data

    token = csrf(admin_client, "/admin/users")
    banned = admin_client.post(
        f"/admin/users/{user_id}/ban",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert "會員帳號已停權".encode() in banned.data
    assert f"/admin/users/{user_id}/unban".encode() in banned.data

    invalidated = client.get("/my-courts", follow_redirects=False)
    assert invalidated.status_code == 302
    assert invalidated.headers["Location"].startswith("/login")

    token = csrf(client, "/login")
    denied = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "alice",
            "password": "strong-pass",
        },
        follow_redirects=True,
    )
    assert "此帳號已被停權".encode() in denied.data

    token = csrf(admin_client, "/admin/users")
    admin_client.post(
        f"/admin/users/{user_id}/unban",
        data={"csrf_token": token},
    )
    token = csrf(client, "/login")
    restored = client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "alice",
            "password": "strong-pass",
        },
        follow_redirects=True,
    )
    assert b"/courts/new" in restored.data

    with app.app_context():
        assert get_db().execute(
            "SELECT banned FROM users WHERE id = ?", (user_id,)
        ).fetchone()["banned"] == 0


def test_admin_can_delete_only_archived_account_and_preserve_courts(client, app):
    signup(client, "alice")
    court_location = create_member_court(client, "Orphaned Court")
    with app.app_context():
        user_id = get_db().execute(
            "SELECT id FROM users WHERE username_key = 'alice'"
        ).fetchone()["id"]

    token = csrf(client, "/my-courts")
    client.post("/logout", data={"csrf_token": token})
    login(client)

    users_page = client.get("/admin/users")
    delete_url = f"/admin/users/{user_id}/delete"
    assert delete_url.encode() not in users_page.data

    token = csrf(client, "/admin/users")
    rejected = client.post(
        delete_url,
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert "刪除帳號前必須先封存".encode() in rejected.data
    with app.app_context():
        assert get_db().execute(
            "SELECT 1 FROM users WHERE id = ?", (user_id,)
        ).fetchone()

    token = csrf(client, "/admin/users")
    archived = client.post(
        f"/admin/users/{user_id}/archive",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert delete_url.encode() in archived.data

    token = csrf(client, "/admin/users")
    deleted = client.post(
        delete_url,
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert "會員帳號已永久刪除".encode() in deleted.data
    with app.app_context():
        assert get_db().execute(
            "SELECT 1 FROM users WHERE id = ?", (user_id,)
        ).fetchone() is None
        court = get_db().execute(
            "SELECT owner_id FROM courts WHERE guid = ?",
            (court_location.rsplit("/", 1)[-1],),
        ).fetchone()
        assert court["owner_id"] is None
    orphaned_detail = client.get(court_location)
    assert orphaned_detail.status_code == 200
    assert b"alice" in orphaned_detail.data
    assert b"Orphaned Court" in client.get("/courts?q=alice").data


def test_member_can_upload_replace_and_remove_profile_picture(client, app):
    signup(client, "alice")
    token = csrf(client, "/account/profile")
    uploaded = client.post(
        "/account/profile",
        data={
            "csrf_token": token,
            "avatar": (io.BytesIO(b"\x89PNG\r\n\x1a\nfirst-image"), "avatar.png"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert uploaded.status_code == 200
    assert "個人照片已更新".encode() in uploaded.data

    with app.app_context():
        first_filename = get_db().execute(
            "SELECT avatar_filename FROM users WHERE username_key = 'alice'"
        ).fetchone()["avatar_filename"]
    first_path = app.config["AVATAR_FOLDER"] + "/" + first_filename
    assert first_filename.endswith(".png")
    assert client.get(f"/avatars/{first_filename}").data.startswith(b"\x89PNG")

    token = csrf(client, "/account/profile")
    client.post(
        "/account/profile",
        data={
            "csrf_token": token,
            "avatar": (io.BytesIO(b"\xff\xd8\xffsecond-image"), "avatar.jpg"),
        },
        content_type="multipart/form-data",
    )
    with app.app_context():
        second_filename = get_db().execute(
            "SELECT avatar_filename FROM users WHERE username_key = 'alice'"
        ).fetchone()["avatar_filename"]
    assert second_filename.endswith(".jpg")
    assert not Path(first_path).exists()

    token = csrf(client, "/account/profile")
    removed = client.post(
        "/account/profile/avatar/remove",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    assert "個人照片已移除".encode() in removed.data
    assert client.get(f"/avatars/{second_filename}").status_code == 404


def test_profile_rejects_non_image_upload(client):
    signup(client, "alice")
    token = csrf(client, "/account/profile")
    rejected = client.post(
        "/account/profile",
        data={
            "csrf_token": token,
            "avatar": (io.BytesIO(b"<script>alert(1)</script>"), "avatar.svg"),
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert "有效的 JPEG".encode() in rejected.data


def test_admin_duplicate_copies_information_without_participants(client, app):
    login(client)
    location = create_court(client)
    original_guid = location.rsplit("/", 1)[-1]

    token = csrf(client, location)
    client.post(
        f"{location}/join",
        data={"csrf_token": token, "username": "Alice", "pin": "123456"},
    )
    token = csrf(client, location)
    duplicated = client.post(
        f"/admin/courts/{original_guid}/duplicate",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert duplicated.status_code == 302
    assert (
        duplicated.headers["Location"]
        == f"/courts/new?duplicate={original_guid}"
    )

    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM courts").fetchone()[0] == 1

    copied_form = client.get(duplicated.headers["Location"])
    assert b'value="Taipei Sports Center"' in copied_form.data
    assert b'name="male_price" value="250"' in copied_form.data
    assert b'name="female_price" value="220"' in copied_form.data
    assert b"YONEX AS-30" in copied_form.data
    assert b'value="Coach Lin"' in copied_form.data
    assert b'value="Mina"' in copied_form.data
    assert b"Bring your own racket." in copied_form.data

    token = csrf(client, duplicated.headers["Location"])
    saved = client.post(
        duplicated.headers["Location"],
        data={
            "csrf_token": token,
            "court_date": "2026-08-20",
            "start_time": "19:00",
            "end_time": "21:00",
            "hall_name": "Taipei Sports Center",
            "location": "Taipei City",
            "google_place_id": "taipei-sports-center",
            "latitude": "25.0480",
            "longitude": "121.5160",
            "remark": "Bring your own racket.",
            "court_id": "A1",
            "male_price": "250",
            "female_price": "220",
            "shuttlecock_info": "YONEX AS-30",
            "reserved_names_visible": "1",
            "member_min": "4",
            "member_max": "8",
            "ordered_count": "2",
            "male_level_min": "6",
            "male_level_max": "12",
            "female_level_min": "4",
            "female_level_max": "10",
            "reserved_nickname": ["Coach Lin", "Mina"],
        },
        follow_redirects=False,
    )
    assert saved.status_code == 302
    duplicate_guid = saved.headers["Location"].rsplit("/", 1)[-1]
    assert duplicate_guid != original_guid

    with app.app_context():
        original = get_db().execute(
            "SELECT * FROM courts WHERE guid = ?", (original_guid,)
        ).fetchone()
        copied = get_db().execute(
            "SELECT * FROM courts WHERE guid = ?", (duplicate_guid,)
        ).fetchone()
        for field in (
            "event_name",
            "badminton_name",
            "court_date",
            "start_time",
            "end_time",
            "hall_name",
            "location",
            "court_id",
            "male_price",
            "female_price",
            "shuttlecock_info",
            "reserved_names_visible",
            "member_min",
            "member_max",
            "ordered_count",
            "male_level_min",
            "male_level_max",
            "female_level_min",
            "female_level_max",
            "remark",
            "owner_id",
        ):
            assert copied[field] == original[field]
        participant_count = get_db().execute(
            "SELECT COUNT(*) FROM participants WHERE court_id = ?",
            (copied["id"],),
        ).fetchone()[0]
        original_reserved = get_db().execute(
            "SELECT position, nickname FROM reserved_members "
            "WHERE court_id = ? ORDER BY position",
            (original["id"],),
        ).fetchall()
        copied_reserved = get_db().execute(
            "SELECT position, nickname FROM reserved_members "
            "WHERE court_id = ? ORDER BY position",
            (copied["id"],),
        ).fetchall()
        assert copied["archived"] == 0
        assert participant_count == 0
        assert [tuple(row) for row in copied_reserved] == [
            tuple(row) for row in original_reserved
        ]


def test_member_can_delete_account_without_deleting_published_courts(client, app):
    signup(client, "alice")
    court_location = create_member_court(client, "Preserved Court")
    token = csrf(client, "/account/profile")
    client.post(
        "/account/profile",
        data={
            "csrf_token": token,
            "avatar": (io.BytesIO(b"\x89PNG\r\n\x1a\navatar"), "avatar.png"),
        },
        content_type="multipart/form-data",
    )
    with app.app_context():
        avatar_filename = get_db().execute(
            "SELECT avatar_filename FROM users WHERE username_key = 'alice'"
        ).fetchone()["avatar_filename"]
    avatar_path = Path(app.config["AVATAR_FOLDER"]) / avatar_filename
    assert avatar_path.exists()

    token = csrf(client, "/account/profile")
    wrong = client.post(
        "/account/delete",
        data={"csrf_token": token, "current_password": "wrong-password"},
        follow_redirects=True,
    )
    assert "不正確".encode() in wrong.data
    with app.app_context():
        assert get_db().execute(
            "SELECT 1 FROM users WHERE username_key = 'alice'"
        ).fetchone()

    token = csrf(client, "/account/profile")
    deleted = client.post(
        "/account/delete",
        data={"csrf_token": token, "current_password": "strong-pass"},
        follow_redirects=True,
    )
    assert "帳號已刪除".encode() in deleted.data
    assert not avatar_path.exists()
    with app.app_context():
        assert get_db().execute(
            "SELECT 1 FROM users WHERE username_key = 'alice'"
        ).fetchone() is None
        preserved = get_db().execute(
            "SELECT owner_id FROM courts WHERE guid = ?",
            (court_location.rsplit("/", 1)[-1],),
        ).fetchone()
        assert preserved["owner_id"] is None
    preserved_detail = client.get(court_location)
    assert preserved_detail.status_code == 200
    assert b"alice" in preserved_detail.data
    assert client.get("/account/profile").status_code == 302


def test_last_login_time_and_ip_visibility(client, app):
    signup(client, "alice")
    token = csrf(client, "/my-courts")
    client.post("/logout", data={"csrf_token": token})

    token = csrf(client, "/login")
    client.post(
        "/login",
        data={
            "csrf_token": token,
            "username": "alice",
            "password": "strong-pass",
        },
        headers={"X-Forwarded-For": "198.51.100.99"},
        environ_overrides={"REMOTE_ADDR": "203.0.113.42"},
    )
    with app.app_context():
        audit = get_db().execute(
            "SELECT last_login_at, last_login_ip FROM users "
            "WHERE username_key = 'alice'"
        ).fetchone()
        assert audit["last_login_at"]
        assert audit["last_login_ip"] == "203.0.113.42"

    profile = client.get("/account/profile")
    assert "上次登入".encode() in profile.data
    assert audit["last_login_at"][:16].replace("T", " ").encode() in profile.data
    assert "IP 位址".encode() not in profile.data
    assert b"203.0.113.42" not in profile.data

    token = csrf(client, "/my-courts")
    client.post("/logout", data={"csrf_token": token})
    login(client)
    users_page = client.get("/admin/users")
    assert "上次登入".encode() in users_page.data
    assert "IP 位址".encode() in users_page.data
    assert b"203.0.113.42" in users_page.data


def test_member_can_choose_12_or_24_hour_datetime_format(client, app):
    login(client)
    court_location = create_court(client)
    with app.app_context():
        db = get_db()
        db.execute(
            "UPDATE users SET last_login_at = '2026-08-23T19:05:06' "
            "WHERE username_key = 'manager'"
        )
        db.commit()

    profile = client.get("/account/profile")
    assert "日期與時間格式".encode() in profile.data
    assert re.search(rb'<option value="24h"[^>]*selected', profile.data)
    assert b"2026-08-23 19:05" in profile.data

    updated = client.post(
        "/account/profile/preferences",
        data={
            "csrf_token": csrf(client, "/account/profile"),
            "time_format": "12h",
        },
        follow_redirects=True,
    )
    assert "個人偏好設定已儲存。".encode() in updated.data
    assert re.search(rb'<option value="12h"[^>]*selected', updated.data)
    assert b"2026-08-23 7:05 PM" in updated.data
    assert b"7:00 PM\xe2\x80\x939:00 PM" in client.get(court_location).data
    with app.app_context():
        assert get_db().execute(
            "SELECT time_format FROM users WHERE username_key = 'manager'"
        ).fetchone()["time_format"] == "12h"

    rejected = client.post(
        "/account/profile/preferences",
        data={
            "csrf_token": csrf(client, "/account/profile"),
            "time_format": "locale",
        },
        follow_redirects=True,
    )
    assert "請選擇有效的日期與時間格式。".encode() in rejected.data
    with app.app_context():
        assert get_db().execute(
            "SELECT time_format FROM users WHERE username_key = 'manager'"
        ).fetchone()["time_format"] == "12h"

    restored = client.post(
        "/account/profile/preferences",
        data={
            "csrf_token": csrf(client, "/account/profile"),
            "time_format": "24h",
        },
        follow_redirects=True,
    )
    assert b"2026-08-23 19:05" in restored.data
    assert b"19:00\xe2\x80\x9321:00" in client.get(court_location).data
