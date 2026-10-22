"""Parsing helpers for importing the old Grav site into the website pages.

Two kinds of input are handled:

* Grav page files (``*.de.md`` / ``*.en.md``: YAML front matter + Markdown), and
* rendered HTML snapshots of the live site, read with the standard library only
  (``html.parser``): a tiny element tree, a descendant selector and an HTML to
  Markdown converter that produces the restricted Markdown the website renders.
"""

import re
from html.parser import HTMLParser
from pathlib import Path

import yaml

VOID_TAGS = frozenset(
    {"br", "hr", "img", "input", "meta", "link", "source", "track", "col", "area", "base", "wbr"}
)
IGNORED_TAGS = frozenset({"script", "style", "svg", "template", "noscript"})
BLOCK_TAGS = frozenset(
    {
        "address",
        "article",
        "blockquote",
        "div",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "ul",
    }
)
HEADING_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6")

# Grav "shortcode-core" style tags that the website cannot render.
GRAV_SHORTCODES = (
    "notice|ui-tabs|ui-tab|ui-accordion|ui-accordion-item|div|section|columns|column|raw|"
    "color|size|center|left|right|justify|mark|u|safe-email|lang|fa|figure|"
    "collapse|details|spoiler|hidden"
)
SHORTCODE_RE = re.compile(rf"\[/?(?:{GRAV_SHORTCODES})(?:[ =][^\]]*)?\](?!\()", re.IGNORECASE)
TWIG_RE = re.compile(r"\{\{.*?\}\}|\{%.*?%\}", re.DOTALL)
MD_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
DATE_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})")


class Node:
    """Element of the parsed HTML tree."""

    __slots__ = ("tag", "attrs", "children", "parent")

    def __init__(self, tag, attrs=None, parent=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children = []
        self.parent = parent

    @property
    def classes(self):
        return set((self.attrs.get("class") or "").split())

    def get(self, name, default=""):
        value = self.attrs.get(name)
        return default if value is None else value

    def elements(self):
        return [c for c in self.children if isinstance(c, Node)]

    def descendants(self):
        for child in self.children:
            if isinstance(child, Node):
                yield child
                yield from child.descendants()

    def text(self) -> str:
        """Whitespace-normalised plain text."""
        return re.sub(r"\s+", " ", "".join(_text_parts(self))).strip()


def _text_parts(node):
    for child in node.children:
        if isinstance(child, str):
            yield child
        elif child.tag in IGNORED_TAGS:
            continue
        elif child.tag == "br":
            yield " "
        else:
            yield from _text_parts(child)


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root")
        self.cur = self.root

    def _close_to(self, tag) -> bool:
        node = self.cur
        while node is not None and node.tag != tag:
            node = node.parent
        if node is None or node.tag == "#root":
            return False
        self.cur = node.parent
        return True

    def handle_starttag(self, tag, attrs):
        if tag in BLOCK_TAGS and self.cur.tag == "p":
            self.cur = self.cur.parent
        if tag == "li" and self.cur.tag == "li":
            self.cur = self.cur.parent
        node = Node(tag, {k: (v or "") for k, v in attrs}, self.cur)
        self.cur.children.append(node)
        if tag not in VOID_TAGS:
            self.cur = node

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, {k: (v or "") for k, v in attrs}, self.cur)
        self.cur.children.append(node)

    def handle_endtag(self, tag):
        if tag in VOID_TAGS:
            return
        self._close_to(tag)

    def handle_data(self, data):
        if self.cur.tag in ("script", "style"):
            return
        self.cur.children.append(data)


def parse_html(text: str) -> Node:
    builder = _TreeBuilder()
    builder.feed(text)
    builder.close()
    return builder.root


_SIMPLE_SELECTOR_RE = re.compile(r"^([a-zA-Z0-9]*)((?:[.#][\w-]+)*)$")


def _matches(node: Node, tag: str, classes: set, ident: str) -> bool:
    if tag and node.tag != tag:
        return False
    if ident and node.attrs.get("id") != ident:
        return False
    return classes <= node.classes


