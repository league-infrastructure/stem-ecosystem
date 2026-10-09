"""The ``updates`` job (sprint 043-006, issue 75).

check -> propose (Haiku, cached) -> apply policy -> write via
the partner writer (actor "haiku") -> consolidate -> save state.

``apply_policy`` output is the ONLY thing ever handed to the writer. One
partner's failure (LLM error, bad record) is reported and never aborts the run.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Callable

from partner_scrape.partners.consolidate import consolidate
from partner_scrape.partners.writer import PartnerWriter
from partner_scrape.profiles.snapshot import read_snapshot
from partner_scrape.storage import Store
from partner_scrape.updates.checks import (
    LinkChecker,
    load_state,
    run_checks,
    save_state,
)
from partner_scrape.updates.policy import PolicyResult, apply_policy
from partner_scrape.updates.proposer import Proposal, Proposer, propose_for_partner
from partner_scrape.updates.quality import QualityReport, run_quality

log = logging.getLogger(__name__)

ACTOR = "haiku"
DEFAULT_MAX_CHANGES = 20
REPORT_PREFIX = "updates"  # in the history store: updates/<ts>.json


@dataclass
class PartnerOutcome:
    slug: str
    flags: list[dict[str, Any]]
    old: dict[str, Any]
    proposal: Proposal | None = None
    from_cache: bool = False
    policy: PolicyResult | None = None
    status: str = "flagged"  # flagged|unchanged|applied|would_apply|deferred|error
    error: str = ""

    def diff(self) -> dict[str, dict[str, Any]]:
        if not (self.policy and self.policy.applied):
            return {}
        new = self.policy.applied
        return {f: {"old": self.old.get(f), "new": new.get(f)}
                for f in self.policy.applied_fields}

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "status": self.status,
            "error": self.error,
            "flags": self.flags,
            "old_record": self.old,
            "proposed": self.proposal.to_dict() if self.proposal else None,
            "from_cache": self.from_cache,
            "applied": self.diff(),
            "rejected": [{"field": f, "reason": r}
                         for f, r in (self.policy.rejected if self.policy else [])],
        }


@dataclass
class UpdatesReport:
    dry_run: bool = False
    no_llm: bool = False
    outcomes: list[PartnerOutcome] = field(default_factory=list)
    check_lines: list[str] = field(default_factory=list)
    redirect_lines: list[str] = field(default_factory=list)
    quality: QualityReport | None = None
    consolidated: bool = False
    state_saved: bool = False
    report_key: str = ""

    def _by(self, *statuses: str) -> list[PartnerOutcome]:
        return [o for o in self.outcomes if o.status in statuses]

    @property
    def applied(self) -> list[PartnerOutcome]:
        return self._by("applied")

    def lines(self) -> list[str]:
        out = list(self.check_lines)
        out.extend(self.redirect_lines)
        for o in self.outcomes:
            if o.proposal is not None:
                for p in o.proposal.fields:
                    out.append(
                        f"PROPOSED {o.slug} {p.field}: {o.old.get(p.field)!r} -> {p.value!r} "
                        f"(confidence {p.confidence:.2f}{', cached' if o.from_cache else ''}): "
                        f"{p.reason}")
                out.extend(f"NOTE {o.slug}: {n}" for n in o.proposal.notes)
            tag = "WOULD APPLY" if o.status == "would_apply" else "APPLIED"
            if o.status in ("applied", "would_apply"):
                for f, d in o.diff().items():
                    out.append(f"{tag} {o.slug} {f}: {d['old']!r} -> {d['new']!r}")
            if o.policy:
                out.extend(f"REJECTED {o.slug} {f}: {r}" for f, r in o.policy.rejected)
            if o.status == "deferred":
                out.append(f"DEFERRED {o.slug}: per-run cap reached; "
                           f"{len(o.policy.applied_fields) if o.policy else 0} field(s) pending")
            if o.status == "error":
                out.append(f"ERROR {o.slug}: {o.error}")
        if self.quality is not None:
            out.extend(self.quality.lines())
        out.append(
            f"updates{' (dry-run)' if self.dry_run else ''}"
            f"{' (no-llm)' if self.no_llm else ''}: examined={len(self.outcomes)} "
            f"applied={len(self._by('applied'))} would_apply={len(self._by('would_apply'))} "
            f"deferred={len(self._by('deferred'))} errors={len(self._by('error'))} "
            f"consolidated={'yes' if self.consolidated else 'no'}")
        return out

    def to_dict(self, ts: str) -> dict[str, Any]:
        return {
            "ts": ts,
            "dry_run": self.dry_run,
            "no_llm": self.no_llm,
            "consolidated": self.consolidated,
            "partners": [o.to_dict() for o in self.outcomes],
            "event_quality": self.quality.to_dict() if self.quality else None,
        }


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _revert(state: dict[str, str], prev: dict[str, str], slug: str) -> None:
    """Forget this run's hash for ``slug`` so it is re-examined next run."""
    if slug in prev:
        state[slug] = prev[slug]
    else:
        state.pop(slug, None)


