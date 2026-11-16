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


def import_pdf_to_md(path: str | Path) -> str:
    """PDF → Markdown（仅支持可提取文字的 PDF）。"""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("缺少 pypdf 依赖，请执行 pip install pypdf") from exc

    reader = PdfReader(str(path))
    chunks: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        body = _merge_lines(text.splitlines())
        if body:
            chunks.append(f"<!-- 第 {index} 页 / Page {index} -->\n\n{body}")

    result = "\n\n".join(chunks).strip()
    return result + "\n" if result else ""