def _parse_simple(token: str):
    match = _SIMPLE_SELECTOR_RE.match(token)
    if not match:
        raise ValueError(f"unsupported selector: {token!r}")
    tag, rest = match.groups()
    classes, ident = set(), ""
    for part in re.findall(r"[.#][\w-]+", rest):
        if part[0] == ".":
            classes.add(part[1:])
        else:
            ident = part[1:]
    return tag.lower(), classes, ident


def select(root: Node, selector: str) -> list[Node]:
    """Descendant selector (``tag.class#id`` tokens separated by spaces), document order."""
    tokens = [t for t in selector.replace(">", " ").split() if t]
    current = [root]
    for token in tokens:
        tag, classes, ident = _parse_simple(token)
        found, seen = [], set()
        for scope in current:
            for node in scope.descendants():
                if id(node) not in seen and _matches(node, tag, classes, ident):
                    seen.add(id(node))
                    found.append(node)
        current = found
    return current


def select_one(root: Node, selector: str):
    found = select(root, selector)
    return found[0] if found else None


def select_text(root: Node, selector: str) -> str:
    node = select_one(root, selector)
    return node.text() if node else ""


# -- HTML -> Markdown -------------------------------------------------------


class Converter:
    """Collects warnings and resolves images while converting HTML or Grav Markdown."""

    def __init__(self, image_hook=None, warn=None):
        # image_hook(src, alt, title) -> markdown URL string, or None when unavailable.
        self.image_hook = image_hook or (lambda src, alt, title: None)
        self.warn = warn or (lambda message: None)


_ESCAPE_RE = re.compile(r"([\\`*_\[\]<>$~^])")


def escape_md(text: str) -> str:
    return _ESCAPE_RE.sub(r"\\\1", text)


def _escape_line_start(line: str) -> str:
    """Escape a leading ``#``, ``-``, ``+`` or ``1.`` that would start a block."""
    if re.match(r"^\s*(#{1,6}\s|[-+]\s)", line):
        return re.sub(r"^(\s*)([#+\-])", r"\1\\\2", line, count=1)
    if re.match(r"^\s*\d+[.)]\s", line):
        return re.sub(r"^(\s*\d+)([.)])", r"\1\\\2", line, count=1)
    return line


def _wrap_inline(mark: str, content: str) -> str:
    stripped = content.strip()
    if not stripped:
        return content
    lead = content[: len(content) - len(content.lstrip())]
    trail = content[len(content.rstrip()) :]
    return f"{lead}{mark}{stripped}{mark}{trail}"


def _link_target(href: str) -> str:
    href = href.strip().replace(" ", "%20")
    return href.replace("(", "%28").replace(")", "%29")


def _inline_nodes(nodes, conv: Converter) -> str:
    out = []
    for node in nodes:
        if isinstance(node, str):
            out.append(escape_md(re.sub(r"\s+", " ", node)))
            continue
        out.append(_inline_node(node, conv))
    return "".join(out)


def _inline_node(node: Node, conv: Converter) -> str:
    tag = node.tag
    if tag in IGNORED_TAGS:
        return ""
    if tag == "br":
        return "\\\n"
    if tag == "img":
        return _image_md(node, conv)
    inner = _inline_nodes(node.children, conv)
    if tag in ("strong", "b"):
        return _wrap_inline("**", inner)
    if tag in ("em", "i"):
        return _wrap_inline("*", inner)
    if tag == "code":
        text = node.text()
        return f"`{text}`" if text else ""
    if tag == "a":
        href = node.get("href")
        label = inner.strip()
        if not href or href.startswith("#") or not label:
            return inner
        return f"[{label}]({_link_target(href)})"
    return inner


def _image_md(node: Node, conv: Converter) -> str:
    src = node.get("src")
    alt = re.sub(r"\s+", " ", node.get("alt")).strip()
    title = re.sub(r"\s+", " ", node.get("title")).strip()
    url = conv.image_hook(src, alt, title) if src else None
    if not url:
        conv.warn(f"image dropped (file not available): {src or '(no src)'}")
        return ""
    return f"![{escape_md(alt)}]({url})"


def _clean_inline(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" ?\\\n ?", "\\\n", text)
    text = text.strip()
    text = re.sub(r"^(\\\n)+|(\\\n)+$", "", text)
    return "\n".join(_escape_line_start(line) for line in text.split("\n"))


