#!/usr/bin/env python3
"""Compose Play Store screenshots from the captured app screens. Requires Pillow and NumPy.

For each style, a procedural panorama (no third-party art) is drawn across all seven
panels and saved to <style>/source/. Each 1080 x 2400 panel then gets a numbered
eyebrow, a feature-led title and subtitle, and the real capture in a rounded frame.

    python3 Android/docs/store-listing/screenshots/render_store.py \
        --input  Android/docs/store-listing/screenshots/closed-testing/alpha/app \
        --output Android/docs/store-listing/screenshots/closed-testing/alpha/store
"""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, PANELS = 1080, 2400, 7
FONT_DIR = Path("/usr/share/fonts/opentype/noto")
FONT_INDEX = 3  # Noto Sans CJK TC: covers Latin and Traditional Chinese.

PANEL_FILES = [
    "01-courts.png", "02-court-detail.png", "03-members-levels.png", "04-join.png",
    "05-messages.png", "06-organize.png", "07-court-form.png",
]

# (eyebrow, title, subtitle) per panel. Keep meaning aligned between locales and only
# describe features the app has.
COPY = {
    "en-US": [
        ("FIND A GAME", "Find your next game", "Browse courts by date, level, and spots left."),
        ("EVENT DETAILS", "Know before you go", "Time, place, court, and photos on one page."),
        ("MEMBERS & LEVELS", "Is it your level?", "Spots left, prices, and a clear level guide."),
        ("NO ACCOUNT NEEDED", "Join in seconds", "Just a name and a PIN. Full courts put you on the waiting list."),
        ("MESSAGE BOARD", "Ask the organizer", "Questions and replies stay with the event."),
        ("FOR ORGANIZERS", "Every event in one place", "Follow sign-ups for every court you host."),
        ("CREATE & EDIT", "Set up a court in minutes", "Schedule, capacity, levels, and leave deadlines."),
    ],
    "zh-TW": [
        ("找球局", "找到下一場球局", "依日期、程度與剩餘名額瀏覽場次。"),
        ("場次資訊", "出發前一次看清楚", "時間、地點、場地與照片集中在同一頁。"),
        ("人數與程度", "程度合不合，一眼就知道", "剩餘名額、費用與清楚的程度說明。"),
        ("免註冊", "幾秒完成報名", "只要名稱與 PIN，場次額滿時自動排入候補名單。"),
        ("留言板", "有問題直接問主辦", "提問與回覆都保留在場次頁面。"),
        ("給主辦人", "所有活動集中管理", "掌握你主辦的每個場次報名狀況。"),
        ("建立與編輯", "幾分鐘開好一個場次", "日期、人數、程度與退出期限一次設定。"),
    ],
}


@dataclass
class Style:
    name: str
    eyebrow: tuple[int, int, int]
    title: tuple[int, int, int]
    body: tuple[int, int, int]
    frame_edge: tuple[int, int, int, int]
    shadow: int
    background: Callable[[int, int], Image.Image]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    name = "NotoSansCJK-Bold.ttc" if bold else "NotoSansCJK-Regular.ttc"
    return ImageFont.truetype(str(FONT_DIR / name), size, index=FONT_INDEX)


def gradient(width: int, height: int, stops: list[tuple[float, tuple[int, int, int]]], axis: int) -> np.ndarray:
    """Linear gradient along axis 0 (vertical) or 1 (horizontal) as float RGB."""
    n = height if axis == 0 else width
    t = np.linspace(0, 1, n)
    channels = []
    for c in range(3):
        channels.append(np.interp(t, [s for s, _ in stops], [col[c] for _, col in stops]))
    line = np.stack(channels, axis=-1)
    if axis == 0:
        return np.repeat(line[:, None, :], width, axis=1)
    return np.repeat(line[None, :, :], height, axis=0)


def glow(arr: np.ndarray, cx: float, cy: float, radius: float, color, strength: float) -> None:
    h, w, _ = arr.shape
    ys, xs = np.ogrid[:h, :w]
    d = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2) / radius
    a = np.clip(1 - d, 0, 1) ** 2 * strength
    arr[:] = arr * (1 - a[..., None]) + np.array(color) * a[..., None]


