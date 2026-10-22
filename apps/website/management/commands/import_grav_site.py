"""Create dalia.education website content from the old Grav site.

Two sources are combined: the Grav page files (primary, mostly German) and a snapshot of
the rendered live pages (``--html-dir``; used for English and for pages missing from Grav).
The import is idempotent and additive: existing pages are never changed, existing images
(same sha256) are reused. A page/language that exists in neither source is skipped.
"""

import hashlib
import io
import re
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import unquote

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction
from pages.image_processing import reencode_image
from pages.models import EventCategory, MediaImage, Page, PageBlock
from pages.rendering import RenderError
from pages.validators import validate_image_upload
from website import grav_snapshot as snap
from website.grav_import import (
    MD_IMAGE_RE,
    Converter,
    convert_grav_markdown,
    grav_file,
    nfc,
    parse_date_text,
    parse_html,
    read_grav_file,
    strip_leading_heading,
    strip_order_prefix,
)

LANGS = ("en", "de")
SITE = Page.SITE_WEBSITE
ALT_MAX = 300
TITLE_MAX = 200
CANONICAL_RE = re.compile(r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"')
CSS_COLOR_RE = re.compile(r"\.btn-back-(\w+)\s*\{[^}]*background-color:\s*(#[0-9A-Fa-f]{6})")
SIBLING_LINK_RE = re.compile(r"\]\(\.\./(?:\d+\.)?([^)/\s]+)/?\)")
LEGAL_SLUGS = ("privacy", "data_policy", "barrierefreiheit")
GRAV_LEGAL_DIRS = {"privacy": "01.privacy", "data_policy": "02.data_policy"}
SECTION_FOLDERS = {"arbeitsfelder": 1, "impressum": 2}
LIST_SECTIONS = {  # slug -> (menu_order, page_type)
    "events": (3, "event_list"),
    "news": (4, "article_list"),
    "newsletter": (5, "article_list"),
    "use_cases": (6, "article_list"),
}


class Report:
    """Created / reused / skipped counters and warnings (no page content, no personal data)."""

    def __init__(self):
        self.created = Counter()
        self.reused = Counter()
        self.skipped: list[tuple[str, str]] = []
        self.warnings: list[str] = []

    def skip(self, label: str, reason: str):
        self.skipped.append((label, reason))

    def warn(self, message: str):
        if message not in self.warnings:
            self.warnings.append(message)


class Snapshots:
    """The rendered HTML snapshots, indexed by the path of their canonical URL."""

    def __init__(self, html_dir: Path | None):
        self.index: dict[tuple, Path] = {}
        self.colors: dict[str, str] = {}
        self._cache: dict[Path, object] = {}
        if html_dir and html_dir.is_dir():
            self._scan(html_dir)

    def _scan(self, html_dir: Path):
        for path in sorted(html_dir.glob("*.html")):
            with path.open(encoding="utf-8", errors="replace") as handle:
                match = CANONICAL_RE.search(handle.read(4000))
            if not match:
                continue
            segments = [nfc(unquote(s)) for s in match.group(1).split("//", 1)[-1].split("/")[1:]]
            segments = [s for s in segments if s]
            if segments and segments[0] in LANGS:
                self.index[tuple(segments)] = path
        css = html_dir / "custom.css"
        if css.is_file():
            self.colors = {c: v.upper() for c, v in CSS_COLOR_RE.findall(css.read_text("utf-8"))}

    def get(self, lang: str, *segments: str):
        path = self.index.get((lang, *[nfc(s) for s in segments]))
        if path is None:
            return None
        if path not in self._cache:
            self._cache[path] = parse_html(path.read_text(encoding="utf-8", errors="replace"))
        return self._cache[path]


class Assets:
    """Resolves image references of the Grav site to files inside the supplied directories."""

    def __init__(self, pages_dir: Path, themes_dir: Path | None, svg_png_dir: Path | None):
        self.pages_dir = pages_dir
        self.themes_dir = themes_dir
        self.svg_png_dir = svg_png_dir

    def _candidates(self, ref: str, base_dir: Path | None):
        if ref.startswith("themes://"):
            rel = ref[len("themes://") :].split("/", 1)[-1]
            yield self.themes_dir, rel
        elif ref.startswith("/user/themes/"):
            rel = ref[len("/user/themes/") :].split("/", 1)[-1]
            yield self.themes_dir, rel
        elif ref.startswith("/user/pages/"):
            yield self.pages_dir, ref[len("/user/pages/") :]
        elif not ref.startswith(("/", "http://", "https://", "data:")) and base_dir:
            yield base_dir, ref

    def find(self, ref: str, base_dir: Path | None = None) -> Path | None:
        ref = unquote(ref.split("?")[0].split("#")[0])
        for root, rel in self._candidates(ref, base_dir):
            if root is None:
                continue
            path = (Path(root) / rel).resolve()
            if path.suffix.lower() == ".svg":
                if not self.svg_png_dir:
                    continue
                path = (self.svg_png_dir / f"{path.stem}.png").resolve()
                root = self.svg_png_dir
            if path.is_file() and Path(root).resolve() in path.parents:
                return path
        return None


class ImageRegistry:
    """Registers files as MediaImage, reusing an existing image with the same sha256."""

    def __init__(self, report: Report):
        self.report = report
        self.by_file: dict[str, MediaImage] = {}
        self.created_names: list[str] = []

    def checkpoint(self):
        return len(self.created_names)

    def rollback(self, mark: int):
        """Remove files of images created since ``mark`` (their rows were rolled back)."""
        for name in self.created_names[mark:]:
            self._delete_file(name)
        del self.created_names[mark:]
        self.by_file = {k: v for k, v in self.by_file.items() if v.pk and self._exists(v)}

    @staticmethod
    def _exists(image: MediaImage) -> bool:
        return MediaImage.objects.filter(pk=image.pk).exists()

    @staticmethod
    def _delete_file(name: str):
        storage = MediaImage._meta.get_field("image").storage
        if storage.exists(name):
            storage.delete(name)

    def remove_all_new_files(self):
        self.rollback(0)

    def register(self, path: Path, title: str, alt_en: str, alt_de: str, page) -> MediaImage | None:
        data = path.read_bytes()
        key = hashlib.sha256(data).hexdigest()
        if key in self.by_file:
            self.report.reused["image"] += 1
            return self.by_file[key]
        try:
            fmt = validate_image_upload(io.BytesIO(data), path.name)
            digest = hashlib.sha256(reencode_image(io.BytesIO(data), fmt)).hexdigest()
        except (ValidationError, ValueError, OSError) as exc:
            self.report.warn(f"image skipped ({path.name}): {self._reason(exc)}")
            return None
        existing = MediaImage.objects.filter(sha256=digest).first()
        if existing:
            self.report.reused["image"] += 1
            self.by_file[key] = existing
            return existing
        image = MediaImage(
            title=title[:TITLE_MAX],
            alt_en=alt_en[:ALT_MAX],
            alt_de=alt_de[:ALT_MAX],
            first_used_on=page,
            image=ContentFile(data, name=path.name),
        )
        image.save()
        self.created_names.append(image.image.name)
        self.by_file[key] = image
        self.report.created["image"] += 1
        return image

    @staticmethod
    def _reason(exc) -> str:
        if isinstance(exc, ValidationError):
            return "; ".join(exc.messages)[:200]
        return type(exc).__name__


class Command(BaseCommand):
    help = (
        "Create dalia.education website pages from the old Grav site (Grav pages directory and "
        "an optional HTML snapshot of the live site). Idempotent; never changes existing data."
    )

    def add_arguments(self, parser):
        parser.add_argument("pages_dir", help="Grav user/pages directory")
        parser.add_argument("--themes", help="Grav theme directory (user/themes/dalia)")
        parser.add_argument("--html-dir", help="Directory with rendered HTML snapshots")
        parser.add_argument("--svg-png-dir", help="Directory with PNG renderings of SVG icons")
        parser.add_argument("--limit-per-list", type=int, default=1)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        pages_dir = Path(options["pages_dir"])
        if not pages_dir.is_dir():
            raise CommandError(f"Not a directory: {pages_dir}")
        importer = GravImporter(
            pages_dir=pages_dir,
            themes_dir=Path(options["themes"]) if options["themes"] else None,
            html_dir=Path(options["html_dir"]) if options["html_dir"] else None,
            svg_png_dir=Path(options["svg_png_dir"]) if options["svg_png_dir"] else None,
            limit=max(1, options["limit_per_list"]),
        )
        if options["dry_run"]:
            with transaction.atomic():
                importer.run()
                transaction.set_rollback(True)
            importer.images.remove_all_new_files()
        else:
            importer.run()
        self._print(importer.report, options["dry_run"])

    def _print(self, report: Report, dry_run: bool):
        out = self.stdout.write
        out(f"Grav import summary{' (dry run, nothing saved)' if dry_run else ''}")
        out(f"{'object':<16}{'created':>8}{'reused':>8}")
        for kind in sorted(set(report.created) | set(report.reused)):
            out(f"{kind:<16}{report.created[kind]:>8}{report.reused[kind]:>8}")
        out(f"skipped: {len(report.skipped)}")
        for label, reason in report.skipped:
            out(f"  - {label}: {reason}")
        out(f"warnings: {len(report.warnings)}")
        for message in report.warnings:
            out(f"  - {message}")


class GravImporter:
    def __init__(self, pages_dir, themes_dir, html_dir, svg_png_dir, limit):
        self.pages_dir = pages_dir
        self.limit = limit
        self.report = Report()
        self.snaps = Snapshots(html_dir)
        self.assets = Assets(pages_dir, themes_dir, svg_png_dir)
        self.images = ImageRegistry(self.report)
        self.home_data: dict[str, dict] = {}
        self.wf_cards: dict[str, list] = {}
        self.nav: dict[str, dict] = {}
        self.lists: dict[str, dict] = {}

    # -- plumbing -------------------------------------------------------------

    def run(self):
        self._load_front_pages()
        self.import_home()
        self.import_work_fields()
        self.import_legal()
        self.import_events()
        for slug in ("news", "newsletter", "use_cases"):
            self.import_articles(slug)

    def warner(self, label: str):
        return lambda message: self.report.warn(f"{label}: {message}")

    def converter(self, label: str) -> Converter:
        """Keeps image references in the Markdown; ``finalize_body`` registers them later."""
        return Converter(
            image_hook=lambda src, alt, title: src.replace(" ", "%20"), warn=self.warner(label)
        )

    @contextmanager
    def unit(self, label: str):
        mark = self.images.checkpoint()
        try:
            with transaction.atomic():
                yield
        except (ValidationError, RenderError, DatabaseError, ValueError) as exc:
            self.images.rollback(mark)
            reason = "; ".join(exc.messages) if isinstance(exc, ValidationError) else str(exc)
            self.report.skip(label, f"{type(exc).__name__}: {reason[:200]}")

    def find_existing(self, lang, slug, label):
        page = Page.objects.filter(site=SITE, language=lang, slug=slug).first()
        if page:
            self.report.skip(label, "already exists (left unchanged)")
        return page

    def new_page(self, lang, slug, parent, page_type, title, **fields) -> Page:
        page = Page(
            site=SITE,
            language=lang,
            slug=slug,
            parent=parent,
            page_type=page_type,
            title=title,
            is_published=True,
            **fields,
        )
        page.full_clean()
        page.save()
        self.report.created[page_type] += 1
        return page

    def set_body(self, page: Page, markdown: str):
        if markdown:
            page.content_md = markdown
            page.save()

    def finalize_body(self, markdown: str, page: Page, base_dir: Path | None = None) -> str:
        """Register body images and point the Markdown at the media library URLs."""

        def replace(match):
            alt, src = match.groups()
            path = self.assets.find(src, base_dir)
            if path is None:
                self.report.warn(f"{page.slug}/{page.language}: image dropped, no file: {src}")
                return ""
            label = alt or path.stem.replace("_", " ")
            image = self.images.register(path, label, label, label, page)
            return f"![{alt}]({image.image.url})" if image else ""

        return self.fix_sibling_links(MD_IMAGE_RE.sub(replace, markdown), page)

    @staticmethod
    def fix_sibling_links(markdown: str, page: Page) -> str:
        """Grav links such as ``../02.data_policy`` point at a sibling page of ``page``."""
        base = page.parent.get_public_path() if page.parent else f"/{page.language}"
        return SIBLING_LINK_RE.sub(lambda m: f"]({base}/{nfc(m.group(1))})", markdown)

    def add_blocks(self, page: Page, specs: list[dict]):
        for order, spec in enumerate(specs):
            block = PageBlock(page=page, sort_order=order, **spec)
            block.full_clean()
            block.save()
        self.report.created["block"] += len(specs)

    def register_file(self, ref, base_dir, page, title, alt_en, alt_de) -> MediaImage | None:
        path = self.assets.find(ref, base_dir) if ref else None
        if path is None:
            if ref:
                self.report.warn(f"{page.slug}/{page.language}: image not available: {ref}")
            return None
        return self.images.register(path, title, alt_en or title, alt_de or alt_en or title, page)

    # -- source loading ---------------------------------------------------------

    def _load_front_pages(self):
        for lang in LANGS:
            root = self.snaps.get(lang)
            if root is None:
                continue
            conv = self.converter(f"home/{lang}")
            try:
                self.home_data[lang] = snap.extract_home(root, conv)
            except ValueError as exc:
                self.report.skip(f"home/{lang}", f"snapshot: {exc}")
                continue
            self.nav[lang] = snap.extract_nav_labels(root)
            self.wf_cards[lang] = self.home_data[lang]["work_fields"]

    def grav_dir(self, *parts) -> Path:
        return self.pages_dir.joinpath(*parts)

    def grav_page(self, directory: Path, stem: str, lang: str, label: str):
        """``(front_matter, body)`` of ``<stem>.<lang>.md`` or ``None``."""
        path = grav_file(directory, stem, lang)
        if path is None:
            return None
        return read_grav_file(path, self.warner(label))

    def nav_label(self, lang: str, path: str) -> str:
        return self.nav.get(lang, {}).get(f"/{lang}/{path}", "")

    # -- home -------------------------------------------------------------------

    def home_overrides(self, lang: str, data: dict):
        """Grav hero / NFDI / partner files take precedence over the snapshot texts."""
        home = self.grav_dir("01.home")
        label = f"home/{lang}"
        conv = self.converter(label)
        hero = self.grav_page(home / "01._hero", "hero", lang, label)
        if hero:
            data["hero"] = {
                "title": hero[0].get("heading") or data["hero"]["title"],
                "quote": hero[0].get("quote") or data["hero"]["quote"],
            }
        for key, folder, stem in (
            ("nfdi", "03._nfdi", "nfdi"),
            ("partners_intro", "04._partner", "partner"),
        ):
            found = self.grav_page(home / folder, stem, lang, label)
            if found:
                front, body = found
                data[key] = {
                    "label": front.get("heading1") or data[key]["label"],
                    "title": front.get("heading2") or data[key]["title"],
                    "body": convert_grav_markdown(body, conv) or data[key]["body"],
                }

    def logo_alts(self, kind: str, src: str) -> tuple[str, str]:
        name = Path(src).name
        alts = {}
        for lang, data in self.home_data.items():
            for logo in data[kind]:
                if Path(logo["src"]).name == name:
                    alts[lang] = logo["alt"]
        fallback = next(iter(alts.values()), Path(src).stem)
        return alts.get("en", fallback), alts.get("de", alts.get("en", fallback))

    def home_blocks(self, lang: str, home: Page) -> list[dict]:
        data = self.home_data[lang]
        specs = [
            {"kind": "hero", "title": data["hero"]["title"], "body_md": data["hero"]["quote"]},
            {"kind": "mission", **self._intro_spec(data["mission"])},
            {"kind": "nfdi_intro", **self._intro_spec(data["nfdi"])},
        ]
        specs += [
            {"kind": "link_card", "title": c["title"], "url": c["url"]} for c in data["nfdi_cards"]
        ]
        specs.append({"kind": "partners_intro", **self._intro_spec(data["partners_intro"])})
        for kind, key in (("partner_logo", "partners"), ("funder_logo", "funders")):
            for logo in data[key]:
                spec = self._logo_spec(kind, key, logo, home)
                if spec:
                    specs.append(spec)
        return specs

    @staticmethod
    def _intro_spec(intro: dict) -> dict:
        return {"label": intro["label"], "title": intro["title"], "body_md": intro["body"]}

    def _logo_spec(self, kind, key, logo, home) -> dict | None:
        alt_en, alt_de = self.logo_alts(key, logo["src"])
        image = self.register_file(logo["src"], None, home, alt_en, alt_en, alt_de)
        if image is None:
            return None
        return {
            "kind": kind,
            "title": alt_en,
            "image": image,
            "url": logo["url"],
            "label": "large" if logo.get("large") else "",
        }

    def import_home(self):
        for lang in LANGS:
            label = f"home/{lang}"
            if lang not in self.home_data:
                self.report.skip(label, "no source (neither Grav nor snapshot)")
                continue
            self.home_overrides(lang, self.home_data[lang])
            with self.unit(label):
                self._import_home_page(lang, label)

    def _import_home_page(self, lang: str, label: str):
        home = Page.objects.filter(site=SITE, language=lang, page_type="home").first()
        if home is not None and home.blocks.exists():
            self.report.skip(label, "home page with blocks already exists")
            return
        if home is None:
            title = "Home" if lang == "en" else "Startseite"
            home = self.new_page(lang, "home", None, "home", title)
        else:
            self.report.warn(f"{label}: existing home page has no blocks; blocks added only")
        self.add_blocks(home, self.home_blocks(lang, home))

    # -- work fields --------------------------------------------------------------

    def snapshot_work_field(self, lang: str, slug: str):
        root = self.snaps.get(lang, "arbeitsfelder", slug)
        if root is None:
            return None
        label = f"arbeitsfelder/{slug}/{lang}"
        return snap.extract_work_field(root, self.converter(label))

    def grav_work_field(self, directory: Path, lang: str, label: str):
        field = self.grav_page(directory / "01._arbeitsfelder", "working_field", lang, label)
        packages = self.grav_page(
            directory / "02._working_packages", "working_packages", lang, label
        )
        if not field or not packages:
            return None
        conv = self.converter(label)
        cards = packages[0].get("cards") or []
        return {
            "summary": convert_grav_markdown(strip_leading_heading(field[1]), conv),
            "icon": field[0].get("image", ""),
            "packages": [
                {
                    "label": str(c.get("smallTitle", "")),
                    "title": str(c.get("mainTitle", "")),
                    "body": convert_grav_markdown(str(c.get("content", "")), conv),
                }
                for c in cards
            ],
        }

    def work_field_data(self, lang, slug, directory):
        label = f"arbeitsfelder/{slug}/{lang}"
        return self.grav_work_field(directory, lang, label) or self.snapshot_work_field(lang, slug)

    def card_title(self, lang: str, index: int) -> str:
        cards = self.wf_cards.get(lang, [])
        return cards[index]["title"] if index < len(cards) else ""

    def import_work_fields(self):
        base = self.grav_dir("02.arbeitsfelder")
        directories = sorted(p for p in base.iterdir() if p.is_dir()) if base.is_dir() else []
        folders = {}
        for lang in LANGS:
            folders[lang] = self.import_folder(lang, "arbeitsfelder")
        for index, directory in enumerate(directories):
            slug = nfc(strip_order_prefix(directory.name))
            for lang in LANGS:
                self._import_work_field(lang, slug, directory, index, folders[lang])

    def import_folder(self, lang: str, slug: str) -> Page | None:
        label = f"{slug}/{lang}"
        title = self.nav_label(lang, slug)
        if not title:
            self.report.skip(label, "no source for the menu title")
            return None
        page = Page.objects.filter(site=SITE, language=lang, slug=slug).first()
        if page:
            self.report.skip(label, "already exists (left unchanged)")
            return page
        created = []
        with self.unit(label):
            created.append(
                self.new_page(
                    lang,
                    slug,
                    None,
                    "folder",
                    title,
                    show_in_menu=True,
                    menu_order=SECTION_FOLDERS[slug],
                )
            )
        return created[0] if created else None

    def _import_work_field(self, lang, slug, directory, index, folder):
        label = f"arbeitsfelder/{slug}/{lang}"
        data = self.work_field_data(lang, slug, directory)
        title = self.card_title(lang, index)
        if data is None or not title or folder is None:
            self.report.skip(label, "no source for this language")
            return
        if self.find_existing(lang, slug, label):
            return
        with self.unit(label):
            card = self.wf_cards[lang][index]
            page = self.new_page(
                lang,
                slug,
                folder,
                "work_field",
                title,
                summary=card["summary"],
                menu_order=index + 1,
                show_in_menu=True,
            )
            self.attach_icon(page, data["icon"], directory / "01._arbeitsfelder", index)
            self.set_body(page, self.finalize_body(data["summary"], page, directory))
            self.add_blocks(
                page,
                [
                    {
                        "kind": "work_package",
                        "label": p["label"],
                        "title": p["title"],
                        "body_md": self.finalize_body(p["body"], page, directory),
                    }
                    for p in data["packages"]
                ],
            )

    def attach_icon(self, page: Page, ref: str, base_dir: Path, index: int):
        alt_en = self.card_title("en", index) or page.title
        alt_de = self.card_title("de", index) or page.title
        image = self.register_file(ref, base_dir, page, f"{alt_en} icon", alt_en, alt_de)
        if image:
            page.cover_image = image
            page.save()

    # -- legal pages --------------------------------------------------------------

    def legal_source(self, lang: str, slug: str):
        """``(title, markdown)`` from Grav (preferred) or the snapshot, else ``None``."""
        label = f"impressum/{slug}/{lang}"
        directory = GRAV_LEGAL_DIRS.get(slug)
        if directory:
            found = self.grav_page(self.grav_dir("05.Impressum", directory), "privacy", lang, label)
            if found:
                body = convert_grav_markdown(found[1], self.converter(label))
                return str(found[0].get("title") or self.nav_label(lang, f"impressum/{slug}")), body
        root = self.snaps.get(lang, "impressum", slug)
        if root is None:
            return None
        data = snap.extract_legal(root, self.converter(label))
        return data["title"], data["body"]

    def import_legal(self):
        for lang in LANGS:
            folder = self.import_folder(lang, "impressum")
            for order, slug in enumerate(LEGAL_SLUGS, 1):
                label = f"impressum/{slug}/{lang}"
                source = self.legal_source(lang, slug)
                if source is None or folder is None:
                    self.report.skip(label, "no source for this language")
                    continue
                if self.find_existing(lang, slug, label):
                    continue
                with self.unit(label):
                    page = self.new_page(
                        lang,
                        slug,
                        folder,
                        "legal",
                        source[0],
                        menu_order=order,
                        show_in_menu=True,
                    )
                    self.set_body(page, self.finalize_body(source[1], page))

    # -- list pages -----------------------------------------------------------------

    def list_snapshot(self, lang: str, slug: str):
        root = self.snaps.get(lang, slug)
        if root is None:
            return None
        if slug == "events":
            return snap.extract_event_list(root)
        return snap.extract_article_list(root, self.converter(f"{slug}/{lang}"))

    def import_list_page(self, slug: str, lang: str) -> Page | None:
        """Create (or find) the list page; ``None`` when the language has no source."""
        label = f"{slug}/{lang}"
        data = self.lists.get((slug, lang))
        if data is None:
            self.report.skip(label, "no source for this language")
            return None
        existing = Page.objects.filter(site=SITE, language=lang, slug=slug).first()
        if existing:
            self.report.skip(label, "already exists (left unchanged)")
            return existing
        order, page_type = LIST_SECTIONS[slug]
        created = []
        with self.unit(label):
            page = self.new_page(
                lang, slug, None, page_type, data["title"], menu_order=order, show_in_menu=True
            )
            self.set_body(page, self.finalize_body(data.get("intro", ""), page))
            created.append(page)
        return created[0] if created else None

    def choose_items(self, candidates: dict[str, list[str]]) -> dict[str, list[str]]:
        """Up to ``limit`` slugs per language, preferring slugs available in both languages."""
        common = [s for s in candidates.get("en", []) if s in candidates.get("de", [])]
        chosen = dict.fromkeys(LANGS, common[: self.limit])
        for lang in LANGS:
            for slug in candidates.get(lang, []):
                if len(chosen[lang]) < self.limit and slug not in chosen[lang]:
                    chosen[lang].append(slug)
        return chosen

    # -- articles (news, newsletter, use cases) ---------------------------------------

    def import_articles(self, slug: str):
        for lang in LANGS:
            self.lists[(slug, lang)] = self.list_snapshot(lang, slug)
        candidates = {
            lang: [
                i["slug"]
                for i in (self.lists[(slug, lang)] or {"items": []})["items"]
                if self.snaps.get(lang, slug, i["slug"]) is not None
            ]
            for lang in LANGS
        }
        chosen = self.choose_items(candidates)
        for lang in LANGS:
            parent = self.import_list_page(slug, lang)
            if parent is None:
                continue
            for item in chosen[lang]:
                self._import_article(slug, lang, parent, item)
            if not chosen[lang]:
                self.report.skip(
                    f"{slug}/{lang}/<item>", "no item with a detail page in the sources"
                )

    def _import_article(self, slug, lang, parent, item_slug):
        label = f"{slug}/{item_slug}/{lang}"
        if self.find_existing(lang, item_slug, label):
            return
        with self.unit(label):
            item = next(i for i in self.lists[(slug, lang)]["items"] if i["slug"] == item_slug)
            data = snap.extract_article(
                self.snaps.get(lang, slug, item_slug), self.converter(label)
            )
            start, _, _ = parse_date_text(data["date_text"])
            page = self.new_page(
                lang,
                item_slug,
                parent,
                "article",
                data["title"],
                authors=data["authors"],
                date=start,
                summary=item["summary"],
            )
            alt = item["image_alt"] or data["title"]
            image = self.register_file(item["image_src"], None, page, data["title"], alt, alt)
            if image:
                page.cover_image = image
                page.save()
            self.set_body(page, self.finalize_body(data["body"], page))

    # -- events ------------------------------------------------------------------------

    def grav_events(self, lang: str) -> dict[str, Path]:
        base = self.grav_dir("06.events")
        found = {}
        for directory in sorted(base.iterdir(), reverse=True) if base.is_dir() else []:
            if directory.is_dir() and grav_file(directory, "event", lang):
                found[nfc(strip_order_prefix(directory.name))] = directory
        return found

    def category_color(self, name: str, code: str) -> str:
        return self.snaps.colors.get(code, "")

    def import_events(self):
        for lang in LANGS:
            self.lists[("events", lang)] = self.list_snapshot(lang, "events")
        grav = {lang: self.grav_events(lang) for lang in LANGS}
        codes = self._category_codes()
        candidates = {}
        for lang in LANGS:
            listed = [i["slug"] for i in (self.lists[("events", lang)] or {"items": []})["items"]]
            usable = [s for s in listed if s in grav[lang] or self.snaps.get(lang, "events", s)]
            candidates[lang] = usable + [s for s in grav[lang] if s not in usable]
        chosen = self.choose_items(candidates)
        for lang in LANGS:
            parent = self.import_list_page("events", lang)
            if parent is None:
                continue
            for slug in chosen[lang]:
                self._import_event(lang, parent, slug, grav[lang].get(slug), codes)

    def _category_codes(self) -> dict[str, str]:
        codes = {}
        for lang in LANGS:
            for item in (self.lists[("events", lang)] or {"items": []})["items"]:
                if item["category"] and item["category_code"]:
                    codes.setdefault(item["category"], item["category_code"])
        return codes

    def event_data(self, lang, slug, directory):
        label = f"events/{slug}/{lang}"
        if directory is not None:
            return self.grav_event(lang, slug, directory, label)
        root = self.snaps.get(lang, "events", slug)
        data = snap.extract_event(root, self.converter(label))
        listed = next(i for i in self.lists[("events", lang)]["items"] if i["slug"] == slug)
        first = data["sections"][0]["body"][:40] if data["sections"] else "\0"
        data["summary"] = "" if listed["details"].startswith(first) else listed["details"]
        data["address"] = "\n".join(data["address_lines"])
        data["image_ref"] = data["image_src"]
        return data

    def grav_event(self, lang, slug, directory, label) -> dict:
        front, _ = self.grav_page(directory, "event", lang, label)
        conv = self.converter(label)
        sections = [
            {
                "label": str(i.get("info1", "")),
                "body": convert_grav_markdown(str(i.get("details", "")), conv),
            }
            for i in front.get("info") or []
        ]
        agenda = []
        for entry in front.get("schedule") or []:
            lines = []
            for detail in entry.get("details") or []:
                lines.append(str(detail.get("text", "")))
                lines += [str(s.get("text", "")) for s in detail.get("sub_detail") or []]
            agenda.append(
                {
                    "label": str(entry.get("time", "")),
                    "title": str(entry.get("event", "")),
                    "lines": lines,
                }
            )
        image = (front.get("image") or [{}])[0] if isinstance(front.get("image"), list) else {}
        parts = [front.get("building"), front.get("street"), front.get("city")]
        return {
            "category": str(front.get("name", "")),
            "title": str(front.get("title", "")),
            "location": str(front.get("city", "") or ""),
            "date_text": str(front.get("calendar_date", "")),
            "time_text": str(front.get("time", "") or ""),
            "summary": str(front.get("detailsTable", "") or ""),
            "sections": sections,
            "agenda": agenda,
            "address": "\n".join(str(p) for p in parts if p),
            "image_ref": image.get("path", "") if isinstance(image, dict) else "",
            "image_alt": str(front.get("alt", "") or ""),
        }

    def event_category(self, name: str, codes: dict, label: str) -> EventCategory | None:
        if not name:
            return None
        existing = EventCategory.objects.filter(name_en=name).first()
        if existing:
            return existing
        color = self.snaps.colors.get(codes.get(name, ""), "")
        if not color:
            self.report.warn(f"{label}: no colour known for category '{name}'; category left empty")
            return None
        category = EventCategory(name_en=name, name_de=name, color=color, is_active=True)
        category.full_clean()
        category.save()
        self.report.created["event_category"] += 1
        return category

    def _import_event(self, lang, parent, slug, directory, codes):
        label = f"events/{slug}/{lang}"
        if self.find_existing(lang, slug, label):
            return
        with self.unit(label):
            data = self.event_data(lang, slug, directory)
            start, end, free_text = parse_date_text(data["date_text"])
            if start is None:
                raise ValueError("no usable date in the source")
            category = self.event_category(data["category"], codes, label)
            sections = list(data["sections"])
            intro = sections.pop(0) if sections and not sections[0]["label"] else None
            page = self.new_page(
                lang,
                slug,
                parent,
                "event",
                data["title"],
                date=start,
                date_end=end,
                date_text=free_text,
                time_text=data["time_text"],
                location=data["location"],
                address=data["address"],
                summary=data["summary"],
                category=category,
            )
            base = directory if directory else None
            alt = data.get("image_alt") or data["title"]
            image = self.register_file(data["image_ref"], base, page, data["title"], alt, alt)
            if image:
                page.cover_image = image
                page.save()
            body = self.finalize_body(intro["body"], page, base) if intro else ""
            self.set_body(page, body)
            self.add_blocks(page, self._event_blocks(sections, data["agenda"], page, base))

    def _event_blocks(self, sections, agenda, page, base) -> list[dict]:
        specs = [
            {
                "kind": "section",
                "label": s["label"],
                "body_md": self.finalize_body(s["body"], page, base),
            }
            for s in sections
        ]
        specs += [
            {
                "kind": "agenda",
                "label": a["label"],
                "title": a["title"],
                "body_md": "\n".join(a["lines"]),
            }
            for a in agenda
        ]
        return specs
