"""Hint schema constants and the hints-file shape.

A hints file is ``{slug, version, updated, hints: [{kind, ...}]}``. Hints
are a pure steering signal: they never supply published facts.
"""

from __future__ import annotations

from typing import Any

KINDS = ("page", "exclude", "note", "identity")
PAGE_ROLES = ("about", "contact", "events", "camps", "programs", "other")

MAX_HINTS_PER_KIND = {"page": 10, "exclude": 20, "note": 10, "identity": 1}
MAX_TOTAL_HINTS = 41
MAX_TEXT_CHARS = 500  # note text
MAX_REASON_CHARS = 200
MAX_MATCH_CHARS = 100
MAX_REGEX_CHARS = 100
MAX_URL_CHARS = 500
MAX_NAME_CHARS = 200

REGEX_PREFIX = "re:"


def empty_hints(slug: str) -> dict[str, Any]:
    return {"slug": slug, "version": 0, "updated": None, "hints": []}


def hints_of(doc: dict[str, Any] | None, kind: str | None = None) -> list[dict[str, Any]]:
    """The hint list from a hints file (empty when `doc` is None), optionally
    filtered by kind."""
    items = list((doc or {}).get("hints") or [])
    return [h for h in items if kind is None or h.get("kind") == kind]
