"""No-LLM fact extraction from a partner page's HTML.

Pure and defensive: malformed HTML or JSON-LD never raises; whatever was
found is returned.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse

_ORG_TYPES = {
    "organization", "localbusiness", "museum", "ngo", "educationalorganization",
    "school", "library", "touristattraction", "nonprofit", "corporation",
    "performinggroup", "sportsorganization", "civicstructure",
}
_NETWORKS = {
    "twitter.com": "twitter", "x.com": "twitter",
    "facebook.com": "facebook", "fb.com": "facebook",
    "instagram.com": "instagram",
    "linkedin.com": "linkedin",
}
# Share/intent links are not the organization's own profile.
_SHARE_MARKERS = ("/sharer", "/share", "/intent/", "/dialog/", "shareArticle", "/plugins/")


@dataclass
class ProfileFacts:
    title: str = ""
    og_site_name: str = ""
    jsonld: list[dict] = field(default_factory=list)  # normalized org objects
    socials: dict[str, str] = field(default_factory=dict)  # network -> url
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class _FactParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.in_title = False
        self.og_site_name = ""
        self.ld_blocks: list[str] = []
        self._ld: list[str] | None = None
        self.hrefs: list[tuple[str, bool]] = []  # (href, in_footer)
        self._footer_depth = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            if (a.get("property") or a.get("name") or "").lower() == "og:site_name":
                self.og_site_name = (a.get("content") or "").strip()
        elif tag == "script" and "ld+json" in (a.get("type") or "").lower():
            self._ld = []
        elif tag == "a" and a.get("href"):
            self.hrefs.append((a["href"].strip(), self._footer_depth > 0))
        if tag == "footer":
            self._footer_depth += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        elif tag == "script" and self._ld is not None:
            self.ld_blocks.append("".join(self._ld))
            self._ld = None
        elif tag == "footer" and self._footer_depth:
            self._footer_depth -= 1

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)
        if self._ld is not None:
            self._ld.append(data)


def _as_list(v):
    return v if isinstance(v, list) else [] if v is None else [v]


def _str(v) -> str:
    return v.strip() if isinstance(v, str) else ""


def _walk_nodes(data):
    """Yield every dict in a JSON-LD document, descending @graph and lists."""
    if isinstance(data, list):
        for item in data:
            yield from _walk_nodes(item)
    elif isinstance(data, dict):
        yield data
        if "@graph" in data:
            yield from _walk_nodes(data["@graph"])


def _address(v) -> str | dict:
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, dict):
        keys = ("streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry")
        out = {}
        for k in keys:
            val = v.get(k)
            if isinstance(val, dict):
                val = val.get("name")
            if _str(val):
                out[k] = val.strip()
        return out
    return ""


def _logo(v) -> str:
    for item in _as_list(v):
        if isinstance(item, str) and item.strip():
            return item.strip()
        if isinstance(item, dict):
            u = _str(item.get("url")) or _str(item.get("contentUrl"))
            if u:
                return u
    return ""


def _org_from_node(node: dict) -> dict | None:
    types = {str(t).lower() for t in _as_list(node.get("@type"))}
    if not types & _ORG_TYPES:
        return None
    return {
        "type": next((str(t) for t in _as_list(node.get("@type"))), ""),
        "name": _str(node.get("name")),
        "address": _address(node.get("address")),
        "telephone": _str(node.get("telephone")),
        "email": _str(node.get("email")).removeprefix("mailto:"),
        "sameAs": [s.strip() for s in _as_list(node.get("sameAs")) if _str(s)],
        "logo": _logo(node.get("logo")),
        "url": _str(node.get("url")),
    }


def _parse_jsonld(blocks: list[str]) -> list[dict]:
    orgs: list[dict] = []
    for block in blocks:
        try:
            data = json.loads(block)
        except (ValueError, RecursionError):
            continue
        for node in _walk_nodes(data):
            org = _org_from_node(node)
            if org:
                orgs.append(org)
    return orgs


def classify_social(url: str) -> str | None:
    """Return the network name for an organization-profile URL, else None."""
    try:
        p = urlparse(url)
    except ValueError:
        return None
    host = (p.hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    if host.startswith(("m.", "mobile.")):
        host = host.split(".", 1)[1]
    net = _NETWORKS.get(host)
    if not net or any(m in url for m in _SHARE_MARKERS):
        return None
    if not [s for s in p.path.split("/") if s]:  # bare homepage of the network
        return None
    return net


def extract_facts(html: str) -> ProfileFacts:
    """Extract profile facts from ``html``; never raises."""
    facts = ProfileFacts()
    parser = _FactParser()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:  # noqa: BLE001 - keep whatever was parsed before the failure
        pass
    facts.title = " ".join("".join(parser.title_parts).split())
    facts.og_site_name = parser.og_site_name
    facts.jsonld = _parse_jsonld(parser.ld_blocks)

    # Footer links first (organization's own), then the rest; first per network wins.
    ordered = sorted(enumerate(parser.hrefs), key=lambda iv: (not iv[1][1], iv[0]))
    for _, (href, _footer) in ordered:
        low = href.lower()
        if low.startswith("mailto:"):
            addr = unquote(href[7:].split("?", 1)[0]).strip()
            if addr and addr not in facts.emails:
                facts.emails.append(addr)
        elif low.startswith("tel:"):
            num = unquote(href[4:]).strip()
            if num and num not in facts.phones:
                facts.phones.append(num)
        else:
            net = classify_social(href)
            if net and net not in facts.socials:
                facts.socials[net] = href
    return facts