def run_updates(
    roster: list[dict[str, Any]],
    *,
    data_store: Store,
    history_store: Store,
    cache_store: Store,
    writer: PartnerWriter,
    proposer: Proposer | None,
    link_checker: LinkChecker | None = None,
    dry_run: bool = False,
    no_llm: bool = False,
    max_changes: int = DEFAULT_MAX_CHANGES,
    slug: str | None = None,
    all_partners: bool = False,
    clock: Callable[[], str] = _stamp,
    today: date | None = None,
) -> UpdatesReport:
    report = UpdatesReport(dry_run=dry_run, no_llm=no_llm)
    check = run_checks(
        roster, history_store, cache_store, link_checker=link_checker,
        all_partners=all_partners, slug=slug)
    report.check_lines = check.lines()
    by_slug = {r.get("slug"): r for r in roster}
    new_state = dict(check.new_state)
    prev_state = load_state(cache_store)
    changed = 0

    for pc in check.checks:
        old = by_slug[pc.slug]
        out = PartnerOutcome(pc.slug, [f.to_dict() for f in pc.flags], old)
        report.outcomes.append(out)
        snap = read_snapshot(history_store, pc.slug) or {}
        for r in snap.get("redirects") or []:
            report.redirect_lines.append(
                f"REDIRECT {pc.slug} {r.get('kind', '')}: "
                f"{r.get('requested', '')} -> {r.get('final', '')}")
        if no_llm or proposer is None or not pc.needs_llm:
            out.status = "flagged" if pc.flags else "unchanged"
            continue
        try:
            out.proposal, out.from_cache = propose_for_partner(
                old, pc.flags, snap, cache_store, proposer)
            out.policy = apply_policy(old, out.proposal)
            if out.policy.applied is None:
                out.status = "unchanged"
                continue
            if changed >= max_changes:
                out.status = "deferred"
                _revert(new_state, prev_state, pc.slug)
                continue
            if dry_run:
                out.status = "would_apply"
                changed += 1
                continue
            # The only writer call: policy output, actor "haiku".
            entry = writer.put_record(pc.slug, out.policy.applied, actor=ACTOR)
            out.status = "applied" if entry else "unchanged"
            changed += 1 if entry else 0
        except Exception as exc:  # noqa: BLE001 - one partner must not abort the run
            log.warning("updates failed for %s: %s", pc.slug, exc)
            out.status = "error"
            out.error = f"{type(exc).__name__}: {exc}"
            _revert(new_state, prev_state, pc.slug)

    if not dry_run and report.applied:
        consolidate(data_store)
        report.consolidated = True

    if no_llm:
        pass  # flags-only: nothing was proposed, so nothing counts as handled
    elif not dry_run:
        save_state(cache_store, new_state)
        report.state_saved = True

    # Report-only event-quality checks: read the data store, never write it.
    try:
        report.quality = run_quality(roster, data_store, today=today, slug=slug)
    except Exception as exc:  # noqa: BLE001 - a report section must not abort the run
        log.warning("event-quality checks failed: %s", exc)

    ts = clock()
    report.report_key = f"{REPORT_PREFIX}/{ts}.json"
    history_store.write_text(
        report.report_key, json.dumps(report.to_dict(ts), indent=1, sort_keys=True),
        "application/json")
    return report
