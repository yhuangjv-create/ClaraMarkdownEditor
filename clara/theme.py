"""浅色 / 深色主题样式表（仿 Word 的 Ribbon 视觉）。

颜色常量以 ACCENT 为主色（Word 蓝），所有界面控件都在 build_stylesheet() 中统一配置。
"""

from __future__ import annotations

from pathlib import Path

ACCENT = "#2b579a"          # Word 主蓝
ACCENT_LIGHT = "#e8f0fb"
ACCENT_PRESSED = "#d3e2f7"

_ASSETS = Path(__file__).resolve().parent / "assets"


def _close_icon(dark: bool) -> str:
    """标签页关闭按钮的图标路径（浅色主题用深灰叉，深色主题用浅灰叉）。"""
    name = "close_dark.svg" if dark else "close_light.svg"
    return (_ASSETS / name).as_posix()


def build_stylesheet(dark: bool = False) -> str:
    if dark:
        c = {
            "win": "#1f1f1f",
            "panel": "#262626",
            "ribbon": "#2d2d2d",
            "ribbon_hover": "#3a3a3a",
            "border": "#3f3f3f",
            "text": "#e6e6e6",
            "subtext": "#9d9d9d",
            "page_bg": "#1a1a1a",
            "editor_bg": "#1e1e1e",
            "accent": "#4a86d8",
            "accent_light": "#313d4d",
            "accent_pressed": "#3b4b60",
        }
    else:
        c = {
            "win": "#f3f3f3",
            "panel": "#ffffff",
            "ribbon": "#ffffff",
            "ribbon_hover": "#edf2fa",
            "border": "#dcdcdc",
            "text": "#1f1f1f",
            "subtext": "#6b6b6b",
            "page_bg": "#e8e8e8",
            "editor_bg": "#ffffff",
            "accent": ACCENT,
            "accent_light": ACCENT_LIGHT,
            "accent_pressed": ACCENT_PRESSED,
        }

    return f"""
    QMainWindow, QWidget {{
        background: {c['win']};
        color: {c['text']};
        font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
        font-size: 9pt;
    }}
    QWidget#RibbonTop {{
        background: {c['ribbon']};
        border-bottom: 1px solid {c['border']};
    }}
    QWidget#RibbonBody {{
        background: {c['ribbon']};
        border-bottom: 1px solid {c['border']};
    }}
    QToolButton#RibbonTab {{
        background: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        padding: 6px 14px;
        color: {c['text']};
        font-size: 9pt;
    }}
    QToolButton#RibbonTab:hover {{
        background: {c['ribbon_hover']};
    }}
    QToolButton#RibbonTab:checked {{
        background: {c['panel']};
        border-bottom: 2px solid {c['accent']};
        color: {c['accent']};
        font-weight: bold;
    }}
    QToolButton#RibbonButton {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 4px;
        padding: 3px 5px;
        color: {c['text']};
        min-width: 52px;
    }}
    QToolButton#RibbonButton:hover {{
        background: {c['accent_light']};
        border: 1px solid {c['accent']};
    }}
    QToolButton#RibbonButton:pressed {{
        background: {c['accent_pressed']};
    }}
    QToolButton#RibbonButton:disabled {{
        color: {c['subtext']};
    }}
    QLabel#GroupTitle {{
        color: {c['subtext']};
        font-size: 8pt;
    }}
    QFrame#GroupBox {{
        border-right: 1px solid {c['border']};
    }}
    QFrame#TopSeparator {{
        background: {c['border']};
        max-height: 1px;
    }}
    QLabel#AppTitle {{
        color: {c['accent']};
        font-weight: bold;
        font-size: 10pt;
        padding-left: 10px;
    }}
    QLabel#DocTitle {{
        color: {c['subtext']};
        font-size: 9pt;
        padding-right: 8px;
    }}
    QToolButton#MiniButton {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 3px;
        padding: 3px 8px;
        color: {c['text']};
    }}
    QToolButton#MiniButton:hover {{
        background: {c['accent_light']};
        border: 1px solid {c['border']};
    }}
    QPlainTextEdit, QTextEdit#Wysiwyg {{
        background: {c['editor_bg']};
        color: {c['text']};
        border: none;
        selection-background-color: {c['accent']};
        selection-color: #ffffff;
        font-family: "Cascadia Mono", "Consolas", "Microsoft YaHei UI", monospace;
        font-size: 11pt;
    }}
    QTextEdit#Preview {{
        background: {c['editor_bg']};
        border: none;
        padding: 0px;
        selection-background-color: {c['accent']};
        selection-color: #ffffff;
    }}
    QFrame#PageFrame {{
        background: {c['page_bg']};
        border: none;
    }}
    QSplitter::handle {{
        background: {c['border']};
    }}
    QSplitter::handle:horizontal {{
        width: 2px;
    }}
    QSplitter::handle:hover {{
        background: {c['accent']};
    }}
    QListWidget#Outline {{
        background: {c['panel']};
        border: none;
        border-right: 1px solid {c['border']};
        outline: none;
        padding: 4px;
    }}
    QListWidget#Outline::item {{
        padding: 3px 6px;
        border-radius: 3px;
    }}
    QListWidget#Outline::item:hover {{
        background: {c['accent_light']};
    }}
    QListWidget#Outline::item:selected {{
        background: {c['accent']};
        color: #ffffff;
    }}
    QLabel#PanelTitle {{
        background: {c['panel']};
        color: {c['subtext']};
        border-right: 1px solid {c['border']};
        padding: 6px 8px;
        font-size: 8pt;
        font-weight: bold;
    }}
    QStatusBar {{
        background: {c['panel']};
        border-top: 1px solid {c['border']};
        color: {c['subtext']};
    }}
    QStatusBar::item {{ border: none; }}
    QLineEdit, QComboBox, QSpinBox {{
        background: {c['panel']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 3px;
        padding: 3px 6px;
        min-height: 18px;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
        border: 1px solid {c['accent']};
    }}
    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
        background: {c['win']};
        color: {c['subtext']};
    }}
    QComboBox QAbstractItemView {{
        background: {c['panel']};
        color: {c['text']};
        selection-background-color: {c['accent']};
        selection-color: #ffffff;
    }}
    QPushButton {{
        background: {c['panel']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-radius: 3px;
        padding: 5px 14px;
    }}
    QPushButton:hover {{
        background: {c['accent_light']};
        border-color: {c['accent']};
    }}
    QPushButton#PrimaryButton {{
        background: {c['accent']};
        color: #ffffff;
        border: 1px solid {c['accent']};
        font-weight: bold;
    }}
    QPushButton#PrimaryButton:hover {{
        background: {c['accent_pressed']};
        color: {c['text']};
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 12px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: #c2c2c2;
        border-radius: 3px;
        min-height: 24px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical:hover {{ background: #a0a0a0; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 12px;
    }}
    QScrollBar::handle:horizontal {{
        background: #c2c2c2;
        border-radius: 3px;
        min-width: 24px;
        margin: 2px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
    QMenu {{
        background: {c['panel']};
        color: {c['text']};
        border: 1px solid {c['border']};
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 24px 6px 18px;
        border-radius: 3px;
    }}
    QMenu::item:selected {{
        background: {c['accent']};
        color: #ffffff;
    }}
    QMenu::separator {{
        height: 1px;
        background: {c['border']};
        margin: 4px 8px;
    }}
    QToolTip {{
        background: {c['panel']};
        color: {c['text']};
        border: 1px solid {c['border']};
        padding: 4px;
    }}
    QFrame#FindBar {{
        background: {c['panel']};
        border-top: 1px solid {c['border']};
    }}
    QTabBar#DocTabs {{
        background: {c['win']};
        border-bottom: 1px solid {c['border']};
    }}
    QTabBar#DocTabs::tab {{
        background: transparent;
        color: {c['subtext']};
        border: 1px solid transparent;
        border-bottom: none;
        padding: 5px 10px;
        margin: 4px 1px 0 1px;
        min-width: 72px;
    }}
    QTabBar#DocTabs::tab:hover:!selected {{
        background: {c['ribbon_hover']};
        color: {c['text']};
    }}
    QTabBar#DocTabs::tab:selected {{
        background: {c['panel']};
        color: {c['text']};
        border: 1px solid {c['border']};
        border-bottom: none;
        border-top: 2px solid {c['accent']};
    }}
    QTabBar#DocTabs::close-button {{
        image: url("{_close_icon(dark)}");
        width: 14px;
        height: 14px;
        margin: 0 2px 0 0;
        border-radius: 3px;
    }}
    QTabBar#DocTabs::close-button:hover {{
        background: {c['ribbon_hover']};
    }}
    """
