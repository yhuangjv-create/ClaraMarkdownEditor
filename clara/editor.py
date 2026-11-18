"""编辑区组件。

包含三种模式：
- 源码模式   左：Markdown 源码（带行号）
- 分屏预览   源码 + 右侧可编辑的实时渲染视图，双向同步、滚动联动
- 所见即所得 富文本编辑（内部保存为 Markdown）

另外提供查找栏（FindBar）以及常用 Markdown 片段插入方法。
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QFontMetricsF,
    QPainter,
    QTextBlockFormat,
    QTextCharFormat,
    QTextCursor,
    QTextListFormat,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSplitter,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .i18n import I18n
from .qt_document import CODE_PROP, QUOTE_PROP, document_to_markdown, mark_quote_blocks
from .render import html_to_md, md_to_html

MODE_SOURCE = "source"
MODE_SPLIT = "split"
MODE_WYSIWYG = "wysiwyg"


class LineNumberArea(QWidget):
    def __init__(self, editor: "SourceEditor"):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class SourceEditor(QPlainTextEdit):
    """带行号、当前行高亮、4 空格缩进的 Markdown 源码编辑器。"""

    filesDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dark = False
        self.line_number_area = LineNumberArea(self)

        font = QFont("Cascadia Mono")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(11)
        self.setFont(font)
        self.setTabStopDistance(QFontMetricsF(font).horizontalAdvance(" ") * 4)
        self.setLineWrapMode(QPlainTextEdit.WidgetWidth)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

    # ---------------- 行号 ----------------
    def line_number_area_width(self) -> int:
        digits = max(2, len(str(max(1, self.blockCount()))))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _count: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event) -> None:
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#f6f8fb") if not self.dark else QColor("#252526"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        color = QColor("#9aa5b4") if not self.dark else QColor("#6f7783")

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(color)
                painter.drawText(
                    0,
                    int(top),
                    self.line_number_area.width() - 6,
                    self.fontMetrics().height(),
                    Qt.AlignRight | Qt.AlignVCenter,
                    str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def highlight_current_line(self) -> None:
        if self.isReadOnly():
            self.setExtraSelections([])
            return
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#eef4fd") if not self.dark else QColor("#2a3442"))
        selection.format.setProperty(QTextCharFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])

    # ---------------- 行为 ----------------
    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Tab and not event.modifiers():
            self.insertPlainText("    ")
            return
        if event.key() == Qt.Key_Backtab:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.StartOfLine)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor, 4)
            if cursor.selectedText() == "    ":
                cursor.removeSelectedText()
            return
        super().keyPressEvent(event)

    def set_dark(self, dark: bool) -> None:
        self.dark = dark
        self.highlight_current_line()
        self.line_number_area.update()

    # ---------------- 文件拖拽 ----------------
    def _dropped_files(self, event) -> list[str]:
        mime = event.mimeData()
        if not mime.hasUrls():
            return []
        return [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]

    def dragEnterEvent(self, event) -> None:
        if self._dropped_files(event):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if self._dropped_files(event):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        paths = self._dropped_files(event)
        if paths:
            event.acceptProposedAction()
            self.filesDropped.emit(paths)
            return
        super().dropEvent(event)


class WysiwygEditor(QTextEdit):
    """所见即所得编辑器，文件拖入时交回主窗口处理。"""

    filesDropped = Signal(list)

    def _dropped_files(self, event) -> list[str]:
        mime = event.mimeData()
        if not mime.hasUrls():
            return []
        return [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]

    def dragEnterEvent(self, event) -> None:
        if self._dropped_files(event):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if self._dropped_files(event):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        paths = self._dropped_files(event)
        if paths:
            event.acceptProposedAction()
            self.filesDropped.emit(paths)
            return
        super().dropEvent(event)


class PreviewEditor(WysiwygEditor):
    """分屏预览右侧的富文本视图：渲染后仍可直接编辑。

    Ctrl + 单击可打开链接；普通单击用于放置光标。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Preview")
        self.setAcceptRichText(True)
        self.setFrameShape(QFrame.NoFrame)

    def mouseReleaseEvent(self, event) -> None:
        if event.modifiers() & Qt.ControlModifier:
            anchor = self.anchorAt(event.position().toPoint())
            if anchor:
                QDesktopServices.openUrl(QUrl(anchor))
                return
        super().mouseReleaseEvent(event)


