"""格式转换中心页面。

界面自上而下：
1. 标题与说明
2. 源文件选择 / 转换方向 / 纸张 / 页边距 / 字号
3. 左右对比预览：左侧源文件效果，右侧目标格式效果
4. 差异概览色带（绿=新增，红=删除，橙=修改，灰=相同）
5. 底部「执行转换并保存」
"""

from __future__ import annotations

import difflib
from pathlib import Path

from PySide6.QtCore import QMargins, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

try:  # QtPdf 随 PySide6 一起安装，缺失时退回文字预览
    from PySide6.QtPdf import QPdfDocument
    from PySide6.QtPdfWidgets import QPdfView
except ImportError:  # pragma: no cover
    QPdfDocument = None
    QPdfView = None

PDF_PREVIEW_AVAILABLE = QPdfView is not None

from .converter import (
    DIRECTIONS,
    DIRECTION_SOURCE,
    ConversionOptions,
    convert,
    source_preview,
    target_preview,
    target_extension,
)
from .fileutils import notify_exported, resolve_overwrite
from .i18n import I18n
from .render import html_to_plain_text

DIRECTION_KEYS = {
    "md2docx": "act.md2docx",
    "md2pdf": "act.md2pdf",
    "docx2md": "act.docx2md",
    "pdf2md": "act.pdf2md",
}


