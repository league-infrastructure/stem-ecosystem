"""The single archiving writer for partner records and logos.

Every change to ``data/partners/<slug>/`` goes through `PartnerWriter`, so
history cannot be bypassed. One code path per write:

1. read the current object; if identical, do nothing (no write, no log line);
2. copy the current object to ``history/partners/<slug>/<UTC ts>-partner.json``
   (or ``-logo.<ext>``) -- skipped on the first write;
3. write the new object to the **data** store (public-read);
4. append one line to ``history/partners/changes.jsonl``:
   ``{slug, ts, actor, kind, changed, archived}``.

It takes two Stores: `data` (rooted at ``data/``, public-read on S3) and
`history` (rooted at ``history/``, private). The changes.jsonl append is
read-modify-write like ``logs.append_index`` (writers are serial).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable

from partner_scrape.partners.records import (
    check_slug,
    logo_key,
    logo_keys,
    read_record,
    record_key,
)
from partner_scrape.storage import Store

CHANGES_KEY = "partners/changes.jsonl"

_CONTENT_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "svg": "image/svg+xml",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PartnerWriter:
    def __init__(
        self,
        data: Store,
        history: Store,
        clock: Callable[[], datetime] = _now,
    ):
        self.data = data
        self.history = history
        self._clock = clock

    # -- public API ---------------------------------------------------

    def put_record(
        self, slug: str, record: dict[str, Any], actor: str
    ) -> dict[str, Any] | None:
        """Write `record` for `slug`. Returns the change entry, or None for
        a no-op. The record's own ``slug`` must equal `slug`."""
        check_slug(slug)
        if record.get("slug") != slug:
            raise ValueError(
                f"record slug {record.get('slug')!r} does not match {slug!r}"
            )
        key = record_key(slug)
        old = read_record(self.data, slug)
        if old == record:
            return None
        changed = sorted(
            k for k in set(old or {}) | set(record) if (old or {}).get(k) != record.get(k)
        )
        ts = self._clock()
        archived = None
        if old is not None:
            archived = self._archive(
                slug, ts, "partner.json", self.data.read_bytes(key) or b"",
                "application/json",
            )
        self.data.write_json(key, record)
        return self._log(slug, ts, actor, "record", changed, archived)

    def put_logo(
        self, slug: str, ext: str, content: bytes, actor: str, content_type: str | None = None
    ) -> dict[str, Any] | None:
        """Write the logo for `slug` as ``logo.<ext>``. Returns the change
        entry, or None if the bytes are unchanged. A logo with a different
        extension is archived and removed so one logo remains."""
        key = logo_key(slug, ext)
        ext = key.rsplit(".", 1)[1]
        existing = logo_keys(self.data, slug)
        if existing == [key] and self.data.read_bytes(key) == content:
            return None
        ts = self._clock()
        archived = None
        for old_key in existing:
            old_ext = old_key.rsplit(".", 1)[1]
            old_bytes = self.data.read_bytes(old_key)
            if old_bytes is not None:
                archived = self._archive(slug, ts, f"logo.{old_ext}", old_bytes, None)
            if old_key != key:
                self.data.delete(old_key)
        self.data.write_bytes(key, content, content_type or _CONTENT_TYPES.get(ext))
        return self._log(slug, ts, actor, "logo", ["logo"], archived)

    # -- internals ----------------------------------------------------

    def _archive(
        self, slug: str, ts: datetime, name: str, data: bytes, content_type: str | None
    ) -> str:
        stamp = ts.strftime("%Y%m%dT%H%M%SZ")
        key = f"partners/{slug}/{stamp}-{name}"
        n = 1
        while self.history.exists(key):  # two writes in one second
            n += 1
            key = f"partners/{slug}/{stamp}-{n}-{name}"
        self.history.write_bytes(key, data, content_type)
        return f"history/{key}"

    def _log(
        self,
        slug: str,
        ts: datetime,
        actor: str,
        kind: str,
        changed: list[str],
        archived: str | None,
    ) -> dict[str, Any]:
        entry = {
            "slug": slug,
            "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "actor": actor,
            "kind": kind,
            "changed": changed,
            "archived": archived,
        }
        existing = self.history.read_text(CHANGES_KEY) or ""
        if existing and not existing.endswith("\n"):
            existing += "\n"
        self.history.write_text(
            CHANGES_KEY,
            existing + json.dumps(entry, sort_keys=True) + "\n",
            "application/x-ndjson",
        )
        return entry


def default_writer() -> PartnerWriter:
    """Writer over the configured data and history stores."""
    from partner_scrape import config

    return PartnerWriter(config.get_data_store(), config.get_history_store())
