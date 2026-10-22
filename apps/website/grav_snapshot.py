"""Extractors for the rendered HTML snapshots of the old Grav site.

Every extractor takes a parsed tree (``grav_import.parse_html``) and returns plain
dictionaries; nothing here touches the database.
"""

import re
from urllib.parse import unquote

from website.grav_import import (
    Converter,
    Node,
    fragment_to_markdown,
    html_to_markdown,
    js_call_strings,
    select,
    select_one,
    select_text,
)


def children_after(container: Node, tag: str) -> list:
    """Children of ``container`` after its first ``tag`` element."""
    seen = False
    out = []
    for child in container.children:
        if seen:
            out.append(child)
        elif isinstance(child, Node) and child.tag == tag:
            seen = True
    return out


def _ancestor_href(node: Node) -> str:
    parent = node.parent
    while parent is not None:
        if parent.tag == "a":
            return parent.get("href")
        parent = parent.parent
    return ""


def last_path_segment(href: str) -> str:
    return unquote(href.rstrip("/").rsplit("/", 1)[-1])


# -- home -------------------------------------------------------------------


def _intro(container: Node, heading: str, conv: Converter) -> dict:
    return {
        "label": select_text(container, "h4"),
        "title": select_text(container, heading),
        "body": html_to_markdown(children_after(container, heading), conv),
    }


def extract_home(root: Node, conv: Converter) -> dict:
    hero = select_one(root, "div.hero-section")
    features = select_one(root, "section#features-section")
    nfdi = select_one(root, "section#nfdi-section")
    partner = select_one(root, "section#partner-section")
    if not (hero and features and nfdi and partner):
        raise ValueError("home page structure not recognised")
    partners, funders, mode = [], [], 0
    column = select_one(partner, "div.mobile-hide")
    for node in column.descendants() if column else []:
        if node.tag == "h4":
            mode += 1
        elif node.tag == "img":
            logo = {"src": node.get("src"), "alt": node.get("alt"), "url": _ancestor_href(node)}
            if mode >= 2:
                logo["large"] = "img-fluid-lg" in node.classes
                funders.append(logo)
            else:
                partners.append(logo)
    return {
        "hero": {
            "title": select_text(hero, "h5.custom-h5"),
            "quote": select_text(hero, "h5.quote"),
        },
        "mission": _intro(select_one(features, "div.feature-heading"), "h1", conv),
        "work_fields": [
            {"title": select_text(box, "h3"), "summary": select_text(box, "p.mobile-hide")}
            for box in select(features, "div.feature-box")
        ],
        "nfdi": _intro(select_one(nfdi, "div.content"), "h2", conv),
        "nfdi_cards": [
            {
                "title": select_text(box, "h3"),
                "url": (select_one(box, "a.read-more-link") or Node("a")).get("href"),
            }
            for box in select(nfdi, "div.feature-box")
        ],
        "partners_intro": _intro(select_one(partner, "div.pright-5"), "h2", conv),
        "partners": partners,
        "funders": funders,
    }


def extract_nav_labels(root: Node) -> dict:
    """Desktop menu labels: ``{path: label}`` for top-level and dropdown links."""
    labels = {}
    nav = select_one(root, "div.navbar-nav.mobile-hide")
    for link in select(nav, "a") if nav else []:
        href = link.get("href")
        if href:
            labels[unquote(href)] = link.text()
    return labels


# -- work fields --------------------------------------------------------------


def extract_work_field(root: Node, conv: Converter) -> dict:
    hero = select_one(root, "section.hero-section-2")
    if hero is None:
        raise ValueError("work field structure not recognised")
    icon = select_one(hero, "img.mobile-icon")
    packages = []
    for tab in select(root, "div#myTab a.nav-link"):
        strings = js_call_strings(tab.get("onclick"))
        packages.append(
            {
                "label": select_text(tab, "p.hover-white"),
                "title": select_text(tab, "h5.tabheading"),
                "body": fragment_to_markdown(strings[2], conv) if len(strings) >= 3 else "",
            }
        )
    return {
        "heading": select_text(hero, "h1"),
        "summary": select_text(hero, "p.text-block"),
        "icon": icon.get("src") if icon else "",
        "packages": packages,
    }


# -- legal ------------------------------------------------------------------


def extract_legal(root: Node, conv: Converter) -> dict:
    body = select_one(root, "div#privacy_text")
    title = select_text(root, "div.imprint-margin h1")
    if body is None or not title:
        raise ValueError("legal page structure not recognised")
    return {"title": title, "body": html_to_markdown(body, conv)}


