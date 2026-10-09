"""`publish.project()`: the build-time projection into partner-scrape's
own data tree (the data Store).

`export/partner_log.py` (ticket 003) accumulates every `Opportunity`
ever seen into a durable, per-partner, append-only `.jsonl` log. That
log is not itself a publishable contract -- it can hold several lines
for the same event (one per content change) and is keyed only by
whatever partners happened to yield opportunities on some past run. This
module turns that accumulated state into issue 15's actual public data
contract: per partner, a current/upcoming events file and a past-events
file. The partner roster itself (`{own_data_dir}/partners.json`) is no
longer written here (sprint 042): it is composed from the per-partner
records by `partners.consolidate.consolidate()`, which the CLI runs right
after this projection.

Sprint 025 ticket 007 (issue 21, "stop writing to the stem-ecosystem
checkout") redirected this projection's write target from
`{site_dir}/public/data/` to partner-scrape's own data location
(since sprint 038 the data Store, `config.get_data_store()`), matching every other sprint-020 export
module's convention -- for stem-ecosystem (or any consumer) to pull
from at its own build time, rather than partner-scrape writing directly
into a sibling checkout. `site_dir` stays as a parameter for
compatibility but no longer locates the roster (sprint 042: the roster
is the data store's partner records).

## Self-describing, not just "correct"

Issue 15's whole point is that a consumer needs *no other data source*
to reconstruct the site: no source code, no separately-communicated
schema, no tribal knowledge of file layout. So every published file
here carries a small metadata envelope alongside its data --
`generated_at`, a `partner_count`/`event_count`, and (for partners.json)
each partner's own reference paths to its two event files -- rather
than shipping a bare, unlabeled array and assuming the reader already
knows what it is or where to look next.

## What this module does not do

Reuses `writer.is_current_or_upcoming` for the current/past split and
`writer.SITE_SCHEMA_FIELDS`/`writer.to_json_dict` for the event field
set -- the exact same promoted helpers `export_opportunities` uses, so
the two published contracts (`opportunities.json` and this module's
`own_data_dir` tree) can never silently disagree about which events are
current or what an event record contains. This module adds no new
judgment on top of those -- see `export/DESIGN.md`.

## One-way dependency on `partner_log.py`

This module imports exactly one thing from `partner_log.py`: the
`.jsonl` filename constant (`_JSONL_FILENAME`), so the two modules'
notion of "where the log lives" cannot drift apart. It does not import
`partner_log.record` or duplicate its slug-computation logic to
*enumerate* partners -- partners come from the curated `partners.json`
(via `model.slugify`, the same shared primitive), not from listing
`log_dir`'s subdirectories. `partner_log.py` never imports this module
-- the dependency is one-way, matching this subsystem's existing
`mirror.py` -> `writer.py`/`ads.py` convention.

## Read-cost note (not solved here)

`project()` reads and parses *every* partner's full `.jsonl` on every
call -- cost grows with total accumulated history, not with one run's
yield, since `partner_log.py` never prunes. Negligible while the store
is young; flagged in `export/DESIGN.md`'s Open Questions as worth
re-measuring later, not solved speculatively here.
"""

from __future__ import annotations

import json
from dataclasses import MISSING, fields
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from partner_scrape.config import resolve_data_store
from partner_scrape.export.partner_log import _JSONL_FILENAME, resolve_log_store
from partner_scrape.export.writer import SITE_SCHEMA_FIELDS, is_current_or_upcoming, to_json_dict
from partner_scrape.model import slugify
from partner_scrape.partners.source import resolve_partners
from partner_scrape.normalize.run import Opportunity
from partner_scrape.storage import Store

