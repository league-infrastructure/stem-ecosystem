"""Collector for notable redirects seen during a run (sprint 043, issue 73).

A fetch that lands on a different site than requested (host differs
ignoring ``www.``) usually means a partner moved. ``PoliteFetcher``
reports such fetches here when a ``RedirectLog`` is supplied, and the run
output summarizes them as plain lines so run logs carry them.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class NotableRedirect:
    source: str
    requested: str
    final: str
    status: int | None


class RedirectLog:
    """Thread-safe, de-duplicated list of notable redirects."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._items: dict[tuple[str, str], NotableRedirect] = {}

    def record(
        self, source: str, requested: str, final: str, status: int | None = None
    ) -> None:
        with self._lock:
            self._items.setdefault(
                (requested, final), NotableRedirect(source, requested, final, status)
            )

    @property
    def items(self) -> list[NotableRedirect]:
        with self._lock:
            return sorted(self._items.values(), key=lambda r: (r.source, r.requested))

    def __len__(self) -> int:
        return len(self.items)

    def lines(self) -> list[str]:
        """One line per notable redirect, prefixed ``REDIRECT``; empty if none."""
        return [
            f"REDIRECT {r.source}: {r.requested} -> {r.final}"
            + (f" ({r.status})" if r.status else "")
            for r in self.items
        ]
