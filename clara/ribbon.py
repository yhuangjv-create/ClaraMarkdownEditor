"""仿 Word 的 Ribbon 功能区。

结构：
    ┌ 顶部：文件 | 开始 | 插入 | 视图 | 转换 …………… [文档名] [中/EN] [主题] ┐
    └ 主体：当前选项卡对应的若干按钮分组（每组底部有分组标题）            ┘

点击按钮时发出 actionTriggered(动作键)，由主窗口统一分发处理。
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .icons import text_icon
from .i18n import I18n
from .theme import ACCENT

# 每个选项卡 -> [(分组标题键, [(动作键, 图标文字), ...]), ...]
RIBBON_LAYOUT: list[tuple[str, list[tuple[str, list[tuple[str, str]]]]]] = [
    (
        "tab.file",
        [
            (
                "group.doc",
                [
                    ("act.new", "+"),
                    ("act.open", "O"),
                    ("act.recent", "R"),
                    ("act.save", "S"),
                    ("act.save_as", "A"),
                ],
            ),
            (
                "group.convert",
                [
                    ("act.export_word", "W"),
                    ("act.export_pdf", "PDF"),
                    ("act.import_word", "W<"),
                    ("act.import_pdf", "P<"),
                ],
            ),
            (
                "group.view",
                [
                    ("act.mode_source", "MD"),
                    ("act.mode_split", "||"),
                    ("act.mode_wysiwyg", "Aa"),
                ],
            ),
        ],
    ),
    (
        "tab.home",
        [
            (
                "group.clipboard",
                [
                    ("act.undo", "<-"),
                    ("act.redo", "->"),
                ],
            ),
            (
                "group.font",
                [
                    ("act.bold", "B"),
                    ("act.italic", "I"),
                    ("act.strike", "S"),
                    ("act.inline_code", "</>"),
                ],
            ),
            (
                "group.paragraph",
                [
                    ("act.h1", "H1"),
                    ("act.h2", "H2"),
                    ("act.h3", "H3"),
                    ("act.ul", "*"),
                    ("act.ol", "1."),
                    ("act.quote", ">"),
                ],
            ),
            ("group.editing", [("act.find", "Q")]),
        ],
    ),
    (
        "tab.insert",
        [
            (
                "group.insert",
                [
                    ("act.link", "lnk"),
                    ("act.image", "IMG"),
                    ("act.table", "TBL"),
                    ("act.hr", "---"),
                    ("act.code_block", "{ }"),
                ],
            ),
        ],
    ),
    (
        "tab.settings",
        [
            (
                "group.tools",
                [
                    ("act.outline", "="),
                    ("act.autosave", "AS"),
                    ("act.about", "i"),
                ],
            ),
        ],
    ),
    (
        "tab.convert",
        [
            (
                "group.convert",
                [
                    ("act.convert_center", "<>"),
                    ("act.md2docx", "M>W"),
                    ("act.md2pdf", "M>P"),
                    ("act.docx2md", "W>M"),
                    ("act.pdf2md", "P>M"),
                ],
            ),
        ],
    ),
]


class RibbonButton(QToolButton):
    def __init__(self, action_key: str, icon_text: str, label: str, dark: bool, parent=None):
        super().__init__(parent)
        self.action_key = action_key
        self.icon_text = icon_text
        self.setObjectName("RibbonButton")
        self.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.setIconSize(QSize(22, 22))
        self.setFixedHeight(60)
        self.setMinimumWidth(56)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.apply_style(label, dark)

    def apply_style(self, label: str, dark: bool) -> None:
        self.setText(label)
        self.setToolTip(label)
        effects = {
            "act.italic": {"italic": True},
            "act.strike": {"strike": True},
        }.get(self.action_key, {})
        self.setIcon(
            text_icon(
                self.icon_text,
                size=22,
                dark=dark,
                color="#cfe1ff" if dark else ACCENT,
                **effects,
            )
        )


class RibbonGroup(QFrame):
    """一组按钮 + 底部标题。"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("GroupBox")
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(6, 4, 6, 2)
        self._layout.setSpacing(2)

        self.buttons_row = QHBoxLayout()
        self.buttons_row.setContentsMargins(0, 0, 0, 0)
        self.buttons_row.setSpacing(2)
        self._layout.addLayout(self.buttons_row)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("GroupTitle")
        self.title_label.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self._layout.addWidget(self.title_label)


