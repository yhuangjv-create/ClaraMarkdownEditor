"""Word (.docx) 与 Markdown 的双向转换。

- export_md_to_docx(): 逐块生成带样式的 Word 文档。
- import_docx_to_md(): 按正文顺序读取段落/表格/图片，还原为 Markdown。
"""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Mm, Pt, RGBColor
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from .render import parse_blocks

# 纸张尺寸（毫米）：宽 × 高
PAPER_SIZES = {
    "A4": (210, 297),
    "A5": (148, 210),
    "B5": (176, 250),
    "Letter": (216, 279),
}

_INLINE_RE = re.compile(
    r"(\[[^\]]+\]\([^)]+\)"      # 链接
    r"|\*\*[^*]+\*\*"            # 粗体
    r"|__[^_]+__"
    r"|`[^`]+`"                  # 行内代码
    r"|~~[^~]+~~"                # 删除线
    r"|\*[^*]+\*"                # 斜体
    r"|_[^_]+_)"
)


# ---------------------------------------------------------------------------
# Markdown → Word
# ---------------------------------------------------------------------------

def _set_east_asian(style, font_name: str) -> None:
    """让中文字体也跟随设置（Word 需单独设置 eastAsia 字体）。"""
    try:
        rpr = style.element.get_or_add_rPr()
        rfonts = rpr.get_or_add_rFonts()
        rfonts.set(qn("w:eastAsia"), font_name)
    except Exception:
        pass


