"""Private profile snapshots: model, hashing, read/write.

Layout: ``profiles/<slug>/profile.json`` in the *history* store (bucket path
``history/profiles/<slug>/profile.json``). Snapshots hold scraped third-party
contact data, so they must never go to a public-read store.
"""

from __future__ import annotations

import hashlib
from typing import Any

from partner_scrape.partners.records import check_slug
from partner_scrape.storage import Store

SNAPSHOT_VERSION = 1


def snapshot_key(slug: str) -> str:
    return f"profiles/{check_slug(slug)}/profile.json"


def body_hash(body: str) -> str:
    return hashlib.sha256((body or "").encode("utf-8")).hexdigest()


def page_entry(
    requested_url: str,
    *,
    status: int | None,
    body: str | None,
    final_url: str = "",
    redirect_chain: list | None = None,
    fetched_at: str = "",
    error: str = "",
) -> dict[str, Any]:
    """One page record; ``sha256`` is None when no body was retrieved."""
    return {
        "url": requested_url,
        "final_url": final_url or requested_url,
        "redirect_chain": [list(h) for h in (redirect_chain or [])],
        "status": status,
        "sha256": body_hash(body) if body is not None and not error else None,
        "fetched_at": fetched_at,
        "error": error,
    }


def fingerprint(snapshot: dict[str, Any]) -> list:
    """The content-bearing part of a snapshot (excludes timestamps).

    Equal fingerprints mean nothing changed, so the file is not rewritten.
    """
    pages = snapshot.get("pages") or {}
    return [
        [
            kind,
            p.get("url"),
            p.get("final_url"),
            p.get("status"),
            p.get("sha256"),
            p.get("error"),
        ]
        for kind, p in sorted(pages.items())
    ]


def read_snapshot(store: Store, slug: str) -> dict[str, Any] | None:
    try:
        data = store.read_json(snapshot_key(slug))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def write_snapshot_if_changed(store: Store, slug: str, snapshot: dict[str, Any]) -> str:
    """Write ``snapshot``; return ``"created"``, ``"updated"`` or ``"unchanged"``.

    Raises ``ValueError`` for a public-read store.
    """
    if getattr(store, "public_read", False):
        raise ValueError("profile snapshots are private; refusing a public-read store")
    old = read_snapshot(store, slug)
    if old is not None and fingerprint(old) == fingerprint(snapshot):
        return "unchanged"
    store.write_json(snapshot_key(slug), snapshot)
    return "created" if old is None else "updated"
