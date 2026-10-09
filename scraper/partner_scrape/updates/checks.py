"""No-LLM change check: compare a partner's profile snapshot with its record.

Pure comparison (``compare_partner``) plus a thin selection/state layer
(``run_checks``). Emits ``Flag`` objects with a ``Severity``; a partner whose
worst flag is MEDIUM or higher is "flagged for the LLM" (stakeholder
decision, sprint 043). Network access is limited to the injectable
``link_checker`` used for social-link liveness; pass ``None`` to skip it.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from enum import IntEnum
from typing import Any, Callable, Iterable
from urllib.parse import urlparse

from partner_scrape.fetch.fetcher import is_notable_redirect
from partner_scrape.profiles.snapshot import fingerprint, read_snapshot
from partner_scrape.storage import Store

STATE_KEY = "updates/state.json"
NETWORKS = ("twitter", "facebook", "instagram", "linkedin")


class Severity(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3

    @property
    def label(self) -> str:
        return self.name.lower()


#: A partner goes to the LLM when any flag is at least this severe.
LLM_THRESHOLD = Severity.MEDIUM


@dataclass(frozen=True)
class Flag:
    kind: str
    severity: Severity
    field: str
    message: str
    record_value: str = ""
    observed_value: str = ""
    #: Social flags only: the link checker reported the record's link dead
    #: (an actual 404/410). Lets the apply policy decide without new I/O.
    dead: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.label
        return d


def needs_llm(flags: Iterable[Flag]) -> bool:
    return any(f.severity >= LLM_THRESHOLD for f in flags)


# A link checker returns True (alive), False (dead) or None (unknown).
LinkChecker = Callable[[str], "bool | None"]


#: Hosts whose plain, logged-out fetches are unreliable even for 404 (robots
#: disallow, login redirects, bot walls, fake 404s). Always "unknown".
SOCIAL_HOSTS = frozenset({
    "facebook.com", "fb.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com",
})


def _is_social_host(url: str) -> bool:
    host = host_of(url)
    return any(host == d or host.endswith("." + d) for d in SOCIAL_HOSTS)


def fetcher_link_checker(fetcher) -> LinkChecker:
    """Liveness via a PoliteFetcher GET.

    Dead ONLY on an actual HTTP 404 or 410 from a non-social host. Everything
    else is unknown (``None``), never dead: exceptions (including
    ``RobotsDisallowed``), timeouts and transport errors, 403/429/999 bot
    walls, and every social-network host (facebook, instagram, twitter/x,
    linkedin), which are not fetched at all because logged-out bots get
    robots blocks, login redirects and spurious 404s there.
    """

    def check(url: str) -> bool | None:
        if _is_social_host(url):
            return None
        try:
            resp = fetcher.get(url, label="liveness")
        except Exception:  # noqa: BLE001  robots disallow, timeout, transport
            return None
        if resp.status in (404, 410):
            return False
        if 200 <= resp.status < 400:
            return True
        return None  # 0 (transport error), 403, 429, 5xx, ...: unknown

    return check


# ---------------------------------------------------------------- normalizers

_STOP = {"the", "of", "and", "a", "an", "for", "at", "in"}
_SUFFIX = {
    "inc", "llc", "ltd", "corp", "corporation", "co", "org", "foundation",
    "nonprofit", "home", "homepage", "official", "site", "website", "welcome",
}
_SEP_RE = re.compile(r"\s+[|–—·:-]\s+|[|–—·]")
_FREE_MAIL = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com",
    "icloud.com", "me.com", "live.com", "msn.com", "proton.me", "protonmail.com",
}


def name_tokens(name: str) -> frozenset[str]:
    """Case/punctuation/suffix-insensitive token set of an organization name."""
    text = (name or "").lower().replace("’", "").replace("'", "")
    words = re.findall(r"[a-z0-9]+", text)
    return frozenset(w for w in words if w not in _STOP and w not in _SUFFIX)


def names_match(a: str, b: str, threshold: float = 0.8) -> bool:
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return False
    return len(ta & tb) / len(ta | tb) >= threshold


def _title_candidates(title: str) -> list[str]:
    parts = [p.strip() for p in _SEP_RE.split(title or "") if p.strip()]
    return ([title.strip()] if title and title.strip() else []) + parts


def host_of(url: str) -> str:
    if not url:
        return ""
    if not urlparse(url).scheme:
        url = "http://" + url
    try:
        h = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


def _same_or_sub(domain: str, host: str) -> bool:
    return bool(domain and host) and (
        domain == host or domain.endswith("." + host) or host.endswith("." + domain)
    )


def digits(phone: str) -> str:
    d = re.sub(r"\D", "", phone or "")
    return d[-10:] if len(d) >= 10 else d


def social_key(url: str) -> str:
    """Canonical identity of a social URL: ``host-network/path`` lowercased."""
    if not url:
        return ""
    if not urlparse(url).scheme:
        url = "https://" + url
    p = urlparse(url)
    host = (p.hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    host = {"x.com": "twitter.com", "fb.com": "facebook.com"}.get(host, host)
    path = p.path.rstrip("/").lower()
    if path.startswith("/#!"):
        path = path[3:]
    return f"{host}{path}"


# -------------------------------------------------------------------- facts

def _all_facts(snapshot: dict) -> list[dict]:
    facts = snapshot.get("facts") or {}
    order = ["home", "about", "contact"]
    return [facts[k] for k in order if k in facts] + [
        v for k, v in facts.items() if k not in order
    ]


def _site_names(snapshot: dict) -> list[str]:
    """Names from the home page (title segments, og:site_name, JSON-LD)."""
    home = (snapshot.get("facts") or {}).get("home") or {}
    out = _title_candidates(home.get("title", ""))
    if home.get("og_site_name"):
        out.append(home["og_site_name"])
    out += [o["name"] for o in home.get("jsonld") or [] if o.get("name")]
    return out


def _site_socials(snapshot: dict) -> dict[str, str]:
    merged: dict[str, str] = {}
    for f in _all_facts(snapshot):
        for net, url in (f.get("socials") or {}).items():
            merged.setdefault(net, url)
    return merged


def _jsonld(snapshot: dict) -> list[dict]:
    return [o for f in _all_facts(snapshot) for o in f.get("jsonld") or []]


# ------------------------------------------------------------------- checks

def _check_website(record, snapshot) -> list[Flag]:
    home = (snapshot.get("pages") or {}).get("home") or {}
    final = home.get("final_url") or ""
    website = record.get("website") or snapshot.get("website") or ""
    if home.get("error") or not final or not website:
        return []
    if is_notable_redirect(website, final):
        return [Flag(
            "website_moved", Severity.HIGH, "website",
            f"website {website} now redirects to {final}",
            website, final,
        )]
    return []


def _check_name(record, snapshot) -> list[Flag]:
    name = record.get("name") or ""
    cands = _site_names(snapshot)
    if not name or not cands:
        return []
    if any(names_match(name, c) for c in cands):
        return []
    best = (snapshot.get("facts", {}).get("home", {}).get("og_site_name")
            or next((o for o in cands if o), ""))
    return [Flag(
        "name_mismatch", Severity.MEDIUM, "name",
        f"record name {name!r} matches none of the site's names {cands[:4]}",
        name, best,
    )]


def _check_phone(record, snapshot) -> list[Flag]:
    rec = digits(record.get("phone") or "")
    site = []
    for f in _all_facts(snapshot):
        site += f.get("phones") or []
    site += [o["telephone"] for o in _jsonld(snapshot) if o.get("telephone")]
    site_d = {digits(p) for p in site if digits(p)}
    if not rec or not site_d or rec in site_d:
        return []
    return [Flag(
        "phone_mismatch", Severity.MEDIUM, "phone",
        f"record phone {record.get('phone')} not on site (site: {sorted(site_d)})",
        record.get("phone") or "", sorted(site_d)[0],
    )]


def _current_host(record, snapshot) -> str:
    home = (snapshot.get("pages") or {}).get("home") or {}
    return host_of(home.get("final_url") or "") or host_of(
        record.get("website") or snapshot.get("website") or ""
    )


def _check_email(record, snapshot) -> list[Flag]:
    email = (record.get("email") or "").strip()
    if "@" not in email:
        return []
    domain = email.rsplit("@", 1)[1].lower()
    if domain in _FREE_MAIL:
        return []
    host = _current_host(record, snapshot)
    if not host or _same_or_sub(domain, host):
        return []
    site_emails = []
    for f in _all_facts(snapshot):
        site_emails += f.get("emails") or []
    if any(e.lower() == email.lower() for e in site_emails):
        return []
    return [Flag(
        "email_domain_mismatch", Severity.MEDIUM, "email",
        f"record email domain {domain} differs from site domain {host}",
        email, site_emails[0] if site_emails else host,
    )]


def _address_text(addr) -> tuple[str, str, str]:
    if isinstance(addr, dict):
        return (addr.get("streetAddress", ""), addr.get("postalCode", ""),
                " ".join(str(v) for v in addr.values()))
    return ("", "", str(addr or ""))


def _check_address(record, snapshot) -> list[Flag]:
    loc = record.get("location") or ""
    if not isinstance(loc, str):
        loc = json.dumps(loc)
    if not loc.strip():
        return []
    loc_tokens = set(re.findall(r"[a-z0-9]+", loc.lower()))
    for org in _jsonld(snapshot):
        street, postal, full = _address_text(org.get("address"))
        if not street and not postal:
            continue
        s_tokens = set(re.findall(r"[a-z0-9]+", street.lower()))
        if (street and s_tokens <= loc_tokens) or (postal and postal[:5] in loc_tokens):
            return []
        return [Flag(
            "address_mismatch", Severity.MEDIUM, "location",
            f"record location {loc!r} does not match site address {full!r}",
            loc, full,
        )]
    return []


def _check_socials(record, snapshot, link_checker) -> list[Flag]:
    site = _site_socials(snapshot)
    flags: list[Flag] = []
    for net in NETWORKS:
        rec = (record.get(net) or "").strip()
        obs = site.get(net, "")
        if not rec:
            if obs:
                flags.append(Flag(
                    "social_new", Severity.LOW, net,
                    f"site links a {net} profile the record lacks", "", obs))
            continue
        if obs and social_key(obs) == social_key(rec):
            continue
        alive = link_checker(rec) if link_checker else None
        dead = alive is False
        if obs:
            suffix = " (record link is dead)" if dead else ""
            flags.append(Flag(
                "social_changed", Severity.MEDIUM, net,
                f"record {net} {rec} differs from site link {obs}{suffix}", rec, obs,
                dead=dead))
        elif dead:
            flags.append(Flag(
                "social_dead", Severity.MEDIUM, net,
                f"record {net} link {rec} is dead and the site links none", rec, "",
                dead=True))
    return flags


def _check_logo(record, snapshot) -> list[Flag]:
    rec = (record.get("logo_src") or "").strip()
    site = next((o["logo"] for o in _jsonld(snapshot) if o.get("logo")), "")
    if rec and site and rec != site:
        return [Flag("logo_changed", Severity.LOW, "logo_src",
                     "site logo differs from record (report-only)", rec, site)]
    return []


def compare_partner(
    record: dict, snapshot: dict, link_checker: LinkChecker | None = None
) -> list[Flag]:
    """All flags for one partner, most severe first. Pure given the checker."""
    flags: list[Flag] = []
    home = (snapshot.get("pages") or {}).get("home") or {}
    if snapshot.get("status") == "failed" or home.get("error"):
        flags.append(Flag(
            "site_unreachable", Severity.LOW, "website",
            f"home page could not be fetched: {home.get('error', '')}",
            record.get("website") or "", ""))
    else:
        flags += _check_website(record, snapshot)
        flags += _check_name(record, snapshot)
        flags += _check_phone(record, snapshot)
        flags += _check_email(record, snapshot)
        flags += _check_address(record, snapshot)
        flags += _check_socials(record, snapshot, link_checker)
        flags += _check_logo(record, snapshot)
    return sorted(flags, key=lambda f: (-f.severity, f.kind, f.field))


# ------------------------------------------------------- selection and state

def snapshot_hash(snapshot: dict) -> str:
    blob = json.dumps(fingerprint(snapshot), sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def load_state(cache_store: Store) -> dict[str, str]:
    try:
        data = cache_store.read_json(STATE_KEY)
    except ValueError:
        return {}
    parts = data.get("partners") if isinstance(data, dict) else None
    return dict(parts) if isinstance(parts, dict) else {}


def save_state(cache_store: Store, state: dict[str, str]) -> None:
    cache_store.write_json(STATE_KEY, {"version": 1, "partners": dict(sorted(state.items()))})


@dataclass
class PartnerCheck:
    slug: str
    flags: list[Flag]
    snapshot_hash: str

    @property
    def needs_llm(self) -> bool:
        return needs_llm(self.flags)


@dataclass
class CheckReport:
    checks: list[PartnerCheck] = field(default_factory=list)
    examined: int = 0
    skipped_unchanged: int = 0
    no_snapshot: list[str] = field(default_factory=list)
    new_state: dict[str, str] = field(default_factory=dict)

    @property
    def flagged_for_llm(self) -> list[PartnerCheck]:
        return [c for c in self.checks if c.needs_llm]

    def lines(self) -> list[str]:
        out = []
        for c in self.checks:
            for f in c.flags:
                out.append(f"FLAG {c.slug} {f.severity.label} {f.kind}: {f.message}")
        out.append(
            f"checks: examined={self.examined} unchanged={self.skipped_unchanged} "
            f"no_snapshot={len(self.no_snapshot)} flagged_llm={len(self.flagged_for_llm)}"
        )
        return out


def run_checks(
    roster: list[dict],
    history_store: Store,
    cache_store: Store,
    *,
    link_checker: LinkChecker | None = None,
    all_partners: bool = False,
    slug: str | None = None,
    hints_fp: Callable[[str], str] | None = None,
) -> CheckReport:
    """Check partners whose snapshot changed since the last run (state in
    ``updates/state.json`` of ``cache_store``), or that have a notable
    redirect, or every partner with ``all_partners``.

    ``hints_fp(slug)`` returns a fingerprint of the partner's stored hints
    ("" for none). It is folded into the state value, so a hints change since
    the last saved state re-examines the partner (a partner with no hints keeps
    the plain snapshot hash, i.e. the pre-hints state value).

    Does not write state: the caller persists ``report.new_state`` with
    ``save_state`` once the downstream work succeeded.
    """
    state = load_state(cache_store)
    report = CheckReport(new_state=dict(state))
    for rec in sorted(roster, key=lambda r: r.get("slug", "")):
        s = rec.get("slug", "")
        if slug and s != slug:
            continue
        snap = read_snapshot(history_store, s)
        if snap is None:
            report.no_snapshot.append(s)
            continue
        h = snapshot_hash(snap)
        fp = hints_fp(s) if hints_fp else ""
        if fp:
            h = f"{h}+h:{fp}"
        changed = state.get(s) != h
        if not (all_partners or changed or snap.get("redirects")):
            report.skipped_unchanged += 1
            continue
        report.examined += 1
        report.checks.append(PartnerCheck(s, compare_partner(rec, snap, link_checker), h))
        report.new_state[s] = h
    return report