def _add_hyperlink(paragraph: Paragraph, url: str, text: str, font_size: int) -> None:
    """在段落中插入真正的 Word 超链接。"""
    try:
        r_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    except Exception:
        paragraph.add_run(f"{text} ({url})")
        return

    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)

    run = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")

    color = OxmlElement("w:color")
    color.set(qn("w:val"), "2B579A")
    r_pr.append(color)

    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    r_pr.append(underline)

    size = OxmlElement("w:sz")
    size.set(qn("w:val"), str(int(font_size * 2)))
    r_pr.append(size)

    run.append(r_pr)
    t = OxmlElement("w:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    run.append(t)
    hyperlink.append(run)
    paragraph._p.append(hyperlink)


def _shade_paragraph(paragraph: Paragraph, fill: str) -> None:
    """给段落加背景色（代码块底色）。"""
    p_pr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    p_pr.append(shd)


def _add_inline_runs(paragraph: Paragraph, text: str, font_size: int) -> None:
    """把含行内标记的文本写入段落。"""
    for token in _INLINE_RE.split(text):
        if not token:
            continue

        link = re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", token)
        if link:
            _add_hyperlink(paragraph, link.group(2), link.group(1), font_size)
            continue

        bold = italic = strike = code = False
        if token.startswith("**") and token.endswith("**") and len(token) > 4:
            token, bold = token[2:-2], True
        elif token.startswith("__") and token.endswith("__") and len(token) > 4:
            token, bold = token[2:-2], True
        elif token.startswith("~~") and token.endswith("~~") and len(token) > 4:
            token, strike = token[2:-2], True
        elif token.startswith("`") and token.endswith("`") and len(token) > 2:
            token, code = token[1:-1], True
        elif token.startswith("*") and token.endswith("*") and len(token) > 2:
            token, italic = token[1:-1], True
        elif token.startswith("_") and token.endswith("_") and len(token) > 2:
            token, italic = token[1:-1], True

        run = paragraph.add_run(token)
        run.bold = bold or None
        run.italic = italic or None
        run.font.strike = strike or None
        if code:
            run.font.name = "Consolas"
            run.font.size = Pt(max(8, font_size - 1))
            run.font.color.rgb = RGBColor(0xB8, 0x33, 0x6A)


def export_md_to_docx(
    md_text: str,
    path: str | Path,
    paper: str = "A4",
    margin_mm: int = 20,
    font_family: str = "Microsoft YaHei",
    font_size: int = 11,
) -> Path:
    """Markdown 文本 → Word 文档。"""
    doc = Document()

    # 页面尺寸与页边距
    width_mm, height_mm = PAPER_SIZES.get(paper, PAPER_SIZES["A4"])
    section = doc.sections[0]
    section.page_width = Mm(width_mm)
    section.page_height = Mm(height_mm)
    section.top_margin = Mm(margin_mm)
    section.bottom_margin = Mm(margin_mm)
    section.left_margin = Mm(margin_mm)
    section.right_margin = Mm(margin_mm)

    # 正文默认字体
    normal = doc.styles["Normal"]
    normal.font.name = font_family
    normal.font.size = Pt(font_size)
    _set_east_asian(normal, font_family)

    for block in parse_blocks(md_text):
        kind = block["type"]

        if kind == "heading":
            level = min(block["level"], 9)
            para = doc.add_paragraph(block["text"], style=f"Heading {level}")
            para.paragraph_format.space_before = Pt(12 if level <= 2 else 8)
            para.paragraph_format.space_after = Pt(6)

        elif kind == "para":
            para = doc.add_paragraph()
            _add_inline_runs(para, block["text"], font_size)
            para.paragraph_format.space_after = Pt(6)
            para.paragraph_format.line_spacing = 1.4

        elif kind == "quote":
            para = doc.add_paragraph(style="Quote")
            _add_inline_runs(para, block["text"], font_size)
            para.paragraph_format.left_indent = Mm(8)

        elif kind == "code":
            lines = block["text"].split("\n") or [""]
            for line in lines:
                para = doc.add_paragraph()
                run = para.add_run(line if line else " ")
                run.font.name = "Consolas"
                run.font.size = Pt(max(8, font_size - 1))
                para.paragraph_format.space_after = Pt(0)
                para.paragraph_format.line_spacing = 1.0
                para.paragraph_format.left_indent = Mm(6)
                _shade_paragraph(para, "F5F6F8")

        elif kind == "list":
            ordered_counter = 1
            for item in block["items"]:
                if item["ordered"]:
                    style = "List Number"
                    ordered_counter += 1
                else:
                    style = "List Bullet"
                    ordered_counter = 1
                para = doc.add_paragraph(style=style)
                _add_inline_runs(para, item["text"], font_size)
                if item["level"]:
                    para.paragraph_format.left_indent = Mm(6 + 8 * item["level"])
                para.paragraph_format.space_after = Pt(3)

        elif kind == "table":
            header = block["header"]
            rows = block["rows"]
            cols = max([len(header)] + [len(r) for r in rows]) if rows else len(header)
            table = doc.add_table(rows=1, cols=cols)
            table.style = "Table Grid"
            table.alignment = WD_TABLE_ALIGNMENT.CENTER

            for idx in range(cols):
                cell = table.rows[0].cells[idx]
                cell.text = ""
                para = cell.paragraphs[0]
                value = header[idx] if idx < len(header) else ""
                _add_inline_runs(para, value, font_size)
                for run in para.runs:
                    run.bold = True

            for row in rows:
                cells = table.add_row().cells
                for idx in range(cols):
                    value = row[idx] if idx < len(row) else ""
                    para = cells[idx].paragraphs[0]
                    _add_inline_runs(para, value, font_size)

            doc.add_paragraph().paragraph_format.space_after = Pt(4)

        elif kind == "hr":
            para = doc.add_paragraph()
            p_pr = para._p.get_or_add_pPr()
            borders = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "6")
            bottom.set(qn("w:color"), "C9D3E3")
            borders.append(bottom)
            p_pr.append(borders)

        elif kind == "image":
            src = block["src"]
            if re.match(r"^https?://", src):
                para = doc.add_paragraph()
                _add_hyperlink(para, src, block["alt"] or src, font_size)
                continue
            img_path = Path(src)
            if img_path.exists():
                try:
                    doc.add_picture(str(img_path), width=Inches(5.8))
                    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
                except Exception:
                    doc.add_paragraph(f"[图片：{img_path.name}]")
            else:
                doc.add_paragraph(f"[图片：{src}]")

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out))
    return out


# ---------------------------------------------------------------------------
# Word → Markdown
# ---------------------------------------------------------------------------

_HEADING_STYLE_RE = re.compile(r"^(Heading|标题)\s*(\d)$")


def _iter_blocks(document):
    """按正文先后顺序产出 Paragraph / Table。"""
    body = document.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, document)
        elif child.tag == qn("w:tbl"):
            yield Table(child, document)


def _run_to_md(run) -> str:
    text = run.text
    if not text:
        return ""
    font_name = (run.font.name or "").lower()
    if font_name in ("consolas", "courier new", "monospace") and text.strip():
        text = f"`{text}`"
    if run.font.strike:
        text = f"~~{text}~~"
    if run.italic:
        text = f"*{text}*"
    if run.bold:
        text = f"**{text}**"
    return text


