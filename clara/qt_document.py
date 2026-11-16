"""把 Qt 富文本文档（所见即所得模式）还原为 Markdown。

为什么不解析 toHtml()？
    QTextEdit 输出的 HTML 会把加粗、斜体等写成 <span style="font-weight:700">，
    表格、引用等结构也会走样。直接读取 QTextDocument 的块格式、字符格式
    和表格对象，可以更准确地还原标题、列表、引用、代码块和表格。
"""

from __future__ import annotations

from PySide6.QtGui import QFont, QTextCursor, QTextDocument, QTextFormat, QTextListFormat

# 自定义块属性：用于标记「引用」和「代码块」语义
QUOTE_PROP = QTextFormat.UserProperty + 1
CODE_PROP = QTextFormat.UserProperty + 2


def _is_code_format(fmt) -> bool:
    if fmt.fontFixedPitch():
        return True
    families = fmt.fontFamilies() or []
    try:
        names = [str(f).lower() for f in families]
    except TypeError:
        names = [str(families).lower()]
    return any(key in name for name in names for key in ("consolas", "monospace", "courier"))


def _wrap(
    text: str,
    bold: bool,
    italic: bool,
    strike: bool,
    code: bool,
    href: str,
) -> str:
    if not text:
        return ""
    if not text.strip():
        return text
    leading = text[: len(text) - len(text.lstrip())]
    trailing = text[len(text.rstrip()) :]
    core = text.strip()

    if code:
        core = f"`{core}`"
    if strike:
        core = f"~~{core}~~"
    if italic:
        core = f"*{core}*"
    if bold:
        core = f"**{core}**"
    if href:
        core = f"[{core}]({href})"
    return leading + core + trailing


def _block_inline(block, strip_bold: bool = False) -> str:
    parts: list[str] = []
    iterator = block.begin()
    while not iterator.atEnd():
        fragment = iterator.fragment()
        if fragment.isValid():
            fmt = fragment.charFormat()
            parts.append(
                _wrap(
                    fragment.text(),
                    fmt.fontWeight() >= QFont.DemiBold and not strip_bold,
                    fmt.fontItalic() and not strip_bold,
                    fmt.fontStrikeOut(),
                    _is_code_format(fmt),
                    fmt.anchorHref() if fmt.isAnchor() else "",
                )
            )
        iterator += 1
    return "".join(parts)


def _list_prefix(block) -> str | None:
    text_list = block.textList()
    if text_list is None:
        return None
    fmt = text_list.format()
    indent = max(0, fmt.indent() - 1)
    ordered = fmt.style() in (
        QTextListFormat.ListDecimal,
        QTextListFormat.ListLowerAlpha,
        QTextListFormat.ListUpperAlpha,
        QTextListFormat.ListLowerRoman,
        QTextListFormat.ListUpperRoman,
    )
    marker = f"{text_list.itemNumber(block) + 1}. " if ordered else "- "
    return "  " * indent + marker


def _block_all_code(block) -> bool:
    """判断整块是否都是等宽字体（识别从 HTML 导入的代码块）。"""
    has_text = False
    iterator = block.begin()
    while not iterator.atEnd():
        fragment = iterator.fragment()
        if fragment.isValid() and fragment.text().strip():
            has_text = True
            if not _is_code_format(fragment.charFormat()):
                return False
        iterator += 1
    return has_text


def _cell_text(cell) -> str:
    if not cell.isValid():
        return ""
    end = cell.lastCursorPosition().position()
    block = cell.firstCursorPosition().block()
    parts: list[str] = []
    while block.isValid() and block.position() < end:
        text = block.text().strip()
        if text:
            parts.append(text)
        block = block.next()
    return " ".join(parts)


def _table_to_md(table) -> str:
    rows: list[list[str]] = []
    for row in range(table.rows()):
        cells = []
        for col in range(table.columns()):
            cells.append(_cell_text(table.cellAt(row, col)).replace("|", "\\|"))
        rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + "|".join([" --- "] * width) + "|"]
    for r in rows[1:]:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def mark_quote_blocks(document: QTextDocument, colors=("#f5f8fd", "#2a2a2a")) -> None:
    """把带引用底色的块标记为引用。

    Qt 导入 HTML 时不会保留 <blockquote> 语义，只能根据我们自己的
    CSS 底色（浅色 / 深色主题各一种）反推，从而保证切回源码时不丢引用。
    """
    block = document.begin()
    while block.isValid():
        brush = block.blockFormat().background()
        if (
            brush.style() != 0  # Qt.NoBrush
            and brush.color().name().lower() in colors
            and block.textList() is None
            and not block.blockFormat().headingLevel()
        ):
            fmt = block.blockFormat()
            fmt.setProperty(QUOTE_PROP, True)
            cursor = QTextCursor(block)
            cursor.setBlockFormat(fmt)
        block = block.next()


def document_to_markdown(document: QTextDocument) -> str:
    """遍历文档，按语义生成 Markdown 文本。"""
    blocks: list[str] = []
    list_buffer: list[str] = []
    code_buffer: list[str] = []
    current_list = None

    def flush_list() -> None:
        nonlocal current_list
        if list_buffer:
            blocks.append("\n".join(list_buffer))
            list_buffer.clear()
        current_list = None

    def flush_code() -> None:
        while code_buffer and not code_buffer[0].strip():
            code_buffer.pop(0)
        while code_buffer and not code_buffer[-1].strip():
            code_buffer.pop()
        if code_buffer:
            blocks.append("```\n" + "\n".join(code_buffer) + "\n```")
            code_buffer.clear()

    block = document.begin()
    last_table = None

    while block.isValid():
        # ---------- 表格 ----------
        table = QTextCursor(block).currentTable()
        if table is not None:
            if table is not last_table:
                flush_list()
                flush_code()
                md_table = _table_to_md(table)
                if md_table:
                    blocks.append(md_table)
                last_table = table
            while block.isValid() and QTextCursor(block).currentTable() is table:
                block = block.next()
            continue

        block_fmt = block.blockFormat()

        # ---------- 代码块 ----------
        is_code = bool(block_fmt.property(CODE_PROP)) or block_fmt.nonBreakableLines()
        if is_code or (
            not block_fmt.headingLevel()
            and block.textList() is None
            and _block_all_code(block)
        ):
            flush_list()
            code_buffer.append(block.text())
            block = block.next()
            continue
        flush_code()

        # ---------- 列表 ----------
        prefix = _list_prefix(block)
        if prefix is not None:
            text_list = block.textList()
            if current_list is not None and text_list is not current_list:
                flush_list()
            current_list = text_list
            text = _block_inline(block)
            if text.strip():
                list_buffer.append(prefix + text.strip())
            block = block.next()
            continue
        flush_list()

        # ---------- 标题 ----------
        heading_level = block_fmt.headingLevel()
        if heading_level:
            text = _block_inline(block, strip_bold=True).strip()
            if text:
                blocks.append(f"{'#' * min(heading_level, 6)} {text}")
        else:
            text = _block_inline(block).strip()
            if not text:
                block = block.next()
                continue
            if bool(block_fmt.property(QUOTE_PROP)) or block_fmt.leftMargin() >= 16:
                blocks.append("> " + text)
            else:
                blocks.append(text)
        block = block.next()

    flush_list()
    flush_code()

    result = "\n\n".join(b for b in blocks if b.strip())
    return result + "\n" if result else ""
