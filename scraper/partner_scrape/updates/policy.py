"""Apply policy: the ONLY gate between a Haiku proposal and ``PartnerWriter``.

Pure: ``apply_policy(record, proposal, flags=, snapshot=)`` returns a
``PolicyResult`` and does no I/O. The job writes ``result.applied`` only.

Field-aware rules (ticket 043-010, from the 2026-10-09 real dry run):

Hard gates (unchanged, a failure is ``rejected``): confidence >= 0.8; never
blank a field; protected fields (id, slug, latitude, longitude,
organization_type); URL/email/phone shape; the record validator.

AUTO-APPLY, after the gates:
- fill an EMPTY phone / email / social field;
- replace a social link with a link on the same network's domain (this
  includes dead-link replacement);
- website: only with a ``website_moved`` flag, proposed host == the snapshot's
  home ``final_url`` host, and the host not a site-builder/staging host;
- name, description, location: only with a HIGH ``website_moved`` flag
  (rebrand evidence).

Everything else is ``needs_review`` (reported, never applied): changing an
existing non-empty email/phone, name/description/location without rebrand
evidence, a website not backed by the redirect, cross-network social values,
logo_src, and any other field.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable
from urllib.parse import urlparse

from partner_scrape.registry.validate_roster import RosterValidationError, validate_records
from partner_scrape.updates.proposer import Proposal

ALLOWLIST = (
    "name", "website", "phone", "email", "location",
    "twitter", "facebook", "instagram", "linkedin", "description",
)
REBRAND_FIELDS = ("name", "description", "location")
NEVER_CHANGE = ("id", "slug", "latitude", "longitude", "organization_type")
MIN_CONFIDENCE = 0.8

_SOCIAL_HOSTS = {
    "twitter": ("twitter.com", "x.com"),
    "facebook": ("facebook.com", "fb.com", "fb.me"),
    "instagram": ("instagram.com",),
    "linkedin": ("linkedin.com",),
}


#: Site-builder / staging hosts that are never a partner's real website
#: (suffix match).
STAGING_HOSTS = (
    "multiscreensite.com", "wixsite.com", "squarespace.com", "godaddysites.com",
    "weebly.com", "webflow.io", "wordpress.com", "netlify.app", "vercel.app",
    "github.io",
)


@dataclass
class PolicyResult:
    applied: dict[str, Any] | None = None
    applied_fields: list[str] = field(default_factory=list)
    rejected: list[tuple[str, str]] = field(default_factory=list)
    #: Proposals held back by policy: dicts of field/current/proposed/reason.
    needs_review: list[dict[str, Any]] = field(default_factory=list)


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


def is_staging_host(host: str) -> bool:
    return any(host == d or host.endswith("." + d) for d in STAGING_HOSTS)


def _flag(f: Any, key: str) -> str:
    if isinstance(f, dict):
        return str(f.get(key) or "")
    v = getattr(f, key, "")
    return str(getattr(v, "label", v) or "")


def _field_rule(name, value, record, flags, snapshot) -> str | None:
    """None when auto-apply is allowed, else the needs-review reason."""
    current = (record.get(name) or "").strip()
    moved = [f for f in flags if _flag(f, "kind") == "website_moved"]
    if name in ("phone", "email"):
        return None if not current else f"changes an existing {name}; the roster value may be the curated contact"
    if name in _SOCIAL_HOSTS:
        host = _host(value)
        if not any(host == d or host.endswith("." + d) for d in _SOCIAL_HOSTS[name]):
            return f"host {host!r} is not a {name} domain"
        return None
    if name == "website":
        if not moved:
            return "no website_moved flag"
        home = ((snapshot or {}).get("pages") or {}).get("home") or {}
        final = _host(home.get("final_url") or "")
        host = _host(value)
        if not final or host != final:
            return f"host {host!r} is not the observed home redirect host {final!r}"
        if is_staging_host(host):
            return f"{host!r} is a site-builder/staging host"
        return None
    if name in REBRAND_FIELDS:
        if any(_flag(f, "severity") == "high" for f in moved):
            return None
        return "no high-severity website_moved flag (rebrand evidence)"
    return "not auto-updatable"


def apply_policy(
    record: dict[str, Any],
    proposal: Proposal,
    *,
    flags: Iterable[Any] = (),
    snapshot: dict[str, Any] | None = None,
    min_confidence: float = MIN_CONFIDENCE,
) -> PolicyResult:
    """Decide which proposed fields to apply to ``record``. Does not mutate it.

    ``flags`` are this run's ``Flag`` objects or their dicts; ``snapshot`` is
    the partner's profile snapshot (for the observed home ``final_url``).
    """
    flags = list(flags)
    result = PolicyResult()
    new = dict(record)

    def review(name, value, reason):
        result.needs_review.append({
            "field": name, "current": record.get(name), "proposed": value,
            "reason": reason})

    for p in proposal.fields:
        name = p.field
        value = p.value.strip() if isinstance(p.value, str) else p.value
        if name in NEVER_CHANGE:
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
        elif name not in ALLOWLIST:
            review(name, value, "report-only field" if name == "logo_src"
                   else "field is not auto-updatable")
        else:
            err = _shape_error(name, value)
            if err and not (name in _SOCIAL_HOSTS and err.startswith("host ")):
                result.rejected.append((name, err))
                continue
            reason = _field_rule(name, value, record, flags, snapshot)
            if reason:
                review(name, value, reason)
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
