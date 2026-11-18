"""主窗口：Ribbon 功能区 + 编辑页 + 转换中心页 + 状态栏。

职责：
- 统一分发 Ribbon 发出的动作键
- 文件的新建 / 打开 / 保存 / 导出 / 导入
- 自动保存草稿、版本备份、中英文与主题切换
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QCursor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QTabBar,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from . import APP_NAME, __version__
from .backup import create_backup
from .convert_page import ConvertPage
from .docx_io import export_md_to_docx, import_docx_to_md
from .editor import MODE_SOURCE, MODE_SPLIT, MODE_WYSIWYG, MarkdownEditor
from .fileutils import notify_exported, resolve_overwrite
from .i18n import I18n, install_qt_translator
from .outline import OutlinePanel
from .pdf_io import export_md_to_pdf, import_pdf_to_md
from .render import count_words
from .ribbon import RibbonBar
from .settings import Settings
from .theme import build_stylesheet

APP_DIR = Path(__file__).resolve().parent.parent
DRAFT_DIR = APP_DIR / ".autosave"

CONVERT_ACTIONS = {
    "act.export_word",
    "act.export_pdf",
    "act.import_word",
    "act.import_pdf",
    "act.convert_center",
    "act.md2docx",
    "act.md2pdf",
    "act.docx2md",
    "act.pdf2md",
}


class RecentMenu(QMenu):
    """最近文件下拉菜单：在条目上点右键可移除该记录。"""

    removeRequested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.remove_label = ""
        self.setToolTipsVisible(True)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.RightButton:
            action = self.actionAt(event.position().toPoint())
            if action is not None and action.data():
                path = str(action.data())
                submenu = QMenu(self)
                remove = submenu.addAction(self.remove_label)
                remove.triggered.connect(lambda _=False, p=path: self._request_remove(p))
                submenu.exec(event.globalPosition().toPoint())
                return
        super().mousePressEvent(event)

    def _request_remove(self, path: str) -> None:
        self.close()
        self.removeRequested.emit(path)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = Settings()
        self.i18n = I18n(self.settings.language)
        self.dark = self.settings.dark_mode
        self.current_file: Path | None = None
        self.dirty = False
        self._docs: list[dict] = []
        self._active = -1

        self.resize(1280, 820)
        self.setMinimumSize(960, 640)
        self.setAcceptDrops(True)

        self._build_ui()
        self._apply_theme()
        self._create_shortcuts()
        self._setup_timers()
        self._update_titles()
        self._update_status()

        QTimer.singleShot(300, self._check_draft)

    # ------------------------------------------------------------------
    # 界面构建
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        self.ribbon = RibbonBar(self.i18n, self.dark)
        self.ribbon.actionTriggered.connect(self._dispatch)
        self.ribbon.languageToggled.connect(self._toggle_language)
        self.ribbon.themeToggled.connect(self._toggle_theme)
        # 让开关按钮反映当前的自动保存 / 会话恢复状态
        self.ribbon.set_action_active(
            "act.autosave", self.settings.autosave_enabled, animate=False
        )
        self.ribbon.set_action_active(
            "act.restore_session", self.settings.restore_session, animate=False
        )
        self.setMenuWidget(self.ribbon)

        self.pages = QStackedWidget()
        self.setCentralWidget(self.pages)

        # 编辑页
        self.editor_page = QWidget()
        page_layout = QVBoxLayout(self.editor_page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        self.doc_tabs = QTabBar()
        self.doc_tabs.setObjectName("DocTabs")
        self.doc_tabs.setExpanding(False)
        self.doc_tabs.setMovable(True)
        self.doc_tabs.setTabsClosable(True)
        self.doc_tabs.setElideMode(Qt.ElideMiddle)
        self.doc_tabs.setUsesScrollButtons(True)
        self.doc_tabs.currentChanged.connect(self._on_tab_changed)
        self.doc_tabs.tabCloseRequested.connect(self._close_tab)
        self.doc_tabs.tabMoved.connect(self._on_tab_moved)
        page_layout.addWidget(self.doc_tabs)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)

        self.outline = OutlinePanel(self.i18n)
        self.outline.headingActivated.connect(self._on_heading_clicked)
        self.main_splitter.addWidget(self.outline)

        self.editor = MarkdownEditor(self.i18n, self.dark)
        self.editor.contentChanged.connect(self._on_content_changed)
        self.editor.cursorMoved.connect(self._on_cursor_moved)
        self.editor.modeChanged.connect(self._on_mode_changed)
        self.editor.documentLoaded.connect(self._on_document_loaded)
        self.editor.filesDropped.connect(self._handle_dropped_files)
        self.main_splitter.addWidget(self.editor)

        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.main_splitter.setSizes([200, 1080])
        page_layout.addWidget(self.main_splitter, 1)

        # 转换页
        self.convert_page = ConvertPage(self.i18n, self.dark)
        self.convert_page.set_context_provider(self._conversion_context)
        self.convert_page.closeRequested.connect(self._close_convert)
        self._convert_return_tab = 0

        self.pages.addWidget(self.editor_page)
        self.pages.addWidget(self.convert_page)
        self.pages.setCurrentIndex(0)

        # 状态栏
        status = QStatusBar()
        self.setStatusBar(status)
        self.status_file = QLabel("")
        self.status_words = QLabel("")
        self.status_cursor = QLabel("")
        self.status_mode = QLabel("")
        status.addWidget(self.status_file, 1)
        status.addPermanentWidget(self.status_words)
        status.addPermanentWidget(self.status_cursor)
        status.addPermanentWidget(self.status_mode)

        # 大纲显示状态
        self.outline.setVisible(self.settings.outline_visible)

        # 初始页面固定为分屏预览
        self.editor.set_mode(MODE_SPLIT, emit=False)
        self.settings.editor_mode = MODE_SPLIT

        # 初始文档标签：优先恢复上次会话，否则新建空白文档
        if not self._restore_session():
            self._add_document(None, "")

    # ------------------------------------------------------------------
    # 定时器：自动保存 / 字数统计 / 大纲刷新
    # ------------------------------------------------------------------
    def _setup_timers(self) -> None:
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._write_draft)
        self._restart_autosave()

        self.word_timer = QTimer(self)
        self.word_timer.setSingleShot(True)
        self.word_timer.setInterval(300)
        self.word_timer.timeout.connect(self._update_status)
        self.word_timer.start()

        self.outline_timer = QTimer(self)
        self.outline_timer.setSingleShot(True)
        self.outline_timer.setInterval(400)
        self.outline_timer.timeout.connect(self._refresh_outline)
        self.outline_timer.start()

    def _restart_autosave(self) -> None:
        if self.settings.autosave_enabled:
            self.autosave_timer.start(self.settings.autosave_interval * 1000)
        else:
            self.autosave_timer.stop()

    # ------------------------------------------------------------------
    # 快捷键
    # ------------------------------------------------------------------
    def _create_shortcuts(self) -> None:
        bindings = {
            "Ctrl+N": lambda: self._dispatch("act.new"),
            "Ctrl+O": lambda: self._dispatch("act.open"),
            "Ctrl+S": lambda: self._dispatch("act.save"),
            "Ctrl+Shift+S": lambda: self._dispatch("act.save_as"),
            "Ctrl+B": lambda: self._dispatch("act.bold"),
            "Ctrl+I": lambda: self._dispatch("act.italic"),
            "Ctrl+K": lambda: self._dispatch("act.link"),
            "Ctrl+F": lambda: self._dispatch("act.find"),
            "Ctrl+Shift+P": lambda: self._dispatch("act.mode_split"),
            "Ctrl+Shift+M": lambda: self._dispatch("act.mode_source"),
            "Ctrl+Shift+W": lambda: self._dispatch("act.mode_wysiwyg"),
            "Esc": self._on_escape,
        }
        self._shortcuts = []
        for sequence, handler in bindings.items():
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(handler)
            self._shortcuts.append(shortcut)

    def _on_escape(self) -> None:
        if self.editor.find_bar.isVisible():
            self.editor.find_bar.hide()
            self.editor.focus_editor()

    # ------------------------------------------------------------------
    # 动作分发
    # ------------------------------------------------------------------
    def _dispatch(self, key: str) -> None:
        handlers = {
            "act.new": self.new_document,
            "act.open": self.open_dialog,
            "act.save": self.save_document,
            "act.save_as": self.save_document_as,
            "act.recent": self.show_recent,
            "act.export_word": self.export_word,
            "act.export_pdf": self.export_pdf,
            "act.import_word": self.import_word,
            "act.import_pdf": self.import_pdf,
            "act.undo": self._undo,
            "act.redo": self._redo,
            "act.bold": self.editor.toggle_bold,
            "act.italic": self.editor.toggle_italic,
            "act.strike": self.editor.toggle_strike,
            "act.inline_code": self.editor.toggle_inline_code,
            "act.h1": lambda: self.editor.set_heading(1),
            "act.h2": lambda: self.editor.set_heading(2),
            "act.h3": lambda: self.editor.set_heading(3),
            "act.ul": lambda: self.editor.toggle_list(False),
            "act.ol": lambda: self.editor.toggle_list(True),
            "act.quote": self.editor.toggle_quote,
            "act.find": self._show_find,
            "act.link": self.editor.insert_link,
            "act.image": self.insert_image,
            "act.table": self.show_table_menu,
            "act.hr": self.editor.insert_hr,
            "act.code_block": self.editor.insert_code_block,
            "act.mode_source": lambda: self._set_mode(MODE_SOURCE),
            "act.mode_split": lambda: self._set_mode(MODE_SPLIT),
            "act.mode_wysiwyg": lambda: self._set_mode(MODE_WYSIWYG),
            "act.outline": self._toggle_outline,
            "act.theme": self._toggle_theme,
            "act.autosave": self.show_autosave_menu,
            "act.restore_session": self.show_restore_menu,
            "act.backup": self.backup_version,
            "act.about": self.show_about,
            "act.convert_center": lambda: self._show_convert("md2docx"),
            "act.md2docx": lambda: self._show_convert("md2docx"),
            "act.md2pdf": lambda: self._show_convert("md2pdf"),
            "act.docx2md": lambda: self._show_convert("docx2md"),
            "act.pdf2md": lambda: self._show_convert("pdf2md"),
        }
        handler = handlers.get(key)
        if handler is None:
            return
        if key not in CONVERT_ACTIONS:
            self.pages.setCurrentIndex(0)
        handler()

    def _enter_convert(self) -> None:
        """切换到转换中心，并记住进入前的功能区选项卡。"""
        if self.pages.currentIndex() != 1:
            self._convert_return_tab = self.ribbon.tab_of_action()
        self.pages.setCurrentIndex(1)
        self.ribbon.set_tab(4)

    def _show_convert(self, direction: str) -> None:
        self._enter_convert()
        self.convert_page.set_direction(direction)
        self.convert_page.refresh()

    def _close_convert(self) -> None:
        """关闭转换中心，回到编辑界面与原来的功能区选项卡。"""
        self.pages.setCurrentIndex(0)
        self.ribbon.set_tab(self._convert_return_tab)

    def _undo(self) -> None:
        if self.editor.mode == MODE_WYSIWYG:
            self.editor.wysiwyg.undo()
        elif self.editor.mode == MODE_SPLIT and self.editor.preview.hasFocus():
            self.editor.preview.undo()
        else:
            self.editor.source.undo()

    def _redo(self) -> None:
        if self.editor.mode == MODE_WYSIWYG:
            self.editor.wysiwyg.redo()
        elif self.editor.mode == MODE_SPLIT and self.editor.preview.hasFocus():
            self.editor.preview.redo()
        else:
            self.editor.source.redo()

    def _show_find(self) -> None:
        bar = self.editor.find_bar
        if bar.isVisible():
            # 再点一次关闭查找栏
            bar.hide()
            self.editor.focus_editor()
            return
        self.pages.setCurrentIndex(0)
        bar.open()

    def _set_mode(self, mode: str) -> None:
        self.pages.setCurrentIndex(0)
        self.ribbon.set_tab(1)
        self.editor.set_mode(mode)

    def _toggle_outline(self) -> None:
        visible = not self.outline.isVisible()
        self.outline.setVisible(visible)
        self.settings.outline_visible = visible

    def _set_autosave(self, enabled: bool) -> None:
        self.settings.autosave_enabled = enabled
        self._restart_autosave()
        self.ribbon.set_action_active("act.autosave", enabled)
        state = self.i18n.t("common.yes") if enabled else self.i18n.t("common.no")
        self.statusBar().showMessage(f"{self.i18n.t('act.autosave')}: {state}", 3000)

    def show_restore_menu(self) -> None:
        menu = QMenu(self)
        action = menu.addAction(self.i18n.t("act.restore_session"))
        action.setCheckable(True)
        action.setChecked(self.settings.restore_session)
        action.toggled.connect(self._set_restore_session)
        self._exec_menu(menu, "act.restore_session")

    def _set_restore_session(self, enabled: bool) -> None:
        self.settings.restore_session = enabled
        if not enabled:
            # 关闭恢复后清掉已保存的会话，避免下次启动仍被还原
            self.settings.set_value("session/state", "")
        self.ribbon.set_action_active("act.restore_session", enabled)
        state = self.i18n.t("common.yes") if enabled else self.i18n.t("common.no")
        self.statusBar().showMessage(
            f"{self.i18n.t('act.restore_session')}: {state}", 3000
        )

    # ------------------------------------------------------------------
    # 文档标签页
    # ------------------------------------------------------------------
    def _doc_label(self, doc: dict) -> str:
        name = doc["path"].name if doc["path"] else self.i18n.t("common.untitled")
        return f"{name}{' *' if doc['dirty'] else ''}"

    def _update_active_tab(self) -> None:
        if not 0 <= self._active < len(self._docs):
            return
        doc = self._docs[self._active]
        self.doc_tabs.setTabText(self._active, self._doc_label(doc))
        self.doc_tabs.setTabToolTip(
            self._active, str(doc["path"]) if doc["path"] else self.i18n.t("common.untitled")
        )

    def _retranslate_tabs(self) -> None:
        for index, doc in enumerate(self._docs):
            self.doc_tabs.setTabText(index, self._doc_label(doc))
            self.doc_tabs.setTabToolTip(
                index, str(doc["path"]) if doc["path"] else self.i18n.t("common.untitled")
            )

    def _store_active(self) -> None:
        if 0 <= self._active < len(self._docs):
            doc = self._docs[self._active]
            doc["text"] = self.editor.get_markdown()
            doc["dirty"] = self.dirty
            doc["path"] = self.current_file
            doc["cursor"] = self.editor.source.textCursor().position()

    def _save_session(self, active: int | None = None) -> None:
        """把当前打开的所有标签页与未保存内容写入会话，供下次启动恢复。"""
        docs = []
        for doc in self._docs:
            if doc["path"] is None and not doc["text"].strip() and not doc["dirty"]:
                continue
            docs.append(
                {
                    "path": str(doc["path"]) if doc["path"] else "",
                    "text": doc["text"],
                    "dirty": bool(doc["dirty"]),
                    "cursor": int(doc.get("cursor", 0) or 0),
                }
            )
        state = {"active": self._active if active is None else active, "docs": docs}
        self.settings.set_value("session/state", json.dumps(state, ensure_ascii=False))

    def _restore_session(self) -> bool:
        """启动时恢复上次会话；没有可恢复内容则返回 False。"""
        raw = self.settings.value("session/state", "")
        if not self.settings.restore_session or not raw:
            return False
        try:
            state = json.loads(str(raw))
            entries = state.get("docs") or []
        except (TypeError, ValueError):
            return False
        entries = [entry for entry in entries if isinstance(entry, dict)]
        if not entries:
            return False
        restored = 0
        cursors: list[tuple[int, int]] = []
        for entry in entries:
            path_text = entry.get("path") or ""
            text = entry.get("text") or ""
            dirty = bool(entry.get("dirty"))
            path = Path(path_text) if path_text else None
            if path is not None:
                if not path.exists():
                    if not text.strip():
                        continue
                elif not dirty:
                    # 已保存的文件以磁盘内容为准
                    try:
                        text = path.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        try:
                            text = path.read_text(encoding="gbk", errors="replace")
                        except Exception:
                            pass
                    except Exception:
                        pass
            self._add_document(path, text, dirty)
            cursors.append((len(self._docs) - 1, int(entry.get("cursor") or 0)))
            restored += 1
        if not restored:
            return False
        # 先切换标签页，再写入各文档光标，避免切换过程把光标覆盖为 0
        try:
            active = int(state.get("active", 0))
        except (TypeError, ValueError):
            active = 0
        self._activate_document(min(max(0, active), len(self._docs) - 1))
        for doc_index, position in cursors:
            self._docs[doc_index]["cursor"] = position
        self._apply_cursor_position(self._docs[self._active].get("cursor"))
        return True

    def _apply_cursor_position(self, position) -> None:
        if isinstance(position, int) and position >= 0:
            cursor = self.editor.source.textCursor()
            cursor.setPosition(min(position, len(self.editor.source.toPlainText())))
            self.editor.source.setTextCursor(cursor)

    def _add_document(self, path: str | Path | None, text: str, dirty: bool = False) -> int:
        self._store_active()
        doc = {"path": Path(path) if path else None, "text": text, "dirty": dirty}
        self._docs.append(doc)
        index = len(self._docs) - 1
        self.doc_tabs.blockSignals(True)
        self.doc_tabs.addTab(self._doc_label(doc))
        self.doc_tabs.setTabToolTip(
            index, str(doc["path"]) if doc["path"] else self.i18n.t("common.untitled")
        )
        self.doc_tabs.setCurrentIndex(index)
        self.doc_tabs.blockSignals(False)
        self._active = -1
        self._activate_document(index)
        return index

    def _activate_document(self, index: int) -> None:
        if not 0 <= index < len(self._docs) or index == self._active:
            return
        self._store_active()
        self._active = index
        doc = self._docs[index]
        self.current_file = doc["path"]
        self.dirty = doc["dirty"]
        self.editor.set_markdown(doc["text"])
        self._apply_cursor_position(doc.get("cursor"))
        self.doc_tabs.blockSignals(True)
        self.doc_tabs.setCurrentIndex(index)
        self.doc_tabs.blockSignals(False)
        self._update_titles()

    def _on_tab_changed(self, index: int) -> None:
        if index >= 0:
            self._activate_document(index)

    def _on_tab_moved(self, from_index: int, to_index: int) -> None:
        if not (0 <= from_index < len(self._docs) and 0 <= to_index < len(self._docs)):
            return
        doc = self._docs.pop(from_index)
        self._docs.insert(to_index, doc)
        if self._active == from_index:
            self._active = to_index
        elif from_index < self._active <= to_index:
            self._active -= 1
        elif to_index <= self._active < from_index:
            self._active += 1

    def _close_tab(self, index: int) -> None:
        if not 0 <= index < len(self._docs):
            return
        if index != self._active:
            self._activate_document(index)
        if not self._maybe_save():
            return
        if self.dirty:
            self._clear_draft()
        self._remove_document(index)

    def _remove_document(self, index: int) -> None:
        if not 0 <= index < len(self._docs):
            return
        self._docs.pop(index)
        self.doc_tabs.blockSignals(True)
        self.doc_tabs.removeTab(index)
        self.doc_tabs.blockSignals(False)
        self._active = -1
        if self._docs:
            self._activate_document(min(index, len(self._docs) - 1))
        else:
            self._add_document(None, "")

    def _is_blank_untitled(self) -> bool:
        return (
            self.current_file is None
            and not self.dirty
            and not self.editor.get_markdown().strip()
        )

    def _load_into_active(self, path: str | Path | None, text: str, dirty: bool = False) -> None:
        doc = self._docs[self._active]
        doc["path"] = Path(path) if path else None
        doc["text"] = text
        doc["dirty"] = dirty
        self.current_file = doc["path"]
        self.dirty = dirty
        self.editor.set_markdown(text)
        self._update_active_tab()
        self._update_titles()
        self._refresh_outline()
        self._update_status()

    # ------------------------------------------------------------------
    # 文件操作
    # ------------------------------------------------------------------
    def _document_name(self) -> str:
        return self.current_file.name if self.current_file else self.i18n.t("common.untitled")

    def _update_titles(self) -> None:
        name = self._document_name()
        mark = " *" if self.dirty else ""
        self.setWindowTitle(f"{APP_NAME} {__version__} — {name}{mark}")
        if hasattr(self.ribbon, "set_document_title"):
            self.ribbon.set_document_title(f"{name}{mark}")
        self.status_file.setText(str(self.current_file) if self.current_file else self.i18n.t("common.untitled"))
        self._update_active_tab()

    def _set_dirty(self, dirty: bool) -> None:
        if 0 <= self._active < len(self._docs):
            self._docs[self._active]["dirty"] = dirty
            self._docs[self._active]["path"] = self.current_file
        if self.dirty == dirty:
            self._update_active_tab()
            return
        self.dirty = dirty
        self._update_titles()

    def _on_content_changed(self) -> None:
        self._set_dirty(True)
        self.word_timer.start()
        self.outline_timer.start()

    def _on_cursor_moved(self, line: int, col: int) -> None:
        self.status_cursor.setText(self.i18n.t("status.line", line=line, col=col))

    def _on_mode_changed(self, mode: str) -> None:
        self.settings.editor_mode = mode
        names = {
            MODE_SOURCE: self.i18n.t("act.mode_source"),
            MODE_SPLIT: self.i18n.t("act.mode_split"),
            MODE_WYSIWYG: self.i18n.t("act.mode_wysiwyg"),
        }
        self.status_mode.setText(self.i18n.t("status.mode", mode=names.get(mode, mode)))

    def _update_status(self) -> None:
        text = self.editor.get_markdown()
        self.status_words.setText(self.i18n.t("status.words", n=count_words(text)))
        self._on_cursor_moved(1, 1)
        self._on_mode_changed(self.editor.mode)

    def _refresh_outline(self) -> None:
        self.outline.refresh(self.editor.get_markdown())

    def _on_document_loaded(self) -> None:
        self._refresh_outline()
        self._update_status()

    def _on_heading_clicked(self, line: int) -> None:
        self.editor.goto_line(line)

    def _maybe_save(self) -> bool:
        if not self.dirty:
            return True
        answer = QMessageBox.question(
            self,
            self.i18n.t("msg.unsaved_title"),
            self.i18n.t("msg.unsaved_text", name=self._document_name()),
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save,
        )
        if answer == QMessageBox.Save:
            return self.save_document()
        if answer == QMessageBox.Cancel:
            return False
        return True

    def new_document(self) -> None:
        self.pages.setCurrentIndex(0)
        if self._is_blank_untitled():
            return
        self._add_document(None, "")

    def open_dialog(self) -> None:
        start_dir = self.settings.last_dir or ""
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.i18n.t("act.open"),
            start_dir,
            f"{self.i18n.t('filter.md')};;{self.i18n.t('filter.all')}",
        )
        if path:
            self.open_path(path)

    def open_path(self, path: str | Path) -> None:
        file = Path(path).resolve()
        try:
            text = file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = file.read_text(encoding="gbk", errors="replace")
        except Exception as exc:
            QMessageBox.critical(self, self.i18n.t("common.error"), self.i18n.t("msg.open_failed", err=exc))
            return

        self.pages.setCurrentIndex(0)
        for index, doc in enumerate(self._docs):
            if doc["path"] is not None and doc["path"] == file:
                self._activate_document(index)
                break
        else:
            if self._is_blank_untitled():
                self._load_into_active(file, text)
            else:
                self._add_document(file, text)
        if self._active >= 0:
            self._store_active()
        self.settings.last_dir = str(file.parent)
        self.settings.add_recent_file(str(file))
        self._update_titles()
        self._refresh_outline()
        self._update_status()

    def save_document(self) -> bool:
        if self.current_file is None:
            return self.save_document_as()
        text = self.editor.get_markdown()
        try:
            self.current_file.write_text(text, encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, self.i18n.t("common.error"), self.i18n.t("msg.save_failed", err=exc))
            return False
        if 0 <= self._active < len(self._docs):
            self._docs[self._active]["path"] = self.current_file
            self._docs[self._active]["text"] = text
        self._set_dirty(False)
        self.settings.last_dir = str(self.current_file.parent)
        self.settings.add_recent_file(str(self.current_file))
        self._clear_draft()
        self.statusBar().showMessage(self.i18n.t("status.saved"), 2000)
        return True

    def save_document_as(self) -> bool:
        start = str(self.current_file) if self.current_file else str(
            Path(self.settings.last_dir or Path.cwd()) / self.i18n.t("common.untitled")
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.i18n.t("act.save_as"),
            start,
            self.i18n.t("filter.md"),
            options=QFileDialog.DontConfirmOverwrite,
        )
        if not path:
            return False
        if not path.lower().endswith((".md", ".markdown")):
            path += ".md"
        target = resolve_overwrite(self, self.i18n, Path(path))
        if target is None:
            return False
        self.current_file = target
        return self.save_document()

    def _recent_entry(self, menu: RecentMenu, path: Path) -> None:
        """最近文件条目：文件名 + 完整路径 + 最后修改时间。"""
        widget = QWidget(menu)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(14, 6, 22, 6)
        layout.setSpacing(1)
        name = QLabel(path.name, widget)
        font = name.font()
        font.setBold(True)
        name.setFont(font)
        meta = QLabel(widget)
        meta.setStyleSheet("color: #8a8f98; font-size: 11px;")
        try:
            stamp = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        except OSError:
            stamp = ""
        meta_text = f"{path}    {stamp}" if stamp else str(path)
        meta.setText(meta.fontMetrics().elidedText(meta_text, Qt.ElideMiddle, 560))
        meta.setToolTip(f"{path}\n{stamp}")
        layout.addWidget(name)
        layout.addWidget(meta)
        # 交给 QMenu 处理点击/右键，避免自定义控件吞掉事件
        for child in (widget, name, meta):
            child.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        action = QWidgetAction(menu)
        action.setData(str(path))
        action.setDefaultWidget(widget)
        action.triggered.connect(lambda _=False, f=str(path): self.open_path(f))
        menu.addAction(action)

    def _recent_menu(self) -> RecentMenu:
        menu = RecentMenu(self)
        menu.remove_label = self.i18n.t("recent.remove")
        menu.removeRequested.connect(self._remove_recent)
        hidden = self.settings.recent_hidden
        files = [] if hidden else self.settings.visible_recent_files()
        if hidden:
            hint = menu.addAction(self.i18n.t("recent.hidden"))
            hint.setEnabled(False)
        elif not files:
            empty = menu.addAction(self.i18n.t("msg.no_recent"))
            empty.setEnabled(False)
        for path in files:
            self._recent_entry(menu, Path(path))
        menu.addSeparator()
        hide_action = menu.addAction(self.i18n.t("recent.hide"))
        hide_action.setCheckable(True)
        hide_action.setChecked(hidden)
        hide_action.toggled.connect(self._toggle_recent_hidden)
        settings_action = menu.addAction(self.i18n.t("recent.settings"))
        settings_action.triggered.connect(self._recent_settings)
        if files:
            clear = menu.addAction(self.i18n.t("recent.clear"))
            clear.triggered.connect(self._clear_recent)
        return menu

    def _toggle_recent_hidden(self, hidden: bool) -> None:
        self.settings.recent_hidden = hidden

    def _recent_settings(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(self.i18n.t("recent.settings"))
        form = QFormLayout(dialog)
        count = QSpinBox(dialog)
        count.setRange(1, 50)
        count.setValue(self.settings.recent_limit)
        days = QSpinBox(dialog)
        days.setRange(0, 36500)
        days.setSpecialValueText(self.i18n.t("recent.days_none"))
        days.setValue(self.settings.recent_days)
        form.addRow(self.i18n.t("recent.limit_label"), count)
        form.addRow(self.i18n.t("recent.days_label"), days)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, dialog)
        buttons.button(QDialogButtonBox.Ok).setText(self.i18n.t("common.ok"))
        buttons.button(QDialogButtonBox.Cancel).setText(self.i18n.t("common.cancel"))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.Accepted:
            return
        self.settings.recent_limit = count.value()
        self.settings.recent_days = days.value()
        if days.value() > 0:
            message = self.i18n.t("recent.saved_both", n=count.value(), d=days.value())
        else:
            message = self.i18n.t("recent.limit_saved", n=count.value())
        self.statusBar().showMessage(message, 2500)

    def _clear_recent(self) -> None:
        self.settings.clear_recent_files()
        self.statusBar().showMessage(self.i18n.t("recent.cleared"), 2500)

    def _remove_recent(self, path: str) -> None:
        self.settings.remove_recent_file(path)
        self.statusBar().showMessage(
            self.i18n.t("recent.removed", name=Path(path).name), 2500
        )

    def _exec_menu(self, menu: QMenu, action_key: str) -> None:
        """在 Ribbon 按钮下方弹出菜单，并在关闭后清除按钮残留状态。"""
        button = self.ribbon.button_for(action_key)
        if button is None:
            menu.exec(QCursor.pos())
            return
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))
        # 菜单为模态，关闭后按钮收不到 leave 事件，需手动清除悬停/按下状态
        button.setDown(False)
        button.clearFocus()
        QApplication.sendEvent(button, QEvent(QEvent.Leave))
        button.update()

    def show_recent(self) -> None:
        self._exec_menu(self._recent_menu(), "act.recent")

    def _autosave_menu(self) -> QMenu:
        menu = QMenu(self)
        action = menu.addAction(self.i18n.t("act.autosave"))
        action.setCheckable(True)
        action.setChecked(self.settings.autosave_enabled)
        action.toggled.connect(self._set_autosave)
        menu.addSeparator()

        # 「每 [n] 分钟自动保存」：数字可在菜单内直接输入，无需弹窗
        row = QWidget(menu)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(18, 4, 18, 4)
        layout.setSpacing(4)
        prefix = QLabel(self.i18n.t("autosave.every_prefix"), row)
        spin = QSpinBox(row)
        spin.setRange(1, 120)
        spin.setValue(max(1, round(self.settings.autosave_interval / 60)))
        spin.setFixedWidth(64)
        suffix = QLabel(self.i18n.t("autosave.every_suffix"), row)
        layout.addWidget(prefix)
        layout.addWidget(spin)
        layout.addWidget(suffix)
        spin.valueChanged.connect(self._set_autosave_minutes)

        widget_action = QWidgetAction(menu)
        widget_action.setDefaultWidget(row)
        menu.addAction(widget_action)
        return menu

    def show_autosave_menu(self) -> None:
        self._exec_menu(self._autosave_menu(), "act.autosave")

    def _spin_row(self, menu: QMenu, label: str, value: int) -> QSpinBox:
        """菜单内的一行「标签 + 数字框」。"""
        row = QWidget(menu)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(18, 4, 18, 4)
        layout.setSpacing(6)
        text = QLabel(label, row)
        spin = QSpinBox(row)
        spin.setRange(1, 2_147_483_647)  # 不限制上限，仅保底 1
        spin.setValue(value)
        spin.setFixedWidth(64)
        layout.addWidget(text)
        layout.addWidget(spin)
        action = QWidgetAction(menu)
        action.setDefaultWidget(row)
        menu.addAction(action)
        return spin

    def _table_menu(self) -> QMenu:
        menu = QMenu(self)
        rows = self._spin_row(menu, self.i18n.t("table.rows"), 3)
        cols = self._spin_row(menu, self.i18n.t("table.cols"), 3)
        menu.addSeparator()
        insert = menu.addAction(self.i18n.t("table.insert"))
        insert.triggered.connect(
            lambda: self.editor.insert_table(rows.value(), cols.value())
        )
        return menu

    def show_table_menu(self) -> None:
        self._exec_menu(self._table_menu(), "act.table")

    def _set_autosave_minutes(self, minutes: int) -> None:
        self.settings.autosave_interval = minutes * 60
        self._restart_autosave()
        self.statusBar().showMessage(
            self.i18n.t("autosave.interval_saved", n=minutes), 3000
        )

    # ---------------- 导出 / 导入 ----------------
    def _export_target(self, suffix: str) -> Path | None:
        base = self.current_file.stem if self.current_file else "未命名"
        folder = self.current_file.parent if self.current_file else Path(self.settings.last_dir or Path.cwd())
        default = str(folder / f"{base}{suffix}")
        filters = {
            ".docx": self.i18n.t("filter.docx"),
            ".pdf": self.i18n.t("filter.pdf"),
        }
        title = self.i18n.t("act.export_pdf" if suffix == ".pdf" else "act.export_word")
        path, _ = QFileDialog.getSaveFileName(
            self,
            title,
            default,
            filters.get(suffix, self.i18n.t("filter.all")),
            options=QFileDialog.DontConfirmOverwrite,
        )
        if not path:
            return None
        if not path.lower().endswith(suffix):
            path += suffix
        return resolve_overwrite(self, self.i18n, Path(path))

    def export_word(self) -> None:
        path = self._export_target(".docx")
        if not path:
            return
        try:
            out = export_md_to_docx(
                self.editor.get_markdown(), path, paper="A4", margin_mm=20, font_size=11
            )
        except Exception as exc:
            QMessageBox.critical(self, self.i18n.t("common.error"), self.i18n.t("msg.convert_failed", err=exc))
            return
        notify_exported(
            self, self.i18n, self.i18n.t("msg.export_done", path=str(out)), str(out)
        )

    def export_pdf(self) -> None:
        path = self._export_target(".pdf")
        if not path:
            return
        try:
            out = export_md_to_pdf(
                self.editor.get_markdown(), path, paper="A4", margin_mm=20, font_size=11
            )
        except Exception as exc:
            QMessageBox.critical(self, self.i18n.t("common.error"), self.i18n.t("msg.convert_failed", err=exc))
            return
        notify_exported(
            self, self.i18n, self.i18n.t("msg.export_done", path=str(out)), str(out)
        )

    def import_word(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, self.i18n.t("act.import_word"), self.settings.last_dir, self.i18n.t("filter.docx")
        )
        if not path:
            return
        try:
            assets = Path(path).parent / "assets"
            text = import_docx_to_md(path, assets)
        except Exception as exc:
            QMessageBox.critical(self, self.i18n.t("common.error"), self.i18n.t("msg.convert_failed", err=exc))
            return
        self._load_imported(text)

    def import_pdf(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, self.i18n.t("act.import_pdf"), self.settings.last_dir, self.i18n.t("filter.pdf")
        )
        if not path:
            return
        try:
            text = import_pdf_to_md(path)
        except Exception as exc:
            QMessageBox.critical(self, self.i18n.t("common.error"), self.i18n.t("msg.convert_failed", err=exc))
            return
        self._load_imported(text)

    def _load_imported(self, text: str) -> None:
        self.pages.setCurrentIndex(0)
        if self._is_blank_untitled():
            self._load_into_active(None, text, dirty=True)
        else:
            self._add_document(None, text, dirty=True)

    def insert_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, self.i18n.t("act.image"), self.settings.last_dir, self.i18n.t("filter.images")
        )
        if path:
            self.editor.insert_image(path)

    # ------------------------------------------------------------------
    # 语言 / 主题
    # ------------------------------------------------------------------
    def _toggle_language(self) -> None:
        self.i18n.toggle()
        self.settings.language = self.i18n.lang
        install_qt_translator(self.i18n.lang)
        self.ribbon.set_language(self.i18n)
        self.ribbon.set_document_title(
            f"{self._document_name()}{' *' if self.dirty else ''}"
        )
        self.outline.retranslate(self.i18n)
        self.editor.retranslate(self.i18n)
        self._retranslate_tabs()
        self.convert_page.i18n = self.i18n
        self.convert_page.retranslate()
        self._update_titles()
        self._update_status()

    def _toggle_theme(self) -> None:
        self.dark = not self.dark
        self.settings.dark_mode = self.dark
        self._apply_theme()

    def _apply_theme(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(self.dark))
        self.editor.set_dark(self.dark)
        self.convert_page.set_dark(self.dark)
        self.ribbon.set_dark(self.dark)
        self.ribbon.set_document_title(f"{self._document_name()}{' *' if self.dirty else ''}")

    # ------------------------------------------------------------------
    # 自动保存草稿
    # ------------------------------------------------------------------
    def _draft_file(self) -> Path:
        return DRAFT_DIR / "draft.md"

    def _draft_meta(self) -> Path:
        return DRAFT_DIR / "draft.json"

    def _write_draft(self) -> None:
        if not self.settings.autosave_enabled or not self.dirty:
            return
        text = self.editor.get_markdown()
        if not text.strip():
            return
        try:
            DRAFT_DIR.mkdir(parents=True, exist_ok=True)
            self._draft_file().write_text(text, encoding="utf-8")
            self._draft_meta().write_text(
                json.dumps(
                    {"path": str(self.current_file) if self.current_file else "", "time": time.time()},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _clear_draft(self) -> None:
        for file in (self._draft_file(), self._draft_meta()):
            try:
                file.unlink(missing_ok=True)
            except Exception:
                pass

    def _check_draft(self) -> None:
        draft = self._draft_file()
        if not draft.exists():
            return
        try:
            text = draft.read_text(encoding="utf-8")
        except Exception:
            return
        if not text.strip() or self.dirty:
            return
        answer = QMessageBox.question(
            self,
            self.i18n.t("msg.recover_title"),
            self.i18n.t("msg.recover_text"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if answer == QMessageBox.Yes:
            original = ""
            try:
                meta = json.loads(self._draft_meta().read_text(encoding="utf-8"))
                original = meta.get("path", "")
            except Exception:
                pass
            self._load_into_active(Path(original) if original else None, text, dirty=True)
        else:
            self._clear_draft()

    # ------------------------------------------------------------------
    # 版本备份 / 关于
    # ------------------------------------------------------------------
    def backup_version(self) -> None:
        note, ok = QInputDialog.getText(
            self, self.i18n.t("act.backup"), self.i18n.t("msg.backup_prompt")
        )
        if not ok:
            return
        try:
            target = create_backup(APP_DIR, __version__, note or "update")
        except Exception as exc:
            QMessageBox.critical(self, self.i18n.t("common.error"), self.i18n.t("msg.create_failed", err=exc))
            return
        QMessageBox.information(
            self, self.i18n.t("common.info"), self.i18n.t("msg.backup_done", path=str(target))
        )

    def _build_about_dialog(self) -> QDialog:
        dialog = QDialog(self)
        dialog.setWindowTitle(self.i18n.t("act.about"))
        dialog.setMinimumWidth(420)
        layout = QVBoxLayout(dialog)
        text = QLabel(self.i18n.t("msg.about_text", ver=__version__))
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(text)

        row = QHBoxLayout()
        backup_button = QPushButton(self.i18n.t("about.backup"))
        backup_button.clicked.connect(self.backup_version)
        close_button = QPushButton(self.i18n.t("common.close"))
        close_button.setDefault(True)
        close_button.clicked.connect(dialog.accept)
        row.addWidget(backup_button)
        row.addStretch(1)
        row.addWidget(close_button)
        layout.addLayout(row)
        return dialog

    def show_about(self) -> None:
        self._build_about_dialog().exec()

    # ------------------------------------------------------------------
    # 拖拽打开
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            event.acceptProposedAction()
            self._handle_dropped_files(paths)

    def _handle_dropped_files(self, paths: list[str]) -> None:
        """处理拖入窗口或编辑区的本地文件。"""
        for path in paths:
            file = Path(path)
            suffix = file.suffix.lower()
            if suffix in (".md", ".markdown"):
                self.open_path(file)
                return
            if suffix == ".docx":
                self._enter_convert()
                self.convert_page.set_direction("docx2md")
                self.convert_page.set_source_file(str(file))
                return
            if suffix == ".pdf":
                self._enter_convert()
                self.convert_page.set_direction("pdf2md")
                self.convert_page.set_source_file(str(file))
                return

    def closeEvent(self, event: QCloseEvent) -> None:
        self._store_active()
        active = self._active
        for index in range(len(self._docs)):
            doc = self._docs[index]
            if not doc["dirty"]:
                continue
            self._activate_document(index)
            if not self._maybe_save():
                event.ignore()
                return
            if self.dirty:
                # 用户选择“不保存”：按磁盘内容恢复，未命名文档不再纳入会话
                path = doc["path"]
                if path is not None and path.exists():
                    try:
                        doc["text"] = path.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        doc["text"] = path.read_text(encoding="gbk", errors="replace")
                    except Exception:
                        doc["text"] = ""
                else:
                    doc["text"] = ""
                doc["dirty"] = False
                self.dirty = False
        if self.dirty:
            self._clear_draft()
        else:
            self._write_draft_if_needed()
        if self.settings.restore_session:
            self._save_session(active)
        event.accept()

    def _write_draft_if_needed(self) -> None:
        if self.dirty:
            self._write_draft()

    # ------------------------------------------------------------------
    def _conversion_context(self) -> tuple[str, str]:
        return self.editor.get_markdown(), str(self.current_file) if self.current_file else ""
