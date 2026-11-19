"""PDF 相关转换。

- export_md_to_pdf(): 使用 Qt 自带排版引擎把 HTML 渲染成 PDF，无需额外依赖。
- import_pdf_to_md(): 使用 pypdf 提取文字并整理成 Markdown 段落。
"""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QMarginsF, QSizeF
from PySide6.QtGui import QFont, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from .render import md_to_html

PAPER_QT = {
    "A3": QPageSize.A3,
    "A4": QPageSize.A4,
    "A5": QPageSize.A5,
    "B5": QPageSize.B5,
    "Letter": QPageSize.Letter,
}


def export_html_to_pdf(
    html: str,
    path: str | Path,
    paper: str = "A4",
    margin_mm: int = 20,
    landscape: bool = False,
    font_family: str = "Microsoft YaHei",
    font_size: int = 11,
) -> Path:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    writer = QPdfWriter(str(out))
    writer.setPageSize(QPageSize(PAPER_QT.get(paper, QPageSize.A4)))
    if landscape:
        writer.setPageOrientation(QPageLayout.Landscape)
    writer.setPageMargins(
        QMarginsF(margin_mm, margin_mm, margin_mm, margin_mm),
        QPageLayout.Millimeter,
    )
    writer.setResolution(96)
    writer.setTitle(out.stem)

    document = QTextDocument()
    document.setDocumentMargin(0)
    document.setDefaultFont(QFont(font_family, font_size))
    document.setHtml(html)

    printable = writer.pageLayout().paintRectPixels(writer.resolution())
    document.setPageSize(QSizeF(printable.width(), printable.height()))
    document.print_(writer)
    return out


def export_md_to_pdf(
    md_text: str,
    path: str | Path,
    paper: str = "A4",
    margin_mm: int = 20,
    font_family: str = "Microsoft YaHei",
    font_size: int = 11,
    dark: bool = False,
) -> Path:
    """Markdown → PDF（A4 等纸张，可配置页边距）。"""
    html = md_to_html(
        md_text,
        dark=dark,
        page=False,
        font_family=font_family,
        font_size=font_size,
        padding="0",
    )
    return export_html_to_pdf(
        html,
        path,
        paper=paper,
        margin_mm=margin_mm,
        font_family=font_family,
        font_size=font_size,
    )


_SENTENCE_END = "。！？!?；;：:"


def _merge_lines(lines: list[str]) -> str:
    """把 PDF 中硬换行的文本重新拼成自然段。"""
    paragraphs: list[str] = []
    buffer = ""
    for raw in lines:
        line = raw.strip()
        if not line:
            if buffer:
                paragraphs.append(buffer.strip())
                buffer = ""
            continue
        if re.match(r"^([-•*·]|\d+[.)、])\s*", line):
            if buffer:
                paragraphs.append(buffer.strip())
                buffer = ""
            paragraphs.append(line)
            continue
        if not buffer:
            buffer = line
        elif buffer.endswith(("。", "！", "？", "!", "?", ".", ":", "：", "；", ";")):
            paragraphs.append(buffer)
            buffer = line
        else:
            # 中文之间直接相连，英文之间补空格
            joiner = "" if re.search(r"[\u4e00-\u9fff]$", buffer) else " "
            buffer += joiner + line
    if buffer:
        paragraphs.append(buffer.strip())

    cleaned = []
    for p in paragraphs:
        if p and p not in cleaned:
            cleaned.append(p)
    return "\n\n".join(cleaned)


def _lines_with_sizes(page) -> list[tuple[str, float, bool]]:
    """按阅读顺序返回 (文本, 字号, 是否粗体)；无法取得排版信息时返回空。"""
    frags: list[tuple[float, float, float, str, bool]] = []

    def visit(text, _cm, tm, font_dict, font_size):
        if not text or not text.strip():
            return
        name = ""
        if font_dict:
            name = f"{font_dict.get('/BaseFont', '')}{font_dict.get('/FontDescriptor', '')}"
        lower = name.lower()
        bold = "bold" in lower or "heavy" in lower or "black" in lower
        frags.append((float(tm[5]), float(tm[4]), float(font_size or 0), text, bold))

    try:
        page.extract_text(visitor_text=visit)
    except Exception:
        return []
    if not frags:
        return []

    # 同一水平线上的文字片段合并成一行（y 向下增大，x 向右增大）
    frags.sort(key=lambda f: (f[0], f[1]))
    rows: list[list[tuple[float, float, float, str, bool]]] = [[frags[0]]]
    for frag in frags[1:]:
        last = rows[-1][-1]
        if abs(frag[0] - last[0]) <= max(2.0, last[2] * 0.3):
            rows[-1].append(frag)
        else:
            rows.append([frag])

    lines: list[tuple[str, float, bool]] = []
    for row in rows:
        row.sort(key=lambda f: f[1])
        text = "".join(f[3] for f in row).strip()
        if not text:
            continue
        lines.append(
            (text, max(f[2] for f in row), all(f[4] for f in row))
        )
    return lines


def _heading_level(text: str, size: float, bold: bool, body: float) -> int:
    """依据字号/字重推断标题层级，0 表示正文。"""
    if not body or len(text) > 60:
        return 0
    if text.endswith(tuple(_SENTENCE_END)):
        return 0
    ratio = size / body
    if ratio >= 1.7:
        return 1
    if ratio >= 1.35:
        return 2
    if ratio >= 1.12:
        return 3
    if bold and ratio >= 0.99 and len(text) <= 30:
        return 3
    return 0


def _page_markdown(page) -> str:
    """把一页 PDF 转成带标题标记的 Markdown（尽力而为）。"""
    lines = _lines_with_sizes(page)
    if not lines:
        return ""
    weights: dict[float, int] = {}
    for text, size, _bold in lines:
        key = round(size, 1)
        weights[key] = weights.get(key, 0) + len(text)
    body = max(weights, key=weights.get) if weights else 0.0

    parts: list[str] = []
    buffer: list[str] = []
    for text, size, bold in lines:
        level = _heading_level(text, size, bold, body)
        if level:
            if buffer:
                parts.append(_merge_lines(buffer))
                buffer = []
            parts.append("#" * level + " " + text)
        else:
            buffer.append(text)
    if buffer:
        parts.append(_merge_lines(buffer))
    return "\n\n".join(p for p in parts if p).strip()


def import_pdf_to_md(path: str | Path) -> str:
    """PDF → Markdown（仅支持可提取文字的 PDF）。"""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("缺少 pypdf 依赖，请执行 pip install pypdf") from exc

    reader = PdfReader(str(path))
    chunks: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        body = _page_markdown(page)
        if not body:
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            body = _merge_lines(text.splitlines())
        if body:
            chunks.append(f"<!-- 第 {index} 页 / Page {index} -->\n\n{body}")

    result = "\n\n".join(chunks).strip()
    return result + "\n" if result else ""
