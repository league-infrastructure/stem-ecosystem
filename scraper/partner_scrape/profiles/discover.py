"""Find a partner's About and Contact pages from its home page.

Pure functions: no network. Candidates come from home-page anchors and
(optionally) sitemap URLs, same site only, in deterministic order.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlparse

# Anchor text / path patterns per page kind. "visit" maps to contact (hours,
# address, directions) at lower priority than an explicit "contact".
_ABOUT_RE = re.compile(r"\b(about|our[\s-]*story|who[\s-]*we[\s-]*are|mission)\b", re.I)
_CONTACT_RE = re.compile(r"\b(contact|visit)\b", re.I)
_SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "data:", "sms:")
_SKIP_EXT = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".zip", ".doc", ".docx", ".xml")


@dataclass(frozen=True)
class Candidate:
    kind: str  # "about" | "contact"
    url: str
    source: str  # "anchor-text" | "anchor-path" | "sitemap"
    rank: tuple


@dataclass
class DiscoveredPages:
    about: str | None = None
    contact: str | None = None
    candidates: list[Candidate] = field(default_factory=list)


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._flush()
            self._href = dict(attrs).get("href") or ""
            self._text = []

    def handle_endtag(self, tag):
        if tag == "a":
            self._flush()

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def _flush(self):
        if self._href:
            self.anchors.append((self._href, " ".join("".join(self._text).split())))
        self._href = None
        self._text = []

    def close(self):
        super().close()
        self._flush()


def _site(host: str) -> str:
    host = (host or "").lower()
    return host[4:] if host.startswith("www.") else host


def _normalize(base: str, href: str) -> str | None:
    href = (href or "").strip()
    if not href or href.startswith("#") or href.lower().startswith(_SKIP_SCHEMES):
        return None
    try:
        url, _ = urldefrag(urljoin(base, href))
        p = urlparse(url)
    except ValueError:
        return None
    if p.scheme not in ("http", "https") or not p.netloc:
        return None
    if p.path.lower().endswith(_SKIP_EXT):
        return None
    return url


def _kind_for(pattern_text: str) -> str | None:
    """about wins over contact when both match; explicit 'contact' beats 'visit'."""
    if _ABOUT_RE.search(pattern_text):
        return "about"
    if _CONTACT_RE.search(pattern_text):
        return "contact"
    return None


def _strength(kind: str, text: str) -> int:
    # 0 = strongest. An explicit "contact" outranks a "visit" match.
    if kind == "contact" and not re.search(r"contact", text, re.I):
        return 1
    return 0


def discover_profile_pages(
    home_url: str, html: str, sitemap_urls: list[str] | tuple[str, ...] = ()
) -> DiscoveredPages:
    """Pick at most one About and one Contact URL for ``home_url``.

    Never raises on malformed HTML. Ranking: anchor text beats anchor path
    beats sitemap; then keyword strength, shallower path, first appearance,
    and finally the URL itself, so the result is deterministic.
    """
    site = _site(urlparse(home_url).netloc)
    home_norm = (_normalize(home_url, home_url) or "").rstrip("/")
    seen: dict[tuple[str, str], Candidate] = {}
    order = 0

    def add(kind: str, url: str, source: str, text: str, src_rank: int) -> None:
        nonlocal order
        p = urlparse(url)
        if _site(p.netloc) != site or url.rstrip("/") == home_norm:
            return
        depth = len([s for s in p.path.split("/") if s])
        rank = (src_rank, _strength(kind, text), depth, order, url)
        order += 1
        key = (kind, url)
        if key not in seen or rank < seen[key].rank:
            seen[key] = Candidate(kind, url, source, rank)

    parser = _AnchorParser()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:  # noqa: BLE001 - malformed markup must never raise
        pass
    for href, text in parser.anchors:
        url = _normalize(home_url, href)
        if not url:
            continue
        path = urlparse(url).path.replace("/", " ").replace("-", " ").replace("_", " ")
        kind = _kind_for(text)
        if kind:
            add(kind, url, "anchor-text", text, 0)
            continue
        kind = _kind_for(path)
        if kind:
            add(kind, url, "anchor-path", path, 1)
    for loc in sitemap_urls or ():
        url = _normalize(home_url, loc)
        if not url:
            continue
        path = urlparse(url).path.replace("/", " ").replace("-", " ").replace("_", " ")
        kind = _kind_for(path)
        if kind:
            add(kind, url, "sitemap", path, 2)

    ordered = sorted(seen.values(), key=lambda c: (c.kind, c.rank))
    out = DiscoveredPages(candidates=ordered)
    for c in ordered:
        if c.kind == "about" and out.about is None:
            out.about = c.url
        elif c.kind == "contact" and out.contact is None:
            out.contact = c.url
    return out
