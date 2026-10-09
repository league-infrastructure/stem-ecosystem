"""One-time import of the Git roster into bucket partner records, and the
equality check that proves it.

`plan_migration` reads ``<site>/src/data/partners.json`` and
``<site>/public/images/logos/`` and builds, without touching any store, the
records and logos to write (slug = ``model.slugify(name)``, stored in the
record; ``logo_src`` becomes the bucket-relative ``partners/<slug>/logo.<ext>``
or ``""``). Anything that makes the import unsafe -- slug collisions, unusable
names, a ``logo_src`` pointing at a missing file or not a bare filename, a
roster that fails validation -- is reported as an *error* and nothing is
written.

`migrate` applies the plan through the archiving `PartnerWriter` with actor
``migration`` and **copies** (never moves or deletes) ``cache/partner_log/**``
to ``history/partner_log/**``. It is idempotent: unchanged records/logos are
no-ops in the writer, identical copied objects are skipped. If a destination
``opportunities.jsonl`` already differs (e.g. the new image has since written
to it), only source lines whose ``(slug, content_hash)`` the destination lacks
are appended; a differing ``partner.json`` snapshot keeps the destination.

`verify_migration` consolidates the stored records in memory (read-only) and
compares them with a baseline roster: everything but ``logo_src`` (and the
fields consolidation adds: ``slug``, ``events_url``, ``past_events_url``) must
be identical; ``logo_src`` may differ only in value, not in whether a logo
exists, and every referenced logo must exist in the store.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from partner_scrape.model import slugify
from partner_scrape.partners.consolidate import published_entry
from partner_scrape.partners.records import (
    PARTNERS_PREFIX,
    check_ext,
    check_slug,
    load_roster,
    logo_key,
    logo_keys,
    read_record,
    record_key,
)
from partner_scrape.partners.writer import PartnerWriter
from partner_scrape.registry.validate_roster import (
    RosterValidationError,
    validate_records,
)
from partner_scrape.storage import Store

ACTOR = "migration"
ROSTER_RELPATH = Path("src/data/partners.json")
LOGOS_RELPATH = Path("public/images/logos")
PARTNER_LOG_PREFIX = "partner_log/"

#: Fields consolidation adds to a published entry (not in the Git roster).
_ADDED_FIELDS = ("slug", "events_url", "past_events_url")


@dataclass
class PlannedPartner:
    slug: str
    record: dict[str, Any]
    logo_file: Path | None  # local logo to upload, or None


@dataclass
class Plan:
    partners: list[PlannedPartner] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    orphan_logos: list[str] = field(default_factory=list)  # files no partner uses
    empty_logo_src: int = 0
    shared_logos: list[str] = field(default_factory=list)


@dataclass
class Report:
    plan: Plan
    dry_run: bool
    records_new: int = 0
    records_updated: int = 0
    records_unchanged: int = 0
    logos_new: int = 0
    logos_updated: int = 0
    logos_unchanged: int = 0
    log_copied: int = 0
    log_merged: int = 0
    log_identical: int = 0
    log_kept: int = 0

    def lines(self) -> list[str]:
        p = self.plan
        verb = "would write" if self.dry_run else "wrote"
        out = [
            f"migration {'DRY RUN (nothing written)' if self.dry_run else 'report'}:",
            f"  partners in roster: {len(p.partners)}",
            f"  with logo: {sum(1 for x in p.partners if x.logo_file)}; "
            f"no logo (logo_src empty): {p.empty_logo_src}",
            f"  records {verb}: {self.records_new} new, "
            f"{self.records_updated} updated, {self.records_unchanged} unchanged",
            f"  logos {verb}: {self.logos_new} new, "
            f"{self.logos_updated} updated, {self.logos_unchanged} unchanged",
            f"  partner_log objects ({'would copy' if self.dry_run else 'copied'} "
            f"cache -> history; source untouched): {self.log_copied} new, "
            f"{self.log_merged} merged, {self.log_identical} identical, "
            f"{self.log_kept} kept destination",
            f"  logo files used by no partner (not migrated): {len(p.orphan_logos)}"
            + (f" ({', '.join(p.orphan_logos)})" if p.orphan_logos else ""),
            f"  logos shared by several partners: {len(p.shared_logos)}"
            + (f" ({', '.join(p.shared_logos)})" if p.shared_logos else ""),
            f"  errors: {len(p.errors)}",
        ]
        out.extend(f"    ERROR {e}" for e in p.errors)
        return out


class MigrationError(RuntimeError):
    """The plan has errors; nothing was written."""


def load_roster_file(path: Path) -> list[dict[str, Any]]:
    """A roster JSON file: a list, or a ``{"partners": [...]}`` envelope."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationError(f"cannot read roster {path}: {exc}") from exc
    if isinstance(data, dict):
        data = data.get("partners")
    if not isinstance(data, list) or not all(isinstance(x, dict) for x in data):
        raise MigrationError(f"{path} is not a list of partner objects")
    return data