def _flush_inline(buffer: list, conv: Converter, blocks: list):
    if not buffer:
        return
    text = _clean_inline(_inline_nodes(buffer, conv))
    buffer.clear()
    if text:
        blocks.append(text)


def _list_block(node: Node, conv: Converter) -> str:
    ordered = node.tag == "ol"
    lines = []
    number = 0
    for item in node.elements():
        if item.tag != "li":
            continue
        number += 1
        marker = f"{number}. " if ordered else "- "
        parts = html_blocks(item.children, conv)
        if not parts:
            continue
        head, *rest = parts
        first = head.split("\n")
        lines.append(marker + first[0])
        lines.extend("    " + line for line in first[1:])
        for part in rest:
            if not re.match(r"(?:- |\d+\. )", part):
                lines.append("")
            lines.extend("    " + line if line else "" for line in part.split("\n"))
    return "\n".join(lines)


def _prefix_lines(text: str, prefix: str) -> str:
    return "\n".join(prefix + line if line else prefix.rstrip() for line in text.split("\n"))


def html_blocks(nodes, conv: Converter) -> list[str]:
    """Block-level Markdown strings for a node sequence."""
    blocks: list[str] = []
    buffer: list = []
    for node in nodes:
        if isinstance(node, str) or node.tag not in BLOCK_TAGS | {"table"}:
            if not isinstance(node, str) and node.tag in IGNORED_TAGS:
                continue
            buffer.append(node)
            continue
        _flush_inline(buffer, conv, blocks)
        blocks.extend(_block_node(node, conv))
    _flush_inline(buffer, conv, blocks)
    return blocks


def _block_node(node: Node, conv: Converter) -> list[str]:
    tag = node.tag
    if tag == "p":
        text = _clean_inline(_inline_nodes(node.children, conv))
        return [text] if text else []
    if tag in HEADING_TAGS:
        text = _clean_inline(_inline_nodes(node.children, conv)).replace("\n", " ")
        return [f"{'#' * int(tag[1])} {text}"] if text else []
    if tag in ("ul", "ol"):
        text = _list_block(node, conv)
        return [text] if text else []
    if tag == "blockquote":
        inner = "\n\n".join(html_blocks(node.children, conv))
        return [_prefix_lines(inner, "> ")] if inner else []
    if tag == "pre":
        code = "".join(_text_parts(node)).strip("\n")
        return [f"```\n{code}\n```"] if code else []
    if tag == "hr":
        return ["* * *"]
    if tag == "figure":
        return _figure_blocks(node, conv)
    if tag == "table":
        conv.warn("table flattened to plain text rows")
        rows = [re.sub(r"\s+", " ", r.text()) for r in select(node, "tr")]
        return [escape_md(r) for r in rows if r]
    return html_blocks(node.children, conv)


def _figure_blocks(node: Node, conv: Converter) -> list[str]:
    blocks = []
    image = ""
    for child in node.elements():
        if child.tag == "img":
            image = _image_md(child, conv)
            if image:
                blocks.append(image)
        elif child.tag == "figcaption" and image:
            caption = child.text()
            if caption:
                blocks.append(f"*{escape_md(caption)}*")
    return blocks


def html_to_markdown(nodes, conv: Converter | None = None) -> str:
    """Markdown for a node or a list of nodes (children of a node are used for a ``Node``)."""
    conv = conv or Converter()
    if isinstance(nodes, Node):
        nodes = nodes.children
    blocks = html_blocks(nodes, conv)
    return "\n\n".join(blocks).strip()


def fragment_to_markdown(html_text: str, conv: Converter | None = None) -> str:
    return html_to_markdown(parse_html(html_text), conv)


