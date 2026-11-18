"""用户偏好设置（基于 QSettings 存储到注册表）。

集中管理语言、主题、分屏模式、自动保存、最近文件等键值。
"""

from __future__ import annotations

import json
import time
from pathlib import Path

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
            return max(10, int(self.value("autosave/interval", 120)))
        except (TypeError, ValueError):
            return 120

    @autosave_interval.setter
    def autosave_interval(self, seconds: int) -> None:
        self.set_value("autosave/interval", int(seconds))

    # ---------------- 会话恢复 ----------------
    @property
    def restore_session(self) -> bool:
        return str(self.value("session/restore", "true")).lower() == "true"

    @restore_session.setter
    def restore_session(self, enabled: bool) -> None:
        self.set_value("session/restore", "true" if enabled else "false")

    # ---------------- 最近文件 ----------------
    def recent_files(self) -> list[str]:
        raw = self.value("files/recent", [])
        if raw is None:
            return []
        if isinstance(raw, str):
            return [raw] if raw else []
        return [str(x) for x in raw]

    @property
    def recent_limit(self) -> int:
        try:
            return min(50, max(1, int(self.value("files/recent_limit", 10))))
        except (TypeError, ValueError):
            return 10

    @recent_limit.setter
    def recent_limit(self, count: int) -> None:
        count = min(50, max(1, int(count)))
        self.set_value("files/recent_limit", count)
        files = self.recent_files()[:count]
        self.set_value("files/recent", files)
        times = self._recent_times()
        self.set_value("files/recent_times", json.dumps({p: times[p] for p in files if p in times}))

    @property
    def recent_hidden(self) -> bool:
        return str(self.value("files/recent_hidden", "false")).lower() == "true"

    @recent_hidden.setter
    def recent_hidden(self, hidden: bool) -> None:
        self.set_value("files/recent_hidden", "true" if hidden else "false")

    @property
    def recent_days(self) -> int:
        try:
            return max(0, int(self.value("files/recent_days", 0)))
        except (TypeError, ValueError):
            return 0

    @recent_days.setter
    def recent_days(self, days: int) -> None:
        self.set_value("files/recent_days", max(0, int(days)))

    def _recent_times(self) -> dict[str, float]:
        raw = self.value("files/recent_times", "{}")
        try:
            data = json.loads(str(raw))
            return {str(k): float(v) for k, v in data.items()}
        except (TypeError, ValueError):
            return {}

    def recent_time(self, path: str) -> float:
        timestamp = self._recent_times().get(path)
        if timestamp is not None:
            return timestamp
        try:
            return Path(path).stat().st_mtime
        except OSError:
            return 0.0

    def visible_recent_files(self) -> list[str]:
        files = [p for p in self.recent_files() if Path(p).exists()]
        days = self.recent_days
        if days > 0:
            cutoff = time.time() - days * 86400
            files = [p for p in files if self.recent_time(p) >= cutoff]
        return files[: self.recent_limit]

    def add_recent_file(self, path: str) -> None:
        files = [p for p in self.recent_files() if p != path]
        files.insert(0, path)
        files = files[: self.recent_limit]
        times = self._recent_times()
        times[path] = time.time()
        self.set_value("files/recent", files)
        self.set_value("files/recent_times", json.dumps({p: times[p] for p in files if p in times}))

    def remove_recent_file(self, path: str) -> None:
        self.set_value("files/recent", [p for p in self.recent_files() if p != path])
        times = self._recent_times()
        times.pop(path, None)
        self.set_value("files/recent_times", json.dumps(times))

    def clear_recent_files(self) -> None:
        self.set_value("files/recent", [])
        self.set_value("files/recent_times", "{}")

    @property
    def last_dir(self) -> str:
        return str(self.value("files/last_dir", ""))

    @last_dir.setter
    def last_dir(self, path: str) -> None:
        self.set_value("files/last_dir", path)
