"""版本备份工具。

每次发版前调用 create_backup()，会在项目的 _backups 目录下
生成一个以「版本号_改动说明」命名的完整副本，例如：
    _backups/1.0.0_初始版本/
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

IGNORE = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    ".git",
    ".idea",
    ".vscode",
    "_backups",
    ".autosave",
    "*.tmp",
)


def _safe_name(note: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|\r\n\t]+', "_", note).strip()
    cleaned = cleaned.strip("_ ")
    return cleaned[:60] if cleaned else "update"


def create_backup(project_root: str | Path, version: str, note: str) -> Path:
    """复制整个项目到 _backups/{version}_{note}/。"""
    root = Path(project_root).resolve()
    folder_name = f"{version}_{_safe_name(note)}"
    backup_root = root / "_backups"
    backup_root.mkdir(parents=True, exist_ok=True)

    target = backup_root / folder_name
    if target.exists():
        stamp = datetime.now().strftime("%H%M%S")
        target = backup_root / f"{folder_name}_{stamp}"

    shutil.copytree(root, target, ignore=IGNORE)

    manifest = target / "BACKUP_INFO.txt"
    manifest.write_text(
        f"版本 / Version: {version}\n"
        f"改动 / Note: {note}\n"
        f"时间 / Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"来源 / From: {root}\n",
        encoding="utf-8",
    )
    return target


if __name__ == "__main__":
    import sys

    from . import __version__

    root = Path(__file__).resolve().parent.parent
    note = " ".join(sys.argv[1:]).strip() or "update"
    path = create_backup(root, __version__, note)
    print(f"Backup created: {path}")