def plan_migration(site_dir: Path) -> Plan:
    """Build the migration plan from the site checkout; reads only."""
    site_dir = Path(site_dir)
    partners = load_roster_file(site_dir / ROSTER_RELPATH)
    logos_dir = site_dir / LOGOS_RELPATH
    plan = Plan()

    by_slug: dict[str, list[str]] = defaultdict(list)
    used_logos: dict[str, list[str]] = defaultdict(list)
    for index, partner in enumerate(partners):
        name = partner.get("name")
        label = f"#{index} id={partner.get('id')!r} name={name!r}"
        if not isinstance(name, str) or not name.strip():
            plan.errors.append(f"{label}: missing or empty name")
            continue
        slug = slugify(name)
        try:
            check_slug(slug)
        except ValueError:
            plan.errors.append(f"{label}: name yields unusable slug {slug!r}")
            continue
        by_slug[slug].append(label)

        record = dict(partner)
        record["slug"] = slug
        logo_file: Path | None = None
        logo_src = partner.get("logo_src")
        if logo_src in (None, ""):
            record["logo_src"] = ""
            plan.empty_logo_src += 1
        elif not isinstance(logo_src, str) or "/" in logo_src or "\\" in logo_src or "://" in logo_src:
            plan.errors.append(f"{label}: logo_src {logo_src!r} is not a bare filename")
        else:
            candidate = logos_dir / logo_src
            if not candidate.is_file():
                plan.errors.append(
                    f"{label}: logo_src {logo_src!r} has no file in {LOGOS_RELPATH}"
                )
            else:
                try:
                    ext = check_ext(candidate.suffix)
                    record["logo_src"] = f"{PARTNERS_PREFIX}{slug}/logo.{ext}"
                    logo_file = candidate
                    used_logos[logo_src].append(slug)
                except ValueError:
                    plan.errors.append(f"{label}: logo {logo_src!r} has an unusable extension")
        plan.partners.append(PlannedPartner(slug, record, logo_file))

    for slug, labels in sorted(by_slug.items()):
        if len(labels) > 1:
            plan.errors.append(f"slug collision {slug!r}: " + "; ".join(labels))

    plan.shared_logos = sorted(f for f, s in used_logos.items() if len(s) > 1)
    if logos_dir.is_dir():
        plan.orphan_logos = sorted(
            f.name for f in logos_dir.iterdir() if f.is_file() and f.name not in used_logos
        )

    if not plan.errors:
        try:
            validate_records([p.record for p in plan.partners])
        except RosterValidationError as exc:
            plan.errors.append(f"roster validation failed: {exc}")
    return plan


def _merge_jsonl(dest_text: str, src_text: str) -> str:
    """`dest_text` plus the `src_text` lines whose (slug, content_hash) it lacks."""

    def lines(text: str) -> list[str]:
        return [x for x in text.splitlines() if x.strip()]

    def ident(line: str) -> tuple[Any, Any]:
        try:
            obj = json.loads(line)
            return (obj.get("slug"), obj.get("content_hash"))
        except (json.JSONDecodeError, AttributeError):
            return (line, None)

    out = lines(dest_text)
    seen = {ident(x) for x in out}
    for line in lines(src_text):
        if ident(line) not in seen:
            seen.add(ident(line))
            out.append(line)
    return "\n".join(out) + "\n"


def _copy_partner_log(cache: Store, history: Store, report: Report, dry_run: bool) -> None:
    for key in cache.list(PARTNER_LOG_PREFIX):
        src = cache.read_bytes(key)
        if src is None:
            continue
        dest = history.read_bytes(key)
        if dest is None:
            report.log_copied += 1
            if not dry_run:
                history.write_bytes(key, src)
        elif dest == src:
            report.log_identical += 1
        elif key.endswith(".jsonl"):
            merged = _merge_jsonl(dest.decode("utf-8"), src.decode("utf-8")).encode("utf-8")
            if merged == dest:
                report.log_identical += 1
            else:
                report.log_merged += 1
                if not dry_run:
                    history.write_bytes(key, merged)
        else:
            report.log_kept += 1


