"""Test helpers shared by the website slices.

* ``website_client`` / ``site_get`` / ``site_post``: a test client that arrives like a request forwarded by nginx
  (``X-Forwarded-Host`` preserved, path under the internal ``/site/`` prefix).
* ``make_page``: create a published website page with sensible defaults.
* ``parse_html`` / ``select`` / ``select_one`` / ``text_of``: a tiny CSS-selector helper on top of the stdlib
  ``html.parser`` (supports ``tag``, ``.class``, ``#id``, ``[attr]``, ``[attr=value]``, descendant (space) and
  child (``>``) combinators and comma-separated alternatives).
"""

import re
from html.parser import HTMLParser

from django.test import Client
from pages.models import WebsitePage

WEBSITE_HOST = "dalia.education"
TEST_HOST = "dalia-home-test.web.gateway.ionos.coscine.dev"
EXTRA_ALLOWED_HOSTS = (
    "testserver",
    "dalia.education",
    "www.dalia.education",
    "search.dalia.education",
    "dalia.education.evil.example",
    ".ionos.coscine.dev",
)


def allow_website_hosts(settings) -> None:
    """Add the website (and a few negative-test) hosts to ``ALLOWED_HOSTS`` via the pytest-django fixture."""
    settings.ALLOWED_HOSTS = [*settings.ALLOWED_HOSTS, *EXTRA_ALLOWED_HOSTS]


def website_client(settings, host: str = WEBSITE_HOST) -> Client:
    """Client whose requests carry ``X-Forwarded-Host: <host>`` (default: the public website host)."""
    allow_website_hosts(settings)
    return Client(HTTP_X_FORWARDED_HOST=host)


def site_get(client: Client, path: str, **extra):
    """GET ``/site`` + ``path`` (``path`` is the public path such as ``/en/events``)."""
    return client.get(f"/site{path}", **extra)


def site_post(client: Client, path: str, data=None, **extra):
    return client.post(f"/site{path}", data or {}, **extra)


def make_page(
    slug: str = "home", *, language: str = "en", page_type: str = "home", **fields
) -> WebsitePage:
    """Create a published website page (``title`` defaults to the slug)."""
    fields.setdefault("title", slug)
    fields.setdefault("is_published", True)
    return WebsitePage.objects.create(slug=slug, language=language, page_type=page_type, **fields)


# -- tiny HTML selector helper ---------------------------------------------

VOID_ELEMENTS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "source",
        "track",
        "wbr",
    }
)


class Node:
    def __init__(self, tag, attrs, parent=None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []
        self.parts = []  # text fragments and child nodes, in document order

    @property
    def classes(self):
        return (self.attrs.get("class") or "").split()

    def text(self) -> str:
        return "".join(p if isinstance(p, str) else p.text() for p in self.parts)

    def iter_descendants(self):
        for child in self.children:
            yield child
            yield from child.iter_descendants()


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("[document]", [])
        self._current = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, [(k, v if v is not None else "") for k, v in attrs], self._current)
        self._current.children.append(node)
        self._current.parts.append(node)
        if tag not in VOID_ELEMENTS:
            self._current = node

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, [(k, v if v is not None else "") for k, v in attrs], self._current)
        self._current.children.append(node)
        self._current.parts.append(node)

    def handle_endtag(self, tag):
        node = self._current
        while node is not self.root and node.tag != tag:
            node = node.parent
        if node is not self.root:
            self._current = node.parent

    def handle_data(self, data):
        self._current.parts.append(data)


def parse_html(html) -> Node:
    if isinstance(html, bytes):
        html = html.decode("utf-8")
    builder = _TreeBuilder()
    builder.feed(html)
    builder.close()
    return builder.root


_COMPOUND = re.compile(
    r"""(?P<tag>^[a-zA-Z][a-zA-Z0-9-]*)|\.(?P<cls>[\w-]+)|\#(?P<id>[\w-]+)|\[(?P<attr>[\w:-]+)(?:=(?P<val>"[^"]*"|'[^']*'|[^\]]*))?\]"""
)


def _parse_compound(text):
    checks = []
    pos = 0
    while pos < len(text):
        match = _COMPOUND.match(text, pos)
        if not match:
            raise ValueError(f"unsupported selector part: {text[pos:]!r}")
        pos = match.end()
        if match.group("tag"):
            checks.append(("tag", match.group("tag").lower(), None))
        elif match.group("cls"):
            checks.append(("cls", match.group("cls"), None))
        elif match.group("id"):
            checks.append(("id", match.group("id"), None))
        else:
            value = match.group("val")
            if value is not None:
                value = value.strip("\"'")
            checks.append(("attr", match.group("attr"), value))
    return checks


def _matches(node, checks) -> bool:
    for kind, name, value in checks:
        if kind == "tag" and node.tag != name:
            return False
        if kind == "cls" and name not in node.classes:
            return False
        if kind == "id" and node.attrs.get("id") != name:
            return False
        if kind == "attr" and (
            name not in node.attrs or (value is not None and node.attrs[name] != value)
        ):
            return False
    return True


def _tokenize(selector):
    tokens = []
    for raw in re.findall(r'(?:"[^"]*"|\'[^\']*\'|\[[^\]]*\]|[^\s>])+|>', selector):
        tokens.append(raw)
    return tokens


def _matches_chain(node, tokens) -> bool:
    """Does ``node`` match the last compound of ``tokens`` and its ancestors the rest?"""
    if not _matches(node, _parse_compound(tokens[-1])):
        return False
    rest = tokens[:-1]
    if not rest:
        return True
    if rest[-1] == ">":
        parent = node.parent
        return (
            parent is not None and parent.tag != "[document]" and _matches_chain(parent, rest[:-1])
        )
    parent = node.parent
    while parent is not None and parent.tag != "[document]":
        if _matches_chain(parent, rest):
            return True
        parent = parent.parent
    return False


def select(root: Node, selector: str) -> list[Node]:
    """All descendants of ``root`` matching ``selector`` (comma separated alternatives allowed)."""
    chains = [_tokenize(part) for part in selector.split(",") if part.strip()]
    return [n for n in root.iter_descendants() if any(_matches_chain(n, chain) for chain in chains)]


def select_one(root: Node, selector: str) -> Node | None:
    found = select(root, selector)
    return found[0] if found else None


def text_of(root: Node, selector: str) -> str:
    """Whitespace-normalised text of the first match (empty string when nothing matches)."""
    node = select_one(root, selector)
    return " ".join(node.text().split()) if node else ""
