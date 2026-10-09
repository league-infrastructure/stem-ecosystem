"""Partner record key layout, readers, and the validated `Roster` loader.

Keys are relative to the **data** store (root ``data/`` in the bucket):

* ``partners/<slug>/partner.json`` -- the curated record (public-read)
* ``partners/<slug>/logo.<ext>``   -- the logo (public-read)

The slug is *stored in the record* and is the directory name; it is never
re-derived from the name here (see ``model.slugify``, used only by migration
and ``partners add``). Reading never writes; all writes go through
``partners.writer``.
"""

from __future__ import annotations

import re
from typing import Any

from partner_scrape.registry.validate_roster import (
    RosterValidationError,
    validate_records,
)
from partner_scrape.storage import Store

PARTNERS_PREFIX = "partners/"
RECORD_NAME = "partner.json"
LOGO_STEM = "logo"

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
_EXT_RE = re.compile(r"^[a-z0-9]{1,8}$")


def check_slug(slug: str) -> str:
    """Return `slug` if it is a safe key segment, else raise ValueError."""
    if not isinstance(slug, str) or not _SLUG_RE.match(slug):
        raise ValueError(f"invalid partner slug {slug!r}")
    return slug


def check_ext(ext: str) -> str:
    """Normalize a logo extension (no dot, lowercase) or raise ValueError."""
    clean = ext.lstrip(".").lower()
    if not _EXT_RE.match(clean):
        raise ValueError(f"invalid logo extension {ext!r}")
    return clean


def read_record_file_safe(path) -> dict[str, Any]:
    """Load a JSON object from a local file; ValueError if it is not one."""
    import json

    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid JSON ({exc})") from exc
    if not isinstance(obj, dict):
        raise ValueError(f"{path}: record must be a JSON object")
    return obj


def record_key(slug: str) -> str:
    return f"{PARTNERS_PREFIX}{check_slug(slug)}/{RECORD_NAME}"


def logo_key(slug: str, ext: str) -> str:
    return f"{PARTNERS_PREFIX}{check_slug(slug)}/{LOGO_STEM}.{check_ext(ext)}"


def logo_keys(store: Store, slug: str) -> list[str]:
    """Existing logo keys for `slug` (normally zero or one)."""
    prefix = f"{PARTNERS_PREFIX}{check_slug(slug)}/{LOGO_STEM}."
    return [k for k in store.list(prefix) if k.startswith(prefix)]


def read_record(store: Store, slug: str) -> dict[str, Any] | None:
    """The record for `slug`, or None if absent."""
    return store.read_json(record_key(slug))


def list_slugs(store: Store) -> list[str]:
    """Sorted slugs that have a ``partner.json`` in the store."""
    slugs = []
    for key in store.list(PARTNERS_PREFIX):
        parts = key[len(PARTNERS_PREFIX):].split("/")
        if len(parts) == 2 and parts[1] == RECORD_NAME:
            slugs.append(parts[0])
    return sorted(slugs)


class Roster:
    """Validated partner records keyed by their stored slug."""

    def __init__(self, records: dict[str, dict[str, Any]]):
        self.by_slug = records

    def __len__(self) -> int:
        return len(self.by_slug)

    def __contains__(self, slug: str) -> bool:
        return slug in self.by_slug

    def get(self, slug: str) -> dict[str, Any] | None:
        return self.by_slug.get(slug)

    def as_list(self) -> list[dict[str, Any]]:
        """Records ordered by id (then slug), the shape of ``partners.json``."""
        return sorted(
            self.by_slug.values(),
            key=lambda r: (r.get("id") is None, r.get("id") or 0, r["slug"]),
        )


def load_roster(store: Store, validate: bool = True) -> Roster:
    """Read every record and return a `Roster` keyed by stored slug.

    Fails loudly (`RosterValidationError`, naming every offender) when a
    record is unreadable, lacks a slug, or its stored slug differs from its
    directory; then runs the content checks in ``validate_roster``.
    """
    records: dict[str, dict[str, Any]] = {}
    problems: list[str] = []
    for slug in list_slugs(store):
        try:
            rec = read_record(store, slug)
        except ValueError as exc:
            problems.append(f"{slug}: unreadable record ({exc})")
            continue
        if not isinstance(rec, dict):
            problems.append(f"{slug}: record is not a JSON object")
        elif rec.get("slug") != slug:
            problems.append(
                f"{slug}: stored slug {rec.get('slug')!r} does not match its directory"
            )
        else:
            records[slug] = rec
    if problems:
        raise RosterValidationError(
            "Partner record check failed:\n  " + "\n  ".join(problems)
        )
    roster = Roster(records)
    if validate:
        validate_records(roster.as_list())
    return roster
