"""转换调度层。

把「界面」和「具体转换实现」隔开：
界面只调用 convert() / preview_pair()，不关心 docx、pdf 的实现细节。
"""

from __future__ import annotations

import html as html_lib
from dataclasses import dataclass
from pathlib import Path

from .docx_io import export_md_to_docx, import_docx_to_md
from .pdf_io import export_md_to_pdf, import_pdf_to_md
from .render import md_to_html

DIRECTIONS = ("md2docx", "md2pdf", "docx2md", "pdf2md")

DIRECTION_SOURCE = {
    "md2docx": "md",
    "md2pdf": "md",
    "docx2md": "docx",
    "pdf2md": "pdf",
}

DIRECTION_TARGET = {
    "md2docx": "docx",
    "md2pdf": "pdf",
    "docx2md": "md",
    "pdf2md": "md",
}


@dataclass
class ConversionOptions:
    paper: str = "A4"
    margin_mm: int = 20
    font_family: str = "Microsoft YaHei"
    font_size: int = 11
    dark: bool = False


def source_extension(direction: str) -> str:
    return {"md": "md", "docx": "docx", "pdf": "pdf"}[DIRECTION_SOURCE[direction]]


def target_extension(direction: str) -> str:
    return DIRECTION_TARGET[direction]


def _source_markdown(md_text: str, source_file: str | Path | None) -> str:
    """Markdown 源：选了文件就读文件，否则用当前文档内容。"""
    if source_file:
        return Path(source_file).read_text(encoding="utf-8", errors="replace")
    return md_text


def convert(
    direction: str,
    out_path: str | Path,
    options: ConversionOptions,
    md_text: str = "",
    source_file: str | Path | None = None,
) -> Path:
    """执行一次转换并返回输出文件路径。"""
    if direction not in DIRECTIONS:
        raise ValueError(f"未知的转换方向: {direction}")

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if direction == "md2docx":
        return export_md_to_docx(
            _source_markdown(md_text, source_file),
            out,
            paper=options.paper,
            margin_mm=options.margin_mm,
            font_family=options.font_family,
            font_size=options.font_size,
        )

    if direction == "md2pdf":
        return export_md_to_pdf(
            _source_markdown(md_text, source_file),
            out,
            paper=options.paper,
            margin_mm=options.margin_mm,
            font_family=options.font_family,
            font_size=options.font_size,
            dark=options.dark,
        )

    if direction == "docx2md":
        if not source_file:
            raise ValueError("Word → Markdown 需要选择源文件")
        assets = out.parent / "assets"
        text = import_docx_to_md(source_file, assets)
        out.write_text(text, encoding="utf-8")
        return out

    if direction == "pdf2md":
        if not source_file:
            raise ValueError("PDF → Markdown 需要选择源文件")
        text = import_pdf_to_md(source_file)
        out.write_text(text, encoding="utf-8")
        return out

    raise ValueError(f"未知的转换方向: {direction}")


def source_preview(
    direction: str,
    options: ConversionOptions,
    md_text: str = "",
    source_file: str | Path | None = None,
) -> tuple[str, bool]:
    """返回 (内容, 是否为 HTML)。"""
    kind = DIRECTION_SOURCE[direction]

    if kind == "md":
        text = _source_markdown(md_text, source_file)
        return md_to_html(text, dark=options.dark, font_size=options.font_size), True

    if not source_file:
        return "", True

    if kind == "docx":
        md = import_docx_to_md(source_file)
        return md_to_html(md, dark=options.dark, font_size=options.font_size), True

    # pdf：直接显示提取出来的文字
    text = import_pdf_to_md(source_file)
    escaped = html_lib.escape(text)
    body = (
        "<pre style=\"white-space:pre-wrap;font-family:Consolas,monospace;"
        f"color:{'#e6e6e6' if options.dark else '#333'};padding:18px;\">"
        f"{escaped}</pre>"
    )
    return body, True


def target_preview(
    direction: str,
    options: ConversionOptions,
    md_text: str = "",
    source_file: str | Path | None = None,
) -> tuple[str, bool]:
    """目标侧预览：转 Word / PDF 时渲染排版效果；转 Markdown 时显示生成的源码。"""
    if direction in ("md2docx", "md2pdf"):
        return (
            md_to_html(
                _source_markdown(md_text, source_file),
                dark=options.dark,
                page=False,
                font_family=options.font_family,
                font_size=options.font_size,
            ),
            True,
        )

    if direction == "docx2md":
        if not source_file:
            return "", False
        return import_docx_to_md(source_file), False

    if direction == "pdf2md":
        if not source_file:
            return "", False
        return import_pdf_to_md(source_file), False

    return "", False
