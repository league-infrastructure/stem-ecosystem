"""The single archiving writer for hints (mirrors `PartnerWriter`).

1. validate (caller supplies the entity's domains / current website);
2. if the hint list equals the stored one, do nothing;
3. archive the current file to ``hints/<slug>/<UTC ts>.json`` in history;
4. write ``<slug>.json`` to the private hints store (version + 1);
5. append ``{slug, ts, actor, kind, changed, archived}`` to
   ``hints/changes.jsonl`` in history.

`actor` should be ``update-agent:<session>``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

from partner_scrape.hints.store import HintStore, hints_key
from partner_scrape.hints.validate import Fetcher, Resolver, validate_hints
from partner_scrape.partners.records import check_slug
from partner_scrape.storage import Store

CHANGES_KEY = "hints/changes.jsonl"


def actor_for(session_id: str) -> str:
    return f"update-agent:{session_id}"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class HintWriter:
    def __init__(
        self,
        store: Store,
        history: Store,
        clock: Callable[[], datetime] = _now,
        fetcher: Fetcher | None = None,
        resolver: Resolver | None = None,
    ):
        self.reader = HintStore(store)
        self.store = store
        self.history = history
        self._clock = clock
        self.fetcher = fetcher
        self.resolver = resolver

    def put_hints(
        self,
        slug: str,
        hints: list[dict[str, Any]],
        actor: str,
        *,
        domains: list[str],
        current_website: str | None = None,
    ) -> dict[str, Any] | None:
        """Validate and write `hints` for `slug`. Returns the change entry,
        or None for a no-op. Raises `HintError` if validation fails."""
        check_slug(slug)
        clean = validate_hints(
            hints, domains=domains, current_website=current_website,
            fetcher=self.fetcher, resolver=self.resolver,
        )
        old = self.reader.read(slug)
        old_hints = list((old or {}).get("hints") or [])
        if old_hints == clean:
            return None
        ts = self._clock()
        archived = None
        if old is not None:
            archived = self._archive(slug, ts, json.dumps(old, indent=2, sort_keys=True))
        doc = {
            "slug": slug,
            "version": int((old or {}).get("version") or 0) + 1,
            "updated": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "hints": clean,
        }
        self.store.write_json(hints_key(slug), doc)
        changed = sorted(
            {h["kind"] for h in clean if h not in old_hints}
            | {h["kind"] for h in old_hints if h not in clean}
        )
        return self._log(slug, ts, actor, changed, archived)

    def _archive(self, slug: str, ts: datetime, text: str) -> str:
        stamp = ts.strftime("%Y%m%dT%H%M%SZ")
        key = f"hints/{slug}/{stamp}.json"
        n = 1
        while self.history.exists(key):
            n += 1
            key = f"hints/{slug}/{stamp}-{n}.json"
        self.history.write_text(key, text, "application/json")
        return f"history/{key}"

    def _log(
        self, slug: str, ts: datetime, actor: str, changed: list[str], archived: str | None
    ) -> dict[str, Any]:
        entry = {
            "slug": slug,
            "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "actor": actor,
            "kind": "hints",
            "changed": changed,
            "archived": archived,
        }
        existing = self.history.read_text(CHANGES_KEY) or ""
        if existing and not existing.endswith("\n"):
            existing += "\n"
        self.history.write_text(
            CHANGES_KEY, existing + json.dumps(entry, sort_keys=True) + "\n",
            "application/x-ndjson",
        )
        return entry


def default_writer(fetcher: Fetcher | None = None) -> HintWriter:
    from partner_scrape import config

    return HintWriter(config.get_hints_store(), config.get_history_store(), fetcher=fetcher)
