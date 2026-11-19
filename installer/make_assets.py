"""生成安装包所需的图标与向导图片。

用法：
    python installer/make_assets.py

输出：
    clara/assets/app.ico         应用与安装程序图标（多尺寸）
    installer/assets/wizard.bmp  Inno Setup 左侧大图（164x314）
    installer/assets/wizard_small.bmp  右上角小图（55x55）
"""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
APP_ASSETS = PROJECT / "clara" / "assets"
OUT = ROOT / "assets"

TOP = (74, 134, 216)
BOTTOM = (23, 50, 94)


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    name = "seguisb.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(Path(os.environ["WINDIR"]) / "Fonts" / name), size)


def _gradient(size: int, top=TOP, bottom=BOTTOM) -> Image.Image:
    img = Image.new("RGBA", (size, size))
    px = img.load()
    for y in range(size):
        t = y / max(1, size - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(size):
            px[x, y] = (*color, 255)
    return img


def _icon(size: int = 1024) -> Image.Image:
    base = _gradient(size)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=int(size * 0.22), fill=255)
    icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    icon.paste(base, (0, 0), mask)

    draw = ImageDraw.Draw(icon)
    font = _font(int(size * 0.62))
    draw.text((size / 2, size * 0.47), "M", font=font, fill=(255, 255, 255, 255), anchor="mm")
    bar_w, bar_h = int(size * 0.30), int(size * 0.045)
    draw.rounded_rectangle(
        ((size - bar_w) / 2, size * 0.79, (size + bar_w) / 2, size * 0.79 + bar_h),
        radius=bar_h // 2,
        fill=(255, 255, 255, 235),
    )
    return icon


def _wizard_large() -> Image.Image:
    w, h = 164, 314
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        t = y / (h - 1)
        color = tuple(int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = (*color, 255)

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.ellipse((-40, 200, 120, 360), fill=(255, 255, 255, 14))
    od.ellipse((70, -50, 230, 110), fill=(255, 255, 255, 12))
    img = Image.alpha_composite(img, overlay)

    icon = _icon(1024).resize((84, 84), Image.LANCZOS)
    img.alpha_composite(icon, (40, 32))

    draw = ImageDraw.Draw(img)
    draw.text((w / 2, 146), "Clara", font=_font(26), fill=(255, 255, 255, 255), anchor="mm")
    draw.text((w / 2, 174), "MarkdownEditor", font=_font(12), fill=(224, 236, 252, 255), anchor="mm")
    draw.line((w / 2 - 34, 194, w / 2 + 34, 194), fill=(255, 255, 255, 120), width=1)
    draw.text((w / 2, 210), "Markdown", font=_font(10, bold=False), fill=(200, 220, 246, 255), anchor="mm")
    draw.text((w / 2, 226), "Word  ·  PDF", font=_font(10, bold=False), fill=(200, 220, 246, 255), anchor="mm")
    return img.convert("RGB")


def _wizard_small() -> Image.Image:
    icon = _icon(1024).resize((220, 220), Image.LANCZOS)
    return icon.convert("RGB").resize((55, 55), Image.LANCZOS)


def main() -> None:
    APP_ASSETS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    icon = _icon(1024)
    icon.save(
        APP_ASSETS / "app.ico",
        format="ICO",
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)],
    )
    _wizard_large().save(OUT / "wizard.bmp", format="BMP")
    _wizard_small().save(OUT / "wizard_small.bmp", format="BMP")
    print("Saved:", APP_ASSETS / "app.ico")
    print("Saved:", OUT / "wizard.bmp")
    print("Saved:", OUT / "wizard_small.bmp")


if __name__ == "__main__":
    main()