class DiffStrip(QWidget):
    """按行差异绘制的彩色概览条。"""

    COLORS = {
        "equal": QColor("#d6dde8"),
        "insert": QColor("#54b06b"),
        "delete": QColor("#dd5f5f"),
        "replace": QColor("#e2a33c"),
    }
    COLORS_DARK = {
        "equal": QColor("#3c424b"),
        "insert": QColor("#4e9e62"),
        "delete": QColor("#b85050"),
        "replace": QColor("#c08a34"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(18)
        self.segments: list[tuple[str, int]] = []
        self.counts = {"insert": 0, "delete": 0, "replace": 0}
        self.dark = False

    def set_dark(self, dark: bool) -> None:
        self.dark = dark
        self.update()

    def _colors(self) -> dict:
        return self.COLORS_DARK if self.dark else self.COLORS

    def set_texts(self, left: str, right: str) -> None:
        left_lines = left.splitlines()
        right_lines = right.splitlines()
        if not left_lines and not right_lines:
            self.segments = []
            self.counts = {"insert": 0, "delete": 0, "replace": 0}
            self.update()
            return

        matcher = difflib.SequenceMatcher(None, left_lines, right_lines, autojunk=False)
        segments: list[tuple[str, int]] = []
        counts = {"insert": 0, "delete": 0, "replace": 0}
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                segments.append(("equal", max(1, i2 - i1)))
            elif tag == "insert":
                counts["insert"] += j2 - j1
                segments.append(("insert", max(1, j2 - j1)))
            elif tag == "delete":
                counts["delete"] += i2 - i1
                segments.append(("delete", max(1, i2 - i1)))
            else:
                counts["replace"] += max(i2 - i1, j2 - j1)
                segments.append(("replace", max(1, i2 - i1, j2 - j1)))
        self.segments = segments
        self.counts = counts
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        colors = self._colors()
        width = self.width()
        height = self.height()
        if not self.segments:
            painter.fillRect(self.rect(), colors["equal"])
            return
        total = sum(n for _, n in self.segments) or 1
        x = 0.0
        for tag, n in self.segments:
            seg_width = width * n / total
            painter.fillRect(QRectF(x, 0, max(1.0, seg_width), height), colors.get(tag, colors["equal"]))
            x += seg_width


class PdfPreview(QWidget):
    """用 QtPdf 渲染真实 PDF 页面，保留原始字体、颜色与排版。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.document = QPdfDocument(self)
        self.view = QPdfView(self)
        self.view.setObjectName("PdfPreview")
        self.view.setDocument(self.document)
        self.view.setPageMode(QPdfView.PageMode.MultiPage)
        self.view.setZoomMode(QPdfView.ZoomMode.FitToWidth)
        self.view.setPageSpacing(10)
        self.view.setDocumentMargins(QMargins(8, 8, 8, 8))
        layout.addWidget(self.view, 1)
        self._path = ""

    def load(self, path: str) -> bool:
        """加载 PDF；渲染由 Qt 在事件循环中完成。"""
        try:
            if path != self._path:
                self.document.close()
                error = self.document.load(path)
                self._path = path
                if error != QPdfDocument.Error.None_:
                    self._path = ""
                    return False
            return True
        except Exception:
            self._path = ""
            return False

    def clear(self) -> None:
        self.document.close()
        self._path = ""


class ConvertPage(QWidget):
    closeRequested = Signal()

    def __init__(self, i18n: I18n, dark: bool = False, parent=None):
        super().__init__(parent)
        self.i18n = i18n
        self.dark = dark
        self.source_file: str | None = None
        self._source_files: dict[str, str] = {}  # 按源类型记住上次选择的文件
        self._provider = None  # 由主窗口注入：返回 (markdown 文本, 当前文件路径)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(260)
        self._timer.timeout.connect(self.refresh)

        self._build_ui()
        self.retranslate()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(10)

        # --- 标题 ---
        header_row = QHBoxLayout()
        header_row.setSpacing(8)
        header = QVBoxLayout()
        header.setSpacing(2)
        self.title_label = QLabel()
        self.title_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #2b579a;")
        self.subtitle_label = QLabel()
        self.subtitle_label.setStyleSheet("color: #7a7a7a;")
        header.addWidget(self.title_label)
        header.addWidget(self.subtitle_label)
        header_row.addLayout(header, 1)

        self.close_btn = QPushButton()
        self.close_btn.setObjectName("ConvertClose")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setMinimumHeight(28)
        self.close_btn.clicked.connect(self.closeRequested.emit)
        header_row.addWidget(self.close_btn, 0, Qt.AlignTop)
        root.addLayout(header_row)

        # --- 参数区 ---
        panel = QFrame()
        panel.setObjectName("ConvertPanel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(6)

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.source_label = QLabel()
        row1.addWidget(self.source_label)
        self.choose_btn = QPushButton()
        self.choose_btn.clicked.connect(self._choose_file)
        row1.addWidget(self.choose_btn)
        self.file_label = QLabel()
        self.file_label.setStyleSheet("color: #7a7a7a;")
        row1.addWidget(self.file_label, 1)
        self.use_current_btn = QPushButton()
        self.use_current_btn.clicked.connect(self._use_current)
        row1.addWidget(self.use_current_btn)
        panel_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.direction_label = QLabel()
        self.direction_label.setMinimumWidth(66)
        row2.addWidget(self.direction_label)
        self.direction_combo = QComboBox()
        for key in DIRECTIONS:
            self.direction_combo.addItem("", key)
        self.direction_combo.currentIndexChanged.connect(self._on_direction_changed)
        row2.addWidget(self.direction_combo)

        self.paper_label = QLabel()
        self.paper_label.setMinimumWidth(34)
        row2.addWidget(self.paper_label)
        self.paper_combo = QComboBox()
        self.paper_combo.addItems(["A3", "A4", "A5", "B5", "Letter"])
        self.paper_combo.setCurrentText("A4")
        self.paper_combo.currentIndexChanged.connect(self._schedule_refresh)
        row2.addWidget(self.paper_combo)

        self.margin_label = QLabel()
        self.margin_label.setMinimumWidth(96)
        row2.addWidget(self.margin_label)
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(5, 50)
        self.margin_spin.setValue(20)
        self.margin_spin.valueChanged.connect(self._schedule_refresh)
        row2.addWidget(self.margin_spin)

        self.fontsize_label = QLabel()
        self.fontsize_label.setMinimumWidth(56)
        row2.addWidget(self.fontsize_label)
        self.fontsize_spin = QSpinBox()
        self.fontsize_spin.setRange(8, 24)
        self.fontsize_spin.setValue(11)
        self.fontsize_spin.valueChanged.connect(self._schedule_refresh)
        row2.addWidget(self.fontsize_spin)

        row2.addStretch(1)
        self.refresh_btn = QPushButton()
        self.refresh_btn.clicked.connect(self.refresh)
        row2.addWidget(self.refresh_btn)
        panel_layout.addLayout(row2)

        root.addWidget(panel)

        # --- 左右对比 ---
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(4)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        self.left_title = QLabel()
        self.left_title.setStyleSheet("font-weight: bold; color: #2b579a;")
        left_layout.addWidget(self.left_title)
        self.left_browser = QTextBrowser()
        self.left_browser.setObjectName("Preview")
        self.left_browser.setOpenExternalLinks(True)
        self.left_browser.setFrameShape(QFrame.NoFrame)
        self.pdf_preview = PdfPreview() if QPdfView is not None else None
        if self.pdf_preview is not None:
            self.left_stack = QStackedWidget()
            self.left_stack.addWidget(self.left_browser)
            self.left_stack.addWidget(self.pdf_preview)
            left_layout.addWidget(self.left_stack, 1)
        else:
            self.left_stack = None
            left_layout.addWidget(self.left_browser, 1)
        self.splitter.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        self.right_title = QLabel()
        self.right_title.setStyleSheet("font-weight: bold; color: #2b579a;")
        right_layout.addWidget(self.right_title)
        self.right_stack = QStackedWidget()
        self.right_browser = QTextBrowser()
        self.right_browser.setObjectName("Preview")
        self.right_browser.setOpenExternalLinks(True)
        self.right_browser.setFrameShape(QFrame.NoFrame)
        self.right_text = QPlainTextEdit()
        self.right_text.setReadOnly(True)
        self.right_stack.addWidget(self.right_browser)
        self.right_stack.addWidget(self.right_text)
        right_layout.addWidget(self.right_stack, 1)
        self.splitter.addWidget(right_panel)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([700, 700])
        root.addWidget(self.splitter, 1)

        # --- 差异概览 ---
        diff_row = QHBoxLayout()
        diff_row.setSpacing(8)
        self.diff_label = QLabel()
        self.diff_label.setMinimumWidth(96)
        diff_row.addWidget(self.diff_label)
        self.diff_strip = DiffStrip()
        diff_row.addWidget(self.diff_strip, 1)
        root.addLayout(diff_row)

        # --- 底部操作 ---
        bottom = QHBoxLayout()
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #7a7a7a;")
        bottom.addWidget(self.status_label, 1)
        self.run_btn = QPushButton()
        self.run_btn.setObjectName("PrimaryButton")
        self.run_btn.setMinimumWidth(170)
        self.run_btn.clicked.connect(self.run_conversion)
        bottom.addWidget(self.run_btn)
        root.addLayout(bottom)

    # ------------------------------------------------------------------
    def set_context_provider(self, provider) -> None:
        """provider() -> (markdown 文本, 当前文件路径)。"""
        self._provider = provider

    def direction(self) -> str:
        data = self.direction_combo.currentData()
        return str(data) if data else "md2docx"

    def options(self) -> ConversionOptions:
        return ConversionOptions(
            paper=self.paper_combo.currentText(),
            margin_mm=self.margin_spin.value(),
            font_size=self.fontsize_spin.value(),
            dark=self.dark,
        )

    def _current_markdown(self) -> tuple[str, str]:
        if callable(self._provider):
            try:
                return self._provider()
            except Exception:
                return "", ""
        return "", ""

    def set_direction(self, key: str) -> None:
        """由主窗口指定当前转换方向（如拖入 docx 时）。"""
        index = self.direction_combo.findData(key)
        if index >= 0 and index != self.direction_combo.currentIndex():
            self.direction_combo.setCurrentIndex(index)
        elif index >= 0:
            self._on_direction_changed()

    def set_source_file(self, path: str) -> None:
        self.source_file = path
        self._source_files[DIRECTION_SOURCE[self.direction()]] = path
        self._update_file_label()
        self.refresh()

    def _schedule_refresh(self) -> None:
        self._timer.start()

    # ------------------------------------------------------------------
    def _choose_file(self) -> None:
        kind = DIRECTION_SOURCE[self.direction()]
        filters = {
            "md": self.i18n.t("filter.md"),
            "docx": self.i18n.t("filter.docx"),
            "pdf": self.i18n.t("filter.pdf"),
        }
        path, _ = QFileDialog.getOpenFileName(
            self, self.i18n.t("conv.source"), "", f"{filters[kind]};;{self.i18n.t('filter.all')}"
        )
        if path:
            self.source_file = path
            self._source_files[kind] = path
            self._update_file_label()
            self.refresh()

    def _use_current(self) -> None:
        self.source_file = None
        self._source_files.pop("md", None)
        self._update_file_label()
        self.refresh()

    def _update_file_label(self) -> None:
        if self.source_file:
            self.file_label.setText(Path(self.source_file).name)
            self.file_label.setToolTip(self.source_file)
        else:
            key = "conv.no_file" if DIRECTION_SOURCE[self.direction()] == "md" else "conv.no_file_plain"
            self.file_label.setText(self.i18n.t(key))
            self.file_label.setToolTip("")

    def _on_direction_changed(self) -> None:
        kind = DIRECTION_SOURCE[self.direction()]
        ext = {"md": ".md", "docx": ".docx", "pdf": ".pdf"}[kind]
        if self.source_file is None or Path(self.source_file).suffix.lower() != ext:
            # 切到需要的源类型时，优先恢复该类型上次选过的文件
            remembered = self._source_files.get(kind)
            self.source_file = (
                remembered if remembered and Path(remembered).exists() else None
            )
        self._update_file_label()

        # 仅导出 Word / PDF 时可设置纸张、页边距与字号
        target_is_md = kind != "md"
        self.paper_combo.setEnabled(not target_is_md)
        self.margin_spin.setEnabled(not target_is_md)
        self.fontsize_spin.setEnabled(not target_is_md)
        # 反向转换必须选源文件，「使用当前文档」没有意义
        self.use_current_btn.setVisible(not target_is_md)
        self.choose_btn.setEnabled(True)
        self.refresh()

    # ------------------------------------------------------------------
    def _show_error(self, message: str) -> None:
        color = "#ff8a80" if self.dark else "#c0392b"
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color};")
        self.left_browser.setHtml(f"<p style='color:{color};padding:16px'>{message}</p>")
        if self.left_stack is not None:
            self.pdf_preview.clear()
            self.left_stack.setCurrentWidget(self.left_browser)
        self.right_stack.setCurrentIndex(0)
        self.right_browser.setHtml("<p style='color:#999;padding:16px'>—</p>")
        self.diff_strip.set_texts("", "")
        self.diff_label.setText(self.i18n.t("conv.diff"))

    def refresh(self) -> None:
        direction = self.direction()
        options = self.options()
        md_text, current_path = self._current_markdown()
        source_file = self.source_file

        if DIRECTION_SOURCE[direction] != "md" and not source_file:
            self._show_error(self.i18n.t("conv.need_file"))
            return
        if DIRECTION_SOURCE[direction] == "md" and source_file is None and not md_text.strip():
            self._show_error(self.i18n.t("conv.need_source"))
            return

        try:
            left_content, left_is_html = source_preview(direction, options, md_text, source_file)
            right_content, right_is_html = target_preview(direction, options, md_text, source_file)
        except Exception as exc:  # 转换失败时把错误显示出来
            self._show_error(self.i18n.t("conv.failed", err=exc))
            return

        if left_is_html:
            self.left_browser.setHtml(left_content)
        else:
            self.left_browser.setPlainText(left_content)
        self._show_source_view(direction, source_file)

        if right_is_html:
            self.right_browser.setHtml(right_content)
            self.right_stack.setCurrentIndex(0)
        else:
            self.right_text.setPlainText(right_content or "")
            self.right_stack.setCurrentIndex(1)

        left_plain = html_to_plain_text(left_content) if left_is_html else left_content
        right_plain = html_to_plain_text(right_content) if right_is_html else right_content
        self.diff_strip.set_texts(left_plain, right_plain)

        counts = self.diff_strip.counts
        self.diff_label.setText(
            f"{self.i18n.t('conv.diff')}  +{counts['insert']}  -{counts['delete']}  ~{counts['replace']}"
        )
        self.diff_label.setToolTip(
            f"insert {counts['insert']} / delete {counts['delete']} / replace {counts['replace']}"
        )
        self.status_label.setStyleSheet("color: #7a7a7a;")
        if self.source_file:
            source_name = Path(self.source_file).name
        elif current_path:
            source_name = Path(current_path).name
        else:
            source_name = self.i18n.t("common.current_doc")
        self.status_label.setText(source_name)

    def _show_source_view(self, direction: str, source_file: str | None) -> None:
        """PDF 源显示真实页面；其余源仍用 HTML 效果预览。"""
        if self.left_stack is None or self.pdf_preview is None:
            return
        if (
            DIRECTION_SOURCE[direction] == "pdf"
            and source_file
            and self.pdf_preview.load(source_file)
        ):
            self.left_stack.setCurrentWidget(self.pdf_preview)
        else:
            self.pdf_preview.clear()
            self.left_stack.setCurrentWidget(self.left_browser)

    # ------------------------------------------------------------------
    def run_conversion(self) -> None:
        direction = self.direction()
        options = self.options()
        md_text, current_path = self._current_markdown()

        if DIRECTION_SOURCE[direction] != "md" and not self.source_file:
            QMessageBox.warning(self, self.i18n.t("common.info"), self.i18n.t("conv.need_file"))
            return
        # 选了 Markdown 文件时按文件内容转换，不再要求当前文档有内容
        if DIRECTION_SOURCE[direction] == "md" and not self.source_file and not md_text.strip():
            QMessageBox.warning(self, self.i18n.t("common.info"), self.i18n.t("conv.need_source"))
            return

        ext = target_extension(direction)
        filters = {
            "docx": self.i18n.t("filter.docx"),
            "pdf": self.i18n.t("filter.pdf"),
            "md": self.i18n.t("filter.md"),
        }
        base = Path(self.source_file or current_path or "转换结果").stem
        default_name = str(Path(self.source_file or current_path or "").parent / f"{base}.{ext}") if (
            self.source_file or current_path
        ) else f"{base}.{ext}"

        path, _ = QFileDialog.getSaveFileName(
            self,
            self.i18n.t("conv.run"),
            default_name,
            filters[ext],
            options=QFileDialog.DontConfirmOverwrite,
        )
        if not path:
            return
        if not path.lower().endswith(f".{ext}"):
            path = f"{path}.{ext}"
        target = resolve_overwrite(self, self.i18n, Path(path))
        if target is None:
            return
        path = str(target)

        try:
            out = convert(direction, path, options, md_text=md_text, source_file=self.source_file)
        except Exception as exc:
            QMessageBox.critical(self, self.i18n.t("common.error"), self.i18n.t("conv.failed", err=exc))
            return

        self.status_label.setStyleSheet("color: #2e7d32;")
        self.status_label.setText(self.i18n.t("conv.done", path=str(out)))
        notify_exported(
            self, self.i18n, self.i18n.t("conv.done", path=str(out)), str(out)
        )

    # ------------------------------------------------------------------
    def set_dark(self, dark: bool) -> None:
        self.dark = dark
        accent = "#6fa8ff" if dark else "#2b579a"
        self.title_label.setStyleSheet(f"font-size: 16pt; font-weight: bold; color: {accent};")
        self.left_title.setStyleSheet(f"font-weight: bold; color: {accent};")
        self.right_title.setStyleSheet(f"font-weight: bold; color: {accent};")
        self.subtitle_label.setStyleSheet(f"color: {'#a0a0a0' if dark else '#7a7a7a'};")
        self.diff_strip.set_dark(dark)
        self.refresh()

    def retranslate(self) -> None:
        i18n = self.i18n
        self.title_label.setText(i18n.t("conv.title"))
        self.subtitle_label.setText(i18n.t("conv.subtitle"))
        self.close_btn.setText(i18n.t("conv.close"))
        self.close_btn.setToolTip(i18n.t("conv.close_tip"))
        self.source_label.setText(i18n.t("conv.source"))
        self.choose_btn.setText(i18n.t("conv.choose_file"))
        self.use_current_btn.setText(i18n.t("conv.use_current"))
        self.direction_label.setText(i18n.t("conv.direction"))
        self.paper_label.setText(i18n.t("conv.paper"))
        self.margin_label.setText(i18n.t("conv.margin"))
        self.fontsize_label.setText(i18n.t("conv.fontsize"))
        self.refresh_btn.setText(i18n.t("conv.refresh"))
        self.left_title.setText(i18n.t("conv.left"))
        self.right_title.setText(i18n.t("conv.right"))
        self.run_btn.setText(i18n.t("conv.run"))
        self.diff_label.setText(i18n.t("conv.diff"))
        self._update_file_label()

        current = self.direction_combo.currentIndex()
        for index, key in enumerate(DIRECTIONS):
            self.direction_combo.setItemText(index, i18n.t(DIRECTION_KEYS[key]))
        self.direction_combo.setCurrentIndex(current)
        self._update_file_label()
