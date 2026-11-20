"""Firebase Cloud Messaging (HTTP v1) sender for the Android app.

The browser keeps using Web Push; the Android app registers its FCM token per
court and gets the same court-change notifications through this client.
Authenticates with a Firebase service account key (``FCM_SERVICE_ACCOUNT_FILE``).
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

import requests
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
SEND_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
# FCM error codes meaning the token will never work again and should be dropped.
STALE_TOKEN_ERRORS = {"UNREGISTERED", "SENDER_ID_MISMATCH"}


class FcmError(Exception):
    def __init__(self, status: int, code: str):
        super().__init__(f"FCM send failed: {status} {code}")
        self.status = status
        self.code = code

    @property
    def stale_token(self) -> bool:
        return self.status == 404 or self.code in STALE_TOKEN_ERRORS


class FcmClient:
    def __init__(self, service_account_file: str | Path, timeout: float = 5):
        info = json.loads(Path(service_account_file).read_text(encoding="utf-8"))
        self.project_id: str = info["project_id"]
        self.timeout = timeout
        self._credentials = service_account.Credentials.from_service_account_info(
            info, scopes=[SCOPE]
        )
        self._session = requests.Session()
        self._lock = threading.Lock()

    def _access_token(self) -> str:
        with self._lock:
            if not self._credentials.valid:
                self._credentials.refresh(GoogleAuthRequest(self._session))
            return self._credentials.token

    def send(
        self,
        token: str,
        data: dict[str, str],
        *,
        collapse_key: str,
        ttl_seconds: int = 86_400,
    ) -> None:
        """Send a high-priority data message; the app builds the notification itself."""
        response = self._session.post(
            SEND_URL.format(project_id=self.project_id),
            headers={"Authorization": f"Bearer {self._access_token()}"},
            json={
                "message": {
                    "token": token,
                    "data": data,
                    "android": {
                        "priority": "high",
                        "collapse_key": collapse_key,
                        "ttl": f"{ttl_seconds}s",
                    },
                }
            },
            timeout=self.timeout,
        )
        if response.ok:
            return
        raise FcmError(response.status_code, error_code(response))


def error_code(response: requests.Response) -> str:
    try:
        error = response.json().get("error", {})
    except ValueError:
        return "unknown"
    for detail in error.get("details", []):
        if detail.get("errorCode"):
            return str(detail["errorCode"])
    return str(error.get("status") or "unknown")
