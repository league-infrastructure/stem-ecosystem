"""Apply policy: the ONLY gate between a Haiku proposal and ``PartnerWriter``.

Pure: ``apply_policy(record, proposal)`` returns a ``PolicyResult`` and does
no I/O. The job (ticket 006) writes ``result.applied`` and nothing else.

Rules (stakeholder decision, sprint 043):
- auto-apply allowlist: name, website, phone, email, location, twitter,
  facebook, instagram, linkedin, description;
- ``logo_src`` is report-only; latitude/longitude, organization_type, id,
  slug (and anything else) never change;
- confidence >= ``min_confidence`` (default 0.8);
- never blank a field (a social link is therefore never removed; a dead link
  may only be replaced by a new link for the same network);
- shape checks (URL / email / phone) and the record validator must pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from partner_scrape.registry.validate_roster import RosterValidationError, validate_records
from partner_scrape.updates.proposer import Proposal

ALLOWLIST = (
    "name", "website", "phone", "email", "location",
    "twitter", "facebook", "instagram", "linkedin", "description",
)
REPORT_ONLY = ("logo_src",)
NEVER_CHANGE = ("id", "slug", "latitude", "longitude", "organization_type")
MIN_CONFIDENCE = 0.8

_SOCIAL_HOSTS = {
    "twitter": ("twitter.com", "x.com"),
    "facebook": ("facebook.com", "fb.com", "fb.me"),
    "instagram": ("instagram.com",),
    "linkedin": ("linkedin.com",),
}


@dataclass
class PolicyResult:
    applied: dict[str, Any] | None = None
    applied_fields: list[str] = field(default_factory=list)
    rejected: list[tuple[str, str]] = field(default_factory=list)


def _host(url: str) -> str:
    try:
        h = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


def _shape_error(name: str, value: str) -> str | None:
    if name in ("website", *_SOCIAL_HOSTS):
        p = urlparse(value)
        if p.scheme not in ("http", "https") or not p.netloc:
            return "not an http(s) URL"
        if name in _SOCIAL_HOSTS:
            host = _host(value)
            if not any(host == d or host.endswith("." + d) for d in _SOCIAL_HOSTS[name]):
                return f"host {host!r} is not a {name} domain"
    elif name == "email":
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            return "not an email address"
    elif name == "phone":
        if len(re.sub(r"\D", "", value)) < 10:
            return "fewer than 10 digits"
    return None


def apply_policy(
    record: dict[str, Any],
    proposal: Proposal,
    *,
    min_confidence: float = MIN_CONFIDENCE,
) -> PolicyResult:
    """Decide which proposed fields to apply to ``record``. Does not mutate it."""
    result = PolicyResult()
    new = dict(record)
    for p in proposal.fields:
        name = p.field
        value = p.value.strip() if isinstance(p.value, str) else p.value
        if name in REPORT_ONLY:
            result.rejected.append((name, "report-only field"))
        elif name in NEVER_CHANGE or name not in ALLOWLIST:
            result.rejected.append((name, "field is not auto-updatable"))
        elif p.confidence < min_confidence:
            result.rejected.append(
                (name, f"confidence {p.confidence:.2f} below {min_confidence:.2f}"))
        elif not value:
            why = ("would remove the link; report-only" if name in _SOCIAL_HOSTS
                   else "would blank the field")
            result.rejected.append((name, why))
        elif value == (record.get(name) or ""):
            continue  # no change
        else:
            err = _shape_error(name, value)
            if err:
                result.rejected.append((name, err))
                continue
            candidate = dict(new, **{name: value})
            try:
                validate_records([candidate])
            except RosterValidationError as exc:
                result.rejected.append((name, f"record validation failed: {exc}".splitlines()[0]))
                continue
            new = candidate
            result.applied_fields.append(name)
    if result.applied_fields:
        result.applied = new
    return result
