"""用代码绘制界图标，避免依赖外部图片资源。

Ribbon 按钮图标统一由 text_icon() 生成：把短文本（如 "B"、"H1"、"PDF"）
绘制成圆角矩形底 + 文字的 QIcon，风格接近 Office 的单色图标。
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap

from .theme import ACCENT

_CACHE: dict[tuple, QIcon] = {}


def text_icon(
    text: str,
    size: int = 22,
    color: str = ACCENT,
    background: str = "#eaf1fb",
    dark: bool = False,
    bold: bool = True,
    font_size: int = 9,
    italic: bool = False,
    strike: bool = False,
) -> QIcon:
    """把文本渲染为圆角图标；italic 让字母倾斜，strike 在字母中间画删除线。"""
    key = (text, size, color, background, dark, bold, font_size, italic, strike)
    if key in _CACHE:
        return _CACHE[key]

    scale = 2
    pm = QPixmap(size * scale, size * scale)
    pm.setDevicePixelRatio(scale)
    pm.fill(Qt.transparent)

    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)

    bg = QColor(background)
    if dark:
        bg = QColor("#33404f")
    if bg.isValid():
        painter.setPen(Qt.NoPen)
        painter.setBrush(bg)
        painter.drawRoundedRect(QRectF(0.5, 0.5, size - 1, size - 1), 4, 4)

    font = QFont("Segoe UI")
    length = len(text.strip())
    if length >= 3:
        pixel_size = size * 0.5
    elif length == 2:
        pixel_size = size * 0.62
    else:
        pixel_size = size * (font_size / 10)
    font.setPixelSize(max(7, int(pixel_size)))
    font.setBold(bold)
    font.setItalic(italic)
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, text)

    if strike:
        pen = QPen(QColor(color), max(1.2, size * 0.07))
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        y = size / 2
        painter.drawLine(QPointF(size * 0.18, y), QPointF(size * 0.82, y))
    painter.end()

    icon = QIcon(pm)
    _CACHE[key] = icon
    return icon


def clear_cache() -> None:
    _CACHE.clear()
