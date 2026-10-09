"""Read side of hints: key layout and `HintStore`. Reading never writes."""

from __future__ import annotations

from typing import Any

from partner_scrape.hints.model import empty_hints
from partner_scrape.partners.records import check_slug
from partner_scrape.storage import Store


def hints_key(slug: str) -> str:
    return f"{check_slug(slug)}.json"


class HintStore:
    """Hints files in a private Store (``hints/<slug>.json`` in the bucket)."""

    def __init__(self, store: Store):
        self.store = store

    def read(self, slug: str) -> dict[str, Any] | None:
        """The stored hints document, or None if absent."""
        doc = self.store.read_json(hints_key(slug))
        return doc if isinstance(doc, dict) else None

    def get(self, slug: str) -> dict[str, Any]:
        """The hints document, or an empty one when no file exists."""
        return self.read(slug) or empty_hints(check_slug(slug))

    def hints(self, slug: str) -> list[dict[str, Any]]:
        return list(self.get(slug)["hints"])


def default_store() -> HintStore:
    from partner_scrape import config

    return HintStore(config.get_hints_store())
