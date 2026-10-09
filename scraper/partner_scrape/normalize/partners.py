"""Partner join: normalized-org-name lookup against the curated roster.

Reads (never writes) the roster. Since sprint 042 the roster is the
per-partner records in the data store (`partners/<slug>/partner.json`),
resolved by `partners.source.resolve_partners`; it is no longer the
site's `src/data/partners.json`.

No match -> the caller keeps the org name and leaves `partner_id`
unset (SUC-005's documented error flow). This module never raises for
an unmatched org -- :func:`find_partner` just returns `None`.
"""

from __future__ import annotations

import re
from typing import Any

from partner_scrape.partners.source import resolve_partners

_NON_ALNUM_RE = re.compile(r"[^a-z0-9 ]")
_LEADING_THE_RE = re.compile(r"^the ")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_org_name(name: str) -> str:
    """Normalize an organization name for partner-join matching.

    Lowercases, strips punctuation (keeping spaces), drops a leading
    "the ", and collapses whitespace -- e.g. "The Living Coast
    Discovery Center" and "Living Coast Discovery Center" normalize
    identically. Ported from `dev/export_site.py`'s `norm_name`.
    """
    lowered = name.lower()
    no_punctuation = _NON_ALNUM_RE.sub("", lowered)
    no_leading_the = _LEADING_THE_RE.sub("", no_punctuation.strip())
    return _WHITESPACE_RE.sub(" ", no_leading_the).strip()


def load_partners(partners: Any = None) -> dict[str, dict[str, Any]]:
    """Load the roster into a dict keyed by :func:`normalize_org_name`.

    ``partners`` is anything `partners.source.resolve_partners` accepts:
    ``None`` (the data store's partner records), a Store, a list, or a
    path to a roster JSON file.

    The first partner record wins a normalized-name collision, matching
    `dev/export_site.py`'s `load_site_partners`'s `setdefault` behavior.
    """
    data = resolve_partners(partners)
    by_norm: dict[str, dict[str, Any]] = {}
    for partner in data:
        by_norm.setdefault(normalize_org_name(partner.get("name", "")), partner)
    return by_norm


def find_partner(org_name: str, partners_by_norm: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    """Look up ``org_name`` in ``partners_by_norm``; `None` on no match."""
    return partners_by_norm.get(normalize_org_name(org_name))
