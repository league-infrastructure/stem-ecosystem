"""Report-only event-quality checks (sprint 043-007, issue 76).

Runs off our own published data in the data store -- ``partners/<slug>/
events.json`` / ``past-events.json`` (falling back to ``opportunities.json``
for a partner without per-partner files). No web, no LLM, and it never writes:
it only reads from the store and returns findings.

Checks (ids): ``non_event``, ``duplicate``, ``date_link_mismatch``,
``past_in_current``, ``age_implausible``, ``missing_cost``,
``recurring_collapsed``. Every heuristic is deliberately conservative: a
false negative is cheap (a follow-up issue), a false positive wastes a
reader's attention.

Age heuristic (``age_implausible``), tags being Pre-K / Grades K-5 / Family
(the "young" bands) and Grades 6-8 / 9-12 (the "older" bands):
  a. title/description plainly names toddlers/preschool/babies/story time
     but the event carries an older band;
  b. title/description names family/kids/all-ages but the event carries
     ONLY older bands (no young band, no Adult);
  c. the event carries ONLY older bands with no teen/high-school wording
     while at least 3 of the partner's other events exist and at least
     two thirds of them carry a young band.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable

from partner_scrape.storage import Store

CHECKS = (
    "non_event", "duplicate", "date_link_mismatch", "past_in_current",
    "age_implausible", "missing_cost", "recurring_collapsed",
)

YOUNG_BANDS = {"Pre-K", "Grades K-5", "Grades 3-5", "Family"}
OLDER_BANDS = {"Grades 6-8", "Grades 9-12"}

_NON_EVENT = re.compile(
    r"\bmember\W{0,2}s?\W*(only|hours)\b|\bholiday\s+hours\b"
    r"|\b(early|late)\s+(closure|close|closing)\b|\bmuseum\s+closed\b"
    r"|\bclosed\s+(for|today|on)\b|^\s*(museum\s+|we\s+are\s+)?closed\s*$"
    r"|\b(special|extended|reduced|summer|winter)\s+hours\b|\bclosure\b",
    re.I)
_YOUNG_TEXT = re.compile(
    r"\b(toddlers?|preschool(ers?)?|pre-?k\b|babies|baby|infants?|tots?\b"
    r"|story\s*time|little\s+ones|ages?\s+(0|1|2|3|4|5)\b\s*(-|–|to)?)", re.I)
_FAMILY_TEXT = re.compile(r"\b(family|families|kids?|children|all\s+ages)\b", re.I)
_TEEN_TEXT = re.compile(
    r"\b(teens?|teenagers?|high\s+school|middle\s+school|grades?\s+(6|7|8|9|10|11|12)"
    r"|ages?\s+1[2-8]|youth|students?)\b", re.I)
_COST_TEXT = re.compile(
    r"\b(admission|ticket(s|ed)?|price[sd]?|fee|included\s+with|"
    r"with\s+(museum\s+)?admission)\b|\$\s?\d", re.I)
_FREE_ADMISSION = re.compile(r"\b(free|no)\s+(admission|cost|charge)\b", re.I)
_TIME = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\b", re.I)
_LINK_DATES = (
    re.compile(r"(?<!\d)(20\d{2})[-/_.](\d{1,2})[-/_.](\d{1,2})(?!\d)"),
    re.compile(r"(?<!\d)(\d{1,2})[-/_.](\d{1,2})[-/_.](20\d{2})(?!\d)"),
    re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)"),
)


@dataclass(frozen=True)
class Finding:
    slug: str
    check: str
    title: str
    url: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        return {"slug": self.slug, "check": self.check, "title": self.title,
                "url": self.url, "detail": self.detail}

    def line(self) -> str:
        return (f"QUALITY {self.slug} {self.check}: {self.title!r}"
                f"{' ' + self.url if self.url else ''} -- {self.detail}")


@dataclass
class QualityReport:
    findings: list[Finding] = field(default_factory=list)
    partners_examined: int = 0
    events_examined: int = 0

    @property
    def counts(self) -> dict[str, int]:
        c = Counter(f.check for f in self.findings)
        return {k: c.get(k, 0) for k in CHECKS}

    def by_partner(self) -> dict[str, list[Finding]]:
        out: dict[str, list[Finding]] = {}
        for f in self.findings:
            out.setdefault(f.slug, []).append(f)
        return dict(sorted(out.items()))

    def lines(self) -> list[str]:
        out = [f.line() for fs in self.by_partner().values() for f in fs]
        counts = " ".join(f"{k}={v}" for k, v in self.counts.items())
        out.append(
            f"event-quality: partners={self.partners_examined} "
            f"events={self.events_examined} findings={len(self.findings)} {counts}")
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "partners_examined": self.partners_examined,
            "events_examined": self.events_examined,
            "total": len(self.findings),
            "counts": self.counts,
            "partners": {s: [f.to_dict() for f in fs]
                         for s, fs in self.by_partner().items()},
        }


# --- helpers -----------------------------------------------------------------

def _text(e: dict[str, Any]) -> str:
    return f"{e.get('title') or ''} {e.get('description') or ''}"


def _day(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _title_key(title: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (title or "").lower()))


def _link_dates(link: str) -> set[date]:
    found: set[date] = set()
    for i, rx in enumerate(_LINK_DATES):
        for m in rx.finditer(link or ""):
            a, b, c = (int(g) for g in m.groups())
            y, mo, d = (a, b, c) if i != 1 else (c, a, b)
            try:
                found.add(date(y, mo, d))
            except ValueError:
                pass
    return found


def _f(slug: str, check: str, e: dict[str, Any], detail: str) -> Finding:
    return Finding(slug, check, str(e.get("title") or ""), str(e.get("link") or ""), detail)


# --- the checks (each pure: events in, findings out) ---------------------------

def check_non_events(slug: str, events: list[dict]) -> list[Finding]:
    return [_f(slug, "non_event", e, "title looks like opening hours / closure, not an event")
            for e in events if _NON_EVENT.search(e.get("title") or "")]


def check_duplicates(slug: str, events: list[dict]) -> list[Finding]:
    out: list[Finding] = []
    for i, a in enumerate(events):
        for b in events[i + 1:]:
            if not a.get("date_start") or a.get("date_start") != b.get("date_start"):
                continue
            ka, kb = _title_key(a.get("title", "")), _title_key(b.get("title", ""))
            if not ka or not kb:
                continue
            if ka == kb or ka.startswith(kb + " ") or kb.startswith(ka + " "):
                short, long_ = (a, b) if len(ka) <= len(kb) else (b, a)
                out.append(_f(slug, "duplicate", short,
                              f"same start {a['date_start']} as {long_.get('title')!r}"))
    return out


def check_date_link_mismatch(slug: str, events: list[dict]) -> list[Finding]:
    out = []
    for e in events:
        start, dates = _day(e.get("date_start")), _link_dates(e.get("link") or "")
        if start and dates and start not in dates:
            shown = ", ".join(sorted(d.isoformat() for d in dates))
            out.append(_f(slug, "date_link_mismatch", e,
                          f"date_start {start.isoformat()} but link dated {shown}"))
    return out


def check_past_in_current(slug: str, events: list[dict], today: date) -> list[Finding]:
    out = []
    for e in events:
        end = _day(e.get("date_end")) or _day(e.get("date_start"))
        if end and end < today:
            out.append(_f(slug, "past_in_current", e,
                          f"ended {end.isoformat()} but listed as current (today {today.isoformat()})"))
    return out


def check_age_tags(slug: str, events: list[dict], all_events: list[dict]) -> list[Finding]:
    out = []
    for e in events:
        tags = set(e.get("age_grade_level") or [])
        older = tags & OLDER_BANDS
        if not older:
            continue
        text = _text(e)
        only_older = tags <= OLDER_BANDS
        reason = ""
        if _YOUNG_TEXT.search(text):
            reason = "text names toddlers/preschool"
        elif only_older and _FAMILY_TEXT.search(text) and not _TEEN_TEXT.search(text):
            reason = "text is family/kids/all-ages"
        elif only_older and not _TEEN_TEXT.search(text):
            others = [o for o in all_events if o is not e]
            young = sum(1 for o in others if set(o.get("age_grade_level") or []) & YOUNG_BANDS)
            if len(others) >= 3 and young * 3 >= len(others) * 2:
                reason = f"{young} of the partner's {len(others)} other events carry young bands"
        if reason:
            out.append(_f(slug, "age_implausible", e,
                          f"tags {sorted(tags)} but {reason}"))
    return out


def check_missing_cost(slug: str, events: list[dict]) -> list[Finding]:
    out = []
    for e in events:
        cost = (e.get("cost_range") or "").strip()
        if cost and cost.lower() != "free":
            continue
        text = _FREE_ADMISSION.sub("", _text(e))
        if _COST_TEXT.search(text):
            out.append(_f(slug, "missing_cost", e,
                          f"cost is {cost or 'blank'!r} but text mentions admission/price"))
    return out


def check_recurring_collapsed(slug: str, events: list[dict]) -> list[Finding]:
    out = []
    for e in events:
        times = {(int(h) % 12 + (12 if ap.lower() == "p" else 0), int(mi or 0))
                 for h, mi, ap in _TIME.findall(_text(e))}
        if len(times) < 2:
            continue
        key, day = _title_key(e.get("title", "")), str(e.get("date_start") or "")[:10]
        stored = sum(1 for o in events
                     if _title_key(o.get("title", "")) == key
                     and str(o.get("date_start") or "")[:10] == day)
        if stored < len(times):
            out.append(_f(slug, "recurring_collapsed", e,
                          f"text lists {len(times)} times, {stored} stored on {day}"))
    return out


def check_events(slug: str, current: list[dict], past: list[dict], today: date) -> list[Finding]:
    all_events = current + past
    return (check_non_events(slug, current) + check_duplicates(slug, current)
            + check_date_link_mismatch(slug, current)
            + check_past_in_current(slug, current, today)
            + check_age_tags(slug, current, all_events)
            + check_missing_cost(slug, current)
            + check_recurring_collapsed(slug, current))


# --- store-reading driver -----------------------------------------------------

def _events_of(store: Store, key: str) -> list[dict] | None:
    try:
        data = store.read_json(key)
    except Exception:  # noqa: BLE001 - unreadable file: treat as absent
        return None
    if isinstance(data, dict) and isinstance(data.get("events"), list):
        return [e for e in data["events"] if isinstance(e, dict)]
    if isinstance(data, list):
        return [e for e in data if isinstance(e, dict)]
    return None


def run_quality(
    roster: Iterable[dict[str, Any]],
    data_store: Store,
    *,
    today: date | None = None,
    slug: str | None = None,
) -> QualityReport:
    """Run every check over each partner's published events. Read-only."""
    today = today or date.today()
    report = QualityReport()
    opps: list[dict] | None = None
    for rec in roster:
        s = rec.get("slug")
        if not s or (slug and s != slug):
            continue
        current = _events_of(data_store, f"partners/{s}/events.json")
        past = _events_of(data_store, f"partners/{s}/past-events.json") or []
        if current is None:
            if opps is None:
                opps = _events_of(data_store, "opportunities.json") or []
            pid = rec.get("id")
            current = [o for o in opps if pid is not None and o.get("partner_id") == pid]
        report.partners_examined += 1
        report.events_examined += len(current)
        report.findings.extend(check_events(s, current, past, today))
    return report
