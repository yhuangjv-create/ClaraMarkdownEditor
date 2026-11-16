"""文档大纲面板：列出所有标题，点击可跳转到对应行。"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from .i18n import I18n
from .render import iter_headings


class OutlinePanel(QWidget):
    headingActivated = Signal(int)  # 行号（从 0 开始）

    def __init__(self, i18n: I18n, parent=None):
        super().__init__(parent)
        self.i18n = i18n
        self.setMinimumWidth(150)
        self.setMaximumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.title_label = QLabel(self.i18n.t("act.outline"))
        self.title_label.setObjectName("PanelTitle")
        layout.addWidget(self.title_label)

        self.list = QListWidget()
        self.list.setObjectName("Outline")
        self.list.setFrameShape(QListWidget.NoFrame)
        self.list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list, 1)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        line = item.data(Qt.UserRole)
        if isinstance(line, int):
            self.headingActivated.emit(line)

    def refresh(self, md_text: str) -> None:
        self.list.clear()
        for level, text, line in iter_headings(md_text):
            item = QListWidgetItem(("    " * (level - 1)) + text)
            item.setData(Qt.UserRole, line)
            weight = "bold" if level <= 2 else "normal"
            size = {1: "10pt", 2: "9pt"}.get(level, "8.5pt")
            item.setToolTip(text)
            item.setToolTip(f"L{line + 1} · {text}")
            font = item.font()
            font.setBold(weight == "bold")
            font.setPointSizeF({"10pt": 10.0, "9pt": 9.0, "8.5pt": 8.5}[size])
            item.setFont(font)
            self.list.addItem(item)

    def retranslate(self, i18n: I18n) -> None:
        self.i18n = i18n
        self.title_label.setText(i18n.t("act.outline"))