def _now_iso() -> str:
    """Current UTC time, matching `writer.py`'s `_now_iso()` format
    exactly -- one timestamp convention across every export this
    subsystem writes."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl_lines(store: Store, key: str) -> list[str]:
    text = store.read_text(key)
    if text is None:
        return []
    return [line for line in text.splitlines() if line.strip()]


def _collapse_last_line_wins(store: Store, key: str) -> list[dict[str, Any]]:
    """Read `key` from `store` and collapse to one record per `slug`, the
    later line in file order winning -- `partner_log.record()` always
    appends, never rewrites, so file order is chronological and a plain
    dict overwrite implements "last line wins" exactly."""
    by_slug: dict[str, dict[str, Any]] = {}
    for line in _read_jsonl_lines(store, key):
        entry = json.loads(line)
        by_slug[entry["slug"]] = entry
    return list(by_slug.values())


def _to_opportunity(entry: dict[str, Any]) -> Opportunity:
    """Reconstruct an `Opportunity` from a persisted log line.

    `entry` carries every `Opportunity` field plus `content_hash`
    (`partner_log._to_log_dict`'s shape); only the known dataclass
    fields are pulled across, so `content_hash` is dropped naturally.
    `sources` round-trips list -> `frozenset` -- the inverse of
    `partner_log._to_log_dict`'s `frozenset` -> sorted-list conversion.

    The per-partner `.jsonl` log is strictly append-only and never
    migrated (`export/DESIGN.md`'s append-only invariant): a line
    recorded before some field existed on `Opportunity` simply lacks
    that key. Subscripting `entry` directly for a field it doesn't have
    would raise `KeyError` and break `project()` on every such line --
    every line recorded before sprint 015 added `eligibility`, for
    example. Instead, each field missing from `entry` falls back to
    `Opportunity`'s own dataclass default for that field, discovered
    generically via `dataclasses.fields()` rather than by name -- so a
    field added to `Opportunity` after a line was recorded is tolerated
    automatically, with no special case here to update when the next
    field is added.
    """
    kwargs: dict[str, Any] = {}
    for f in fields(Opportunity):
        if f.name in entry:
            kwargs[f.name] = entry[f.name]
        elif f.default is not MISSING:
            kwargs[f.name] = f.default
        elif f.default_factory is not MISSING:  # type: ignore[misc]
            kwargs[f.name] = f.default_factory()
        else:
            # No dataclass default exists for this field, and it's
            # absent from `entry` too. Not expected for any real log
            # line -- `partner_log.record()` always wrote every field
            # that existed on `Opportunity` at record time, and a
            # non-defaulted field can only be one that existed from the
            # start (dataclass field-ordering requires every defaulted
            # field to follow every non-defaulted one). Subscript
            # `entry` anyway, to raise the same `KeyError` naming this
            # field rather than inventing a value for a field the
            # dataclass itself declares required.
            kwargs[f.name] = entry[f.name]
    kwargs["sources"] = frozenset(kwargs["sources"])
    return Opportunity(**kwargs)


def _split_current_and_past(
    opportunities: list[Opportunity], today: date
) -> tuple[list[Opportunity], list[Opportunity]]:
    """Partition `opportunities` into (current/upcoming, past) using
    `writer.is_current_or_upcoming` as the sole judgment -- every
    collapsed record lands in exactly one of the two lists (this is a
    split, not a filter): nothing accumulated in the persistent log is
    ever silently dropped from the published export, unlike the legacy
    flat `opportunities.json`, which is issue 15's whole point.

    Both lists are sorted by `date_start`, matching
    `export_opportunities`'s own sort key -- no new ordering judgment
    invented here.
    """
    current = [o for o in opportunities if is_current_or_upcoming(o, today)]
    past = [o for o in opportunities if not is_current_or_upcoming(o, today)]
    current.sort(key=lambda o: o.date_start)
    past.sort(key=lambda o: o.date_start)
    return current, past


def _events_payload(kind: str, partner_slug: str, opportunities: list[Opportunity]) -> dict[str, Any]:
    """Wrap `opportunities` (already filtered/sorted) in a small
    self-describing envelope -- `generated_at`/`event_count`/`kind`/
    `partner_slug` alongside the `events` array -- so this file alone
    (with no partners.json context) tells a reader what it is."""
    return {
        "generated_at": _now_iso(),
        "partner_slug": partner_slug,
        "kind": kind,
        "event_count": len(opportunities),
        "events": [to_json_dict(o) for o in opportunities],
    }


def project(
    site_dir: str | Path | None = None,
    *,
    log_dir: str | Path | None = None,
    partners_path: Any = None,
    own_data_dir: str | Path | Store | None = None,
    today: date | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Project every partner's accumulated `.jsonl` log into
    partner-scrape's own `{own_data_dir}/` tree.

    For every partner in the curated `partners_path` (not only ones
    with an accumulated log), resolves its stored slug (matching
    `partner_log.log_slug_for`) and looks up
    `{log_dir}/<slug>/opportunities.jsonl`. If present, collapses it to
    one record per event slug (last line wins) and splits into current/
    upcoming vs. past (`writer.is_current_or_upcoming`). If absent, that
    partner still gets (empty) event files.

    Writes:
        - `{own_data_dir}/partners/<slug>/events.json` and
          `.../past-events.json` per partner -- each an envelope
          (`generated_at`/`kind`/`event_count`) around an `events` array
          using exactly `writer.SITE_SCHEMA_FIELDS` (`sources` excluded,
          matching `opportunities.json`).

    `partners.json` is not written here: `partners.consolidate` composes
    it from the per-partner records (the CLI runs it after this).
    `own_data_dir/opportunities.json` (written by `export_opportunities`)
    is untouched -- this is a purely additive second contract.

    Args:
        site_dir: unused since sprint 042 (kept for caller
            compatibility); this function never touches `site_dir`.
        log_dir: root of the per-partner accumulation store
            (`partner_log.py`'s `log_dir`). Defaults to
            the history Store's `partner_log/` prefix
            (`partner_log.resolve_log_store`).
        partners_path: the curated roster to project (a list, a roster
            JSON file, or a Store). Defaults to the partner records in
            the `own_data_dir` store.
        own_data_dir: where to write -- a local path, an `s3://` location,
            or a `Store`; this function's sole write target. Defaults to
            `config.get_data_store()` when `None`. A local directory is
            created automatically if missing. Tests should always pass
            an explicit `tmp_path` here, never rely on the default.
        today: reference date for the current/past split. Defaults to
            `date.today()`. Tests should pass an explicit value.
        dry_run: when `True`, compute and return the summary without
            touching disk at all.

    Returns:
        A summary dict: `partner_count`, `current_event_count`,
        `past_event_count`.

    Raises:
        RuntimeError: the roster cannot be read or is empty,
            or `own_data_dir` cannot be created/written (e.g. the path
            is occupied by a file). Never silently skips the write,
            matching `export_opportunities`'s loud-failure contract.
    """
    log_store, log_prefix = resolve_log_store(log_dir)
    store = resolve_data_store(own_data_dir)
    partners = resolve_partners(partners_path if partners_path is not None else store)
    reference_date = today if today is not None else date.today()

    total_current = 0
    total_past = 0
    per_partner_events: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}

    for partner in partners:
        # Both the accumulated log (partner_log.py) and the published event
        # files are keyed by the record's stored slug, so a rename keeps its
        # history. slugify(name) only for slug-less (list-based) records.
        partner_slug = partner.get("slug") or slugify(partner.get("name", ""))
        log_slug = partner_slug
        jsonl_key = f"{log_prefix}{log_slug}/{_JSONL_FILENAME}"

        collapsed = [_to_opportunity(entry) for entry in _collapse_last_line_wins(log_store, jsonl_key)]
        current, past = _split_current_and_past(collapsed, reference_date)
        total_current += len(current)
        total_past += len(past)

        per_partner_events[partner_slug] = (
            _events_payload("current", partner_slug, current),
            _events_payload("past", partner_slug, past),
        )

    summary = {
        "partner_count": len(per_partner_events),
        "current_event_count": total_current,
        "past_event_count": total_past,
    }

    if dry_run:
        return summary

    try:
        for partner_slug, (events_payload, past_events_payload) in per_partner_events.items():
            store.write_text(
                f"partners/{partner_slug}/events.json",
                json.dumps(events_payload, indent=1, ensure_ascii=False),
                "application/json",
            )
            store.write_text(
                f"partners/{partner_slug}/past-events.json",
                json.dumps(past_events_payload, indent=1, ensure_ascii=False),
                "application/json",
            )
    except RuntimeError as exc:
        raise RuntimeError(
            f"Cannot write published data export: {exc}. "
            "Check that the data location is writable."
        ) from exc

    return summary
