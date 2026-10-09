"""The ``profiles`` job: fetch home/About/Contact for each roster partner,
extract facts (no LLM), and write private snapshots (issue 74)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse

from partner_scrape.fetch.fetcher import is_notable_redirect
from partner_scrape.fetch.redirects import RedirectLog
from partner_scrape.profiles.discover import discover_profile_pages
from partner_scrape.profiles.extract import extract_facts
from partner_scrape.profiles.snapshot import (
    SNAPSHOT_VERSION,
    page_entry,
    write_snapshot_if_changed,
)
from partner_scrape.storage import Store

log = logging.getLogger(__name__)

_LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)


@dataclass
class ProfilesReport:
    partners: int = 0
    fetched: int = 0  # partners with a usable home page
    failed: int = 0  # partners whose home page failed, plus failed about/contact pages
    redirects: int = 0
    skipped: list[str] = field(default_factory=list)  # slugs without a website
    errors: list[str] = field(default_factory=list)
    written: int = 0
    unchanged: int = 0
    redirect_lines: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        out = list(self.redirect_lines)
        for s in self.skipped:
            out.append(f"SKIPPED {s}: no website")
        out.extend(f"FAILED {e}" for e in self.errors)
        out.append(
            f"profiles: partners={self.partners} fetched={self.fetched} "
            f"failed={self.failed} redirects={self.redirects} "
            f"skipped={len(self.skipped)} written={self.written} "
            f"unchanged={self.unchanged}"
        )
        return out


def _normalize_website(site: Any) -> str:
    site = (site or "").strip() if isinstance(site, str) else ""
    if not site:
        return ""
    if not urlparse(site).scheme:
        site = "https://" + site
    return site


def _fetch_page(fetcher, url: str, label: str) -> tuple[dict, str]:
    """Fetch one page; return (page entry, body). Never raises."""
    try:
        resp = fetcher.get(url, label=label)
    except Exception as exc:  # noqa: BLE001 - one bad page must not abort the run
        return page_entry(url, status=None, body=None, error=f"{type(exc).__name__}: {exc}"), ""
    err = f"HTTP {resp.status}" if resp.status >= 400 else ""
    entry = page_entry(
        url,
        status=resp.status,
        body=resp.body,
        final_url=getattr(resp, "final_url", "") or url,
        redirect_chain=getattr(resp, "redirect_chain", []),
        fetched_at=resp.fetched_at.isoformat(),
        error=err,
    )
    return entry, ("" if err else resp.body)


def _sitemap_urls(fetcher, home_final: str, label: str) -> list[str]:
    try:
        resp = fetcher.get(urljoin(home_final, "/sitemap.xml"), label=label)
    except Exception:  # noqa: BLE001
        return []
    if resp.status >= 400:
        return []
    return _LOC_RE.findall(resp.body or "")[:2000]


def profile_partner(record: dict, fetcher, now: datetime | None = None) -> tuple[dict, int]:
    """Build the snapshot for one record. Returns (snapshot, failed_page_count)."""
    slug = record["slug"]
    website = _normalize_website(record.get("website"))
    pages: dict[str, dict] = {}
    facts: dict[str, dict] = {}
    failed = 0

    home, home_body = _fetch_page(fetcher, website, f"{slug}:home")
    pages["home"] = home
    if home["error"]:
        failed += 1
    else:
        facts["home"] = extract_facts(home_body).to_dict()
        home_final = home["final_url"]
        found = discover_profile_pages(home_final, home_body)
        if not (found.about and found.contact):
            found = discover_profile_pages(
                home_final, home_body, _sitemap_urls(fetcher, home_final, f"{slug}:sitemap")
            )
        for kind, url in (("about", found.about), ("contact", found.contact)):
            if not url:
                continue
            entry, body = _fetch_page(fetcher, url, f"{slug}:{kind}")
            pages[kind] = entry
            if entry["error"]:
                failed += 1
            else:
                facts[kind] = extract_facts(body).to_dict()

    redirects = [
        {"kind": k, "requested": p["url"], "final": p["final_url"]}
        for k, p in pages.items()
        if not p["error"] and is_notable_redirect(p["url"], p["final_url"])
    ]
    if home["error"]:
        status = "failed"
    elif failed:
        status = "partial"
    else:
        status = "ok"
    when = (now or datetime.now(timezone.utc)).isoformat()
    snapshot = {
        "version": SNAPSHOT_VERSION,
        "slug": slug,
        "website": website,
        "status": status,
        "fetched_at": when,
        "pages": pages,
        "facts": facts,
        "redirects": redirects,
    }
    return snapshot, failed


def run_profiles(
    roster: list[dict],
    fetcher,
    history_store: Store,
    *,
    slug: str | None = None,
    limit: int | None = None,
    redirect_log: RedirectLog | None = None,
) -> ProfilesReport:
    """Run the job over ``roster`` (record dicts). The fetcher should have
    been built with ``redirect_log`` so home-page redirects are reported."""
    if getattr(history_store, "public_read", False):
        raise ValueError("profile snapshots are private; refusing a public-read store")
    report = ProfilesReport()
    records = sorted(roster, key=lambda r: r.get("slug", ""))
    if slug:
        records = [r for r in records if r.get("slug") == slug]
    if limit is not None:
        records = records[:limit]
    for rec in records:
        s = rec.get("slug", "")
        report.partners += 1
        if not _normalize_website(rec.get("website")):
            report.skipped.append(s)
            continue
        try:
            snap, failed = profile_partner(rec, fetcher)
            result = write_snapshot_if_changed(history_store, s, snap)
        except Exception as exc:  # noqa: BLE001 - never abort the run
            report.failed += 1
            report.errors.append(f"{s}: {type(exc).__name__}: {exc}")
            continue
        if snap["status"] == "failed":
            report.failed += 1
            report.errors.append(f"{s}: {snap['pages']['home']['error']}")
        else:
            report.fetched += 1
            report.failed += failed
            for k, p in snap["pages"].items():
                if p["error"] and k != "home":
                    report.errors.append(f"{s}:{k}: {p['error']}")
        if result == "unchanged":
            report.unchanged += 1
        else:
            report.written += 1
    if redirect_log is not None:
        report.redirects = len(redirect_log)
        report.redirect_lines = redirect_log.lines()
    return report