# -- lists and articles ---------------------------------------------------------


def extract_article_list(root: Node, conv: Converter) -> dict:
    section = select_one(root, "section#news-section")
    if section is None:
        raise ValueError("article list structure not recognised")
    intro = select_one(section, "div.center-box.border-bottom")
    desktop = select_one(section, "div.center-box.mobile-hide")
    items = []
    for article in select(desktop, "div.article") if desktop else []:
        link = select_one(article, "h2 a")
        image = select_one(article, "img")
        items.append(
            {
                "slug": last_path_segment(link.get("href")) if link else "",
                "title": link.text() if link else "",
                "summary": select_text(article, "div.width-65 p"),
                "image_src": image.get("src") if image else "",
                "image_alt": image.get("alt") if image else "",
            }
        )
    return {
        "title": select_text(section, "h1.feature-heading"),
        "intro": html_to_markdown(intro, conv) if intro else "",
        "items": items,
    }


def extract_article(root: Node, conv: Converter) -> dict:
    article = select_one(root, "article.center-box")
    body = select_one(article, "div.post-content") if article else None
    if body is None:
        raise ValueError("article structure not recognised")
    return {
        "title": select_text(article, "h1"),
        "authors": select_text(article, "p.text-left"),
        "date_text": select_text(article, "p.text-right"),
        "body": html_to_markdown(body, conv),
    }


# -- events -----------------------------------------------------------------


def extract_event_list(root: Node) -> dict:
    section = select_one(root, "section#events-section")
    if section is None:
        raise ValueError("event list structure not recognised")
    items = []
    for event in select(section, "div.single-event"):
        link = select_one(event, "button.height-50 a.buttonlink")
        button = select_one(event, "button.height-50")
        code = ""
        for cls in button.classes if button else ():
            if cls.startswith("btn-back-"):
                code = cls[len("btn-back-") :]
        paragraphs = select(event, "div.col-md-2 p")
        cols = select(event, "div.col-md-4 p")
        items.append(
            {
                "slug": last_path_segment(link.get("href")) if link else "",
                "category": select_text(event, "div.col-md-3 p.m-0"),
                "category_code": code,
                "title": select_text(event, "h3"),
                "details": cols[0].text() if cols else "",
                "date_text": paragraphs[0].text() if paragraphs else "",
            }
        )
    return {"title": select_text(section, "h1.feature-heading"), "items": items}


def _sections(column: Node, conv: Converter) -> list[dict]:
    sections = [{"label": "", "nodes": []}]
    for child in column.children:
        if isinstance(child, Node) and child.tag == "h6":
            sections.append({"label": child.text(), "nodes": []})
        else:
            sections[-1]["nodes"].append(child)
    result = []
    for section in sections:
        body = html_to_markdown(section["nodes"], conv)
        if body or section["label"]:
            result.append({"label": section["label"], "body": body})
    return result


def _agenda(root: Node) -> list[dict]:
    items = []
    agenda = select_one(root, "ul.pl-4")
    for entry in agenda.elements() if agenda else []:
        if entry.tag != "li":
            continue
        strong = select_one(entry, "strong")
        label = strong.text().rstrip(":").strip() if strong else ""
        parts = [c for c in entry.children if isinstance(c, str)]
        subitems = [li.text() for li in select(entry, "ul.schedule-list li")]
        items.append(
            {
                "label": label,
                "title": re.sub(r"\s+", " ", "".join(parts)).strip(),
                "lines": [line for line in subitems if line],
            }
        )
    return items


def extract_event(root: Node, conv: Converter) -> dict:
    header = select_one(root, "div.row.mt-5")
    if header is None:
        raise ValueError("event structure not recognised")
    left = select_one(header, "div.col-md-7")
    facts = [h.text() for h in select(select_one(header, "div.col-md-5"), "h3")]
    facts += [""] * (3 - len(facts))
    description = select_one(root, "div.py-5")
    column = select_one(description, "div.col-md-7")
    sections = _sections(column, conv) if column else []
    image = select_one(description, "div.width-50 img")
    address = select_one(description, "div.width-50.mt-4")
    return {
        "category": select_text(left, "p.m-0"),
        "title": select_text(header, "h1"),
        "location": facts[0],
        "date_text": facts[1],
        "time_text": facts[2],
        "sections": sections,
        "image_src": image.get("src") if image else "",
        "image_alt": image.get("alt") if image else "",
        "address_lines": [p.text() for p in select(address, "p")] if address else [],
        "agenda": _agenda(root),
    }