def decode_js_string(raw: str) -> str:
    """Decode a JavaScript single-quoted string literal body (``\\u0020`` etc.)."""
    text = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), raw)
    text = re.sub(r"\\x([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), text)
    text = text.replace("\\n", "\n").replace("\\r", "").replace("\\t", " ")
    return re.sub(r"\\(.)", r"\1", text)


def js_call_strings(call: str) -> list[str]:
    """The quoted string arguments of a call such as ``updateContent('a', 'b', 'c')``."""
    return [decode_js_string(m) for m in re.findall(r"'((?:\\.|[^'\\])*)'", call)]


# -- Grav source ------------------------------------------------------------

FRONT_MATTER_RE = re.compile(r"\A---[ \t]*\n(.*?)\n---[ \t]*\n?(.*)\Z", re.DOTALL)


def split_front_matter(text: str, warn=None):
    """``(front_matter_dict, body)``; a broken YAML block yields an empty dict and a warning."""
    text = text.lstrip("﻿")
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}, text
    raw, body = match.groups()
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError:
        if warn:
            warn("front matter could not be parsed; ignored")
        data = {}
    return (data if isinstance(data, dict) else {}), body


def read_grav_file(path: Path, warn=None):
    return split_front_matter(path.read_text(encoding="utf-8"), warn)


def grav_file(directory: Path, stem: str, lang: str) -> Path | None:
    path = directory / f"{stem}.{lang}.md"
    return path if path.is_file() else None


def strip_leading_heading(markdown: str) -> str:
    return re.sub(r"\A\s*#\s[^\n]*\n+", "", markdown)


def convert_grav_markdown(text: str, conv: Converter) -> str:
    """Grav Markdown to the Markdown the website renders (drops what it cannot render)."""
    twig = TWIG_RE.findall(text)
    if twig:
        conv.warn(f"{len(twig)} Twig expression(s) dropped")
        text = TWIG_RE.sub("", text)
    shortcodes = SHORTCODE_RE.findall(text)
    if shortcodes:
        conv.warn(f"{len(shortcodes)} Grav shortcode(s) dropped")
        text = SHORTCODE_RE.sub("", text)
    text = re.sub(r"<br\s*/?>", "\\\\\n", text, flags=re.IGNORECASE)
    html_tags = re.findall(r"</?[a-zA-Z][^>\n]*>", text)
    if html_tags:
        conv.warn(f"{len(html_tags)} raw HTML tag(s) removed (text kept)")
        text = re.sub(r"</?(?!https?:|mailto:)[a-zA-Z][^>\n]*>", "", text)

    def replace_image(match):
        alt, src = match.groups()
        url = conv.image_hook(src, alt, "")
        if not url:
            conv.warn(f"image dropped (file not available): {src}")
            return ""
        return f"![{alt}]({url})"

    text = MD_IMAGE_RE.sub(replace_image, text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# -- dates ------------------------------------------------------------------

_RANGE_FULL_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})\s*[-–]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})")
_RANGE_YEAR_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.\s*[-–]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})")
_RANGE_MONTH_RE = re.compile(r"(\d{1,2})\.\s*[-–]\s*(\d{1,2})\.(\d{1,2})\.(\d{4})")


def parse_date_text(text: str):
    """``(start, end, free_text)`` as ``datetime.date`` values; the text is kept when no exact
    single date can be derived. Returns ``(None, None, text)`` for unparseable input."""
    import datetime as dt

    text = (text or "").strip()

    def make(day, month, year):
        try:
            return dt.date(int(year), int(month), int(day))
        except ValueError:
            return None

    match = _RANGE_FULL_RE.search(text)
    if match:
        d1, m1, y1, d2, m2, y2 = match.groups()
        return make(d1, m1, y1), make(d2, m2, y2), ""
    match = _RANGE_YEAR_RE.search(text)
    if match:
        d1, m1, d2, m2, y = match.groups()
        return make(d1, m1, y), make(d2, m2, y), ""
    match = _RANGE_MONTH_RE.search(text)
    if match:
        d1, d2, m, y = match.groups()
        return make(d1, m, y), make(d2, m, y), ""
    match = DATE_RE.search(text)
    if match:
        day, month, year = match.groups()
        start = make(day, month, year)
        exact = re.fullmatch(r"\d{1,2}\.\d{1,2}\.\d{4}", text)
        return start, None, "" if exact else text
    return None, None, text


def nfc(text: str) -> str:
    import unicodedata

    return unicodedata.normalize("NFC", text)


def strip_order_prefix(name: str) -> str:
    """``02.arbeitsfelder`` -> ``arbeitsfelder`` (Grav ordering prefix)."""
    return re.sub(r"^\d+\.", "", name)