class RibbonBar(QWidget):
    actionTriggered = Signal(str)
    languageToggled = Signal()
    themeToggled = Signal()
    collapseToggled = Signal(bool)

    def __init__(self, i18n: I18n, dark: bool = False, parent=None):
        super().__init__(parent)
        self.i18n = i18n
        self.dark = dark
        self._current_tab = 0
        self._body_visible = True

        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        self._top = QWidget()
        self._top.setObjectName("RibbonTop")
        self._top_layout = QHBoxLayout(self._top)
        self._top_layout.setContentsMargins(8, 2, 8, 0)
        self._top_layout.setSpacing(2)
        self._root.addWidget(self._top)

        self._body = QWidget()
        self._body.setObjectName("RibbonBody")
        self._body_layout = QHBoxLayout(self._body)
        self._body_layout.setContentsMargins(6, 2, 6, 2)
        self._body_layout.setSpacing(0)
        self._root.addWidget(self._body)

        self._tab_buttons: list[QToolButton] = []
        self._pages: list[QWidget] = []
        self._action_buttons: dict[str, RibbonButton] = {}
        self.rebuild()

    # ------------------------------------------------------------------
    def rebuild(self) -> None:
        """按当前语言 / 主题重新生成整个功能区（切换语言、主题时调用）。"""
        index = self._current_tab
        self._clear(self._top_layout)
        self._clear(self._body_layout)
        self._tab_buttons.clear()
        self._pages.clear()
        self._action_buttons.clear()

        for tab_key, _groups in RIBBON_LAYOUT:
            btn = QToolButton()
            btn.setObjectName("RibbonTab")
            btn.setText(self.i18n.t(tab_key))
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(self.i18n.t(tab_key))
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            btn.setMinimumWidth(btn.fontMetrics().horizontalAdvance(btn.text()) + 30)
            btn.clicked.connect(lambda _=False, b=btn: self._on_tab_clicked(b))
            self._top_layout.addWidget(btn)
            self._tab_buttons.append(btn)

        self._top_layout.addStretch(1)

        self.doc_label = QLabel("")
        self.doc_label.setObjectName("DocTitle")
        self.doc_label.setMaximumWidth(260)
        self._top_layout.addWidget(self.doc_label)

        self.lang_button = QToolButton()
        self.lang_button.setObjectName("MiniButton")
        self.lang_button.setText(self.i18n.t("act.lang"))
        self.lang_button.setToolTip("中文 / English")
        self.lang_button.setCursor(Qt.PointingHandCursor)
        self.lang_button.clicked.connect(self.languageToggled.emit)
        self._top_layout.addWidget(self.lang_button)

        self.theme_button = QToolButton()
        self.theme_button.setObjectName("MiniButton")
        self.theme_button.setText(self._theme_label())
        self.theme_button.setToolTip(self._theme_label())
        self.theme_button.setCursor(Qt.PointingHandCursor)
        self.theme_button.clicked.connect(self.themeToggled.emit)
        self._top_layout.addWidget(self.theme_button)

        self.collapse_button = QToolButton()
        self.collapse_button.setObjectName("MiniButton")
        self.collapse_button.setText("^" if self._body_visible else "v")
        self.collapse_button.setToolTip("Ribbon")
        self.collapse_button.setCursor(Qt.PointingHandCursor)
        self.collapse_button.clicked.connect(self._toggle_collapse)
        self._top_layout.addWidget(self.collapse_button)

        for btn in (self.lang_button, self.theme_button, self.collapse_button):
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            btn.setMinimumWidth(btn.fontMetrics().horizontalAdvance(btn.text()) + 18)

        for _tab_key, groups in RIBBON_LAYOUT:
            page = QWidget()
            page_layout = QHBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setSpacing(0)
            for group_key, buttons in groups:
                group = RibbonGroup(self.i18n.t(group_key))
                for action_key, icon_text in buttons:
                    button = RibbonButton(
                        action_key,
                        icon_text,
                        self._theme_label() if action_key == "act.theme" else self.i18n.t(action_key),
                        self.dark,
                    )
                    button.clicked.connect(
                        lambda _=False, k=action_key: self.actionTriggered.emit(k)
                    )
                    group.buttons_row.addWidget(button)
                    self._action_buttons[action_key] = button
                page_layout.addWidget(group)
            page_layout.addStretch(1)
            self._pages.append(page)

        for page in self._pages:
            self._body_layout.addWidget(page)
            page.setVisible(False)

        self._current_tab = min(index, len(self._pages) - 1) if self._pages else 0
        self.set_tab(self._current_tab)
        self._body.setVisible(self._body_visible)

    @staticmethod
    def _clear(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout() is not None:
                RibbonBar._clear(item.layout())

    # ------------------------------------------------------------------
    def _on_tab_clicked(self, button: QToolButton) -> None:
        try:
            index = self._tab_buttons.index(button)
        except ValueError:
            return
        self.set_tab(index)
        if not self._body_visible:
            self._body_visible = True
            self._body.setVisible(True)
            self.collapse_button.setText("^")

    def set_tab(self, index: int) -> None:
        if not self._pages:
            return
        index = max(0, min(index, len(self._pages) - 1))
        self._current_tab = index
        for i, page in enumerate(self._pages):
            page.setVisible(i == index)
        for i, btn in enumerate(self._tab_buttons):
            btn.setChecked(i == index)

    def tab_of_action(self) -> int:
        return self._current_tab

    def _toggle_collapse(self) -> None:
        self._body_visible = not self._body_visible
        self._body.setVisible(self._body_visible)
        self.collapse_button.setText("^" if self._body_visible else "v")
        self.collapseToggled.emit(self._body_visible)

    def set_document_title(self, title: str) -> None:
        if hasattr(self, "doc_label"):
            self.doc_label.setText(title)

    def button_for(self, action_key: str) -> RibbonButton | None:
        """返回动作对应的按钮（用于把下拉菜单挂到按钮下方）。"""
        return self._action_buttons.get(action_key)

    def _theme_label(self) -> str:
        """按钮显示“将切换到的主题”：浅色时显示深色主题，反之亦然。"""
        return self.i18n.t("act.theme_light" if self.dark else "act.theme")

    def set_dark(self, dark: bool) -> None:
        self.dark = dark
        self.rebuild()

    def set_language(self, i18n: I18n) -> None:
        self.i18n = i18n
        self.rebuild()
