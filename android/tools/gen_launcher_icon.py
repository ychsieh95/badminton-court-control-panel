#!/usr/bin/env python3
"""Generate the app's adaptive launcher icon from the website icon.

Source: web/static/shuttlecock.png, a white shuttlecock with a red band on a blue
gradient circle. The shuttlecock is separated from the circle (un-blending its
anti-aliased edges against the fitted gradient) and written as:

  res/mipmap-*/ic_launcher_foreground.png  white shuttlecock + red band
  res/mipmap-*/ic_launcher_monochrome.png  silhouette for themed icons (band cut out)
  res/drawable/ic_launcher_background.xml  the circle's gradient, full bleed
  res/drawable-*/ic_notification.png       status-bar icon (cropped silhouette)

The circle's diameter maps to the adaptive icon's 72dp visible area, so the
launcher mask shows the same framing as the website icon.

Run from android/:  python3 tools/gen_launcher_icon.py   (needs Pillow + numpy)
"""
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / "web" / "static" / "shuttlecock.png"
RES = ROOT / "app" / "src" / "main" / "res"
DENSITIES = {"mdpi": 1.0, "hdpi": 1.5, "xhdpi": 2.0, "xxhdpi": 3.0, "xxxhdpi": 4.0}
CANVAS_DP = 108
VISIBLE_DP = 72


def main() -> None:
    src = np.asarray(Image.open(SOURCE).convert("RGBA"), dtype=np.float64)
    h, w = src.shape[:2]
    rgb, alpha = src[..., :3], src[..., 3] / 255

    # Circle geometry from the opaque area.
    ys, xs = np.nonzero(alpha > 0.5)
    cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
    radius = (xs.max() - xs.min() + ys.max() - ys.min()) / 4

    # Fit the background as a linear gradient over clearly blue pixels.
    yy, xx = np.mgrid[0:h, 0:w]
    blue = (alpha > 0.99) & (rgb[..., 2] - rgb[..., 0] > 70)
    design = np.column_stack([np.ones(blue.sum()), xx[blue], yy[blue]])
    coef, *_ = np.linalg.lstsq(design, rgb[blue], rcond=None)
    bg = coef[0] + xx[..., None] * coef[1] + yy[..., None] * coef[2]

    # Un-blend: shuttlecock alpha is how far a pixel moved from the background
    # toward its foreground colour (white, or the red band on its red channel).
    toward_white = (rgb - bg) / np.maximum(255 - bg, 1)
    raw_alpha = np.clip(toward_white.max(axis=2), 0, 1) * (alpha > 0.99)
    # The source gradient isn't perfectly linear; treat the leftover on plain
    # background pixels as noise so no ghost of the circle survives.
    floor = np.percentile(raw_alpha[blue], 99.9) + 0.02
    fg_alpha = np.clip((raw_alpha - floor) / (1 - floor), 0, 1)
    fg_rgb = np.where(
        fg_alpha[..., None] > 0.01,
        bg + (rgb - bg) / np.maximum(fg_alpha[..., None], 0.01),
        255,
    )
    fg = np.dstack([np.clip(fg_rgb, 0, 255), fg_alpha * 255]).astype(np.uint8)

    red = (fg_rgb[..., 0] - fg_rgb[..., 1] > 60) & (fg_alpha > 0.5)
    mono_alpha = np.where(red, 0, fg_alpha)
    mono = np.dstack([np.full((h, w, 3), 255.0), mono_alpha * 255]).astype(np.uint8)

    for name, image in (("ic_launcher_foreground", fg), ("ic_launcher_monochrome", mono)):
        write_layer(Image.fromarray(image, "RGBA"), name, cx, cy, radius)
    write_notification_icon(Image.fromarray(mono, "RGBA"))

    corner = lambda x, y: "#%02X%02X%02X" % tuple(
        int(round(v)) for v in np.clip(coef[0] + x * coef[1] + y * coef[2], 0, 255)
    )
    # Gradient direction in the source runs along (coef x-slope, y-slope); sample its ends.
    direction = np.array([coef[1].mean(), coef[2].mean()])
    direction /= np.linalg.norm(direction)
    start = np.array([cx, cy]) - direction * radius
    end = np.array([cx, cy]) + direction * radius
    # Android gradient angles are counter-clockwise from +x with y pointing up.
    angle = (np.degrees(np.arctan2(-direction[1], direction[0])) + 360) % 360
    write_background(corner(*start), corner(*end), int(round(angle / 45)) * 45 % 360)


def write_layer(image: Image.Image, name: str, cx: float, cy: float, radius: float) -> None:
    for density, scale in DENSITIES.items():
        size = round(CANVAS_DP * scale)
        px_per_src = VISIBLE_DP * scale / (2 * radius)
        scaled = image.resize(
            (round(image.width * px_per_src), round(image.height * px_per_src)), Image.LANCZOS
        )
        canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        canvas.alpha_composite(
            scaled, (round(size / 2 - cx * px_per_src), round(size / 2 - cy * px_per_src))
        )
        out = RES / f"mipmap-{density}" / f"{name}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out, optimize=True)


def write_notification_icon(silhouette: Image.Image) -> None:
    """24dp status-bar icon: the silhouette fitted to the 22dp live area."""
    cropped = silhouette.crop(silhouette.getbbox())
    for density, scale in DENSITIES.items():
        size, live = round(24 * scale), 22 * scale
        factor = live / max(cropped.size)
        scaled = cropped.resize(
            (round(cropped.width * factor), round(cropped.height * factor)), Image.LANCZOS
        )
        canvas = Image.new("RGBA", (size, size), (255, 255, 255, 0))
        canvas.alpha_composite(
            scaled, ((size - scaled.width) // 2, (size - scaled.height) // 2)
        )
        out = RES / f"drawable-{density}" / "ic_notification.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(out, optimize=True)


def write_background(start: str, end: str, angle: int) -> None:
    (RES / "drawable" / "ic_launcher_background.xml").write_text(
        f"""<?xml version="1.0" encoding="utf-8"?>
<!-- Generated by tools/gen_launcher_icon.py from web/static/shuttlecock.png. -->
<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">
    <gradient
        android:angle="{angle}"
        android:startColor="{start}"
        android:endColor="{end}"
        android:type="linear" />
</shape>
"""
    )


if __name__ == "__main__":
    main()
