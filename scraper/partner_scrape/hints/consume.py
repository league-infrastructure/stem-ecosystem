"""Read-side helpers the scraper jobs use to consume hints.

Hints are a steering signal only: nothing here returns a value that a job
may write into a record. Every function degrades to "no hints" (the
pre-hints behavior) on a missing, unreadable or malformed hints file.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any, Callable

from partner_scrape.hints.model import MAX_REGEX_CHARS, REGEX_PREFIX, hints_of
from partner_scrape.hints.store import HintStore
from partner_scrape.hints.validate import domains_of, on_domain

log = logging.getLogger(__name__)

EVENT_ROLES = ("events", "camps", "programs")


def load_hints(store: HintStore | None, slug: str) -> list[dict[str, Any]]:
    """The hint list for ``slug``; empty with no store, no file, or any error."""
    if store is None or not slug:
        return []
    try:
        return [h for h in hints_of(store.get(slug)) if isinstance(h, dict)]
    except Exception as exc:  # noqa: BLE001 - hints are optional; never abort a job
        log.warning("could not read hints for %s: %s", slug, exc)
        return []


def page_hint_urls(
    hints: list[dict[str, Any]], website: str | None, roles: tuple[str, ...]
) -> dict[str, list[str]]:
    """Page-hint URLs by role (only ``roles``), in hint order. A URL is kept
    only if its host is on the partner's website domain (re-checked here even
    though it was validated at write time)."""
    domains = domains_of(website)
    out: dict[str, list[str]] = {}
    for h in hints_of({"hints": hints}, "page"):
        role, url = h.get("role"), h.get("url")
        if role not in roles or not isinstance(url, str) or not url:
            continue
        host = domains_of(url)
        if not host or not on_domain(host[0], domains):
            continue
        if url not in out.setdefault(role, []):
            out[role].append(url)
    return out


def _clip(text: Any, limit: int = 500) -> str:
    return str(text or "")[:limit]


def context_hints(
    hints: list[dict[str, Any]], *, allow_identity: bool
) -> tuple[list[dict[str, Any]], list[str]]:
    """Note/identity hints for the proposer prompt, plus ignore reasons.

    Identity hints are included only when ``allow_identity`` (existing
    redirect/title evidence is present); otherwise they are dropped and the
    reason is returned for the report.
    """
    ctx: list[dict[str, Any]] = []
    ignored: list[str] = []
    for h in hints:
        kind = h.get("kind")
        if kind == "note" and h.get("text"):
            ctx.append({"kind": "note", "text": _clip(h["text"])})
        elif kind == "identity":
            if allow_identity:
                ctx.append({k: _clip(h[k], 200) for k in ("kind", "name", "website") if h.get(k)})
            else:
                ignored.append("identity hint ignored: no redirect or site-title evidence")
    return ctx, ignored


def hints_fingerprint(hints: list[dict[str, Any]]) -> str:
    """Stable hash of a partner's hints; "" when there are none (so a partner
    without hints keeps its pre-hints state value unchanged)."""
    if not hints:
        return ""
    blob = json.dumps(hints, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


_MAX_MATCH_TEXT = 500


def exclude_matcher(hints: list[dict[str, Any]]) -> Callable[[str], bool] | None:
    """A predicate ``text -> bool`` for a partner's exclude hints, or None when
    there are none usable. A ``match`` is a case-insensitive substring, or a
    ``re:``-prefixed regex. Invalid or over-long regexes are skipped (never
    raise), and the text tested is length-capped."""
    subs: list[str] = []
    regexes: list[re.Pattern[str]] = []
    for h in hints_of({"hints": hints}, "exclude"):
        m = h.get("match")
        if not isinstance(m, str) or not m.strip():
            continue
        if m.startswith(REGEX_PREFIX):
            pat = m[len(REGEX_PREFIX):]
            if not pat or len(pat) > MAX_REGEX_CHARS:
                continue
            try:
                regexes.append(re.compile(pat, re.IGNORECASE))
            except re.error:
                log.warning("skipping invalid exclude regex %r", pat)
        else:
            subs.append(m.strip().lower())
    if not subs and not regexes:
        return None

    def matches(text: str) -> bool:
        t = (text or "")[:_MAX_MATCH_TEXT]
        low = t.lower()
        return any(s in low for s in subs) or any(r.search(t) for r in regexes)

    return matches
