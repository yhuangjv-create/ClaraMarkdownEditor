"""用户偏好设置（基于 QSettings 存储到注册表）。

集中管理语言、主题、分屏模式、自动保存、最近文件等键值。
"""

from __future__ import annotations

from PySide6.QtCore import QSettings

from . import APP_NAME, ORG_NAME


class Settings:
    def __init__(self) -> None:
        self._s = QSettings(ORG_NAME, APP_NAME)

    # ---------------- 基础读写 ----------------
    def value(self, key: str, default=None):
        return self._s.value(key, default)

    def set_value(self, key: str, value) -> None:
        self._s.setValue(key, value)
        self._s.sync()

    # ---------------- 语言与主题 ----------------
    @property
    def language(self) -> str:
        return str(self.value("ui/language", "zh"))

    @language.setter
    def language(self, lang: str) -> None:
        self.set_value("ui/language", lang)

    @property
    def dark_mode(self) -> bool:
        return str(self.value("ui/dark", "false")).lower() == "true"

    @dark_mode.setter
    def dark_mode(self, enabled: bool) -> None:
        self.set_value("ui/dark", "true" if enabled else "false")

    # ---------------- 编辑器状态 ----------------
    @property
    def editor_mode(self) -> str:
        return str(self.value("editor/mode", "split"))

    @editor_mode.setter
    def editor_mode(self, mode: str) -> None:
        self.set_value("editor/mode", mode)

    @property
    def outline_visible(self) -> bool:
        return str(self.value("editor/outline", "true")).lower() == "true"

    @outline_visible.setter
    def outline_visible(self, visible: bool) -> None:
        self.set_value("editor/outline", "true" if visible else "false")

    # ---------------- 自动保存 ----------------
    @property
    def autosave_enabled(self) -> bool:
        return str(self.value("autosave/enabled", "true")).lower() == "true"

    @autosave_enabled.setter
    def autosave_enabled(self, enabled: bool) -> None:
        self.set_value("autosave/enabled", "true" if enabled else "false")

    @property
    def autosave_interval(self) -> int:
        try:
            return max(10, int(self.value("autosave/interval", 60)))
        except (TypeError, ValueError):
            return 60

    @autosave_interval.setter
    def autosave_interval(self, seconds: int) -> None:
        self.set_value("autosave/interval", int(seconds))

    # ---------------- 最近文件 ----------------
    def recent_files(self) -> list[str]:
        raw = self.value("files/recent", [])
        if raw is None:
            return []
        if isinstance(raw, str):
            return [raw] if raw else []
        return [str(x) for x in raw]

    def add_recent_file(self, path: str, limit: int = 10) -> None:
        files = [p for p in self.recent_files() if p != path]
        files.insert(0, path)
        self.set_value("files/recent", files[:limit])

    @property
    def last_dir(self) -> str:
        return str(self.value("files/last_dir", ""))

    @last_dir.setter
    def last_dir(self, path: str) -> None:
        self.set_value("files/last_dir", path)
