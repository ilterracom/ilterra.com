#!/usr/bin/env python3
"""Static site generator for ilterra.com.

    python build.py                 # build into _site/
    python build.py --serve         # build, serve on :8000 and rebuild on changes
    python build.py --strict        # fail on broken internal links (used in CI)

Content lives in content/: the path of every Markdown file is its URL
(content/products/lumev/index.md -> /products/lumev/), so old WordPress URLs
stay the same. Every internal link in the generated HTML is rewritten to a
relative one, so the output works on any domain or sub-path.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import http.server
import json
import os
import posixpath
import re
import shutil
import sys
import threading
import time
import unicodedata
from functools import partial
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
DATA = ROOT / "data"
SITE_CONFIG = ROOT / "site.yaml"

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]
FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)


# --------------------------------------------------------------------------- helpers

def slugify(value: str) -> str:
    """WordPress-compatible slug: 'Draw.io' -> 'draw-io', 'Performance & Load Testing' -> 'performance-load-testing'."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-z0-9]+", "-", value.lower().replace("&", ""))
    return value.strip("-")


def parse_date(value) -> dt.date | None:
    if value in (None, ""):
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    return dt.date.fromisoformat(str(value)[:10])


def parse_month(value) -> dt.date | None:
    """'2012-11' -> date(2012, 11, 1); None/'present' -> None."""
    if value in (None, "", "present", "now"):
        return None
    y, m = str(value).split("-")[:2]
    return dt.date(int(y), int(m), 1)


def date_long(d: dt.date | None) -> str:
    return f"{MONTHS[d.month - 1]} {d.day}, {d.year}" if d else ""


def date_short(d: dt.date | None) -> str:
    return d.strftime("%d.%m.%Y") if d else ""


def month_label(d: dt.date | None) -> str:
    return f"{MONTHS[d.month - 1][:3]} {d.year}" if d else "Present"


def strip_tags(text: str) -> str:
    text = re.sub(r"<(script|style)\b.*?</\1>", " ", text, flags=re.S)
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))).strip()


def truncate(text: str, length: int) -> str:
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0].rstrip(",.;:—–-") + "…"


def relative_url(target: str, from_dir: str, index_links: bool = False) -> str:
    """Turn a site-absolute URL (/a/b/) into one relative to from_dir (also /x/y/)."""
    path, sep, frag = target.partition("#")
    path, qsep, query = path.partition("?")
    suffix = (qsep + query if qsep else "") + (sep + frag if sep else "")
    if not path:
        return target
    is_dir = path.endswith("/")
    rel = posixpath.relpath(path, from_dir)
    if rel == ".":
        rel = "./"
    elif is_dir:
        rel += "/"
    if index_links and rel.endswith("/"):
        rel += "index.html"
    return rel + suffix


# --------------------------------------------------------------------------- model

class Page:
    """One Markdown file from content/."""

    def __init__(self, source: Path, meta: dict, body: str):
        self.source = source
        self.meta = meta
        rel = source.relative_to(CONTENT).with_suffix("")
        parts = list(rel.parts)
        if parts[-1] == "index":
            parts = parts[:-1]
        self.url = "/" + "/".join(parts) + ("/" if parts else "")
        self.dir_url = self.url
        self.title = str(meta.get("title", parts[-1] if parts else "Home"))
        self.type = meta.get("type", "page")
        self.date = parse_date(meta.get("date"))
        self.updated = parse_date(meta.get("updated"))
        self.tags = [str(t) for t in meta.get("tags", []) or []]
        self.categories = [str(c).strip("/") for c in meta.get("categories", []) or []]
        self.weight = meta.get("weight")
        self.lang = meta.get("lang")
        self.draft = bool(meta.get("draft", False))
        self.body_md = body
        self.content = Markup("")
        self.toc: list = []
        self.cover = self.resolve(meta.get("cover"))
        self.summary = str(meta.get("summary", "") or "")
        self.description = str(meta.get("description", "") or self.summary)
        self.text = ""

    def resolve(self, ref):
        """Resolve a path from front matter relative to the page folder."""
        if not ref:
            return None
        ref = str(ref)
        if re.match(r"^[a-z]+:|^/", ref):
            return ref
        return posixpath.normpath(posixpath.join(self.dir_url, ref))

    def __getattr__(self, item):  # front-matter fields are available as page.<field>
        meta = self.__dict__.get("meta", {})
        if item in meta:
            return meta[item]
        raise AttributeError(item)

    def __repr__(self):
        return f"<Page {self.url}>"