def to_image(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


# --- backgrounds ---------------------------------------------------------------------
def court_green(width: int, height: int) -> Image.Image:
    """Deep green floor with gold badminton court lines running across all panels."""
    arr = gradient(width, height, [(0, (10, 52, 38)), (0.55, (18, 86, 60)), (1, (8, 40, 30))], 0)
    for i in range(PANELS):
        glow(arr, (i + 0.5) * W + (180 if i % 2 else -180), height * 0.18, 900, (70, 160, 110), 0.35)
    im = to_image(arr)
    lines = Image.new("L", (width, height), 0)
    d = ImageDraw.Draw(lines)
    horizon = int(height * 0.40)
    vx = width / 2
    # Receding sidelines and service lines in a wide perspective.
    for k in range(-18, 19):
        d.line((vx + k * 60, horizon, vx + k * 760, height), fill=60, width=5)
    for j, depth in enumerate([0.0, 0.09, 0.22, 0.42, 0.7, 1.0]):
        y = horizon + (height - horizon) * depth
        d.line((0, y, width, y), fill=50 + j * 8, width=4 + j)
    lines = lines.filter(ImageFilter.GaussianBlur(1.2))
    fade = Image.linear_gradient("L").resize((width, height)).point(lambda v: min(255, int(v * 1.6)))
    lines = Image.composite(lines, Image.new("L", (width, height), 0), fade)
    im.paste((250, 214, 90), (0, 0), lines.point(lambda v: v // 2))
    return im


def shuttle_ivory(width: int, height: int) -> Image.Image:
    """Warm ivory with soft amber and gold shuttle-flight arcs."""
    arr = gradient(width, height, [(0, (250, 246, 236)), (1, (241, 236, 220))], 0)
    for i in range(PANELS):
        glow(arr, (i + 0.5) * W, height * 0.92, 1100, (250, 236, 196), 0.6)
    im = to_image(arr)
    layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    colors = [(148, 98, 0, 60), (250, 204, 21, 110), (148, 98, 0, 35)]
    for k in range(9):
        x0 = k * width / 8 - 500
        span = 1700 + (k % 3) * 300
        top = height * (0.30 + 0.05 * (k % 4))
        pts = []
        for s in np.linspace(0, 1, 120):
            pts.append((x0 + span * s, top + 900 - 1100 * math.sin(math.pi * s) * (0.6 + 0.1 * (k % 3))))
        d.line(pts, fill=colors[k % 3], width=10 if k % 3 == 1 else 6, joint="curve")
    layer = layer.filter(ImageFilter.GaussianBlur(1.5))
    im.paste(layer, (0, 0), layer)
    return im


def night_arena(width: int, height: int) -> Image.Image:
    """Indoor arena at night: navy hall, overhead light beams, amber floor glow."""
    arr = gradient(width, height, [(0, (9, 14, 38)), (0.6, (18, 30, 74)), (1, (10, 16, 42))], 0)
    for i in range(PANELS):
        cx = (i + 0.5) * W
        glow(arr, cx, -200, 1300, (60, 90, 190), 0.55)
        glow(arr, cx, height + 150, 900, (245, 158, 11), 0.30)
    im = to_image(arr)
    beams = Image.new("L", (width, height), 0)
    d = ImageDraw.Draw(beams)
    for i in range(PANELS * 2):
        cx = (i + 0.5) * W / 2
        d.polygon([(cx - 30, 0), (cx + 30, 0), (cx + 260, height), (cx - 260, height)], fill=26)
    beams = beams.filter(ImageFilter.GaussianBlur(40))
    im.paste((150, 180, 255), (0, 0), beams)
    return im


STYLES = {
    "court-green": Style("court-green", (250, 204, 21), (255, 255, 255), (214, 236, 222),
                         (255, 255, 255, 60), 150, court_green),
    "shuttle-ivory": Style("shuttle-ivory", (148, 98, 0), (38, 33, 19), (119, 111, 91),
                           (80, 60, 10, 40), 70, shuttle_ivory),
    "night-arena": Style("night-arena", (250, 204, 21), (255, 255, 255), (200, 210, 236),
                         (255, 255, 255, 70), 170, night_arena),
}


# --- composition ---------------------------------------------------------------------
def wrap(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont, width: int) -> list[str]:
    """Wrap on spaces for Latin text and between characters for CJK."""
    lines: list[str] = []
    line = ""
    tokens = text.split(" ") if text.isascii() else list(text)
    sep = " " if text.isascii() else ""
    for token in tokens:
        candidate = f"{line}{sep}{token}" if line else token
        if draw.textlength(candidate, font=f) <= width:
            line = candidate
            continue
        if not text.isascii() and token in "，。、：；！？":
            line = candidate  # keep CJK punctuation off the start of a line
            continue
        lines.append(line)
        line = token
    lines.append(line)
    return lines


PHONE_X, PHONE_Y, PHONE_W = 130, 560, 820
RADIUS = 58


def frame(capture: Image.Image, style: Style) -> tuple[Image.Image, Image.Image]:
    scale = PHONE_W / capture.width
    shot = capture.convert("RGB").resize((PHONE_W, round(capture.height * scale)), Image.LANCZOS)
    mask = Image.new("L", shot.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, shot.width - 1, shot.height - 1), RADIUS, fill=255)
    return shot, mask


def panel(background: Image.Image, capture: Image.Image, copy: tuple[str, str, str], index: int,
          style: Style) -> Image.Image:
    im = background.copy().convert("RGBA")
    d = ImageDraw.Draw(im)
    eyebrow, title, subtitle = copy
    x, width = 76, W - 152
    d.text((x, 76), f"{index:02d}  •  {eyebrow}", font=font(36, True), fill=style.eyebrow)
    y = 150
    title_font = font(76, True)
    for line in wrap(d, title, title_font, width):
        d.text((x, y), line, font=title_font, fill=style.title)
        y += 96
    y += 18
    body_font = font(40)
    for line in wrap(d, subtitle, body_font, width):
        d.text((x, y), line, font=body_font, fill=style.body)
        y += 58
    if y > PHONE_Y - 30:
        raise SystemExit(f"copy for panel {index} is too long for {style.name}")

    shot, mask = frame(capture, style)
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (PHONE_X, PHONE_Y + 24, PHONE_X + shot.width, PHONE_Y + shot.height + 24), RADIUS,
        fill=(0, 0, 0, style.shadow))
    im = Image.alpha_composite(im, shadow.filter(ImageFilter.GaussianBlur(34)))
    im.paste(shot, (PHONE_X, PHONE_Y), mask)
    ImageDraw.Draw(im).rounded_rectangle(
        (PHONE_X - 1, PHONE_Y - 1, PHONE_X + shot.width, PHONE_Y + shot.height), RADIUS + 1,
        outline=style.frame_edge, width=3)
    return im.convert("RGB")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", type=Path, required=True, help="Directory with en-US/ and zh-TW/ captures.")
    parser.add_argument("--output", type=Path, required=True, help="Store root; one subdirectory per style.")
    parser.add_argument("--styles", default=",".join(STYLES))
    args = parser.parse_args()

    for name in args.styles.split(","):
        style = STYLES[name]
        panorama = style.background(W * PANELS, H)
        source = args.output / name / "source"
        source.mkdir(parents=True, exist_ok=True)
        panorama.resize((W * PANELS // 2, H // 2), Image.LANCZOS).save(source / f"{name}-panorama.png", optimize=True)
        for locale, copies in COPY.items():
            out = args.output / name / locale
            out.mkdir(parents=True, exist_ok=True)
            for i, (filename, copy) in enumerate(zip(PANEL_FILES, copies)):
                capture = Image.open(args.input / locale / filename)
                background = panorama.crop((i * W, 0, (i + 1) * W, H))
                panel(background, capture, copy, i + 1, style).save(out / filename, optimize=True)
                print(f"OK  {name}/{locale}/{filename}")


if __name__ == "__main__":
    main()