def _hyperlink_to_md(paragraph: Paragraph, element) -> str:
    text = "".join(node.text or "" for node in element.findall(".//" + qn("w:t")))
    if not text:
        return ""
    url = ""
    r_id = element.get(qn("r:id"))
    if r_id:
        try:
            url = paragraph.part.rels[r_id].target_ref
        except Exception:
            url = ""
    return f"[{text}]({url})" if url else text


def _runs_to_md(paragraph: Paragraph) -> str:
    """按文档顺序拼接普通文本、超链接的文字。"""
    parts: list[str] = []
    for child in paragraph._p.iterchildren():
        if child.tag == qn("w:r"):
            parts.append(_run_to_md(Run(child, paragraph)))
        elif child.tag == qn("w:hyperlink"):
            parts.append(_hyperlink_to_md(paragraph, child))
    return "".join(parts)


def _save_paragraph_images(paragraph: Paragraph, assets_dir: Path | None, counter: list[int]) -> list[str]:
    """提取段落中的内嵌图片并保存为文件，返回 Markdown 图片引用列表。"""
    refs: list[str] = []
    if assets_dir is None:
        return refs
    for blip in paragraph._p.findall(".//" + qn("a:blip")):
        r_id = blip.get(qn("r:embed"))
        if not r_id:
            continue
        try:
            part = paragraph.part.related_parts[r_id]
            blob = part.blob
            ext = (str(part.partname).rsplit(".", 1)[-1] or "png").lower()
        except Exception:
            continue
        counter[0] += 1
        name = f"image{counter[0]}.{ext}"
        assets_dir.mkdir(parents=True, exist_ok=True)
        (assets_dir / name).write_bytes(blob)
        refs.append(f"![{name}](assets/{name})")
    return refs


def _table_to_md(table: Table) -> str:
    rows: list[list[str]] = []
    for row in table.rows:
        cells = []
        for cell in row.cells:
            text = " ".join(p.text.strip() for p in cell.paragraphs).strip()
            cells.append(text.replace("|", "\\|").replace("\n", " "))
        rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(rows[0]) + " |", "|" + "|".join([" --- "] * width) + "|"]
    for r in rows[1:]:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


def import_docx_to_md(path: str | Path, assets_dir: str | Path | None = None) -> str:
    """Word 文档 → Markdown 文本（图片会导出到 assets_dir）。"""
    document = Document(str(path))
    assets = Path(assets_dir) if assets_dir else None
    counter = [0]
    chunks: list[str] = []

    for block in _iter_blocks(document):
        if isinstance(block, Table):
            md_table = _table_to_md(block)
            if md_table:
                chunks.append(md_table)
            continue

        paragraph = block
        style_name = (paragraph.style.name or "").strip() if paragraph.style is not None else ""
        text_md = _runs_to_md(paragraph).strip()
        images = _save_paragraph_images(paragraph, assets, counter)

        heading_match = _HEADING_STYLE_RE.match(style_name)
        if heading_match:
            level = int(heading_match.group(2))
            if text_md:
                chunks.append(f"{'#' * max(1, min(level, 6))} {text_md}")
        elif style_name.lower() in ("title", "标题"):
            if text_md:
                chunks.append(f"# {text_md}")
        elif style_name.lower() in ("subtitle", "副标题"):
            if text_md:
                chunks.append(f"## {text_md}")
        elif style_name.lower().startswith("list bullet") or style_name.lower().startswith("列表段落"):
            if text_md:
                chunks.append(f"- {text_md}")
        elif style_name.lower().startswith("list number"):
            if text_md:
                chunks.append(f"1. {text_md}")
        elif style_name.lower() in ("quote", "intense quote", "引用"):
            if text_md:
                chunks.append(f"> {text_md}")
        elif text_md:
            chunks.append(text_md)

        if images:
            chunks.append("\n".join(images))

    text = "\n\n".join(chunks)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 相邻列表项之间用单换行（标题后的列表仍保留空行）
    text = re.sub(
        r"((?:^|\n)(?:[-*+] |\d+\. )[^\n]*)\n\n(?=(?:[-*+] |\d+\. ))", r"\1\n", text
    )
    return text.strip() + "\n" if text.strip() else ""