def load_pages(include_drafts: bool) -> list[Page]:
    pages = []
    for path in sorted(CONTENT.rglob("*.md")):
        raw = path.read_text(encoding="utf-8")
        m = FRONT_MATTER.match(raw)
        meta = yaml.safe_load(m.group(1)) if m else {}
        body = raw[m.end():] if m else raw
        page = Page(path, meta or {}, body)
        if page.draft and not include_drafts:
            continue
        pages.append(page)
    return pages


def render_markdown(page: Page):
    md = markdown.Markdown(
        extensions=["extra", "sane_lists", "toc"],
        extension_configs={"toc": {"toc_depth": "2-3"}},
        output_format="html",
    )
    out = md.convert(page.body_md)
    # lazy images, external links in a new tab
    out = re.sub(r"<img (?![^>]*\bloading=)", '<img loading="lazy" decoding="async" ', out)
    out = IMG_RE.sub(classify_image, out)
    out = re.sub(r'<a href="(https?://[^"]+)"(?![^>]*\btarget=)', r'<a href="\1" target="_blank" rel="noopener"', out)
    out = out.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")
    page.content = Markup(out)
    page.toc = md.toc_tokens
    page.text = strip_tags(out)
    page.words = len(page.text.split())
    page.reading_time = max(1, round(page.words / 220))
    if not page.summary:
        page.summary = truncate(page.text, 200)
    if not page.description:
        page.description = page.summary


IMG_RE = re.compile(r"<img\b[^>]*>")


def classify_image(m: re.Match) -> str:
    """Tag images so the layout can size them: phone screenshots and store badges."""
    tag = m.group(0)
    src = re.search(r'\ssrc="([^"]*)"', tag)
    w = re.search(r'\swidth="(\d+)"', tag)
    h = re.search(r'\sheight="(\d+)"', tag)
    classes = []
    name = posixpath.basename(src.group(1)).lower() if src else ""
    if re.search(r"(^|[-_])(button|badge)", name):
        classes.append("is-badge")
    elif w and h and int(h.group(1)) >= 1.6 * int(w.group(1)):
        classes.append("is-portrait")
    if not classes:
        return tag
    if ' class="' in tag:
        return tag.replace(' class="', f' class="{" ".join(classes)} ', 1)
    return tag.replace("<img ", f'<img class="{" ".join(classes)}" ', 1)


def markdown_inline(text: str) -> Markup:
    """Short Markdown snippet (front matter) -> inline HTML; line breaks are kept."""
    out = markdown.markdown(str(text or "").strip(), extensions=["nl2br"])
    out = re.sub(r"^<p>|</p>$", "", out.strip())
    return Markup(out)


def toc_count(tokens) -> int:
    return sum(1 + toc_count(t["children"]) for t in tokens)


# --------------------------------------------------------------------------- site

