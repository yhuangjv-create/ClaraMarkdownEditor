"""导出文件时的冲突处理：覆盖 / 自动编号 / 取消。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QMessageBox, QWidget

_FILTER_KEYS = {".docx": "filter.docx", ".pdf": "filter.pdf", ".md": "filter.md"}


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
        filters = i18n.t(_FILTER_KEYS.get(path.suffix.lower(), "filter.all"))
        chosen, _ = QFileDialog.getSaveFileName(
            parent, i18n.t("act.save_as"), str(unique_path(path)), filters
        )
        if not chosen:
            return None
        chosen_path = Path(chosen)
        if not chosen_path.suffix:
            chosen_path = chosen_path.with_suffix(path.suffix)
        return chosen_path
    return None


def notify_exported(parent: QWidget, i18n, message: str, path: str) -> None:
    """导出完成提示：可「直接打开」生成的文件，或点「确定」结束。"""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Information)
    box.setWindowTitle(i18n.t("common.info"))
    box.setText(message)
    open_btn = box.addButton(i18n.t("common.open_file"), QMessageBox.AcceptRole)
    ok_btn = box.addButton(i18n.t("common.ok"), QMessageBox.AcceptRole)
    box.setDefaultButton(ok_btn)
    box.exec()
    if box.clickedButton() is open_btn:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
