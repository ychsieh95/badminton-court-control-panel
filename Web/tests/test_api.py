import io
import re
from datetime import date, timedelta

import pytest
from PIL import Image

from app import create_app, get_db

API = "/api/v1"


@pytest.fixture()
def app(tmp_path):
    return create_app(
        {
            "TESTING": True,
            "DATABASE": str(tmp_path / "test.sqlite"),
            "SECRET_KEY": "test-secret",
            "ADMIN_USERNAME": "manager",
            "ADMIN_PASSWORD": "correct-horse",
            "TURNSTILE_SITE_KEY": "",
            "TURNSTILE_SECRET_KEY": "",
            "WEB_PUSH_PUBLIC_KEY": "",
            "WEB_PUSH_PRIVATE_KEY": "",
            "WEB_PUSH_SUBJECT": "",
            "FCM_SERVICE_ACCOUNT_FILE": "",
            "AVATAR_FOLDER": str(tmp_path / "avatars"),
            "COURT_MEDIA_FOLDER": str(tmp_path / "court-media"),
            "SOCIAL_THUMBNAIL_FOLDER": str(tmp_path / "social-thumbnails"),
            "DEFAULT_COUNTRY_CODE": "",
            "LOGIN_MAX_ATTEMPTS": 5,
            "LEAVE_MAX_ATTEMPTS": 5,
        }
    )


