"""Markdown 解析与渲染。

包含三部分：
1. md_to_html()      Markdown → 完整 HTML（带 Word 风格 CSS），用于预览和 PDF。
2. html_to_md()      富文本 HTML → Markdown，供「所见即所得」模式回写。
3. parse_blocks()    Markdown → 结构化块列表，供导出 Word 时逐块生成样式。
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Iterable

try:  # markdown 为可选依赖，缺失时退回到内置简易解析器
    import markdown as _markdown

    HAS_MARKDOWN = True
except Exception:  # pragma: no cover - 环境缺失依赖时
    _markdown = None
    HAS_MARKDOWN = False


# ---------------------------------------------------------------------------
# Markdown → HTML
# ---------------------------------------------------------------------------

def _fallback_markdown(text: str) -> str:
    """内置的极简 Markdown 渲染器（markdown 包不可用时兜底）。"""
    out: list[str] = []
    in_code = False
    code_lines: list[str] = []
    list_open = False

    def inline(s: str) -> str:
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
        return s

    for line in text.splitlines():
        if line.strip().startswith("```"):
            if in_code:
                out.append("<pre><code>" + "\n".join(code_lines) + "</code></pre>")
                code_lines = []
            in_code = not in_code
            continue
        if in_code:
            code_lines.append(line)
            continue
        if list_open and not re.match(r"^\s*[-*+]\s+", line):
            out.append("</ul>")
            list_open = False
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            continue
        if re.match(r"^\s*[-*+]\s+", line):
            if not list_open:
                out.append("<ul>")
                list_open = True
            out.append("<li>" + inline(re.sub(r"^\s*[-*+]\s+", "", line)) + "</li>")
            continue
        if line.strip():
            out.append("<p>" + inline(line) + "</p>")
    if in_code and code_lines:
        out.append("<pre><code>" + "\n".join(code_lines) + "</code></pre>")
    if list_open:
        out.append("</ul>")
    return "\n".join(out)


_CSS_LAYOUT = """
* { box-sizing: border-box; }
body {
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 15px; line-height: 1.75;
    margin: 0; padding: 28px 36px; word-wrap: break-word;
}
h1, h2, h3, h4, h5, h6 { margin: 22px 0 10px; line-height: 1.35; }
h1 { font-size: 27px; padding-bottom: 8px; }
h2 { font-size: 22px; padding-bottom: 5px; }
h3 { font-size: 18px; }
h4 { font-size: 16px; }
h5 { font-size: 15px; }
h6 { font-size: 14px; }
p { margin: 8px 0; }
code {
    font-family: "Cascadia Mono", "Consolas", monospace;
    padding: 1px 5px; border-radius: 3px; font-size: 0.9em;
}
pre {
    padding: 12px 14px; border-radius: 4px; overflow-x: auto; line-height: 1.55;
}
pre code { background: transparent; padding: 0; }
blockquote { margin: 12px 0; padding: 8px 16px; }
blockquote p { margin: 2px 0; }
table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14px; }
th, td { padding: 7px 10px; text-align: left; vertical-align: top; }
th { font-weight: 600; }
hr { border: none; margin: 20px 0; }
img { max-width: 100%; height: auto; }
ul, ol { margin: 8px 0; padding-left: 26px; }
li { margin: 3px 0; }
"""

_CSS_LIGHT = _CSS_LAYOUT + """
body { color: #1f1f1f; background: #ffffff; }
h1, h2, h3, h4, h5, h6 { color: #1f3864; }
h1 { border-bottom: 2px solid #2b579a; }
h2 { border-bottom: 1px solid #d5dff0; }
h6 { color: #555; }
strong { color: #12233f; }
a { color: #2b579a; text-decoration: none; }
a:hover { text-decoration: underline; }
code { background: #f2f4f7; color: #b8336a; }
pre { background: #f7f8fa; border: 1px solid #e3e7ee; border-left: 4px solid #2b579a; }
pre code { color: #1f1f1f; }
blockquote { border-left: 4px solid #2b579a; background: #f5f8fd; color: #444; }
th, td { border: 1px solid #c9d3e3; }
th { background: #eaf1fb; color: #1f3864; }
tr:nth-child(even) td { background: #fafbfd; }
hr { border-top: 1px solid #d5dff0; }
"""

_CSS_DARK = _CSS_LAYOUT + """
body { color: #e6e6e6; background: #1e1e1e; }
h1, h2, h3, h4, h5, h6 { color: #9cc3ff; }
h1 { border-bottom: 2px solid #4a86d8; }
h2 { border-bottom: 1px solid #3a4a60; }
strong { color: #f2f2f2; }
a { color: #6fa8ff; text-decoration: none; }
a:hover { text-decoration: underline; }
code { background: #2b2b2b; color: #ff9ec4; }
pre { background: #262626; border: 1px solid #3a3a3a; border-left: 4px solid #4a86d8; }
pre code { color: #e6e6e6; }
blockquote { border-left: 4px solid #4a86d8; background: #2a2a2a; color: #cfcfcf; }
th, td { border: 1px solid #3f3f3f; }
th { background: #313d4d; color: #cfe1ff; }
tr:nth-child(even) td { background: #242424; }
hr { border-top: 1px solid #3f3f3f; }
"""


def md_to_body_html(md_text: str) -> str:
    """Markdown → HTML 片段（不含 <html> 外壳）。"""
    if HAS_MARKDOWN:
        return _markdown.markdown(
            md_text,
            extensions=["extra", "sane_lists", "toc", "nl2br"],
            output_format="html5",
        )
    return _fallback_markdown(md_text)


def md_to_html(
    md_text: str,
    dark: bool = False,
    page: bool = False,
    font_family: str = "",
    font_size: int = 0,
    padding: str = "",
) -> str:
    """Markdown → 完整 HTML。

    page=True 时按 A4 纸张样式渲染（用于 PDF 导出与目标预览）。
    padding 用于覆盖正文内边距，例如 PDF 导出时由打印机页边距控制。
    """
    body = md_to_body_html(md_text)
    css = _CSS_DARK if dark else _CSS_LIGHT
    extra = ""
    if page:
        extra = """
        @page { size: A4; margin: 0; }
        body { width: 210mm; min-height: 297mm; padding: 22mm 20mm; }
        """
    if font_family:
        extra += f'body {{ font-family: "{font_family}", "Microsoft YaHei UI", sans-serif; }}'
    if font_size:
        extra += f"body {{ font-size: {font_size}pt; }}"
    if padding:
        extra += f"body {{ padding: {padding}; }}"

    bg = "#1e1e1e" if dark else "#ffffff"
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>{css}{extra}</style></head>
<body style="background:{bg}">{body}</body></html>"""


# ---------------------------------------------------------------------------
# HTML → Markdown（所见即所得模式回写）
# ---------------------------------------------------------------------------

_VOID_TAGS = {
    "br", "img", "hr", "meta", "link", "input", "area",
    "base", "col", "embed", "param", "source", "track", "wbr",
}


class _Node:
    __slots__ = ("tag", "attrs", "children")

    def __init__(self, tag: str, attrs: dict, children: list) -> None:
        self.tag = tag
        self.attrs = attrs
        self.children = children


class _TreeBuilder(HTMLParser):
    """把 HTML 解析成轻量节点树，便于递归生成 Markdown。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("document", {}, [])
        self.stack: list[_Node] = [self.root]
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "head"):
            self.skip_depth += 1
            return
        node = _Node(tag, dict(attrs), [])
        self.stack[-1].children.append(node)
        if tag not in _VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        if tag in ("style", "script", "head"):
            return
        self.stack[-1].children.append(_Node(tag, dict(attrs), []))

    def handle_endtag(self, tag):
        if tag in ("style", "script", "head"):
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if self.skip_depth:
            return
        self.stack[-1].children.append(data)


def _collapse(text: str) -> str:
    return re.sub(r"[ \t\r\n]+", " ", text)


def _inline(node) -> str:
    """渲染行内 Markdown。"""
    if isinstance(node, str):
        return _collapse(node)
    tag = node.tag
    inner = "".join(_inline(c) for c in node.children)
    stripped = inner.strip()

    if tag in ("strong", "b"):
        return f"**{stripped}**" if stripped else ""
    if tag in ("em", "i"):
        return f"*{stripped}*" if stripped else ""
    if tag in ("del", "s", "strike"):
        return f"~~{stripped}~~" if stripped else ""
    if tag == "code":
        return f"`{stripped}`" if stripped else ""
    if tag == "a":
        href = node.attrs.get("href", "")
        if not href or href.startswith("#"):
            return inner
        return f"[{stripped}]({href})"
    if tag == "img":
        src = node.attrs.get("src", "")
        alt = node.attrs.get("alt", "")
        return f"![{alt}]({src})" if src else ""
    if tag == "br":
        return "  \n"
    if tag in ("p", "div", "span", "font", "u", "small", "big", "li", "td", "th", "tr", "sup", "sub"):
        return inner
    return inner


def _inline_text(node) -> str:
    """只取纯文本，用于标题等不允许行内格式的位置。"""
    if isinstance(node, str):
        return _collapse(node).strip()
    return "".join(_inline_text(c) for c in node.children).strip()


def _render_list(node, depth: int) -> list[str]:
    ordered = node.tag == "ol"
    lines: list[str] = []
    index = 1
    for child in node.children:
        if isinstance(child, str):
            continue
        if child.tag != "li":
            continue
        # li 内可能嵌套子列表，先取非列表子节点作为正文
        text_parts = []
        sub_lists = []
        for c in child.children:
            if isinstance(c, str):
                text_parts.append(_collapse(c))
            elif c.tag in ("ul", "ol"):
                sub_lists.append(c)
            elif c.tag == "p":
                text_parts.append(_inline(c).strip())
            else:
                text_parts.append(_inline(c))
        text = "".join(text_parts).strip()
        marker = f"{index}. " if ordered else "- "
        indent = "  " * depth
        if text:
            lines.append(f"{indent}{marker}{text}")
        index += 1
        for sub in sub_lists:
            lines.extend(_render_list(sub, depth + 1))
    return lines


def _render_table(node) -> list[str]:
    # Qt 生成的 HTML 会把首行放在 <thead>，因此需要递归查找所有 tr
    rows: list[list[str]] = []

    def collect_tr(current) -> None:
        for child in current.children:
            if isinstance(child, str):
                continue
            if child.tag == "tr":
                cells = []
                for td in child.children:
                    if isinstance(td, str) or td.tag not in ("td", "th"):
                        continue
                    cell = _inline(td).strip()
                    cells.append(cell.replace("|", "\\|"))
                if cells:
                    rows.append(cells)
            elif child.tag in ("thead", "tbody", "tfoot"):
                collect_tr(child)

    collect_tr(node)
    if not rows:
        return []
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |", "|" + "|".join([" --- "] * width) + "|"]
    for r in rows[1:]:
        out.append("| " + " | ".join(r) + " |")
    return out


def _render_block(node) -> list[str]:
    """返回若干 Markdown 片段。"""
    if isinstance(node, str):
        text = _collapse(node).strip()
        return [text] if text else []

    tag = node.tag
    if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(tag[1])
        text = _inline_text(node)
        return [f"{'#' * level} {text}"] if text else []
    if tag == "p":
        text = _inline(node).strip()
        return [text] if text else []
    if tag in ("ul", "ol"):
        lines = _render_list(node, 0)
        return ["\n".join(lines)] if lines else []
    if tag == "blockquote":
        inner: list[str] = []
        for c in node.children:
            inner.extend(_render_block(c))
        lines = []
        for block in inner:
            for line in block.split("\n"):
                lines.append(f"> {line}".rstrip())
        return lines
    if tag == "pre":
        raw = _raw_text(node)
        return ["```\n" + raw.rstrip("\n") + "\n```"]
    if tag == "table":
        return _render_table(node)
    if tag == "hr":
        return ["---"]
    if tag in ("body", "div", "section", "article", "blockquote_", "td", "li", "span"):
        out: list[str] = []
        for c in node.children:
            out.extend(_render_block(c))
        return out
    # 其他未知标签：递归处理
    out = []
    for c in node.children:
        out.extend(_render_block(c))
    return out


def _raw_text(node) -> str:
    if isinstance(node, str):
        return node
    return "".join(_raw_text(c) for c in node.children)


def html_to_md(html: str) -> str:
    """把 HTML（例如 QTextEdit.toHtml() 的输出）转回 Markdown。"""
    builder = _TreeBuilder()
    try:
        builder.feed(html)
        builder.close()
    except Exception:
        return html
    blocks = _render_block(builder.root)
    # 合并连续空块
    cleaned: list[str] = []
    for b in blocks:
        b = b.rstrip()
        if not b:
            continue
        if cleaned and cleaned[-1] == b:
            continue
        cleaned.append(b)
    return "\n\n".join(cleaned) + ("\n" if cleaned else "")


def html_to_plain_text(html: str) -> str:
    """去掉标签，仅保留文字（用于差异对比）。"""
    builder = _TreeBuilder()
    try:
        builder.feed(html)
        builder.close()
    except Exception:
        return re.sub(r"<[^>]+>", " ", html)
    return _raw_text(builder.root)


# ---------------------------------------------------------------------------
# Markdown → 结构块（导出 Word 用）
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^\s*```")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_LIST_RE = re.compile(r"^\s*([-*+]|\d+[.)])\s+(.*)$")
_HR_RE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:\-|]+\|[\s:\-|]*$")
_IMAGE_RE = re.compile(r"^!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)$")


def _split_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c.strip() for c in line.split("|")]


def parse_blocks(md_text: str) -> list[dict]:
    """把 Markdown 拆成块级结构（标题 / 段落 / 列表 / 代码 / 表格 / 引用 / 图片）。"""
    lines = md_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[dict] = []
    i = 0
    total = len(lines)

    while i < total:
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        if _FENCE_RE.match(line):
            lang = stripped[3:].strip()
            i += 1
            code: list[str] = []
            while i < total and not _FENCE_RE.match(lines[i]):
                code.append(lines[i])
                i += 1
            i += 1
            blocks.append({"type": "code", "lang": lang, "text": "\n".join(code)})
            continue

        m = _HEADING_RE.match(stripped)
        if m:
            blocks.append({"type": "heading", "level": len(m.group(1)), "text": m.group(2).strip()})
            i += 1
            continue

        if _HR_RE.match(line):
            blocks.append({"type": "hr"})
            i += 1
            continue

        if "|" in stripped and i + 1 < total and _TABLE_SEP_RE.match(lines[i + 1]):
            header = _split_row(stripped)
            i += 2
            rows: list[list[str]] = []
            while i < total and "|" in lines[i] and lines[i].strip():
                rows.append(_split_row(lines[i]))
                i += 1
            blocks.append({"type": "table", "header": header, "rows": rows})
            continue

        if stripped.startswith(">"):
            buf = []
            while i < total and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]).strip())
                i += 1
            blocks.append({"type": "quote", "text": " ".join(x for x in buf if x)})
            continue

        if _LIST_RE.match(line):
            items = []
            while i < total and _LIST_RE.match(lines[i]):
                raw = lines[i]
                indent = len(raw) - len(raw.lstrip(" "))
                mm = _LIST_RE.match(raw)
                items.append(
                    {
                        "text": mm.group(2).strip(),
                        "level": min(3, indent // 2),
                        "ordered": mm.group(1)[0].isdigit(),
                    }
                )
                i += 1
            blocks.append({"type": "list", "items": items})
            continue

        m = _IMAGE_RE.match(stripped)
        if m:
            blocks.append({"type": "image", "alt": m.group(1), "src": m.group(2)})
            i += 1
            continue

        # 普通段落：连续非空行合并为一段
        buf = [stripped]
        i += 1
        while i < total and lines[i].strip():
            nxt = lines[i].strip()
            if (
                _HEADING_RE.match(nxt)
                or _LIST_RE.match(lines[i])
                or nxt.startswith(">")
                or _FENCE_RE.match(lines[i])
                or _HR_RE.match(nxt)
            ):
                break
            buf.append(nxt)
            i += 1
        blocks.append({"type": "para", "text": " ".join(buf)})

    return blocks


def iter_headings(md_text: str) -> Iterable[tuple[int, str, int]]:
    """遍历标题，返回 (级别, 标题文本, 行号) —— 行号从 0 开始。"""
    for idx, line in enumerate(md_text.splitlines()):
        m = re.match(r"^(#{1,6})\s+(.*)$", line.strip())
        if m:
            yield len(m.group(1)), m.group(2).strip(), idx


def count_words(text: str) -> int:
    """统计字数：中文字符按 1 个字，英文按单词计。"""
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    english = len(re.findall(r"[A-Za-z0-9_]+", re.sub(r"[\u4e00-\u9fff]", " ", text)))
    return chinese + english
