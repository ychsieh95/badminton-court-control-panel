"""Small adb helpers for capture.py. Every command is scoped to one emulator with -s."""
from __future__ import annotations

import json
import os
import re
import struct
import subprocess
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

APP_ID = "cc.holey.badmintoncourtcontrolpanel"
ACTIVITY = f"{APP_ID}/io.github.ychsieh95.bccp.MainActivity"
DATASTORE = "files/datastore/bccp.preferences_pb"


def _varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        out.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(out)


def _field(number: int, payload: bytes) -> bytes:
    return _varint(number << 3 | 2) + _varint(len(payload)) + payload


def preferences_pb(values: dict[str, str]) -> bytes:
    """Encode string entries as a Jetpack DataStore PreferenceMap protobuf."""
    out = b""
    for key, value in values.items():
        entry = _field(1, key.encode()) + _field(2, _field(5, value.encode()))
        out += _field(1, entry)
    return out


@dataclass
class Node:
    text: str
    desc: str
    bounds: tuple[int, int, int, int]
    clickable: bool
    scrollable: bool

    @property
    def center(self) -> tuple[int, int]:
        l, t, r, b = self.bounds
        return (l + r) // 2, (t + b) // 2


class Device:
    def __init__(self, serial: str, adb: str):
        self.serial = serial
        self.adb = adb

    def run(self, *args: str, check: bool = True, capture: bool = True) -> str:
        result = subprocess.run([self.adb, "-s", self.serial, *args], check=False,
                                stdout=subprocess.PIPE if capture else None,
                                stderr=subprocess.STDOUT if capture else None)
        output = result.stdout.decode(errors="replace") if capture else ""
        if check and result.returncode != 0:
            raise RuntimeError(f"adb {' '.join(args)} failed: {output}")
        return output

    def shell(self, command: str, check: bool = True) -> str:
        return self.run("shell", command, check=check)

    # --- app state -----------------------------------------------------------------
    def reset_app(self, locale: str, prefs: dict[str, str]) -> None:
        """Clear the app, then seed its DataStore before the first launch."""
        self.shell(f"am force-stop {APP_ID}")
        self.shell(f"pm clear {APP_ID}")
        self.shell(f"cmd locale set-app-locales {APP_ID} --locales {locale}")
        # Avoid the first-launch notification permission prompt covering the UI.
        self.shell(f"pm grant {APP_ID} android.permission.POST_NOTIFICATIONS", check=False)
        local = Path(os.environ.get("TMPDIR", "/tmp")) / f"bccp-prefs-{self.serial}.pb"
        local.write_bytes(preferences_pb(prefs))
        remote = "/data/local/tmp/bccp.preferences_pb"
        self.run("push", str(local), remote)
        local.unlink()
        self.shell(f"run-as {APP_ID} mkdir -p files/datastore")
        self.shell(f"cat {remote} | run-as {APP_ID} sh -c 'cat > {DATASTORE}'")
        self.shell(f"rm -f {remote}")

    def launch(self, uri: str | None = None) -> None:
        self.shell(f"am force-stop {APP_ID}")
        if uri:
            self.shell(f"am start -W -a android.intent.action.VIEW -d '{uri}' -n {ACTIVITY}")
        else:
            self.shell(f"am start -W -n {ACTIVITY}")

    # --- UI tree -------------------------------------------------------------------
    def nodes(self) -> list[Node]:
        remote = "/data/local/tmp/bccp-window.xml"
        for _ in range(5):
            self.shell(f"uiautomator dump {remote}", check=False)
            xml = self.shell(f"cat {remote}", check=False)
            start = xml.find("<?xml")
            if start >= 0:
                break
            time.sleep(0.5)
        else:
            return []
        root = ET.fromstring(xml[start:].strip())
        found = []
        for el in root.iter("node"):
            l, t, r, b = map(int, re.findall(r"\d+", el.get("bounds", "[0,0][0,0]")))
            found.append(Node(el.get("text", ""), el.get("content-desc", ""), (l, t, r, b),
                              el.get("clickable") == "true", el.get("scrollable") == "true"))
        return found

    def find(self, label: str, exact: bool = True) -> Node | None:
        for node in self.nodes():
            for value in (node.text, node.desc):
                if (value == label) if exact else (label in value):
                    return node
        return None

    def wait_for(self, label: str, timeout: float = 30, exact: bool = True) -> Node:
        deadline = time.time() + timeout
        while time.time() < deadline:
            node = self.find(label, exact)
            if node:
                return node
            time.sleep(0.7)
        raise RuntimeError(f"'{label}' did not appear on {self.serial}")

    def tap(self, label: str, exact: bool = True, timeout: float = 30) -> None:
        x, y = self.wait_for(label, timeout, exact).center
        self.shell(f"input tap {x} {y}")

    def tap_xy(self, x: int, y: int) -> None:
        self.shell(f"input tap {x} {y}")

    def swipe(self, x1: int, y1: int, x2: int, y2: int, ms: int = 600) -> None:
        self.shell(f"input swipe {x1} {y1} {x2} {y2} {ms}")

    def scroll_to(self, label: str, top: int, max_swipes: int = 12, exact: bool = True) -> Node:
        """Scroll the page until `label` sits near y = top, then return its node."""
        width, height = self.size()
        x = width // 2
        for _ in range(max_swipes):
            node = self.find(label, exact)
            if node and node.bounds[1] <= height * 0.85:
                break
            self.swipe(x, int(height * 0.75), x, int(height * 0.35), 700)
            time.sleep(0.8)
        else:
            raise RuntimeError(f"could not scroll to '{label}'")
        for _ in range(4):  # slow drags do not fling, so a few passes converge
            delta = node.bounds[1] - top
            if abs(delta) <= 24:
                return node
            start = height // 2 + max(min(delta, height // 3), -height // 3) // 2
            self.swipe(x, start, x, start - max(min(delta, height // 3), -height // 3), 2000)
            time.sleep(1.0)
            node = self.find(label, exact) or node
        return node

    def size(self) -> tuple[int, int]:
        out = self.shell("wm size")
        w, h = map(int, re.findall(r"(\d+)x(\d+)", out)[-1])
        return w, h

    def hide_keyboard(self) -> None:
        if "mInputShown=true" in self.shell("dumpsys input_method", check=False):
            self.shell("input keyevent 4")
            time.sleep(0.6)

    def screenshot(self, path: Path) -> str:
        data = subprocess.run([self.adb, "-s", self.serial, "exec-out", "screencap", "-p"],
                              check=True, stdout=subprocess.PIPE).stdout
        if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
            raise RuntimeError(f"invalid PNG for {path}")
        w, h = struct.unpack(">II", data[16:24])
        if h <= w:
            raise RuntimeError(f"non-portrait screenshot for {path}: {w}x{h}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"{w}x{h}"


def prefs_for(state: dict, server_url: str, theme: str = "Light", palette: str | None = None) -> dict[str, str]:
    """App preferences for a capture. Without `palette`, the app's default palette is shown."""
    prefs = {
        "server_url": server_url,
        "theme_mode": theme,
        "api_token": state["token"],
        "api_user": json.dumps(state["user"], ensure_ascii=False),
    }
    if palette:
        prefs["palette"] = palette
    return prefs