class Site:
    def __init__(self, args):
        self.args = args
        self.out = Path(args.out).resolve()
        self.site_url = (args.site_url or os.environ.get("SITE_URL", "")).rstrip("/")
        self.config = yaml.safe_load(SITE_CONFIG.read_text(encoding="utf-8"))
        self.categories_def = yaml.safe_load((DATA / "categories.yaml").read_text(encoding="utf-8")) or []
        self.experience = self.load_experience()
        self.pages = load_pages(args.drafts)
        self.by_url = {p.url: p for p in self.pages}
        self.generated: list[tuple[str, str, dict]] = []  # (url, template, context)
        self.errors: list[str] = []
        self.warnings: list[str] = []

        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.env.filters.update(date_long=date_long, date_short=date_short, month_label=month_label,
                                slugify=slugify, truncate_text=truncate, markdown_inline=markdown_inline)
        self.env.globals.update(site=self.config, build_year=dt.date.today().year,
                                icon=self.icon, abs_url=self.abs_url, site_url=self.site_url)

    # ---- data

    def load_experience(self):
        raw = yaml.safe_load((DATA / "experience.yaml").read_text(encoding="utf-8")) or []
        items = []
        for e in raw:
            item = dict(e)
            item["start_date"] = parse_month(e.get("start"))
            item["end_date"] = parse_month(e.get("end"))
            item["tags"] = [str(t) for t in e.get("tags", []) or []]
            items.append(item)
        items.sort(key=lambda e: (e["start_date"], e["end_date"] or dt.date.max))
        return items

    def icon(self, name: str, cls: str = "icon") -> Markup:
        path = TEMPLATES / "icons" / f"{name}.svg"
        svg = path.read_text(encoding="utf-8").strip()
        return Markup(svg.replace("<svg ", f'<svg class="{cls}" aria-hidden="true" focusable="false" ', 1))

    def abs_url(self, url: str) -> str:
        """Absolute URL for canonical/og/sitemap; empty when SITE_URL is unknown."""
        if not self.site_url or not url:
            return ""
        if re.match(r"^[a-z]+:", url):
            return url
        return self.site_url + url

    # ---- taxonomies

    def build_taxonomies(self):
        tags: dict[str, dict] = {}

        def add(name, item, kind):
            slug = slugify(name)
            if not slug:
                return
            t = tags.setdefault(slug, {"slug": slug, "name": name, "url": f"/tag/{slug}/", "pages": [], "experience": []})
            t[kind].append(item)

        for p in self.pages:
            for name in p.tags:
                add(name, p, "pages")
        for e in self.experience:
            for name in e["tags"]:
                add(name, e, "experience")
        for t in tags.values():
            t["count"] = len(t["pages"]) + len(t["experience"])
            t["pages"].sort(key=lambda p: p.date or dt.date.min, reverse=True)
        self.tags = dict(sorted(tags.items(), key=lambda kv: kv[1]["name"].lower()))
        self.tag_cloud = self.make_cloud(list(self.tags.values()))
        self.tag_by_name = {t["name"]: t for t in self.tags.values()}
        for p in self.pages:
            p.tag_items = [self.tags[slugify(n)] for n in p.tags if slugify(n) in self.tags]

        cats = []
        for c in self.categories_def:
            path = c["path"].strip("/")
            members = [p for p in self.pages
                       if any(pc == path or pc.startswith(path + "/") for pc in p.categories)]
            members.sort(key=lambda p: p.date or dt.date.min, reverse=True)
            cats.append({**c, "path": path, "url": f"/category/{path}/", "pages": members})
        self.categories = {c["path"]: c for c in cats}
        known = set(self.categories)
        for p in self.pages:
            for c in p.categories:
                if c not in known:
                    self.errors.append(f"{p.source.relative_to(ROOT)}: unknown category '{c}' (add it to data/categories.yaml)")
            p.category_items = [self.categories[c] for c in p.categories if c in self.categories]

    def make_cloud(self, tags):
        cfg = self.config.get("tag_cloud", {})
        smallest, largest = cfg.get("smallest", 8), cfg.get("largest", 22)
        limit = cfg.get("limit") or 0
        tags = [t for t in tags if t["count"] > 0]
        if limit:
            tags = sorted(tags, key=lambda t: -t["count"])[:limit]
            tags.sort(key=lambda t: t["name"].lower())
        if not tags:
            return []
        lo, hi = min(t["count"] for t in tags), max(t["count"] for t in tags)
        step = (largest - smallest) / (hi - lo) if hi > lo else 0
        return [{**t, "size": round(smallest + (t["count"] - lo) * step, 1)} for t in tags]

    # ---- collections used by templates

    def collections(self):
        def by_type(*types):
            return [p for p in self.pages if p.type in types]

        def newest(items):
            return sorted(items, key=lambda p: p.date or dt.date.min, reverse=True)

        products = by_type("product")
        featured = sorted([p for p in products if p.weight is not None], key=lambda p: p.weight)
        others = newest([p for p in products if p.weight is None])
        return {
            "products": featured + others,
            "featured_products": featured,
            "other_products": others,
            "clients": newest(by_type("client")),
            "articles": newest(by_type("article")),
            "experience": self.experience,
            "tag_cloud": self.tag_cloud,
            "tags": self.tags,
            "categories": self.categories,
            "page_by_url": self.by_url,
        }

    def children_of(self, page: Page):
        return sorted([p for p in self.pages if p.meta.get("parent") == page.url],
                      key=lambda p: (p.weight if p.weight is not None else 999, p.title))

    # Section a page belongs to: (label for the eyebrow, breadcrumb title, breadcrumb url)
    SECTIONS = {
        "product": ("Product", "Products", "/products/"),
        "client": ("Case study", "Experience", "/work-experience/"),
        "article": ("Knowledge sharing", "Knowledge Sharing", "/category/knowledge-sharing/"),
        "doc": ("Guide", None, None),
    }

    def breadcrumbs(self, page: Page, depth: int = 0) -> list[dict]:
        """Trail of {title, url} above the page (the page itself is not included)."""
        trail = [{"title": "Home", "url": "/"}]
        parent = self.by_url.get(page.meta.get("parent", ""))
        if parent and depth < 5:
            return self.breadcrumbs(parent, depth + 1) + [{"title": parent.title, "url": parent.url}]
        sec = self.SECTIONS.get(page.type)
        if sec and sec[2] and sec[2] != page.url:
            trail.append({"title": sec[1], "url": sec[2]})
        return trail

    def eyebrow(self, page: Page) -> str:
        if page.meta.get("eyebrow"):
            return str(page.meta["eyebrow"])
        if page.type == "article":
            sub = [c for c in page.category_items if c["path"].startswith("knowledge-sharing/")]
            return sub[0]["name"] if sub else "Knowledge sharing"
        return self.SECTIONS.get(page.type, ("",))[0]

    def related(self, page: Page, limit: int = 3) -> list[Page]:
        """Same-type pages, most shared tags first, then newest."""
        if page.type not in ("product", "client", "article"):
            return []
        mine = {slugify(t) for t in page.tags}
        pool = [p for p in self.pages if p.type == page.type and p is not page]
        pool.sort(key=lambda p: (len(mine & {slugify(t) for t in p.tags}), p.date or dt.date.min), reverse=True)
        return pool[:limit]

    # ---- rendering

    def render(self, template: str, url: str, **ctx) -> str:
        tpl = self.env.get_template(template)
        html_out = tpl.render(url=url, **self.coll, **ctx)
        return self.relativize(html_out, url)

    ATTR_RE = re.compile(r'(\s(?:href|src|action|poster|data-[\w-]+)=)(["\'])(/(?!/)[^"\']*)\2')
    SRCSET_RE = re.compile(r'(\ssrcset=)(["\'])([^"\']*)\2')
    CSS_URL_RE = re.compile(r'url\((["\']?)(/(?!/)[^)"\']*)\1\)')

    def relativize(self, text: str, url: str) -> str:
        from_dir = url if url.endswith("/") else posixpath.dirname(url) + "/"
        rel = partial(relative_url, from_dir=from_dir, index_links=self.args.index_links)
        text = self.ATTR_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{rel(m.group(3))}{m.group(2)}", text)

        def srcset(m):
            parts = []
            for cand in m.group(3).split(","):
                bits = cand.strip().split()
                if bits and bits[0].startswith("/") and not bits[0].startswith("//"):
                    bits[0] = rel(bits[0])
                parts.append(" ".join(bits))
            return f"{m.group(1)}{m.group(2)}{', '.join(parts)}{m.group(2)}"

        text = self.SRCSET_RE.sub(srcset, text)
        text = self.CSS_URL_RE.sub(lambda m: f"url({m.group(1)}{rel(m.group(2))}{m.group(1)})", text)
        return text

    def write(self, url: str, content: str):
        rel = url.lstrip("/")
        target = self.out / rel / "index.html" if url.endswith("/") else self.out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def build(self):
        start = time.time()
        if self.out.exists():
            shutil.rmtree(self.out)
        self.out.mkdir(parents=True)
        shutil.copytree(STATIC, self.out, dirs_exist_ok=True)
        for f in CONTENT.rglob("*"):
            if f.is_file() and f.suffix != ".md" and not f.name.startswith("."):
                dest = self.out / f.relative_to(CONTENT)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)

        for p in self.pages:
            render_markdown(p)
        self.build_taxonomies()
        self.coll = self.collections()

        urls: list[tuple[str, dt.date | None]] = []
        for p in self.pages:
            template = p.meta.get("template") or {
                "home": "home.html", "section": "products.html", "experience": "experience.html",
            }.get(p.type, "page.html")
            parent = self.by_url.get(p.meta.get("parent", ""))
            ctx = {"page": p, "children": self.children_of(p), "parent": parent,
                   "siblings": [s for s in self.children_of(parent) if s is not p] if parent else [],
                   "toc_count": toc_count(p.toc),
                   "crumbs": self.breadcrumbs(p), "eyebrow": self.eyebrow(p), "related": self.related(p)}
            self.write(p.url, self.render(template, p.url, **ctx))
            urls.append((p.url, p.updated or p.date))

        for c in self.categories.values():
            parts = c["path"].split("/")
            crumbs = [{"title": "Home", "url": "/"}] + [
                {"title": self.categories[a]["name"], "url": self.categories[a]["url"]}
                for a in ("/".join(parts[:i]) for i in range(1, len(parts))) if a in self.categories]
            subcats = [s for s in self.categories.values()
                       if s["path"].startswith(c["path"] + "/") and s["path"].count("/") == c["path"].count("/") + 1]
            desc = c.get("description") or f"{c['name']}: {len(c['pages'])} item{'s' if len(c['pages']) != 1 else ''}."
            fake = {"title": c["name"], "description": desc, "url": c["url"]}
            self.write(c["url"], self.render("list.html", c["url"], page=fake, items=c["pages"], heading=c["name"],
                                             eyebrow="Category", crumbs=crumbs, subcats=subcats,
                                             lead=c.get("description", ""), experience_items=[]))
            urls.append((c["url"], None))
        for t in self.tags.values():
            fake = {"title": f"Tag: {t['name']}", "description": f"Projects, clients and notes tagged {t['name']}.", "url": t["url"]}
            self.write(t["url"], self.render("list.html", t["url"], page=fake, items=t["pages"], heading=t["name"],
                                             eyebrow="Tag", crumbs=[{"title": "Home", "url": "/"}], subcats=[],
                                             lead=f"Projects, clients and notes tagged “{t['name']}”.",
                                             experience_items=t["experience"]))
            urls.append((t["url"], None))

        search_page = {"title": "Search", "description": "Search the site", "url": "/search/", "noindex": True}
        self.write("/search/", self.render("search.html", "/search/", page=search_page))
        self.write("/404.html", self.render("404.html", "/", page={"title": "Page not found", "description": "", "url": "/404.html", "noindex": True}))
        self.write_search_index()
        self.write_seo(urls)
        self.check_links()
        took = time.time() - start
        n_html = sum(1 for _ in self.out.rglob("*.html"))
        print(f"Built {n_html} HTML files into {self.out.relative_to(ROOT) if self.out.is_relative_to(ROOT) else self.out} in {took:.2f}s"
              + (f" (site URL {self.site_url})" if self.site_url else " (no SITE_URL: canonical/sitemap skipped)"))
        for w in self.warnings:
            print("  warning:", w)
        for e in self.errors:
            print("  ERROR:", e)

    def write_search_index(self):
        docs = []
        for p in self.pages:
            if p.type in ("home",) or p.meta.get("noindex"):
                continue
            docs.append({"t": p.title, "u": p.url.lstrip("/"), "s": p.summary, "k": p.tags,
                         "d": date_short(p.date), "x": truncate(p.text, 4000)})
        (self.out / "search-index.json").write_text(json.dumps(docs, ensure_ascii=False, separators=(",", ":")),
                                                     encoding="utf-8")

    def write_seo(self, urls):
        robots = ["User-agent: *", "Allow: /", "Disallow: /search/"]
        if self.site_url:
            rows = []
            for url, lastmod in sorted(urls):
                lm = f"<lastmod>{lastmod.isoformat()}</lastmod>" if lastmod else ""
                rows.append(f"  <url><loc>{html.escape(self.site_url + url)}</loc>{lm}</url>")
            xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                   '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(rows) + "\n</urlset>\n")
            (self.out / "sitemap.xml").write_text(xml, encoding="utf-8")
            robots.append(f"Sitemap: {self.site_url}/sitemap.xml")
        (self.out / "robots.txt").write_text("\n".join(robots) + "\n", encoding="utf-8")
        (self.out / ".nojekyll").write_text("", encoding="utf-8")

    LINK_RE = re.compile(r'\s(?:href|src|action|poster)=["\']([^"\']+)["\']')

    def check_links(self):
        own = [d.lower() for d in self.config.get("own_domains", [])]
        for f in self.out.rglob("*.html"):
            if f.name == "404.html" and f.parent == self.out:
                continue  # served from any depth; uses <base> when SITE_URL is known
            text = f.read_text(encoding="utf-8")
            # canonical URLs and <base> must be absolute by definition: not part of the check
            text = re.sub(r'<link rel="canonical"[^>]*>|<base\b[^>]*>', "", text)
            for link in self.LINK_RE.findall(text):
                link = html.unescape(link)
                low = link.lower()
                if re.match(r"^(mailto:|tel:|data:|javascript:|#)", low):
                    continue
                if re.match(r"^(https?:)?//", low):
                    host = re.sub(r"^(https?:)?//", "", low).split("/")[0].split(":")[0]
                    if host in own:
                        self.errors.append(f"{f.relative_to(self.out)}: absolute link to own domain: {link}")
                    continue
                if link.startswith("/"):
                    self.errors.append(f"{f.relative_to(self.out)}: root-absolute link left: {link}")
                    continue
                path = link.split("#")[0].split("?")[0]
                if not path:
                    continue
                target = (f.parent / path).resolve()
                if target.is_dir():
                    target = target / "index.html"
                if not target.exists():
                    self.errors.append(f"{f.relative_to(self.out)}: broken link: {link}")


