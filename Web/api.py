"""JSON API (v1) for Badminton Court Control Panel.

Every endpoint lives under ``/api/v1`` and speaks JSON. Clients authenticate
with a bearer token from ``POST /api/v1/auth/login`` (or ``/auth/signup``)::

    Authorization: Bearer bccp_...

API requests never read the browser session cookie, so they need no CSRF
token. Business rules are shared with the HTML views through the service
functions in ``app.py``; this module only parses input and shapes output.

Errors use one envelope::

    {"error": {"code": "court_full", "message": "...", "fields": {...}}}

``message`` is localized by ``?lang=zh-tw|en-us`` or ``Accept-Language``.
See ``API.md`` for the endpoint reference.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from types import ModuleType
from typing import Any, Callable

from flask import Blueprint, abort, g, jsonify, request, url_for
from werkzeug.exceptions import HTTPException

API_VERSION = 1
API_PREFIX = f"/api/v{API_VERSION}"
TOKEN_PREFIX = "bccp_"
MAX_JSON_BYTES = 64 * 1024
TOKEN_TOUCH_INTERVAL = timedelta(minutes=1)
# Mirror app.py: event moderation is open to every admin tier, account and
# site administration only to admin and super_admin.
EVENT_ADMIN_ROLES = {"sub_admin", "admin", "super_admin"}
ACCOUNT_ADMIN_ROLES = {"admin", "super_admin"}
HTTP_ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    429: "rate_limited",
    500: "server_error",
}

bp = Blueprint("api", __name__, url_prefix=API_PREFIX)
# The application module (app.py). Passed in instead of imported so running
# ``python app.py`` (module ``__main__``) does not load a second copy.
core: ModuleType
# When the blueprint was created, i.e. roughly when the process started.
STARTED_AT: datetime


def create_api_blueprint(core_module: ModuleType) -> Blueprint:
    global core, STARTED_AT
    core = core_module
    STARTED_AT = datetime.now()
    if core.CourtActionError not in bp.error_handler_spec[None][None]:
        bp.register_error_handler(core.CourtActionError, handle_action_error)
    return bp


# ---------------------------------------------------------------------------
# Request plumbing
# ---------------------------------------------------------------------------


def now_text() -> str:
    return datetime.now().isoformat(timespec="seconds")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def api_error(code: str, status: int = 400, **kwargs: Any) -> Exception:
    return core.CourtActionError(code, status, **kwargs)


@bp.before_request
def authenticate_request():
    g.api_request = True
    header = request.headers.get("Authorization", "")
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        return token_rejected()
    db = core.get_db()
    row = db.execute(
        "SELECT id, user_id, expires_at, last_used_at FROM api_tokens "
        "WHERE token_hash = ?",
        (hash_token(token),),
    ).fetchone()
    now = datetime.now()
    if row is None or datetime.fromisoformat(row["expires_at"]) <= now:
        return token_rejected()
    g.api_user_id = row["user_id"]
    g.api_token_id = row["id"]
    last_used = row["last_used_at"]
    if not last_used or now - datetime.fromisoformat(last_used) >= TOKEN_TOUCH_INTERVAL:
        db.execute(
            "UPDATE api_tokens SET last_used_at = ? WHERE id = ?",
            (now.isoformat(timespec="seconds"), row["id"]),
        )
        db.commit()
    return None


def token_rejected():
    response, status = core.api_error_response("invalid_token", 401)
    response.headers["WWW-Authenticate"] = 'Bearer error="invalid_token"'
    return response, status


@bp.after_request
def no_store(response):
    response.headers.setdefault("Cache-Control", "no-store")
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@bp.errorhandler(HTTPException)
def handle_http_error(error: HTTPException):
    status = error.code or 500
    return core.api_error_response(HTTP_ERROR_CODES.get(status, "error"), status)


def handle_action_error(error: Exception):
    return core.api_error_response(
        error.code, error.status, error.message, error.fields
    )


@bp.app_errorhandler(405)
def method_not_allowed(error: HTTPException):
    if request.path.startswith(API_PREFIX + "/"):
        return core.api_error_response("method_not_allowed", 405)
    return error


def json_body() -> dict[str, Any]:
    if request.content_length is not None and request.content_length > MAX_JSON_BYTES:
        abort(413)
    if not request.get_data(cache=True):
        return {}
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise api_error("bad_request", message=localized(
            "Send a JSON object body.", "請傳送 JSON 物件格式的內容。"
        ))
    return payload


def court_payload() -> tuple[dict[str, Any], list[Any]]:
    """Read a court body as JSON, or multipart with a ``court`` JSON field
    plus ``media`` file parts."""
    if request.mimetype == "multipart/form-data":
        raw = request.form.get("court", "") or "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = None
        if not isinstance(payload, dict):
            raise api_error("bad_request", fields={"court": "invalid_json"})
        return payload, request.files.getlist("media")
    return json_body(), []


def localized(english: str, chinese: str) -> str:
    return chinese if core.current_language() == "zh-tw" else english


def text_value(payload: dict[str, Any], field: str, default: str = "") -> str:
    value = payload.get(field, default)
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (str, int, float)):
        return str(value)
    raise api_error("bad_request", fields={field: "invalid_type"})


def bool_value(payload: dict[str, Any], field: str) -> bool:
    value = payload.get(field)
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    raise api_error("bad_request", fields={field: "invalid_type"})


def int_list(payload: dict[str, Any], field: str) -> list[int]:
    value = payload.get(field, [])
    if not isinstance(value, list) or any(
        isinstance(item, bool) or not isinstance(item, int) for item in value
    ):
        raise api_error("bad_request", fields={field: "invalid_type"})
    return value


def require_member(
    *, roles: set[str] | None = None, allow_temporary_password: bool = False
) -> Callable:
    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapped(*args, **kwargs):
            member = core.current_member()
            if member is None:
                raise api_error("unauthorized", 401)
            if roles is not None and member["role"] not in roles:
                raise api_error("forbidden", 403)
            if member["must_change_password"] and not allow_temporary_password:
                raise api_error("temporary_password_required", 403)
            return view(*args, **kwargs)

        return wrapped

    return decorator


def viewer_is_admin() -> bool:
    member = core.current_member()
    return bool(member and member["role"] in core.ADMIN_ROLES)


def no_content():
    return "", 204


# ---------------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------------


def avatar_url(filename: str) -> str | None:
    if not filename:
        return None
    return url_for("avatar_file", filename=filename, _external=True)


def serialize_user(row: Any, *, private: bool = False) -> dict[str, Any]:
    data = {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "avatar_url": avatar_url(row["avatar_filename"]),
        "created_at": row["created_at"],
    }
    if private:
        data.update(
            {
                "time_format": row["time_format"],
                "last_login_at": row["last_login_at"],
                "must_change_password": bool(row["must_change_password"]),
                "is_admin": row["role"] in core.ADMIN_ROLES,
            }
        )
    return data


def serialize_court(court: Any) -> dict[str, Any]:
    return {
        "guid": court["guid"],
        "event_name": court["event_name"],
        "badminton_name": court["badminton_name"],
        "court_date": court["court_date"],
        "start_time": court["start_time"],
        "end_time": court["end_time"],
        "hall_name": court["hall_name"],
        "location": court["location"],
        "google_place_id": court["google_place_id"],
        "latitude": court["latitude"],
        "longitude": court["longitude"],
        "court_id": court["court_id"],
        "creator_username": court["creator_username"],
        "created_at": court["created_at"],
        "status": core.court_csv_status(court),
        "archived": bool(court["archived"]),
        "expired": bool(court["is_expired"]),
        "roll_clearing_locked": bool(court["roll_clearing_locked"]),
        "leave_deadline": {
            "enabled": bool(court["leave_deadline_enabled"]),
            "at": court["leave_deadline_at"] or None,
            "passed": bool(court["leave_deadline_passed"]),
        },
        "members": {
            "min": court["member_min"],
            "max": court["member_max"],
            "reserved": court["ordered_count"],
            "signed_up": court["online_count"],
            "waiting": court["waiting_count"],
            "confirmed_total": court["total_count"],
        },
        "levels": {
            "male": {"min": court["male_level_min"], "max": court["male_level_max"]},
            "female": {
                "min": court["female_level_min"],
                "max": court["female_level_max"],
            },
        },
        "prices": {"male": court["male_price"], "female": court["female_price"]},
        "shuttlecock_info": court["shuttlecock_info"],
        "remark": court["remark"],
        "reserved_names_visible": bool(court["reserved_names_visible"]),
        "cover_image_url": (
            url_for("court_media_file", filename=court["cover_image"], _external=True)
            if court["cover_image"]
            else None
        ),
        "web_url": url_for("court_detail", guid=court["guid"], _external=True),
        "thumbnail_url": url_for(
            "download_court_thumbnail", guid=court["guid"], _external=True
        ),
    }


def serialize_court_detail(court: Any) -> dict[str, Any]:
    db = core.get_db()
    member = core.current_member()
    is_admin = bool(member and member["role"] in core.ADMIN_ROLES)
    is_owner = bool(member and court["owner_id"] == member["id"])
    can_manage = is_admin or is_owner

    participants = db.execute(
        "SELECT id, username, joined_at, waitlisted, roll_called, cleared "
        "FROM participants WHERE court_id = ? ORDER BY joined_at, id",
        (court["id"],),
    ).fetchall()

    def participant(row: Any) -> dict[str, Any]:
        data = {"id": row["id"], "username": row["username"], "joined_at": row["joined_at"]}
        if can_manage:
            data["roll_called"] = bool(row["roll_called"])
            data["cleared"] = bool(row["cleared"])
        return data

    reserved_rows = db.execute(
        "SELECT id, nickname, position, roll_called, cleared "
        "FROM reserved_members WHERE court_id = ? ORDER BY position, id",
        (court["id"],),
    ).fetchall()
    if can_manage:
        reserved = [
            {
                "id": row["id"],
                "position": row["position"],
                "nickname": row["nickname"],
                "roll_called": bool(row["roll_called"]),
                "cleared": bool(row["cleared"]),
            }
            for row in reserved_rows
        ]
    elif court["reserved_names_visible"]:
        reserved = [
            {"position": row["position"], "nickname": row["nickname"]}
            for row in reserved_rows
            if row["nickname"]
        ]
    else:
        reserved = []

    history_columns = "id, username, event_type, occurred_at"
    if is_admin:
        history_columns += ", ip_address, device_information"
    history = [
        dict(row)
        for row in db.execute(
            f"SELECT {history_columns} FROM participation_history "
            "WHERE court_id = ? ORDER BY occurred_at DESC, id DESC",
            (court["id"],),
        ).fetchall()
    ]

    data = serialize_court(court)
    data.update(
        {
            "participants": [participant(p) for p in participants if not p["waitlisted"]],
            "waiting_participants": [
                participant(p) for p in participants if p["waitlisted"]
            ],
            "reserved_members": reserved,
            "media": [
                {
                    "id": item["id"],
                    "media_type": item["media_type"],
                    "mime_type": item["mime_type"],
                    "original_name": item["original_name"],
                    "url": url_for(
                        "court_media_file", filename=item["filename"], _external=True
                    ),
                }
                for item in core.fetch_court_media(court["id"])
            ],
            "participation_history": history,
            "viewer": {
                "is_owner": is_owner,
                "is_admin": is_admin,
                "can_manage": can_manage,
            },
        }
    )
    if can_manage:
        # Editable values in the same shape PATCH /courts/<guid> accepts.
        data["form_values"] = core.court_form_values(court)
        if is_owner:
            data["owner_notifications"] = bool(court["owner_notifications"])
        data["reserved_nicknames"] = core.reserved_nickname_values(
            court["id"], court["ordered_count"]
        )
    return data


def court_detail_response(guid: str, status: int = 200):
    court = core.fetch_court(guid)
    if court is None:
        abort(404)
    return jsonify({"court": serialize_court_detail(court)}), status


def fetch_public_court(guid: str) -> Any:
    court = core.fetch_court(guid)
    if court is None:
        abort(404)
    return court


def paginate(rows: list[Any]) -> tuple[list[Any], dict[str, int]]:
    try:
        limit = int(request.args.get("limit", "100"))
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        raise api_error("bad_request", fields={"limit": "invalid_type"}) from None
    limit = min(200, max(1, limit))
    offset = max(0, offset)
    return rows[offset : offset + limit], {
        "total": len(rows),
        "limit": limit,
        "offset": offset,
    }


def court_list_response(where_sql: str, parameters: list[Any], order_by: str, **extra: Any):
    rows = core.get_db().execute(
        core.court_query() + where_sql + order_by, parameters
    ).fetchall()
    page, pagination = paginate(rows)
    return jsonify(
        {
            "courts": [serialize_court(court) for court in page],
            "pagination": pagination,
            **extra,
        }
    )


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------


def issue_token(user_id: int, name: str) -> dict[str, Any]:
    token = TOKEN_PREFIX + secrets.token_urlsafe(32)
    created = datetime.now()
    ttl_days = max(1, int(core.current_app_config("API_TOKEN_TTL_DAYS")))
    expires_at = (created + timedelta(days=ttl_days)).isoformat(timespec="seconds")
    db = core.get_db()
    db.execute(
        "INSERT INTO api_tokens "
        "(user_id, token_hash, name, created_at, last_used_at, expires_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            user_id,
            hash_token(token),
            name,
            created.isoformat(timespec="seconds"),
            created.isoformat(timespec="seconds"),
            expires_at,
        ),
    )
    # Drop this account's expired tokens while we are here.
    db.execute(
        "DELETE FROM api_tokens WHERE user_id = ? AND expires_at <= ?",
        (user_id, created.isoformat(timespec="seconds")),
    )
    db.commit()
    return {"token": token, "token_type": "Bearer", "expires_at": expires_at}


def device_name(payload: dict[str, Any]) -> str:
    name = core.clean_username(text_value(payload, "device_name"))
    if not name:
        name = core.client_device_information()
    return "".join(ch for ch in name if ch.isprintable())[:80]


def auth_response(user_id: int, payload: dict[str, Any], status: int):
    token = issue_token(user_id, device_name(payload))
    g.api_user_id = user_id
    member = core.current_member()
    return jsonify({**token, "user": serialize_user(member, private=True)}), status


def require_turnstile(payload: dict[str, Any], action: str) -> None:
    if not core.verify_turnstile_response(action, text_value(payload, "turnstile_token")):
        raise api_error("turnstile_required", 403)


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------


def version_info() -> dict[str, Any]:
    return {
        "app_version": core.current_app_config("APP_VERSION"),
        "api_version": API_VERSION,
        "last_updated": core.SITE_UPDATE_HISTORY[0]["date"],
    }


@bp.get("/version")
def version():
    return jsonify(version_info())


@bp.get("/status")
def status():
    try:
        core.get_db().execute("SELECT 1").fetchone()
        database = "ok"
    except sqlite3.Error:
        database = "error"
    healthy = database == "ok"
    now = datetime.now()
    return jsonify(
        {
            "status": "ok" if healthy else "degraded",
            "checks": {"database": database},
            "server_time": now.isoformat(timespec="seconds"),
            "started_at": STARTED_AT.isoformat(timespec="seconds"),
            "uptime_seconds": int((now - STARTED_AT).total_seconds()),
            **version_info(),
        }
    ), (200 if healthy else 503)


@bp.get("/meta")
def meta():
    turnstile = core.turnstile_enabled()
    return jsonify(
        {
            "api_version": API_VERSION,
            "language": core.current_language(),
            "languages": sorted(core.LANGUAGES),
            "turnstile": {
                "enabled": turnstile,
                "site_key": core.current_app_config("TURNSTILE_SITE_KEY") if turnstile else "",
            },
            "push": {"fcm": core.fcm_enabled()},
            "limits": {
                "participant_name": {"min": 2, "max": 40},
                "pin_digits": 6,
                "account_username": {"min": 3, "max": 40},
                "password_min": 8,
                "level": {"min": 1, "max": 18},
                "members": {"min": 1, "max": 99},
                "court_media_files": core.MAX_COURT_MEDIA_FILES,
                "court_image_bytes": core.MAX_COURT_IMAGE_BYTES,
                "court_video_bytes": core.MAX_COURT_VIDEO_BYTES,
                "avatar_bytes": core.MAX_AVATAR_BYTES,
            },
            "court_defaults": core.default_court_values(),
        }
    )


@bp.get("/courts")
def list_courts():
    clauses, parameters, filters = core.build_court_filters(request.args)
    return court_list_response(
        core.court_where_sql(clauses),
        parameters,
        " ORDER BY is_expired, c.court_date, c.start_time",
        filters=filters,
    )


@bp.get("/courts/<guid>")
def get_court(guid: str):
    return court_detail_response(guid)


@bp.post("/courts/<guid>/join")
def join_court(guid: str):
    payload = json_body()
    court = fetch_public_court(guid)
    waitlisted = core.join_court_entry(
        court, text_value(payload, "username"), text_value(payload, "pin")
    )
    response, _ = court_detail_response(guid)
    body = response.get_json()
    body["waitlisted"] = waitlisted
    return jsonify(body), 201


@bp.post("/courts/<guid>/leave")
def leave_court(guid: str):
    payload = json_body()
    court = fetch_public_court(guid)
    core.leave_court_entry(
        court, text_value(payload, "username"), text_value(payload, "pin")
    )
    return court_detail_response(guid)


# Message board. Players post with the nickname and PIN they joined with; the
# court's organizer (or an administrator) posts as their account.


def serialize_court_message(row: Any, show_audit: bool) -> dict[str, Any]:
    data = {
        "id": row["id"],
        "author_name": row["author_name"],
        "author_kind": row["author_kind"],
        "message": row["message"],
        "posted_at": row["posted_at"],
    }
    if show_audit:
        data["ip_address"] = row["ip_address"]
    return data


def court_messages_body(court: Any) -> dict[str, Any]:
    court_messages, threads = core.fetch_court_message_threads(court["id"])
    show_audit = viewer_is_admin()
    return {
        "messages": [
            {
                **serialize_court_message(top, show_audit),
                "replies": [serialize_court_message(r, show_audit) for r in replies],
            }
            for top, replies in threads
        ],
        "count": len(court_messages),
        "version": core.court_messages_version(court_messages),
    }


@bp.get("/courts/<guid>/messages")
def list_court_messages(guid: str):
    court = fetch_public_court(guid)
    body = court_messages_body(court)
    if request.args.get("version", "") == body["version"]:
        return jsonify({"changed": False, "version": body["version"]})
    return jsonify({"changed": True, **body})


@bp.post("/courts/<guid>/messages")
def post_court_message(guid: str):
    payload = json_body()
    court = fetch_public_court(guid)
    message_id, thread_id = core.create_court_message(
        court,
        text_value(payload, "username"),
        text_value(payload, "pin"),
        text_value(payload, "message"),
        text_value(payload, "parent_id"),
        raw_fcm_token=text_value(payload, "fcm_token"),
    )
    return jsonify(
        {
            "message_id": message_id,
            "thread_id": thread_id,
            "changed": True,
            **court_messages_body(court),
        }
    ), 201


@bp.delete("/courts/<guid>/messages/<int:message_id>")
@require_member()
def delete_court_message(guid: str, message_id: int):
    court = core.fetch_managed_court(guid)
    core.delete_court_message_entry(court, message_id)
    return jsonify({"changed": True, **court_messages_body(court)})


# Android push (FCM). The device's registration token identifies the
# subscriber, so no account is needed, the same as browser Web Push.


def fcm_token(payload: dict[str, Any], field: str = "token") -> str:
    token = core.validated_fcm_token(payload.get(field))
    if token is None:
        raise api_error("bad_request", fields={field: "invalid"})
    return token


def fcm_subscribed(court_id: int, token: str) -> bool:
    return core.get_db().execute(
        "SELECT 1 FROM fcm_subscriptions WHERE court_id = ? AND token = ?",
        (court_id, token),
    ).fetchone() is not None


@bp.post("/courts/<guid>/push/status")
def court_push_status(guid: str):
    court = fetch_public_court(guid)
    token = fcm_token(json_body())
    return jsonify({"subscribed": fcm_subscribed(court["id"], token)})


@bp.put("/courts/<guid>/push")
def subscribe_court_push(guid: str):
    if not core.fcm_enabled():
        raise api_error("push_unavailable", 503)
    court = fetch_public_court(guid)
    token = fcm_token(json_body())
    now = now_text()
    db = core.get_db()
    db.execute(
        """
        INSERT INTO fcm_subscriptions (court_id, token, language, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(court_id, token) DO UPDATE SET
            language = excluded.language,
            updated_at = excluded.updated_at
        """,
        (court["id"], token, core.current_language(), now, now),
    )
    db.commit()
    return jsonify({"subscribed": True})


@bp.delete("/courts/<guid>/push")
def unsubscribe_court_push(guid: str):
    court = fetch_public_court(guid)
    token = fcm_token(json_body())
    db = core.get_db()
    db.execute(
        "DELETE FROM fcm_subscriptions WHERE court_id = ? AND token = ?",
        (court["id"], token),
    )
    db.commit()
    return jsonify({"subscribed": False})


@bp.put("/push/token")
def replace_push_token():
    """Move every court subscription from a rotated FCM token to its replacement."""
    payload = json_body()
    previous = fcm_token(payload, "previous_token")
    token = fcm_token(payload)
    db = core.get_db()
    if previous != token:
        # Drop rows the new token already has, then move the rest.
        db.execute(
            "DELETE FROM fcm_subscriptions WHERE token = ? AND court_id IN "
            "(SELECT court_id FROM fcm_subscriptions WHERE token = ?)",
            (previous, token),
        )
        db.execute(
            "UPDATE fcm_subscriptions SET token = ?, updated_at = ? WHERE token = ?",
            (token, now_text(), previous),
        )
        db.execute(
            "UPDATE api_tokens SET fcm_token = ? WHERE fcm_token = ?",
            (token, previous),
        )
        db.commit()
    count = db.execute(
        "SELECT COUNT(*) FROM fcm_subscriptions WHERE token = ?", (token,)
    ).fetchone()[0]
    return jsonify({"subscriptions": count})


@bp.post("/contact")
def send_contact_message():
    payload = json_body()
    values = {
        field: text_value(payload, field).strip()
        for field in ("sender_name", "reply_contact", "subject", "message")
    }
    errors = core.validate_contact_message(values)
    if errors:
        raise api_error("contact_form_invalid", 422, fields=errors)
    require_turnstile(payload, "contact_message")
    core.store_contact_message(
        values,
        core.current_language(),
        core.clean_contact_client(payload.get("client")),
    )
    return jsonify({"sent": True}), 201


# ---------------------------------------------------------------------------
# Authentication and the signed-in account
# ---------------------------------------------------------------------------


@bp.post("/auth/signup")
def signup():
    payload = json_body()
    require_turnstile(payload, "signup")
    password = text_value(payload, "password")
    user_id = core.register_member(
        text_value(payload, "username"),
        password,
        text_value(payload, "confirm_password", password),
    )
    return auth_response(user_id, payload, 201)


@bp.post("/auth/login")
def login():
    payload = json_body()
    require_turnstile(payload, "login")
    user = core.authenticate_member(
        text_value(payload, "username"), text_value(payload, "password")
    )
    return auth_response(user["id"], payload, 200)


@bp.post("/auth/logout")
@require_member(allow_temporary_password=True)
def logout():
    db = core.get_db()
    db.execute("DELETE FROM api_tokens WHERE id = ?", (g.api_token_id,))
    db.commit()
    return no_content()


@bp.get("/auth/tokens")
@require_member()
def list_tokens():
    rows = core.get_db().execute(
        "SELECT id, name, created_at, last_used_at, expires_at FROM api_tokens "
        "WHERE user_id = ? AND expires_at > ? ORDER BY last_used_at DESC, id DESC",
        (g.api_user_id, now_text()),
    ).fetchall()
    return jsonify(
        {
            "tokens": [
                {**dict(row), "current": row["id"] == g.api_token_id}
                for row in rows
            ]
        }
    )


@bp.delete("/auth/tokens/<int:token_id>")
@require_member()
def revoke_token(token_id: int):
    db = core.get_db()
    result = db.execute(
        "DELETE FROM api_tokens WHERE id = ? AND user_id = ?",
        (token_id, g.api_user_id),
    )
    db.commit()
    if result.rowcount == 0:
        abort(404)
    return no_content()


@bp.put("/me/push-token")
@require_member(allow_temporary_password=True)
def register_account_push_token():
    """Link this device's FCM token to the current sign-in.

    The organizer then hears about changes others make to their courts.
    Signing out deletes the sign-in token, and the link with it.
    """
    token = fcm_token(json_body())
    db = core.get_db()
    # One account per device: a token moves to the newest sign-in.
    db.execute(
        "UPDATE api_tokens SET fcm_token = NULL WHERE fcm_token = ? AND id != ?",
        (token, g.api_token_id),
    )
    db.execute(
        "UPDATE api_tokens SET fcm_token = ?, fcm_language = ? WHERE id = ?",
        (token, core.current_language(), g.api_token_id),
    )
    db.commit()
    return jsonify({"registered": True})


@bp.delete("/me/push-token")
@require_member(allow_temporary_password=True)
def unregister_account_push_token():
    db = core.get_db()
    db.execute(
        "UPDATE api_tokens SET fcm_token = NULL WHERE id = ?", (g.api_token_id,)
    )
    db.commit()
    return jsonify({"registered": False})


@bp.get("/me")
@require_member(allow_temporary_password=True)
def get_me():
    return jsonify({"user": serialize_user(core.current_member(), private=True)})


@bp.patch("/me")
@require_member()
def update_me():
    payload = json_body()
    if "time_format" in payload:
        time_format = text_value(payload, "time_format").strip().lower()
        if time_format not in core.TIME_FORMATS:
            raise api_error("invalid_datetime_format", fields={"time_format": "invalid"})
        db = core.get_db()
        db.execute(
            "UPDATE users SET time_format = ? WHERE id = ?",
            (time_format, g.api_user_id),
        )
        db.commit()
    return get_me()


@bp.delete("/me")
@require_member()
def delete_me():
    payload = json_body()
    core.delete_member_account(
        core.current_member(), text_value(payload, "current_password")
    )
    return no_content()


@bp.post("/me/password")
@require_member(allow_temporary_password=True)
def change_password():
    payload = json_body()
    new_password = text_value(payload, "new_password")
    core.change_member_password(
        g.api_user_id,
        text_value(payload, "current_password"),
        new_password,
        text_value(payload, "confirm_password", new_password),
    )
    return get_me()


@bp.put("/me/avatar")
@require_member()
def upload_avatar():
    core.save_member_avatar(core.current_member(), request.files.get("avatar"))
    return get_me()


@bp.delete("/me/avatar")
@require_member()
def delete_avatar():
    core.remove_member_avatar(core.current_member())
    return get_me()


@bp.get("/me/saved-locations")
@require_member()
def list_saved_locations():
    return jsonify(
        {
            "saved_locations": [
                {
                    "id": row["id"],
                    "hall_name": row["hall_name"],
                    "location": row["location"],
                    "google_place_id": row["google_place_id"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                }
                for row in core.fetch_saved_locations(g.api_user_id)
            ]
        }
    )


@bp.delete("/me/saved-locations/<int:location_id>")
@require_member()
def delete_saved_location(location_id: int):
    db = core.get_db()
    result = db.execute(
        "DELETE FROM saved_locations WHERE id = ? AND user_id = ?",
        (location_id, g.api_user_id),
    )
    if result.rowcount == 0:
        abort(404)
    db.commit()
    return no_content()


@bp.get("/me/courts")
@require_member()
def list_my_courts():
    return court_list_response(
        " WHERE c.owner_id = ?",
        [g.api_user_id],
        " ORDER BY c.archived, c.court_date DESC, c.start_time DESC",
    )


# ---------------------------------------------------------------------------
# Organizer: create and manage events
# ---------------------------------------------------------------------------


def reserved_nicknames_from(payload: dict[str, Any], default: list[str]) -> list[str]:
    if "reserved_nicknames" not in payload:
        return default
    value = payload["reserved_nicknames"]
    if (
        not isinstance(value, list)
        or len(value) > 99
        or any(not isinstance(item, str) for item in value)
    ):
        raise api_error("bad_request", fields={"reserved_nicknames": "invalid_type"})
    return value


def owner_notifications_from(payload: dict[str, Any]) -> bool | None:
    """The organizer's change-alert preference, or None when not sent."""
    if "owner_notifications" not in payload:
        return None
    return bool_value(payload, "owner_notifications")


def apply_owner_notifications(guid: str, enabled: bool | None) -> None:
    if enabled is None:
        return
    db = core.get_db()
    db.execute(
        "UPDATE courts SET owner_notifications = ? WHERE guid = ?",
        (1 if enabled else 0, guid),
    )
    db.commit()


def validated_court_input(
    payload: dict[str, Any], base_values: dict[str, str], base_nicknames: list[str]
) -> tuple[dict[str, Any], list[str], dict[str, str]]:
    values = dict(base_values)
    for field in base_values:
        if field in payload:
            values[field] = text_value(payload, field).strip()
    cleaned, errors = core.validate_court(values)
    nicknames = core.validate_reserved_nicknames(
        reserved_nicknames_from(payload, base_nicknames),
        cleaned.get("ordered_count") if "ordered_count" not in errors else None,
        errors,
    )
    return cleaned, nicknames, errors


@bp.post("/courts")
@require_member()
def create_court():
    payload, files = court_payload()
    owner_notifications = owner_notifications_from(payload)
    member = core.current_member()
    cleaned, nicknames, errors = validated_court_input(
        payload, core.default_court_values(), []
    )
    media_uploads = core.validate_court_media_uploads(files, 0, errors)
    if errors:
        raise api_error("invalid_form", 422, fields=errors)
    guid = core.create_court_record(
        cleaned,
        owner_id=member["id"],
        creator_name=member["username"],
        reserved_nicknames=nicknames,
        media_uploads=media_uploads,
    )
    if payload.get("save_location") is True:
        core.save_member_location(member["id"], cleaned)
    apply_owner_notifications(guid, owner_notifications)
    return court_detail_response(guid, 201)


@bp.patch("/courts/<guid>")
@require_member()
def update_court(guid: str):
    court = core.fetch_managed_court(guid)
    if court["roll_clearing_locked"]:
        raise api_error("court_read_only", 409)
    payload, files = court_payload()
    owner_notifications = owner_notifications_from(payload)
    if court["owner_id"] != g.api_user_id:
        # Only the organizer chooses whether they get change alerts.
        owner_notifications = None
    cleaned, nicknames, errors = validated_court_input(
        payload,
        core.court_form_values(court),
        core.reserved_nickname_values(court["id"], court["ordered_count"]),
    )
    existing_media = core.fetch_court_media(court["id"])
    remove_ids = set(int_list(payload, "remove_media_ids")) & {
        item["id"] for item in existing_media
    }
    media_uploads = core.validate_court_media_uploads(
        files, len(existing_media) - len(remove_ids), errors
    )
    if errors:
        raise api_error("invalid_form", 422, fields=errors)
    core.update_court_record(guid, cleaned, nicknames, media_uploads, remove_ids)
    apply_owner_notifications(guid, owner_notifications)
    return court_detail_response(guid)


@bp.delete("/courts/<guid>")
@require_member()
def delete_court(guid: str):
    owner_id = None if viewer_is_admin() else g.api_user_id
    if not core.delete_court_record(guid, owner_id):
        abort(404)
    return no_content()


def set_court_archived(guid: str, archived: int):
    if viewer_is_admin():
        core.update_court_status(guid, archived)
    else:
        core.update_owned_court_status(guid, g.api_user_id, archived)
    return court_detail_response(guid)


@bp.post("/courts/<guid>/archive")
@require_member()
def archive_court(guid: str):
    return set_court_archived(guid, 1)


@bp.post("/courts/<guid>/restore")
@require_member()
def restore_court(guid: str):
    return set_court_archived(guid, 0)


@bp.post("/courts/<guid>/roll-clearing")
@require_member()
def start_roll_clearing(guid: str):
    core.start_roll_clearing_mode(core.fetch_managed_court(guid))
    return court_detail_response(guid)


@bp.patch("/courts/<guid>/roll-clearing")
@require_member()
def update_roll_clearing(guid: str):
    court = core.fetch_managed_court(guid)
    payload = json_body()
    db = core.get_db()

    def statuses(field: str, table: str) -> dict[int, tuple[bool, bool]]:
        items = payload.get(field, [])
        if not isinstance(items, list):
            raise api_error("bad_request", fields={field: "invalid_type"})
        current = {
            row["id"]: (bool(row["roll_called"]), bool(row["cleared"]))
            for row in db.execute(
                f"SELECT id, roll_called, cleared FROM {table} WHERE court_id = ?",
                (court["id"],),
            ).fetchall()
        }
        result: dict[int, tuple[bool, bool]] = {}
        for item in items:
            member_id = item.get("id") if isinstance(item, dict) else None
            if isinstance(member_id, bool) or not isinstance(member_id, int):
                raise api_error("bad_request", fields={field: "invalid_type"})
            roll, cleared = current.get(member_id, (False, False))
            if "roll_called" in item:
                roll = bool_value(item, "roll_called")
            if "cleared" in item:
                cleared = bool_value(item, "cleared")
            result[member_id] = (roll, cleared)
        return result

    core.save_roll_clearing_statuses(
        court,
        statuses("participants", "participants"),
        statuses("reserved_members", "reserved_members"),
        reset_unlisted=False,
    )
    return court_detail_response(guid)


@bp.delete("/courts/<guid>/roll-clearing")
@require_member()
def end_roll_clearing(guid: str):
    core.restore_court_editing_mode(core.fetch_managed_court(guid))
    return court_detail_response(guid)


@bp.patch("/courts/<guid>/participants/<int:participant_id>")
@require_member(roles=EVENT_ADMIN_ROLES)
def update_participant(guid: str, participant_id: int):
    court = fetch_public_court(guid)
    payload = json_body()
    if "username" in payload:
        core.rename_court_participant(
            court, participant_id, text_value(payload, "username")
        )
    if "pin" in payload:
        core.reset_court_participant_pin(
            court, participant_id, text_value(payload, "pin")
        )
    return court_detail_response(guid)


@bp.delete("/courts/<guid>/participants/<int:participant_id>")
@require_member(roles=EVENT_ADMIN_ROLES)
def delete_participant(guid: str, participant_id: int):
    core.remove_court_participant(fetch_public_court(guid), participant_id)
    return court_detail_response(guid)


# ---------------------------------------------------------------------------
# Administration
# ---------------------------------------------------------------------------

@bp.get("/admin/courts")
@require_member(roles=EVENT_ADMIN_ROLES)
def admin_list_courts():
    clauses, parameters, filters = core.build_court_filters(request.args, admin=True)
    return court_list_response(
        core.court_where_sql(clauses),
        parameters,
        " ORDER BY c.archived, c.court_date DESC, c.start_time DESC",
        filters=filters,
    )


def serialize_admin_user(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
        "archived": bool(row["archived"]),
        "banned": bool(row["banned"]),
        "must_change_password": bool(row["must_change_password"]),
        "created_at": row["created_at"],
        "last_login_at": row["last_login_at"],
        "last_login_ip": row["last_login_ip"],
        "court_count": row["court_count"],
        "failed_login_attempts": row["failed_login_attempts"],
    }


def admin_user_response(user_id: int):
    for row in core.fetch_admin_user_rows():
        if row["id"] == user_id:
            return jsonify({"user": serialize_admin_user(row)})
    abort(404)


@bp.get("/admin/users")
@require_member(roles=ACCOUNT_ADMIN_ROLES)
def admin_list_users():
    return jsonify(
        {"users": [serialize_admin_user(row) for row in core.fetch_admin_user_rows()]}
    )


@bp.put("/admin/users/<int:user_id>/role")
@require_member(roles={"super_admin"})
def admin_set_role(user_id: int):
    payload = json_body()
    core.set_member_role(core.current_member(), user_id, text_value(payload, "role"))
    return admin_user_response(user_id)


def admin_user_status_action(user_id: int, update: Callable[[], None]):
    core.reject_privileged_account_mutation(user_id)
    update()
    return admin_user_response(user_id)


@bp.post("/admin/users/<int:user_id>/archive")
@require_member(roles=ACCOUNT_ADMIN_ROLES)
def admin_archive_user(user_id: int):
    return admin_user_status_action(user_id, lambda: core.update_user_status(user_id, 1))


@bp.post("/admin/users/<int:user_id>/restore")
@require_member(roles=ACCOUNT_ADMIN_ROLES)
def admin_restore_user(user_id: int):
    return admin_user_status_action(user_id, lambda: core.update_user_status(user_id, 0))


@bp.post("/admin/users/<int:user_id>/ban")
@require_member(roles=ACCOUNT_ADMIN_ROLES)
def admin_ban_user(user_id: int):
    return admin_user_status_action(user_id, lambda: core.update_user_ban(user_id, 1))


@bp.post("/admin/users/<int:user_id>/unban")
@require_member(roles=ACCOUNT_ADMIN_ROLES)
def admin_unban_user(user_id: int):
    return admin_user_status_action(user_id, lambda: core.update_user_ban(user_id, 0))


@bp.post("/admin/users/<int:user_id>/reset-login-retries")
@require_member(roles=ACCOUNT_ADMIN_ROLES)
def admin_reset_login_retries(user_id: int):
    db = core.get_db()
    user = db.execute(
        "SELECT username_key FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    if user is None:
        abort(404)
    db.execute(
        "DELETE FROM login_attempts WHERE scope = 'member' AND username_key = ?",
        (user["username_key"],),
    )
    db.commit()
    return admin_user_response(user_id)


@bp.post("/admin/users/<int:user_id>/temporary-password")
@require_member(roles=ACCOUNT_ADMIN_ROLES)
def admin_set_temporary_password(user_id: int):
    payload = json_body()
    core.reject_privileged_account_mutation(user_id)
    temporary_password = text_value(payload, "temporary_password")
    if len(temporary_password) < 8:
        raise api_error("password_too_short")
    db = core.get_db()
    result = db.execute(
        "UPDATE users SET password_hash = ?, must_change_password = 1 WHERE id = ?",
        (core.generate_password_hash(temporary_password), user_id),
    )
    if result.rowcount == 0:
        abort(404)
    db.commit()
    core.revoke_api_tokens(user_id)
    return admin_user_response(user_id)


@bp.delete("/admin/users/<int:user_id>")
@require_member(roles=ACCOUNT_ADMIN_ROLES)
def admin_delete_user(user_id: int):
    core.delete_archived_member(user_id)
    return no_content()


@bp.get("/admin/messages")
@require_member(roles=ACCOUNT_ADMIN_ROLES)
def admin_list_messages():
    message_status = request.args.get("status", "all").strip().lower()
    if message_status not in {"all", "unread", "read"}:
        message_status = "all"
    try:
        page = int(request.args.get("page", "1"))
    except ValueError:
        page = 1
    result = core.fetch_contact_message_page(message_status, page)
    return jsonify(
        {
            "messages": [dict(row) for row in result["messages"]],
            "status": message_status,
            "page": result["page"],
            "page_count": result["page_count"],
            "total_count": result["total_count"],
            "unread_count": result["unread_count"],
        }
    )


@bp.patch("/admin/messages/<int:message_id>")
@require_member(roles=ACCOUNT_ADMIN_ROLES)
def admin_update_message(message_id: int):
    payload = json_body()
    if not core.set_contact_message_read(message_id, bool_value(payload, "read")):
        abort(404)
    row = core.get_db().execute(
        "SELECT id, sender_name, reply_contact, subject, message, language, "
        "submitted_at, read_at FROM contact_messages WHERE id = ?",
        (message_id,),
    ).fetchone()
    return jsonify({"message": dict(row)})


def admin_settings_body() -> dict[str, Any]:
    channels = core.contact_notification_channels()
    return {
        "homepage_court_limit": core.get_int_setting("homepage_court_limit", 12, 1, 100),
        "contact_notifications_enabled": core.get_bool_setting(
            "contact_notifications_enabled"
        ),
        "contact_notification_channels": {
            "discord_ready": channels["discord_ready"],
            "telegram_ready": channels["telegram_ready"],
        },
    }


@bp.get("/admin/settings")
@require_member(roles=ACCOUNT_ADMIN_ROLES)
def admin_get_settings():
    return jsonify({"settings": admin_settings_body()})


@bp.patch("/admin/settings")
@require_member(roles=ACCOUNT_ADMIN_ROLES)
def admin_update_settings():
    payload = json_body()
    if "homepage_court_limit" in payload:
        limit = payload["homepage_court_limit"]
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise api_error(
                "invalid_homepage_court_limit",
                fields={"homepage_court_limit": "invalid"},
            )
        core.set_setting("homepage_court_limit", str(limit))
    if "contact_notifications_enabled" in payload:
        enabled = bool_value(payload, "contact_notifications_enabled")
        channels = core.contact_notification_channels()
        if enabled and not channels["discord_ready"]:
            raise api_error("contact_notification_unavailable", 409)
        core.set_setting("contact_notifications_enabled", "1" if enabled else "0")
    return jsonify({"settings": admin_settings_body()})
