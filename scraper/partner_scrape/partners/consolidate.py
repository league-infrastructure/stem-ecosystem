"""Consolidate ``data/partners/*/partner.json`` into ``data/partners.json``.

Lists every record in the data store, validates them (a bad record fails
loudly, naming its slug, before anything is written) and writes the public
roster in the same envelope ``export/publish.py`` has always produced:
``generated_at``, ``partner_count``, ``partners[]`` where each partner is
its curated record plus ``slug``, ``events_url`` and ``past_events_url``.
The envelope helpers here are shared with ``publish.project``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from partner_scrape.partners.records import load_roster
from partner_scrape.storage import Store

ROSTER_KEY = "partners.json"


def published_entry(partner: dict[str, Any], slug: str) -> dict[str, Any]:
    """A curated record as published: slug and the two event-file URLs last."""
    entry = {k: v for k, v in partner.items() if k != "slug"}
    entry["slug"] = slug
    entry["events_url"] = f"partners/{slug}/events.json"
    entry["past_events_url"] = f"partners/{slug}/past-events.json"
    return entry


def build_envelope(entries: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    return {
        "generated_at": generated_at,
        "partner_count": len(entries),
        "partners": entries,
    }


def dumps_envelope(envelope: dict[str, Any]) -> str:
    return json.dumps(envelope, indent=1, ensure_ascii=False)


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def consolidate(store: Store, generated_at: str | None = None) -> dict[str, Any]:
    """Validate all records and write ``partners.json``; returns the envelope.

    Raises `RosterValidationError` (nothing written) if any record is bad.
    """
    roster = load_roster(store, validate=True)
    entries = [published_entry(r, r["slug"]) for r in roster.as_list()]
    envelope = build_envelope(entries, generated_at or now_iso())
    store.write_text(ROSTER_KEY, dumps_envelope(envelope), "application/json")
    return envelope