@pytest.fixture()
def client(app):
    return app.test_client()


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def signup(client, username="organizer", password="password123"):
    response = client.post(
        f"{API}/auth/signup",
        json={"username": username, "password": password, "device_name": "Pixel"},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["token"]


def admin_token(client):
    response = client.post(
        f"{API}/auth/login", json={"username": "manager", "password": "correct-horse"}
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()["token"]


def court_body(**overrides):
    body = {
        "event_name": "Friday Night",
        "court_date": (date.today() + timedelta(days=7)).isoformat(),
        "start_time": "19:00",
        "end_time": "21:00",
        "hall_name": "North Hall",
        "location": "1 Main Street",
        "court_id": "A1",
        "member_min": 1,
        "member_max": 2,
        "ordered_count": 0,
    }
    body.update(overrides)
    return body


def create_court(client, token, **overrides):
    response = client.post(f"{API}/courts", json=court_body(**overrides), headers=auth(token))
    assert response.status_code == 201, response.get_json()
    return response.get_json()["court"]


def test_meta_and_json_errors(client):
    meta = client.get(f"{API}/meta")
    assert meta.status_code == 200
    assert meta.get_json()["api_version"] == 1
    assert meta.headers["Cache-Control"] == "no-store"

    missing = client.get(f"{API}/nothing-here")
    assert missing.status_code == 404
    assert missing.get_json()["error"]["code"] == "not_found"

    wrong_method = client.delete(f"{API}/meta")
    assert wrong_method.status_code == 405
    assert wrong_method.get_json()["error"]["code"] == "method_not_allowed"

    not_json = client.post(
        f"{API}/auth/login", data="nope", content_type="application/json"
    )
    assert not_json.status_code == 400


def test_version_and_status(app, client):
    version = client.get(f"{API}/version")
    assert version.status_code == 200
    body = version.get_json()
    assert body["api_version"] == 1
    assert re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", body["app_version"])
    assert body["last_updated"] == body["app_version"]

    app.config["APP_VERSION"] = "1.2.3"
    status = client.get(f"{API}/status")
    assert status.status_code == 200
    data = status.get_json()
    assert data["status"] == "ok"
    assert data["checks"] == {"database": "ok"}
    assert data["app_version"] == "1.2.3"
    assert data["uptime_seconds"] >= 0
    assert status.headers["Cache-Control"] == "no-store"


def test_signup_login_logout_and_token_lifecycle(client):
    token = signup(client)
    me = client.get(f"{API}/me", headers=auth(token))
    assert me.status_code == 200
    assert me.get_json()["user"]["username"] == "organizer"
    assert me.get_json()["user"]["must_change_password"] is False

    duplicate = client.post(
        f"{API}/auth/signup", json={"username": "ORGANIZER", "password": "password123"}
    )
    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"]["code"] == "username_taken"

    bad = client.post(
        f"{API}/auth/login", json={"username": "organizer", "password": "wrong-pass"}
    )
    assert bad.status_code == 401
    assert bad.get_json()["error"]["code"] == "invalid_credentials"
    assert "4" in bad.get_json()["error"]["message"]

    second = client.post(
        f"{API}/auth/login", json={"username": "organizer", "password": "password123"}
    ).get_json()["token"]
    tokens = client.get(f"{API}/auth/tokens", headers=auth(second)).get_json()["tokens"]
    assert len(tokens) == 2
    assert [item["current"] for item in tokens].count(True) == 1

    assert client.post(f"{API}/auth/logout", headers=auth(second)).status_code == 204
    rejected = client.get(f"{API}/me", headers=auth(second))
    assert rejected.status_code == 401
    assert rejected.get_json()["error"]["code"] == "invalid_token"
    assert "invalid_token" in rejected.headers["WWW-Authenticate"]
    assert client.get(f"{API}/me", headers=auth(token)).status_code == 200

    assert client.get(f"{API}/me").status_code == 401


def test_api_ignores_browser_session_cookie(client):
    page = client.get("/login")
    csrf = re.search(rb'name="csrf_token" value="([^"]+)"', page.data).group(1).decode()
    client.post(
        "/login",
        data={"csrf_token": csrf, "username": "manager", "password": "correct-horse"},
    )
    assert client.get("/admin").status_code == 200
    assert client.get(f"{API}/me").status_code == 401


def test_localized_error_messages(client):
    zh = client.post(
        f"{API}/auth/login",
        json={"username": "nobody", "password": "whatever1"},
        headers={"Accept-Language": "zh-TW,zh;q=0.9"},
    )
    en = client.post(
        f"{API}/auth/login?lang=en-us", json={"username": "nobody", "password": "whatever1"}
    )
    assert zh.get_json()["error"]["message"] != en.get_json()["error"]["message"]
    assert re.search(r"[一-鿿]", zh.get_json()["error"]["message"])


def test_create_validate_list_and_update_court(client):
    token = signup(client)
    invalid = client.post(
        f"{API}/courts",
        json=court_body(end_time="18:00", member_max=0),
        headers=auth(token),
    )
    assert invalid.status_code == 422
    fields = invalid.get_json()["error"]["fields"]
    assert "end_time" in fields and "member_max" in fields

    court = create_court(
        client, token, ordered_count=1, reserved_nicknames=["Coach"], save_location=True
    )
    assert court["status"] == "open"
    assert court["viewer"]["can_manage"] is True
    assert court["reserved_nicknames"] == ["Coach"]
    assert court["members"] == {
        "min": 1, "max": 2, "reserved": 1, "signed_up": 0, "waiting": 0,
        "confirmed_total": 1,
    }

    listed = client.get(f"{API}/courts?q=North").get_json()
    assert [item["guid"] for item in listed["courts"]] == [court["guid"]]
    assert client.get(f"{API}/courts?q=nomatch").get_json()["courts"] == []
    mine = client.get(f"{API}/me/courts", headers=auth(token)).get_json()
    assert mine["pagination"]["total"] == 1
    saved = client.get(f"{API}/me/saved-locations", headers=auth(token)).get_json()
    assert saved["saved_locations"][0]["hall_name"] == "North Hall"

    public = client.get(f"{API}/courts/{court['guid']}").get_json()["court"]
    assert public["viewer"]["can_manage"] is False
    assert "form_values" not in public
    assert public["reserved_members"] == [{"position": 0, "nickname": "Coach"}]

    updated = client.patch(
        f"{API}/courts/{court['guid']}",
        json={"hall_name": "South Hall", "reserved_names_visible": False},
        headers=auth(token),
    )
    assert updated.status_code == 200
    body = updated.get_json()["court"]
    assert body["hall_name"] == "South Hall"
    assert body["event_name"] == "Friday Night"
    assert body["reserved_nicknames"] == ["Coach"]
    hidden = client.get(f"{API}/courts/{court['guid']}").get_json()["court"]
    assert hidden["reserved_members"] == []

    other = signup(client, "stranger")
    assert client.patch(
        f"{API}/courts/{court['guid']}", json={"hall_name": "X"}, headers=auth(other)
    ).status_code == 404
    assert client.delete(
        f"{API}/courts/{court['guid']}", headers=auth(other)
    ).status_code == 404

    archived = client.post(f"{API}/courts/{court['guid']}/archive", headers=auth(token))
    assert archived.get_json()["court"]["status"] == "archived"
    assert client.get(f"{API}/courts").get_json()["courts"] == []
    client.post(f"{API}/courts/{court['guid']}/restore", headers=auth(token))
    assert client.delete(f"{API}/courts/{court['guid']}", headers=auth(token)).status_code == 204
    assert client.get(f"{API}/courts/{court['guid']}").status_code == 404


def test_create_court_with_multipart_media(client):
    token = signup(client)
    image = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(image, "PNG")
    import json

    response = client.post(
        f"{API}/courts",
        data={
            "court": json.dumps(court_body()),
            "media": (io.BytesIO(image.getvalue()), "cover.png"),
        },
        headers=auth(token),
        content_type="multipart/form-data",
    )
    assert response.status_code == 201, response.get_json()
    court = response.get_json()["court"]
    assert len(court["media"]) == 1
    assert court["cover_image_url"].startswith("http")

    removed = client.patch(
        f"{API}/courts/{court['guid']}",
        json={"remove_media_ids": [court["media"][0]["id"]]},
        headers=auth(token),
    )
    assert removed.get_json()["court"]["media"] == []


def test_join_leave_waitlist_and_leave_throttling(client):
    token = signup(client)
    guid = create_court(client, token, member_max=1)["guid"]

    joined = client.post(f"{API}/courts/{guid}/join", json={"username": "Amy", "pin": "123456"})
    assert joined.status_code == 201
    assert joined.get_json()["waitlisted"] is False

    duplicate = client.post(f"{API}/courts/{guid}/join", json={"username": "amy", "pin": "123456"})
    assert duplicate.status_code == 409
    assert duplicate.get_json()["error"]["code"] == "duplicate_username"

    bad_pin = client.post(f"{API}/courts/{guid}/join", json={"username": "Ben", "pin": "12"})
    assert bad_pin.get_json()["error"]["code"] == "invalid_pin"

    waiting = client.post(f"{API}/courts/{guid}/join", json={"username": "Ben", "pin": "654321"})
    assert waiting.get_json()["waitlisted"] is True
    court = waiting.get_json()["court"]
    assert [p["username"] for p in court["participants"]] == ["Amy"]
    assert [p["username"] for p in court["waiting_participants"]] == ["Ben"]
    assert "roll_called" not in court["participants"][0]

    wrong = client.post(f"{API}/courts/{guid}/leave", json={"username": "Amy", "pin": "000000"})
    assert wrong.status_code == 403
    assert wrong.get_json()["error"]["code"] == "leave_failed"

    left = client.post(f"{API}/courts/{guid}/leave", json={"username": "Amy", "pin": "123456"})
    assert left.status_code == 200
    court = left.get_json()["court"]
    assert [p["username"] for p in court["participants"]] == ["Ben"]
    assert court["waiting_participants"] == []
    assert [event["event_type"] for event in court["participation_history"]] == [
        "leave", "join", "join",
    ]
    assert "ip_address" not in court["participation_history"][0]

    for _ in range(5):
        client.post(f"{API}/courts/{guid}/leave", json={"username": "Ben", "pin": "000000"})
    locked = client.post(f"{API}/courts/{guid}/leave", json={"username": "Ben", "pin": "654321"})
    assert locked.status_code == 429
    assert locked.get_json()["error"]["code"] == "leave_locked"


def test_roll_clearing_flow(client):
    token = signup(client)
    guid = create_court(client, token, ordered_count=1, reserved_nicknames=["Coach"])["guid"]
    client.post(f"{API}/courts/{guid}/join", json={"username": "Amy", "pin": "123456"})

    early = client.patch(f"{API}/courts/{guid}/roll-clearing", json={}, headers=auth(token))
    assert early.status_code == 409
    assert early.get_json()["error"]["code"] == "court_not_read_only"

    started = client.post(f"{API}/courts/{guid}/roll-clearing", headers=auth(token))
    court = started.get_json()["court"]
    assert court["status"] == "read_only"
    participant_id = court["participants"][0]["id"]
    reserved_id = court["reserved_members"][0]["id"]

    blocked = client.post(f"{API}/courts/{guid}/join", json={"username": "Ben", "pin": "123456"})
    assert blocked.get_json()["error"]["code"] == "court_read_only"
    assert client.patch(
        f"{API}/courts/{guid}", json={"hall_name": "X"}, headers=auth(token)
    ).status_code == 409

    saved = client.patch(
        f"{API}/courts/{guid}/roll-clearing",
        json={
            "participants": [{"id": participant_id, "roll_called": True}],
            "reserved_members": [{"id": reserved_id, "cleared": True}],
        },
        headers=auth(token),
    ).get_json()["court"]
    assert saved["participants"][0]["roll_called"] is True
    assert saved["participants"][0]["cleared"] is False
    assert saved["reserved_members"][0]["roll_called"] is False
    assert saved["reserved_members"][0]["cleared"] is True

    # A partial update keeps flags that were not sent.
    again = client.patch(
        f"{API}/courts/{guid}/roll-clearing",
        json={"participants": [{"id": participant_id, "cleared": True}]},
        headers=auth(token),
    ).get_json()["court"]
    assert again["participants"][0]["roll_called"] is True
    assert again["participants"][0]["cleared"] is True
    assert again["reserved_members"][0]["cleared"] is True

    unknown = client.patch(
        f"{API}/courts/{guid}/roll-clearing",
        json={"participants": [{"id": 9999, "cleared": True}]},
        headers=auth(token),
    )
    assert unknown.get_json()["error"]["code"] == "unknown_member"

    other = signup(client, "stranger")
    assert client.post(
        f"{API}/courts/{guid}/roll-clearing", headers=auth(other)
    ).status_code == 404

    ended = client.delete(f"{API}/courts/{guid}/roll-clearing", headers=auth(token))
    assert ended.get_json()["court"]["roll_clearing_locked"] is False


def test_admin_participant_moderation_and_user_management(client):
    admin = admin_token(client)
    member = signup(client, "player")
    guid = create_court(client, member)["guid"]
    client.post(f"{API}/courts/{guid}/join", json={"username": "Amy", "pin": "123456"})
    court = client.get(f"{API}/courts/{guid}", headers=auth(admin)).get_json()["court"]
    assert court["viewer"]["is_admin"] is True
    assert "ip_address" in court["participation_history"][0]
    participant_id = court["participants"][0]["id"]

    assert client.patch(
        f"{API}/courts/{guid}/participants/{participant_id}",
        json={"username": "Amelia"},
        headers=auth(member),
    ).status_code == 403
    renamed = client.patch(
        f"{API}/courts/{guid}/participants/{participant_id}",
        json={"username": "Amelia", "pin": "222222"},
        headers=auth(admin),
    ).get_json()["court"]
    assert renamed["participants"][0]["username"] == "Amelia"
    left = client.post(f"{API}/courts/{guid}/leave", json={"username": "Amelia", "pin": "222222"})
    assert left.status_code == 200
    assert client.delete(
        f"{API}/courts/{guid}/participants/{participant_id}", headers=auth(admin)
    ).status_code == 404

    assert client.get(f"{API}/admin/users", headers=auth(member)).status_code == 403
    users = client.get(f"{API}/admin/users", headers=auth(admin)).get_json()["users"]
    player = next(user for user in users if user["username"] == "player")
    assert player["court_count"] == 1

    assert client.delete(f"{API}/admin/users/{player['id']}", headers=auth(admin)).status_code == 409
    archived = client.post(f"{API}/admin/users/{player['id']}/archive", headers=auth(admin))
    assert archived.get_json()["user"]["archived"] is True
    assert client.get(f"{API}/me", headers=auth(member)).status_code == 401
    client.post(f"{API}/admin/users/{player['id']}/restore", headers=auth(admin))

    promoted = client.put(
        f"{API}/admin/users/{player['id']}/role", json={"role": "sub_admin"}, headers=auth(admin)
    )
    assert promoted.get_json()["user"]["role"] == "sub_admin"
    assert client.get(f"{API}/admin/courts", headers=auth(member)).status_code == 200
    assert client.get(f"{API}/admin/users", headers=auth(member)).status_code == 403

    settings = client.patch(
        f"{API}/admin/settings", json={"homepage_court_limit": 5}, headers=auth(admin)
    )
    assert settings.get_json()["settings"]["homepage_court_limit"] == 5
    assert client.patch(
        f"{API}/admin/settings", json={"homepage_court_limit": 500}, headers=auth(admin)
    ).status_code == 400


def test_temporary_password_restricts_api_until_changed(client):
    admin = admin_token(client)
    member = signup(client, "player")
    user_id = client.get(f"{API}/me", headers=auth(member)).get_json()["user"]["id"]

    client.post(
        f"{API}/admin/users/{user_id}/temporary-password",
        json={"temporary_password": "temporary1"},
        headers=auth(admin),
    )
    # Setting a temporary password signs out every app device.
    assert client.get(f"{API}/me", headers=auth(member)).status_code == 401

    token = client.post(
        f"{API}/auth/login", json={"username": "player", "password": "temporary1"}
    ).get_json()["token"]
    assert client.get(f"{API}/me", headers=auth(token)).get_json()["user"]["must_change_password"]
    blocked = client.get(f"{API}/me/courts", headers=auth(token))
    assert blocked.status_code == 403
    assert blocked.get_json()["error"]["code"] == "temporary_password_required"

    changed = client.post(
        f"{API}/me/password",
        json={"current_password": "temporary1", "new_password": "brand-new-pass"},
        headers=auth(token),
    )
    assert changed.status_code == 200
    assert changed.get_json()["user"]["must_change_password"] is False
    assert client.get(f"{API}/me/courts", headers=auth(token)).status_code == 200


def test_password_change_revokes_other_tokens_and_account_deletion(client, app):
    first = signup(client, "player")
    second = client.post(
        f"{API}/auth/login", json={"username": "player", "password": "password123"}
    ).get_json()["token"]
    client.post(
        f"{API}/me/password",
        json={"current_password": "password123", "new_password": "another-pass"},
        headers=auth(first),
    )
    assert client.get(f"{API}/me", headers=auth(first)).status_code == 200
    assert client.get(f"{API}/me", headers=auth(second)).status_code == 401

    assert client.patch(
        f"{API}/me", json={"time_format": "12h"}, headers=auth(first)
    ).get_json()["user"]["time_format"] == "12h"

    wrong = client.delete(f"{API}/me", json={"current_password": "nope"}, headers=auth(first))
    assert wrong.status_code == 403
    assert client.delete(
        f"{API}/me", json={"current_password": "another-pass"}, headers=auth(first)
    ).status_code == 204
    with app.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM api_tokens").fetchone()[0] == 0


def test_contact_message_via_api(client):
    invalid = client.post(f"{API}/contact", json={"sender_name": "Amy"})
    assert invalid.status_code == 422
    assert "subject" in invalid.get_json()["error"]["fields"]
    sent = client.post(
        f"{API}/contact",
        json={"sender_name": "Amy", "subject": "Hi", "message": "Hello there"},
    )
    assert sent.status_code == 201
    admin = admin_token(client)
    messages = client.get(f"{API}/admin/messages", headers=auth(admin)).get_json()
    assert messages["unread_count"] == 1
    message_id = messages["messages"][0]["id"]
    read = client.patch(
        f"{API}/admin/messages/{message_id}", json={"read": True}, headers=auth(admin)
    )
    assert read.get_json()["message"]["read_at"]


class FakeFcm:
    """Stands in for fcm.FcmClient; records sends and can reject chosen tokens."""

    def __init__(self, rejected=None):
        self.sent = []
        self.rejected = rejected or {}

    def send(self, token, data, *, collapse_key, ttl_seconds=86_400):
        from fcm import FcmError

        if token in self.rejected:
            raise FcmError(*self.rejected[token])
        self.sent.append({"token": token, "data": data, "collapse_key": collapse_key})


PHONE = "phone-token:" + "a" * 140
TABLET = "tablet-token:" + "b" * 140


def fcm_rows(app):
    with app.app_context():
        return [
            tuple(row)
            for row in get_db().execute(
                "SELECT court_id, token, language FROM fcm_subscriptions ORDER BY id"
            )
        ]


def test_fcm_push_unavailable_without_service_account(client):
    assert client.get(f"{API}/meta").get_json()["push"] == {"fcm": False}
    guid = create_court(client, signup(client))["guid"]

    response = client.put(f"{API}/courts/{guid}/push", json={"token": PHONE})
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "push_unavailable"

    status = client.post(f"{API}/courts/{guid}/push/status", json={"token": PHONE})
    assert status.get_json() == {"subscribed": False}


def test_fcm_subscribe_notify_and_unsubscribe(app, client):
    fake = FakeFcm()
    app.extensions["fcm_client"] = fake
    assert client.get(f"{API}/meta").get_json()["push"] == {"fcm": True}
    token = signup(client)
    guid = create_court(client, token, event_name="Friday Night")["guid"]

    bad = client.put(f"{API}/courts/{guid}/push", json={"token": "short"})
    assert bad.status_code == 400
    assert bad.get_json()["error"]["fields"] == {"token": "invalid"}
    assert client.put(f"{API}/courts/missing/push", json={"token": PHONE}).status_code == 404

    subscribed = client.put(
        f"{API}/courts/{guid}/push",
        json={"token": PHONE},
        headers={"Accept-Language": "zh-TW"},
    )
    assert subscribed.get_json() == {"subscribed": True}
    # Subscribing twice keeps one row.
    client.put(f"{API}/courts/{guid}/push", json={"token": PHONE}, headers={"Accept-Language": "zh-TW"})
    assert len(fcm_rows(app)) == 1
    assert client.post(f"{API}/courts/{guid}/push/status", json={"token": PHONE}).get_json() == {"subscribed": True}

    client.post(f"{API}/courts/{guid}/join", json={"username": "Amy", "pin": "123456"})
    assert len(fake.sent) == 1
    message = fake.sent[0]
    assert message["token"] == PHONE
    assert message["collapse_key"] == f"court-{guid}"
    assert message["data"]["type"] == "court_changed"
    assert message["data"]["guid"] == guid
    assert message["data"]["change"] == "members_changed"
    assert message["data"]["title"] == "Friday Night 已更新"
    assert message["data"]["url"].endswith(f"/{guid}")
    assert all(isinstance(value, str) for value in message["data"].values())

    unsubscribed = client.delete(f"{API}/courts/{guid}/push", json={"token": PHONE})
    assert unsubscribed.get_json() == {"subscribed": False}
    client.post(f"{API}/courts/{guid}/join", json={"username": "Ben", "pin": "123456"})
    assert len(fake.sent) == 1


def test_fcm_drops_stale_tokens_and_notifies_on_delete(app, client):
    fake = FakeFcm(rejected={TABLET: (404, "UNREGISTERED")})
    app.extensions["fcm_client"] = fake
    token = signup(client)
    guid = create_court(client, token)["guid"]
    for device in (PHONE, TABLET):
        client.put(f"{API}/courts/{guid}/push", json={"token": device})

    client.post(f"{API}/courts/{guid}/join", json={"username": "Amy", "pin": "123456"})
    assert [m["token"] for m in fake.sent] == [PHONE]
    assert [row[1] for row in fcm_rows(app)] == [PHONE]

    # A transient failure keeps the token.
    fake.rejected[PHONE] = (503, "UNAVAILABLE")
    client.post(f"{API}/courts/{guid}/join", json={"username": "Ben", "pin": "123456"})
    assert [row[1] for row in fcm_rows(app)] == [PHONE]
    del fake.rejected[PHONE]

    assert client.delete(f"{API}/courts/{guid}", headers=auth(token)).status_code == 204
    assert fake.sent[-1]["data"]["change"] == "deleted"
    assert fcm_rows(app) == []


def test_fcm_token_rotation_moves_subscriptions(app, client):
    app.extensions["fcm_client"] = FakeFcm()
    token = signup(client)
    first = create_court(client, token)["guid"]
    second = create_court(client, token, event_name="Saturday")["guid"]
    client.put(f"{API}/courts/{first}/push", json={"token": PHONE})
    client.put(f"{API}/courts/{second}/push", json={"token": PHONE})
    # The new token already follows one court; that row must not be duplicated.
    client.put(f"{API}/courts/{second}/push", json={"token": TABLET})

    moved = client.put(f"{API}/push/token", json={"previous_token": PHONE, "token": TABLET})
    assert moved.get_json() == {"subscriptions": 2}
    assert sorted(row[1] for row in fcm_rows(app)) == [TABLET, TABLET]
    assert client.post(f"{API}/courts/{first}/push/status", json={"token": TABLET}).get_json() == {"subscribed": True}

    invalid = client.put(f"{API}/push/token", json={"previous_token": "x", "token": TABLET})
    assert invalid.status_code == 400


def test_fcm_error_classification():
    from fcm import FcmError

    assert FcmError(404, "NOT_FOUND").stale_token
    assert FcmError(400, "UNREGISTERED").stale_token
    assert FcmError(403, "SENDER_ID_MISMATCH").stale_token
    assert not FcmError(400, "INVALID_ARGUMENT").stale_token
    assert not FcmError(503, "UNAVAILABLE").stale_token


OWNER_PHONE = "owner-phone:" + "c" * 140


def test_owner_devices_get_change_notifications(app, client):
    fake = FakeFcm()
    app.extensions["fcm_client"] = fake
    owner = signup(client)
    assert client.put(f"{API}/me/push-token", json={"token": "short"}, headers=auth(owner)).status_code == 400
    assert client.put(f"{API}/me/push-token", json={"token": OWNER_PHONE}).status_code == 401
    registered = client.put(
        f"{API}/me/push-token",
        json={"token": OWNER_PHONE},
        headers={**auth(owner), "Accept-Language": "zh-TW"},
    )
    assert registered.get_json() == {"registered": True}

    court = create_court(client, owner, event_name="Friday Night")
    guid = court["guid"]
    assert court["owner_notifications"] is True
    # The organizer's own changes are not echoed back to them.
    assert fake.sent == []

    client.post(f"{API}/courts/{guid}/join", json={"username": "Amy", "pin": "123456"})
    assert len(fake.sent) == 1
    sent = fake.sent[0]
    assert sent["token"] == OWNER_PHONE
    assert sent["data"]["audience"] == "owner"
    assert sent["data"]["change"] == "members_changed"
    assert sent["data"]["title"] == "你的場次「Friday Night」有異動"

    # A device that also follows the court gets one message, worded for the owner.
    client.put(f"{API}/courts/{guid}/push", json={"token": OWNER_PHONE})
    client.put(f"{API}/courts/{guid}/push", json={"token": PHONE})
    client.post(f"{API}/courts/{guid}/leave", json={"username": "Amy", "pin": "123456"})
    latest = fake.sent[1:]
    assert sorted((m["token"], m["data"]["audience"]) for m in latest) == [
        (OWNER_PHONE, "owner"),
        (PHONE, "subscription"),
    ]

    # Admin moderation reaches the owner too.
    admin = admin_token(client)
    fake.sent.clear()
    client.post(f"{API}/courts/{guid}/archive", headers=auth(admin))
    assert {m["token"] for m in fake.sent} == {OWNER_PHONE, PHONE}

    # Turning owner notifications off in the court settings stops them.
    client.post(f"{API}/courts/{guid}/restore", headers=auth(admin))
    bad = client.patch(f"{API}/courts/{guid}", json={"owner_notifications": "no"}, headers=auth(owner))
    assert bad.status_code == 400
    updated = client.patch(f"{API}/courts/{guid}", json={"owner_notifications": False}, headers=auth(owner))
    assert updated.get_json()["court"]["owner_notifications"] is False
    client.delete(f"{API}/courts/{guid}/push", json={"token": OWNER_PHONE})
    fake.sent.clear()
    client.post(f"{API}/courts/{guid}/join", json={"username": "Ben", "pin": "123456"})
    assert [m["token"] for m in fake.sent] == [PHONE]

    # An admin edit cannot change the organizer's preference, and admins do
    # not see it.
    admin_view = client.patch(
        f"{API}/courts/{guid}", json={"owner_notifications": True}, headers=auth(admin)
    ).get_json()["court"]
    assert "owner_notifications" not in admin_view
    owner_view = client.get(f"{API}/courts/{guid}", headers=auth(owner)).get_json()["court"]
    assert owner_view["owner_notifications"] is False

    # Created with alerts off.
    quiet = create_court(client, owner, owner_notifications=False)
    assert quiet["owner_notifications"] is False


def test_owner_push_token_follows_sign_in_and_rotation(app, client):
    fake = FakeFcm()
    app.extensions["fcm_client"] = fake
    owner = signup(client)
    guid = create_court(client, owner)["guid"]
    client.put(f"{API}/me/push-token", json={"token": OWNER_PHONE}, headers=auth(owner))

    # The token rotates; owner alerts follow it.
    client.put(f"{API}/push/token", json={"previous_token": OWNER_PHONE, "token": TABLET})
    client.post(f"{API}/courts/{guid}/join", json={"username": "Amy", "pin": "123456"})
    assert [m["token"] for m in fake.sent] == [TABLET]

    # Another account signs in on the same device: the token moves to it.
    other = signup(client, username="someone")
    client.put(f"{API}/me/push-token", json={"token": TABLET}, headers=auth(other))
    fake.sent.clear()
    client.post(f"{API}/courts/{guid}/join", json={"username": "Ben", "pin": "123456"})
    assert fake.sent == []

    # Unregistering and signing out both stop alerts.
    client.put(f"{API}/me/push-token", json={"token": OWNER_PHONE}, headers=auth(owner))
    assert client.delete(f"{API}/me/push-token", headers=auth(owner)).get_json() == {"registered": False}
    client.post(f"{API}/courts/{guid}/leave", json={"username": "Ben", "pin": "123456"})
    assert fake.sent == []
    client.put(f"{API}/me/push-token", json={"token": OWNER_PHONE}, headers=auth(owner))
    client.post(f"{API}/auth/logout", headers=auth(owner))
    client.post(f"{API}/courts/{guid}/leave", json={"username": "Amy", "pin": "123456"})
    assert fake.sent == []


def test_stale_owner_token_is_unlinked(app, client):
    fake = FakeFcm(rejected={OWNER_PHONE: (404, "UNREGISTERED")})
    app.extensions["fcm_client"] = fake
    owner = signup(client)
    guid = create_court(client, owner)["guid"]
    client.put(f"{API}/me/push-token", json={"token": OWNER_PHONE}, headers=auth(owner))
    client.post(f"{API}/courts/{guid}/join", json={"username": "Amy", "pin": "123456"})
    with app.app_context():
        assert get_db().execute(
            "SELECT COUNT(*) FROM api_tokens WHERE fcm_token IS NOT NULL"
        ).fetchone()[0] == 0


def test_contact_report_goes_to_telegram_with_app_details(app, client, monkeypatch):
    import json as json_module

    import app as app_module

    app.config.update(
        CONTACT_TELEGRAM_BOT_TOKEN="123456789:abcdefghijklmnopqrstuvwxyzABCDE",
        CONTACT_TELEGRAM_CHAT_ID="-1001234567890",
        CONTACT_DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/123456/abcdefghijklmnopqrstuvwxyz",
    )
    sent = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def read(self, _limit):
            return b'{"ok": true}'

    def fake_urlopen(request, timeout):
        sent.append(request)
        return Response()

    monkeypatch.setattr(app_module, "urlopen", fake_urlopen)
    owner = signup(client, username="reporter")
    response = client.post(
        f"{API}/contact",
        json={
            "sender_name": "Amy",
            "reply_contact": "amy@example.test",
            "subject": "Crash on join",
            "message": "The app closed.",
            "client": {
                "platform": "android",
                "app_version": "1.0.0 (1)",
                "os_version": "15 (API 35)",
                "device_model": "Google Pixel 8\n",
                "ignored": "x",
            },
        },
        headers={**auth(owner), "Accept-Language": "zh-TW"},
    )
    assert response.status_code == 201
    # Telegram does not need the admin switch; Discord does.
    assert len(sent) == 1
    assert "api.telegram.org" in sent[0].full_url
    text = json_module.loads(sent[0].data)["text"]
    assert "Crash on join" in text
    assert "The app closed." in text
    assert "amy@example.test" in text
    assert "reporter (#" in text
    assert "Android app / App 1.0.0 (1)" in text
    assert "Google Pixel 8 · Android 15 (API 35)" in text
    assert "zh-tw" in text
    assert "ignored" not in text

    admin = admin_token(client)
    client.patch(f"{API}/admin/settings", json={"contact_notifications_enabled": True}, headers=auth(admin))
    sent.clear()
    client.post(f"{API}/contact", json={"sender_name": "Ben", "subject": "Hi", "message": "Hello"})
    assert sorted("telegram" if "telegram" in r.full_url else "discord" for r in sent) == ["discord", "telegram"]
    assert "Guest / 訪客" in json_module.loads(sent[0].data).get("text", json_module.loads(sent[0].data).get("content", ""))


def test_contact_notification_switch_needs_discord(app, client):
    app.config.update(
        CONTACT_TELEGRAM_BOT_TOKEN="123456789:abcdefghijklmnopqrstuvwxyzABCDE",
        CONTACT_TELEGRAM_CHAT_ID="-1001234567890",
    )
    admin = admin_token(client)
    response = client.patch(
        f"{API}/admin/settings", json={"contact_notifications_enabled": True}, headers=auth(admin)
    )
    assert response.status_code == 409


def test_android_app_page(app, client):
    page = client.get("/android", headers={"Accept-Language": "en-US"})
    assert page.status_code == 200
    assert b"footer-android-link" in page.data
    assert b"/contact#contact-form" in page.data
    app.config["ANDROID_APP_URL"] = "https://play.google.com/store/apps/details?id=example"
    page = client.get("/android")
    assert b'href="https://play.google.com/store/apps/details?id=example"' in page.data
    app.config["ANDROID_APP_URL"] = "javascript:alert(1)"
    assert b"javascript:" not in client.get("/android").data