class FindBar(QFrame):
    """底部查找栏。"""

    closeRequested = Signal()

    def __init__(self, target: QPlainTextEdit, i18n: I18n, parent=None):
        super().__init__(parent)
        self.setObjectName("FindBar")
        self.target = target
        self.i18n = i18n

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(6)

        self.edit = QLineEdit()
        self.edit.setMinimumWidth(220)
        layout.addWidget(self.edit)

        self.prev_btn = QToolButton()
        self.next_btn = QToolButton()
        self.prev_btn.setObjectName("MiniButton")
        self.next_btn.setObjectName("MiniButton")
        self.prev_btn.setText("▲")
        self.next_btn.setText("▼")
        layout.addWidget(self.prev_btn)
        layout.addWidget(self.next_btn)

        self.result_label = QLabel("")
        layout.addWidget(self.result_label)
        layout.addStretch(1)

        self.close_btn = QToolButton()
        self.close_btn.setObjectName("MiniButton")
        self.close_btn.setText("✕")
        layout.addWidget(self.close_btn)

        self.edit.returnPressed.connect(lambda: self.find_next(True))
        self.next_btn.clicked.connect(lambda: self.find_next(True))
        self.prev_btn.clicked.connect(lambda: self.find_next(False))
        self.close_btn.clicked.connect(self._close)
        self.edit.textChanged.connect(self._on_text_changed)

        self.retranslate()

    def retranslate(self) -> None:
        self.edit.setPlaceholderText(self.i18n.t("find.placeholder"))
        self.next_btn.setToolTip(self.i18n.t("find.next"))
        self.prev_btn.setToolTip(self.i18n.t("find.prev"))
        self.close_btn.setToolTip(self.i18n.t("find.close"))
        self.result_label.clear()

    def _close(self) -> None:
        self.hide()
        self.closeRequested.emit()
        self.target.setFocus()

    def _on_text_changed(self, text: str) -> None:
        if not text:
            self.result_label.clear()
            return
        self.result_label.setText(self._count_matches(text))

    def _count_matches(self, text: str) -> str:
        content = self.target.toPlainText()
        count = content.count(text) if text else 0
        return self.i18n.t("find.count", n=count) if count else self.i18n.t("find.none")

    def find_next(self, forward: bool = True) -> bool:
        text = self.edit.text()
        if not text:
            return False
        flags = QPlainTextEdit.FindFlags()
        if not forward:
            flags |= QPlainTextEdit.FindBackward
        found = self.target.find(text, flags)
        if not found:
            # 从文档头/尾回绕再找一次
            cursor = self.target.textCursor()
            cursor.movePosition(
                QTextCursor.Start if forward else QTextCursor.End
            )
            self.target.setTextCursor(cursor)
            found = self.target.find(text, flags)
        self.result_label.setText(self._count_matches(text))
        return found

    def open(self) -> None:
        self.show()
        self.edit.setFocus()
        self.edit.selectAll()


