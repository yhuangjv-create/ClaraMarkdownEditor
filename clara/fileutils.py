"""导出文件时的冲突处理：覆盖 / 自动编号 / 取消。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QWidget


def unique_path(path: Path) -> Path:
    """若目标已存在，返回同目录下 name (1).ext、name (2).ext … 中第一个可用的路径。"""
    if not path.exists():
        return path
    index = 1
    while True:
        candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def resolve_overwrite(parent: QWidget, i18n, path: Path) -> Path | None:
    """目标存在时询问用户；返回要写入的路径，取消则返回 None。"""
    if not path.exists():
        return path
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle(i18n.t("msg.exists_title"))
    box.setText(i18n.t("msg.exists_text", name=path.name))
    overwrite = box.addButton(i18n.t("msg.exists_overwrite"), QMessageBox.AcceptRole)
    renumber = box.addButton(i18n.t("msg.exists_rename"), QMessageBox.AcceptRole)
    box.addButton(i18n.t("common.cancel"), QMessageBox.RejectRole)
    box.setDefaultButton(renumber)
    box.exec()
    clicked = box.clickedButton()
    if clicked is overwrite:
        return path
    if clicked is renumber:
        return unique_path(path)
    return None
