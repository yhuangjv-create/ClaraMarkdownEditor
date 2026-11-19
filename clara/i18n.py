"""中英文界面文案。

所有界面文字都集中在此字典中，键名被界面代码引用；
新增文字时只需在 STRINGS 中补一条 (中文, 英文) 元组。
"""

from __future__ import annotations

from PySide6.QtCore import QLibraryInfo, QTranslator
from PySide6.QtWidgets import QApplication

_qt_translator: QTranslator | None = None


def install_qt_translator(lang: str) -> None:
    """加载 Qt 标准控件（右键菜单、对话框按钮等）的中文翻译。"""
    global _qt_translator
    app = QApplication.instance()
    if app is None:
        return
    if _qt_translator is not None:
        app.removeTranslator(_qt_translator)
        _qt_translator = None
    if lang != "zh":
        return
    translator = QTranslator(app)
    path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
    if translator.load("qtbase_zh_CN", path):
        app.installTranslator(translator)
        _qt_translator = translator


LANG_ZH = "zh"
LANG_EN = "en"

# key: (中文, English)
STRINGS: dict[str, tuple[str, str]] = {
    # ---------- 通用 ----------
    "app.name": ("ClaraMarkdownEditor", "ClaraMarkdownEditor"),
    "common.ok": ("确定", "OK"),
    "common.open_file": ("直接打开", "Open file"),
    "common.cancel": ("取消", "Cancel"),
    "common.yes": ("是", "Yes"),
    "common.no": ("否", "No"),
    "common.close": ("关闭", "Close"),
    "common.save": ("保存", "Save"),
    "common.open": ("打开", "Open"),
    "common.error": ("错误", "Error"),
    "common.info": ("提示", "Info"),
    "common.untitled": ("未命名", "Untitled"),
    "common.current_doc": ("当前文档", "Current document"),

    # ---------- Ribbon 选项卡 ----------
    "tab.file": ("文件", "File"),
    "tab.home": ("开始", "Home"),
    "tab.insert": ("插入", "Insert"),
    "tab.settings": ("设置", "Settings"),
    "tab.convert": ("转换", "Convert"),

    # ---------- 文件操作 ----------
    "act.new": ("新建", "New"),
    "act.open": ("打开", "Open"),
    "act.save": ("保存", "Save"),
    "act.save_as": ("另存为", "Save As"),
    "act.recent": ("最近文件", "Recent"),
    "act.export_word": ("导出 Word", "Export Word"),
    "act.export_pdf": ("导出 PDF", "Export PDF"),
    "act.import_word": ("导入 Word", "Import Word"),
    "act.import_pdf": ("导入 PDF", "Import PDF"),

    # ---------- 编辑 ----------
    "act.undo": ("撤销", "Undo"),
    "act.redo": ("重做", "Redo"),
    "act.bold": ("加粗", "Bold"),
    "act.italic": ("斜体", "Italic"),
    "act.strike": ("删除线", "Strike"),
    "act.inline_code": ("行内代码", "Inline Code"),
    "act.h1": ("标题 1", "Heading 1"),
    "act.h2": ("标题 2", "Heading 2"),
    "act.h3": ("标题 3", "Heading 3"),
    "act.ul": ("无序列表", "Bullet List"),
    "act.ol": ("有序列表", "Numbered List"),
    "act.quote": ("引用", "Quote"),
    "act.find": ("查找", "Find"),

    # ---------- 插入 ----------
    "act.link": ("链接", "Link"),
    "act.image": ("图片", "Image"),
    "act.table": ("表格", "Table"),
    "act.hr": ("分割线", "Divider"),
    "act.code_block": ("代码块", "Code Block"),
    "table.rows": ("行数", "Rows"),
    "table.cols": ("列数", "Columns"),
    "table.insert": ("插入表格", "Insert Table"),

    # ---------- 视图 ----------
    "act.mode_source": ("源码模式", "Source Mode"),
    "act.mode_split": ("分屏预览", "Split Preview"),
    "act.mode_wysiwyg": ("所见即所得", "WYSIWYG"),
    "act.outline": ("大纲", "Outline"),
    "act.theme": ("深色主题", "Dark Theme"),
    "act.theme_light": ("浅色主题", "Light Theme"),
    "act.autosave": ("自动保存", "Auto Save"),
    "act.restore_session": ("恢复上次会话", "Restore Last Session"),
    "autosave.every_prefix": ("每", "Every"),
    "autosave.every_suffix": ("分钟自动保存", "min auto-save"),
    "autosave.interval_saved": ("自动保存间隔：每 {n} 分钟", "Auto-save interval: every {n} min"),
    "act.lang": ("English", "中文"),
    "act.about": ("关于", "About"),

    # ---------- 转换 ----------
    "act.convert_center": ("转换中心", "Convert Center"),
    "act.md2docx": ("MD → Word", "MD → Word"),
    "act.md2pdf": ("MD → PDF", "MD → PDF"),
    "act.docx2md": ("Word → MD", "Word → MD"),
    "act.pdf2md": ("PDF → MD", "PDF → MD"),

    # ---------- 分组标题 ----------
    "group.doc": ("文档", "Document"),
    "group.clipboard": ("剪贴板", "Clipboard"),
    "group.font": ("字体", "Font"),
    "group.paragraph": ("段落", "Paragraph"),
    "group.editing": ("编辑", "Editing"),
    "group.insert": ("插入对象", "Insert"),
    "group.view": ("显示", "Display"),
    "group.tools": ("工具", "Tools"),
    "group.convert": ("格式转换", "Conversion"),

    # ---------- 转换中心 ----------
    "conv.title": ("格式转换中心", "Format Conversion Center"),
    "conv.subtitle": (
        "左右对比预览，拖动中间分割条调整比例，转换前后差异一目了然。",
        "Side-by-side preview. Drag the splitter to compare, diffs are highlighted.",
    ),
    "conv.close": ("✕ 关闭", "✕ Close"),
    "conv.close_tip": ("关闭转换中心，返回编辑界面", "Close the conversion center and return to the editor"),
    "conv.source": ("源文件", "Source"),
    "conv.use_current": ("使用当前文档", "Use current document"),
    "conv.choose_file": ("选择文件…", "Choose file…"),
    "conv.direction": ("转换方向", "Direction"),
    "conv.paper": ("纸张", "Paper"),
    "conv.margin": ("页边距 (mm)", "Margin (mm)"),
    "conv.fontsize": ("正文字号", "Font size"),
    "conv.left": ("源预览", "Source preview"),
    "conv.right": ("目标预览", "Target preview"),
    "conv.run": ("执行转换并保存", "Convert & Save"),
    "conv.refresh": ("刷新预览", "Refresh"),
    "conv.diff": ("差异概览", "Diff overview"),
    "conv.no_file": ("未选择文件（将使用当前文档）", "No file selected (current doc will be used)"),
    "conv.no_file_plain": ("未选择文件", "No file selected"),
    "msg.no_recent": ("暂无最近文件", "No recent files"),
    "recent.remove": ("移除该记录", "Remove from recent"),
    "recent.clear": ("清空所有记录", "Clear all recent"),
    "recent.cleared": ("已清空最近文件", "Recent files cleared"),
    "recent.settings": ("设置", "Settings"),
    "recent.hide": ("不显示最近文件", "Don't show recent files"),
    "recent.hidden": ("最近文件已隐藏", "Recent files are hidden"),
    "recent.limit_label": ("显示最近文件条数（1-50）：", "Number of recent files to show (1-50):"),
    "recent.limit_saved": ("最近文件显示 {n} 条", "Showing {n} recent files"),
    "recent.days_label": ("仅显示最近多少天内打开的文件：", "Only show files opened within (days):"),
    "recent.days_none": ("不限", "No limit"),
    "recent.saved_both": ("最近文件：显示 {n} 条，{d} 天内", "Recent files: {n} entries, within {d} days"),
    "recent.removed": ("已从最近文件移除：{name}", "Removed from recent files: {name}"),
    "conv.need_file": ("请先选择一个源文件。", "Please choose a source file first."),
    "conv.need_source": ("当前没有可转换的内容。", "There is nothing to convert."),
    "conv.done": ("转换完成：{path}", "Conversion finished: {path}"),
    "conv.failed": ("转换失败：{err}", "Conversion failed: {err}"),
    "conv.auto_note": (
        "提示：PDF 仅支持可提取文字的电子文档，扫描件需要 OCR。",
        "Note: PDF import works for text-based PDFs only; scans need OCR.",
    ),
    "conv.md_preview_empty": ("（无内容）", "(empty)"),

    # ---------- 状态栏 ----------
    "status.words": ("字数：{n}", "Words: {n}"),
    "status.line": ("行 {line}，列 {col}", "Ln {line}, Col {col}"),
    "status.mode": ("模式：{mode}", "Mode: {mode}"),
    "status.pages": ("共 {n} 页", "{n} pages"),
    "status.pdf_readonly": ("PDF 为只读预览，不能保存", "PDF preview is read-only"),
    "status.saved": ("已保存", "Saved"),
    "status.modified": ("未保存的更改", "Unsaved changes"),
    "status.converted": ("已转换：{name}", "Converted: {name}"),

    # ---------- 提示与对话框 ----------
    "msg.unsaved_title": ("有未保存的更改", "Unsaved changes"),
    "msg.unsaved_text": ("是否保存对「{name}」的更改？", "Save changes to \"{name}\"?"),
    "msg.open_failed": ("无法打开文件：{err}", "Cannot open file: {err}"),
    "msg.save_failed": ("保存失败：{err}", "Save failed: {err}"),
    "msg.convert_failed": ("转换失败：{err}", "Conversion failed: {err}"),
    "msg.pdf_no_text": (
        "该 PDF 没有可提取的文字，无法显示 Markdown 视图",
        "This PDF has no extractable text; Markdown views are unavailable",
    ),
    "msg.export_done": ("已导出到：{path}", "Exported to: {path}"),
    "msg.exists_title": ("文件已存在", "File already exists"),
    "msg.exists_text": (
        "「{name}」已存在，可覆盖、另存为（文件名自动加编号），或取消。",
        "“{name}” already exists. Overwrite, save as (a numbered name is pre-filled), or cancel.",
    ),
    "msg.exists_overwrite": ("覆盖", "Overwrite"),
    "msg.exists_rename": ("另存为…", "Save as…"),
    "msg.recover_title": ("发现自动保存草稿", "Auto-saved draft found"),
    "msg.recover_text": ("检测到未保存的自动保存草稿，是否恢复？", "An auto-saved draft was found. Restore it?"),
    "msg.about_text": (
        "ClaraMarkdownEditor 版本 {ver}\n\n轻量级 Markdown 编辑器，支持 Markdown / Word / PDF 三向转换与左右对比预览。\n\n技术栈：Python + PySide6 + python-docx + pypdf",
        "ClaraMarkdownEditor version {ver}\n\nA lightweight Markdown editor with Markdown / Word / PDF conversion and side-by-side preview.\n\nBuilt with Python + PySide6 + python-docx + pypdf",
    ),

    # ---------- 文件对话框 ----------
    "filter.md": ("Markdown 文件 (*.md *.markdown)", "Markdown files (*.md *.markdown)"),
    "filter.docx": ("Word 文档 (*.docx)", "Word documents (*.docx)"),
    "filter.pdf": ("PDF 文件 (*.pdf)", "PDF files (*.pdf)"),
    "filter.images": ("图片文件 (*.png *.jpg *.jpeg *.gif *.bmp *.svg)", "Images (*.png *.jpg *.jpeg *.gif *.bmp *.svg)"),
    "filter.all": ("所有文件 (*.*)", "All files (*.*)"),

    # ---------- 查找 ----------
    "find.placeholder": ("输入要查找的内容", "Find text"),
    "find.next": ("下一个", "Next"),
    "find.prev": ("上一个", "Previous"),
    "find.count": ("{n} 处匹配", "{n} matches"),
    "find.none": ("未找到", "Not found"),
    "find.close": ("关闭查找栏", "Close find bar"),
}


class I18n:
    """极简的界面翻译器。"""

    def __init__(self, lang: str = LANG_ZH) -> None:
        self.lang = lang if lang in (LANG_ZH, LANG_EN) else LANG_ZH

    def set_lang(self, lang: str) -> None:
        self.lang = LANG_ZH if lang == LANG_ZH else LANG_EN

    def toggle(self) -> str:
        self.lang = LANG_EN if self.lang == LANG_ZH else LANG_ZH
        return self.lang

    def t(self, key: str, **fmt) -> str:
        pair = STRINGS.get(key)
        if pair is None:
            return key
        text = pair[0] if self.lang == LANG_ZH else pair[1]
        return text.format(**fmt) if fmt else text