def migrate(
    site_dir: Path,
    data: Store,
    history: Store,
    cache: Store,
    dry_run: bool = False,
    writer: PartnerWriter | None = None,
) -> Report:
    """Import the roster and logos and copy partner_log; see module docstring.

    Raises `MigrationError` (before writing anything) if the plan has errors.
    """
    plan = plan_migration(site_dir)
    report = Report(plan=plan, dry_run=dry_run)
    if plan.errors:
        raise MigrationError("\n".join(Report(plan, dry_run).lines()))
    writer = writer or PartnerWriter(data, history)

    for item in plan.partners:
        old = read_record(data, item.slug)
        if old is None:
            report.records_new += 1
        elif old != item.record:
            report.records_updated += 1
        else:
            report.records_unchanged += 1
        if not dry_run:
            writer.put_record(item.slug, item.record, ACTOR)

        if item.logo_file is not None:
            content = item.logo_file.read_bytes()
            ext = check_ext(item.logo_file.suffix)
            existing = logo_keys(data, item.slug)
            if existing == [logo_key(item.slug, ext)] and data.read_bytes(existing[0]) == content:
                report.logos_unchanged += 1
            else:
                if existing:
                    report.logos_updated += 1
                else:
                    report.logos_new += 1
                if not dry_run:
                    writer.put_logo(item.slug, ext, content, ACTOR)

    _copy_partner_log(cache, history, report, dry_run)
    return report


# -- verification -----------------------------------------------------


def _strip(entry: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in entry.items() if k not in _ADDED_FIELDS and k != "logo_src"}


def verify_migration(
    data: Store, baseline: list[dict[str, Any]]
) -> tuple[list[str], list[str]]:
    """``(diffs, notes)`` for the consolidated records vs `baseline`.

    An empty `diffs` means equal apart from ``logo_src`` values. `notes` are
    non-fatal: partner *order* (consolidation sorts by id; the Git roster was
    never id-sorted, and the site sorts by name itself). Read-only."""
    try:
        roster = load_roster(data, validate=True)
    except RosterValidationError as exc:
        return [f"consolidation failed: {exc}"], []
    consolidated = [published_entry(r, r["slug"]) for r in roster.as_list()]

    diffs: list[str] = []
    if len(consolidated) != len(baseline):
        diffs.append(f"partner count: consolidated {len(consolidated)} != baseline {len(baseline)}")

    base_by_id = {b.get("id"): b for b in baseline}
    cons_by_id = {c.get("id"): c for c in consolidated}
    for pid in sorted(base_by_id.keys() - cons_by_id.keys(), key=str):
        diffs.append(f"id {pid!r} ({base_by_id[pid].get('name')!r}) missing from consolidated")
    for pid in sorted(cons_by_id.keys() - base_by_id.keys(), key=str):
        diffs.append(f"id {pid!r} ({cons_by_id[pid].get('name')!r}) not in baseline")

    for pid in sorted(base_by_id.keys() & cons_by_id.keys(), key=str):
        base, cons = base_by_id[pid], cons_by_id[pid]
        who = f"id {pid!r} ({base.get('name')!r})"
        b, c = _strip(base), _strip(cons)
        for key in sorted(b.keys() | c.keys()):
            if b.get(key, "<absent>") != c.get(key, "<absent>"):
                diffs.append(
                    f"{who}: {key}: baseline {b.get(key, '<absent>')!r} != "
                    f"consolidated {c.get(key, '<absent>')!r}"
                )
        slug = cons["slug"]
        if cons.get("events_url") != f"partners/{slug}/events.json":
            diffs.append(f"{who}: events_url {cons.get('events_url')!r} does not match slug")
        had, has = bool(base.get("logo_src")), bool(cons.get("logo_src"))
        if had != has:
            diffs.append(
                f"{who}: logo presence changed (baseline {base.get('logo_src')!r}, "
                f"consolidated {cons.get('logo_src')!r})"
            )
        elif has:
            ext = str(cons["logo_src"]).rsplit(".", 1)[-1]
            if cons["logo_src"] != f"{PARTNERS_PREFIX}{slug}/logo.{ext}" or not data.exists(
                f"{PARTNERS_PREFIX}{slug}/logo.{ext}"
            ):
                diffs.append(f"{who}: logo_src {cons['logo_src']!r} has no logo object in the store")

    base_order = [b.get("id") for b in baseline]
    cons_order = [c.get("id") for c in consolidated]
    notes = []
    if not diffs and base_order != cons_order:
        notes.append("partner order differs from baseline (consolidation sorts by id)")
    return diffs, notes