class MarkdownEditor(QWidget):
    """源码 / 分屏 / 所见即所得 三模式编辑器。"""

    contentChanged = Signal()
    documentLoaded = Signal()
    cursorMoved = Signal(int, int)  # 行, 列
    modeChanged = Signal(str)
    filesDropped = Signal(list)

    def __init__(self, i18n: I18n, dark: bool = False, parent=None):
        super().__init__(parent)
        self.i18n = i18n
        self.dark = dark
        self._mode = MODE_SPLIT

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(2)
        layout.addWidget(self.splitter, 1)

        self.source = SourceEditor()
        self.source.setPlaceholderText("# 在这里输入 Markdown …")
        self.splitter.addWidget(self.source)

        self.preview = PreviewEditor()
        self.splitter.addWidget(self.preview)

        self.wysiwyg = WysiwygEditor()
        self.wysiwyg.setObjectName("Wysiwyg")
        self.wysiwyg.setAcceptRichText(True)
        self.wysiwyg.setFrameShape(QFrame.NoFrame)
        self.wysiwyg.document().setDocumentMargin(28)
        self.splitter.addWidget(self.wysiwyg)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([600, 600])

        self.find_bar = FindBar(self.source, i18n)
        self.find_bar.hide()
        layout.addWidget(self.find_bar)

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(160)
        self._preview_timer.timeout.connect(self._refresh_preview)

        self._syncing_scroll = False
        self._preview_syncing = False
        self._rich_focus = None

        self.source.textChanged.connect(self._on_source_changed)
        self.source.cursorPositionChanged.connect(self._emit_cursor)
        self.preview.textChanged.connect(self._on_preview_changed)
        self.preview.cursorPositionChanged.connect(self._emit_cursor)
        self.wysiwyg.textChanged.connect(self._on_wysiwyg_changed)
        self.source.filesDropped.connect(self.filesDropped)
        self.preview.filesDropped.connect(self.filesDropped)
        self.wysiwyg.filesDropped.connect(self.filesDropped)

        app = QApplication.instance()
        if app is not None:
            app.focusChanged.connect(self._on_focus_changed)

        self._connect_scrollbars()
        self.set_mode(MODE_SPLIT, emit=False)

    def _on_focus_changed(self, _old, new) -> None:
        """记录最后一次聚焦的可编辑区域，供 Ribbon 按钮判断操作目标。"""
        if new is self.preview or (new is not None and self.preview.isAncestorOf(new)):
            self._rich_focus = self.preview
        elif new is self.source or (new is not None and self.source.isAncestorOf(new)):
            self._rich_focus = None

    def _rich_editor(self):
        """返回当前应接收富文本格式操作的控件；None 表示操作源码。"""
        if self._mode == MODE_WYSIWYG:
            return self.wysiwyg
        if self._mode != MODE_SPLIT:
            return None
        # 点击 Ribbon 按钮时焦点通常仍在编辑区，这里实时校正一次，
        # 避免焦点未发生变化（收不到 focusChanged）时沿用旧目标。
        current = QApplication.focusWidget()
        if current is self.preview or (
            current is not None and self.preview.isAncestorOf(current)
        ):
            self._rich_focus = self.preview
        elif current is self.source or (
            current is not None and self.source.isAncestorOf(current)
        ):
            self._rich_focus = None
        return self.preview if self._rich_focus is self.preview else None

    # ---------------- 滚动同步 ----------------
    def _connect_scrollbars(self) -> None:
        self.source.verticalScrollBar().valueChanged.connect(self._sync_source_to_preview)
        self.preview.verticalScrollBar().valueChanged.connect(self._sync_preview_to_source)

    def _sync_source_to_preview(self, value: int) -> None:
        if self._syncing_scroll or self._mode != MODE_SPLIT:
            return
        source_bar = self.source.verticalScrollBar()
        preview_bar = self.preview.verticalScrollBar()
        if source_bar.maximum() <= 0:
            return
        self._syncing_scroll = True
        ratio = value / source_bar.maximum()
        preview_bar.setValue(int(ratio * preview_bar.maximum()))
        self._syncing_scroll = False

    def _sync_preview_to_source(self, value: int) -> None:
        if self._syncing_scroll or self._mode != MODE_SPLIT:
            return
        source_bar = self.source.verticalScrollBar()
        preview_bar = self.preview.verticalScrollBar()
        if preview_bar.maximum() <= 0:
            return
        self._syncing_scroll = True
        ratio = value / preview_bar.maximum()
        source_bar.setValue(int(ratio * source_bar.maximum()))
        self._syncing_scroll = False

    # ---------------- 内容同步 ----------------
    def _on_source_changed(self) -> None:
        if self._mode != MODE_WYSIWYG:
            self._preview_timer.start()
        self._emit_cursor()
        self.contentChanged.emit()

    def _on_wysiwyg_changed(self) -> None:
        if self._mode == MODE_WYSIWYG:
            self._emit_cursor()
            self.contentChanged.emit()

    def _on_preview_changed(self) -> None:
        """在右侧渲染视图里直接编辑时，把富文本回写成 Markdown 源码。"""
        if self._preview_syncing or self._mode != MODE_SPLIT:
            return
        md = document_to_markdown(self.preview.document())
        self._preview_syncing = True
        self.source.blockSignals(True)
        self.source.setPlainText(md)
        self.source.blockSignals(False)
        self._preview_syncing = False
        self._emit_cursor()
        self.contentChanged.emit()

    def _refresh_preview(self) -> None:
        text = self.source.toPlainText()
        bar = self.preview.verticalScrollBar()
        ratio = bar.value() / bar.maximum() if bar.maximum() else 0.0
        pos = self.preview.textCursor().position()
        self._preview_syncing = True
        self.preview.blockSignals(True)
        self.preview.setHtml(md_to_html(text, dark=self.dark))
        mark_quote_blocks(self.preview.document())
        cursor = self.preview.textCursor()
        cursor.setPosition(min(pos, self.preview.document().characterCount() - 1))
        self.preview.setTextCursor(cursor)
        self.preview.blockSignals(False)
        self._preview_syncing = False
        bar.setValue(round(ratio * bar.maximum()))

    def refresh_preview(self) -> None:
        self._refresh_preview()

    def set_mode(self, mode: str, emit: bool = True) -> None:
        if mode not in (MODE_SOURCE, MODE_SPLIT, MODE_WYSIWYG):
            mode = MODE_SPLIT

        # 离开所见即所得时，把富文本回写成 Markdown
        if self._mode == MODE_WYSIWYG and mode != MODE_WYSIWYG:
            md = document_to_markdown(self.wysiwyg.document())
            self.source.blockSignals(True)
            self.source.setPlainText(md)
            self.source.blockSignals(False)
            self._refresh_preview()

        self._mode = mode

        self.source.setVisible(mode in (MODE_SOURCE, MODE_SPLIT))
        self.preview.setVisible(mode == MODE_SPLIT)
        self.wysiwyg.setVisible(mode == MODE_WYSIWYG)

        if mode == MODE_WYSIWYG:
            html = md_to_html(self.source.toPlainText(), dark=self.dark)
            self.wysiwyg.blockSignals(True)
            self.wysiwyg.setHtml(html)
            mark_quote_blocks(self.wysiwyg.document())
            self.wysiwyg.blockSignals(False)
            self.wysiwyg.setFocus()
        elif mode == MODE_SOURCE:
            self.source.setFocus()
        else:
            self._refresh_preview()
            self.splitter.setSizes([600, 600])

        if emit:
            self.modeChanged.emit(mode)

    @property
    def mode(self) -> str:
        return self._mode

    # ---------------- 文本读写 ----------------
    def get_markdown(self) -> str:
        if self._mode == MODE_WYSIWYG:
            return document_to_markdown(self.wysiwyg.document())
        return self.source.toPlainText()

    def set_markdown(self, text: str) -> None:
        self.source.blockSignals(True)
        self.source.setPlainText(text)
        self.source.blockSignals(False)
        if self._mode == MODE_WYSIWYG:
            self.wysiwyg.blockSignals(True)
            self.wysiwyg.setHtml(md_to_html(text, dark=self.dark))
            mark_quote_blocks(self.wysiwyg.document())
            self.wysiwyg.blockSignals(False)
        self._refresh_preview()
        self.documentLoaded.emit()

    def clear(self) -> None:
        self.set_markdown("")
        self.source.moveCursor(QTextCursor.Start)

    # ---------------- 光标 / 定位 ----------------
    def _emit_cursor(self) -> None:
        if self._mode == MODE_WYSIWYG:
            cursor = self.wysiwyg.textCursor()
        elif self._mode == MODE_SPLIT and self.preview.hasFocus():
            cursor = self.preview.textCursor()
        else:
            cursor = self.source.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.positionInBlock() + 1
        self.cursorMoved.emit(line, col)

    def goto_line(self, line: int) -> None:
        if self._mode == MODE_WYSIWYG:
            self.set_mode(MODE_SOURCE)
        block = self.source.document().findBlockByNumber(max(0, line))
        cursor = QTextCursor(block)
        self.source.setTextCursor(cursor)
        self.source.centerCursor()
        self.source.setFocus()

    def focus_editor(self) -> None:
        if self._mode == MODE_WYSIWYG:
            self.wysiwyg.setFocus()
        else:
            self.source.setFocus()

    # ---------------- 主题 ----------------
    def set_dark(self, dark: bool) -> None:
        self.dark = dark
        self.source.set_dark(dark)
        self._refresh_preview()
        if self._mode == MODE_WYSIWYG:
            pos = self.wysiwyg.textCursor().position()
            self.wysiwyg.blockSignals(True)
            self.wysiwyg.setHtml(md_to_html(self.source.toPlainText(), dark=dark))
            mark_quote_blocks(self.wysiwyg.document())
            self.wysiwyg.blockSignals(False)
            cursor = self.wysiwyg.textCursor()
            cursor.setPosition(min(pos, self.wysiwyg.document().characterCount() - 1))
            self.wysiwyg.setTextCursor(cursor)

    def retranslate(self, i18n: I18n) -> None:
        self.i18n = i18n
        self.find_bar.i18n = i18n
        self.find_bar.retranslate()
        self.source.setPlaceholderText(
            "# 在这里输入 Markdown …" if i18n.lang == "zh" else "# Start writing Markdown here…"
        )

    # ---------------- 源码模式编辑辅助 ----------------
    def _wrap_source_selection(self, before: str, after: str) -> None:
        cursor = self.source.textCursor()
        selected = cursor.selectedText()
        if selected:
            cursor.insertText(f"{before}{selected}{after}")
        else:
            cursor.insertText(f"{before}{after}")
            cursor.movePosition(QTextCursor.Left, QTextCursor.MoveAnchor, len(after))
            self.source.setTextCursor(cursor)
        self.source.setFocus()

    def _prefix_selected_lines(self, compute_prefix) -> None:
        cursor = self.source.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        text = self.source.toPlainText()
        start_line = text.count("\n", 0, start)
        end_line = text.count("\n", 0, end)
        lines = text.split("\n")
        for idx in range(start_line, min(end_line + 1, len(lines))):
            lines[idx] = compute_prefix(lines[idx])
        new_text = "\n".join(lines)
        cursor.blockSignals(True)
        self.source.setPlainText(new_text)
        cursor.blockSignals(False)
        line_start = sum(len(l) + 1 for l in lines[:start_line])
        new_cursor = self.source.textCursor()
        new_cursor.setPosition(min(line_start, len(new_text)))
        self.source.setTextCursor(new_cursor)
        self.source.setFocus()
        self._refresh_preview()
        self.contentChanged.emit()

    # ---------------- 格式操作：两种模式统一入口 ----------------
    def _rich_style_active(self, target, getter) -> bool:
        """判断当前选区（或光标处）是否整体处于某种字符样式。"""
        cursor = target.textCursor()
        if not cursor.hasSelection():
            return bool(getter(cursor.charFormat()))
        probe = QTextCursor(target.document())
        probe.setPosition(cursor.selectionStart())
        end = cursor.selectionEnd()
        seen = False
        while probe.position() < end:
            probe.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
            if not probe.selectedText().strip():
                continue
            seen = True
            if not getter(probe.charFormat()):
                return False
        return seen or bool(getter(cursor.charFormat()))

    def toggle_bold(self) -> None:
        target = self._rich_editor()
        if target is not None:
            active = self._rich_style_active(
                target, lambda f: f.fontWeight() >= QFont.Bold
            )
            fmt = QTextCharFormat()
            fmt.setFontWeight(QFont.Normal if active else QFont.Bold)
            target.mergeCurrentCharFormat(fmt)
            return
        cursor = self.source.textCursor()
        selected = cursor.selectedText()
        if selected.startswith("**") and selected.endswith("**") and len(selected) > 4:
            cursor.insertText(selected[2:-2])
            return
        self._wrap_source_selection("**", "**")

    def toggle_italic(self) -> None:
        target = self._rich_editor()
        if target is not None:
            active = self._rich_style_active(target, lambda f: f.fontItalic())
            fmt = QTextCharFormat()
            fmt.setFontItalic(not active)
            target.mergeCurrentCharFormat(fmt)
            return
        self._wrap_source_selection("*", "*")

    def toggle_strike(self) -> None:
        target = self._rich_editor()
        if target is not None:
            active = self._rich_style_active(target, lambda f: f.fontStrikeOut())
            fmt = QTextCharFormat()
            fmt.setFontStrikeOut(not active)
            target.mergeCurrentCharFormat(fmt)
            return
        cursor = self.source.textCursor()
        selected = cursor.selectedText()
        if selected.startswith("~~") and selected.endswith("~~") and len(selected) > 4:
            cursor.insertText(selected[2:-2])
            return
        self._wrap_source_selection("~~", "~~")

    def toggle_inline_code(self) -> None:
        target = self._rich_editor()
        if target is not None:
            fmt = QTextCharFormat()
            fmt.setFontFamilies(["Consolas"])
            fmt.setFontFixedPitch(True)
            target.mergeCurrentCharFormat(fmt)
            return
        self._wrap_source_selection("`", "`")

    def set_heading(self, level: int) -> None:
        prefix = "#" * level + " "
        target = self._rich_editor()
        if target is not None:
            cursor = target.textCursor()
            block_fmt = cursor.blockFormat()
            block_fmt.setHeadingLevel(level)
            cursor.setBlockFormat(block_fmt)
            fmt = QTextCharFormat()
            sizes = {1: 24, 2: 20, 3: 17}
            fmt.setFontPointSize(sizes.get(level, 15))
            fmt.setFontWeight(QFont.Bold)
            cursor.mergeCharFormat(fmt)
            return

        def apply(line: str) -> str:
            stripped = line.lstrip("#").lstrip()
            if line.startswith(prefix):
                return stripped
            return prefix + line

        self._prefix_selected_lines(apply)

    def toggle_list(self, ordered: bool = False) -> None:
        target = self._rich_editor()
        if target is not None:
            cursor = target.textCursor()
            current = cursor.currentList()
            if current is not None:
                current.remove(cursor.block())
                return
            fmt = QTextListFormat()
            fmt.setStyle(
                QTextListFormat.ListDecimal if ordered else QTextListFormat.ListDisc
            )
            fmt.setIndent(1)
            cursor.createList(fmt)
            target.setFocus()
            return

        def apply(line: str) -> str:
            stripped = line.lstrip()
            if ordered:
                if stripped[:2].rstrip(".").isdigit() or stripped.startswith("1. "):
                    return stripped.split(" ", 1)[1] if " " in stripped else ""
                return "1. " + stripped
            if stripped.startswith(("- ", "* ", "+ ")):
                return stripped[2:]
            return "- " + stripped

        self._prefix_selected_lines(apply)

    def toggle_quote(self) -> None:
        target = self._rich_editor()
        if target is not None:
            cursor = target.textCursor()
            block_fmt = cursor.blockFormat()
            active = bool(block_fmt.property(QUOTE_PROP))
            block_fmt.setProperty(QUOTE_PROP, not active)
            block_fmt.setLeftMargin(0 if active else 18)
            cursor.setBlockFormat(block_fmt)
            target.setFocus()
            return

        def apply(line: str) -> str:
            if line.startswith("> "):
                return line[2:]
            return "> " + line

        self._prefix_selected_lines(apply)

    # ---------------- 插入片段 ----------------
    def _insert(self, text: str) -> None:
        target = self._rich_editor()
        if target is not None:
            cursor = target.textCursor()
            cursor.insertText(text)
            target.setTextCursor(cursor)
            target.setFocus()
            return
        cursor = self.source.textCursor()
        cursor.insertText(text)
        self.source.setTextCursor(cursor)
        self.source.setFocus()
        self._refresh_preview()
        self.contentChanged.emit()

    def insert_link(self) -> None:
        target = self._rich_editor()
        if target is not None:
            cursor = target.textCursor()
            text = cursor.selectedText() or "链接文字"
            cursor.insertText(f"{text} (https://)")
            target.setTextCursor(cursor)
            target.setFocus()
            return
        cursor = self.source.textCursor()
        text = cursor.selectedText() or "链接文字"
        cursor.insertText(f"[{text}](https://)")
        self.source.setTextCursor(cursor)
        self.source.setFocus()

    def insert_image(self, path: str = "") -> None:
        if path:
            src = Path(path).as_posix()
            alt = Path(path).stem
        else:
            src, alt = "图片路径.png", "图片"
        self._insert(f"![{alt}]({src})")

    def insert_table(self) -> None:
        table = (
            "\n| 列 1 | 列 2 | 列 3 |\n"
            "| --- | --- | --- |\n"
            "| 内容 | 内容 | 内容 |\n\n"
        )
        self._insert(table)

    def insert_hr(self) -> None:
        self._insert("\n---\n\n")

    def insert_code_block(self) -> None:
        target = self._rich_editor()
        if target is not None:
            cursor = target.textCursor()
            cursor.insertBlock()
            block_fmt = QTextBlockFormat()
            block_fmt.setProperty(CODE_PROP, True)
            cursor.setBlockFormat(block_fmt)
            char_fmt = QTextCharFormat()
            char_fmt.setFontFamilies(["Consolas"])
            char_fmt.setFontFixedPitch(True)
            cursor.setCharFormat(char_fmt)
            cursor.insertText("代码")
            cursor.insertBlock()
            cursor.setBlockFormat(QTextBlockFormat())
            target.setTextCursor(cursor)
            target.setFocus()
            return
        self._insert("\n```\n\n```\n\n")