# --------------------------------------------------------------------------- CLI

def snapshot():
    files = [SITE_CONFIG, Path(__file__)]
    for d in (CONTENT, TEMPLATES, STATIC, DATA):
        files.extend(p for p in d.rglob("*") if p.is_file())
    return {str(p): p.stat().st_mtime for p in files}


def serve(args):
    out = Path(args.out).resolve()

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def send_error(self, code, message=None, explain=None):
            if code == 404 and (out / "404.html").exists():
                self.send_response(404)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write((out / "404.html").read_bytes())
                return
            super().send_error(code, message, explain)

    httpd = http.server.ThreadingHTTPServer((args.host, args.port), partial(Quiet, directory=str(out)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"Serving {out} at http://localhost:{args.port}/ (Ctrl+C to stop)")
    last = snapshot()
    me = str(Path(__file__))
    try:
        while True:
            time.sleep(0.7)
            now = snapshot()
            if now != last:
                if now.get(me) != last.get(me):  # the generator itself changed: restart with new code
                    print("build.py changed, restarting…")
                    httpd.shutdown()
                    httpd.server_close()
                    os.execv(sys.executable, [sys.executable] + sys.argv)
                last = now
                try:
                    Site(args).build()
                except Exception as exc:  # keep serving on template errors
                    print("Build failed:", exc)
    except KeyboardInterrupt:
        httpd.shutdown()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "_site"))
    ap.add_argument("--site-url", default="", help="public base URL (enables canonical links and sitemap.xml); "
                                                 "defaults to $SITE_URL")
    ap.add_argument("--index-links", action="store_true",
                    help="link to dir/index.html instead of dir/ (for browsing the build via file://)")
    ap.add_argument("--drafts", action="store_true", help="include pages with draft: true")
    ap.add_argument("--strict", action="store_true", help="exit with an error when link checks fail")
    ap.add_argument("--serve", action="store_true", help="serve the build and rebuild on changes")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args(argv)

    site = Site(args)
    site.build()
    if site.errors and args.strict:
        sys.exit(1)
    if args.serve:
        serve(args)


if __name__ == "__main__":
    main()
