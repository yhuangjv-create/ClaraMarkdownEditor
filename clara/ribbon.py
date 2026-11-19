"""仿 Word 的 Ribbon 功能区。

结构：
    ┌ 顶部：文件 | 开始 | 插入 | 视图 | 转换 …………… [文档名] [中/EN] [主题] ┐
    └ 主体：当前选项卡对应的若干按钮分组（每组底部有分组标题）            ┘

点击按钮时发出 actionTriggered(动作键)，由主窗口统一分发处理。
"""

from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen
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

# 需要显示「按下」状态的开关类按钮
TOGGLE_ACTIONS = {"act.autosave", "act.restore_session"}

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
                    ("act.outline", "="),
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
    (
        "tab.settings",
        [
            (
                "group.tools",
                [
                    ("act.autosave", "AS"),
                    ("act.restore_session", "RS"),
                    ("act.about", "i"),
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


class RibbonToggleButton(RibbonButton):
    """可保持「按下」外观的 Ribbon 按钮（自动保存 / 恢复会话开关）。

    激活时呈下陷效果：底色叠加、顶部内阴影、底部高光与内描边，
    状态变化通过 QVariantAnimation 平滑过渡。
    """

    def __init__(self, action_key: str, icon_text: str, label: str, dark: bool, parent=None):
        super().__init__(action_key, icon_text, label, dark, parent)
        self._dark = dark
        self._active = False
        self._hover = False
        self._level = 0.0
        self._anim = QVariantAnimation(self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_anim_value)
        # 背景与描边改由 paintEvent 绘制，避免样式表覆盖动画
        self.setStyleSheet(
            "QToolButton, QToolButton:hover, QToolButton:pressed {"
            " background: transparent; border: none; }"
        )

    def set_active(self, active: bool, animate: bool = True) -> None:
        self._active = bool(active)
        self._anim.stop()
        target = 1.0 if self._active else 0.0
        if not animate:
            self._level = target
            self.update()
            return
        self._anim.setStartValue(self._level)
        self._anim.setEndValue(target)
        self._anim.start()

    def is_active(self) -> bool:
        return self._active

    def _on_anim_value(self, value) -> None:
        self._level = float(value)
        self.update()

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        radius = 5.0
        level = self._level
        hover = self._hover and not self._active

        if level > 0.001 or hover:
            if self._dark:
                fill = QColor("#3b4b60") if level > 0.001 else QColor("#313d4d")
                border = QColor("#4a86d8")
            else:
                fill = QColor("#d3e2f7") if level > 0.001 else QColor("#e8f0fb")
                border = QColor("#2b579a")
            fill.setAlphaF(level if level > 0.001 else 0.9)
            painter.setPen(Qt.NoPen)
            painter.setBrush(fill)
            painter.drawRoundedRect(rect, radius, radius)

            if level > 0.001:
                inner = rect.adjusted(0.5, 0.5, -0.5, -0.5)
                # 顶部内阴影：让按钮看起来凹下去
                shadow = QLinearGradient(
                    inner.topLeft(),
                    QPointF(inner.left(), inner.top() + inner.height() * 0.55),
                )
                shadow.setColorAt(0.0, QColor(0, 0, 0, int(60 * level)))
                shadow.setColorAt(1.0, QColor(0, 0, 0, 0))
                painter.setBrush(shadow)
                painter.drawRoundedRect(inner, radius - 0.5, radius - 0.5)
                # 底部高光：强化下陷层次
                highlight = QLinearGradient(
                    inner.bottomLeft(),
                    QPointF(inner.left(), inner.bottom() - inner.height() * 0.35),
                )
                highlight.setColorAt(0.0, QColor(255, 255, 255, int(90 * level)))
                highlight.setColorAt(1.0, QColor(255, 255, 255, 0))
                painter.setBrush(highlight)
                painter.drawRoundedRect(inner, radius - 0.5, radius - 0.5)

                border.setAlphaF(level)
                painter.setPen(QPen(border, 1.2))
            else:
                border.setAlphaF(0.6)
                painter.setPen(QPen(border, 1.0))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(rect, radius, radius)

        painter.end()
        super().paintEvent(event)


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
        self._toggle_states: dict[str, bool] = {key: False for key in TOGGLE_ACTIONS}
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
                    button_class = (
                        RibbonToggleButton
                        if action_key in TOGGLE_ACTIONS
                        else RibbonButton
                    )
                    button = button_class(
                        action_key,
                        icon_text,
                        self._theme_label() if action_key == "act.theme" else self.i18n.t(action_key),
                        self.dark,
                    )
                    if isinstance(button, RibbonToggleButton):
                        button.set_active(
                            self._toggle_states.get(action_key, False), animate=False
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

    def set_tab_key(self, key: str) -> None:
        """按选项卡键切换（避免依赖布局里的下标）。"""
        keys = [tab_key for tab_key, _groups in RIBBON_LAYOUT]
        if key in keys:
            self.set_tab(keys.index(key))

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

    def set_action_active(
        self, action_key: str, active: bool, animate: bool = True
    ) -> None:
        """更新开关类按钮的按下状态（重建功能区后仍保持）。"""
        if action_key not in TOGGLE_ACTIONS:
            return
        self._toggle_states[action_key] = bool(active)
        button = self._action_buttons.get(action_key)
        if isinstance(button, RibbonToggleButton):
            button.set_active(active, animate)

    def _theme_label(self) -> str:
        """按钮显示“将切换到的主题”：浅色时显示深色主题，反之亦然。"""
        return self.i18n.t("act.theme_light" if self.dark else "act.theme")

    def set_dark(self, dark: bool) -> None:
        self.dark = dark
        self.rebuild()

    def set_language(self, i18n: I18n) -> None:
        self.i18n = i18n
        self.rebuild()
