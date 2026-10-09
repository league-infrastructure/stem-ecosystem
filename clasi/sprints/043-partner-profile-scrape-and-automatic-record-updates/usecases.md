---
status: done
---
# Sprint 043 Use Cases

## SUC-001: Redirects are noticed on every fetch
Parent: UC-XXX
- **Actor**: Scheduled scraper
- **Main Flow**: Any fetch (plain or headless) records `final_url` and `redirect_chain`; the cache stores them; notable redirects (host change, ignoring `www.` and http->https) are collected and reported in run logs.
- **Acceptance Criteria**:
  - [ ] 301 to another host flagged; http->https and www-only not flagged; no redirect leaves `final_url == url`

## SUC-002: Weekly partner profile snapshot
Parent: UC-XXX
- **Actor**: Scheduled `profiles` job
- **Main Flow**: For each partner with a website, fetch home, About, Contact (robots, rate limits, headless fallback); extract title, og:site_name, JSON-LD Organization facts, social links, mailto/tel; write a private snapshot with per-page content hashes.
- **Postconditions**: `history/profiles/<slug>/profile.json` per partner; partners without a website listed in the report.
- **Acceptance Criteria**:
  - [ ] No LLM; unchanged pages give identical hashes; one partner's failure never aborts the run

## SUC-003: Flag partners whose records look stale
Parent: UC-XXX
- **Actor**: `updates` job
- **Main Flow**: Compare snapshot (and notable redirect) with the partner record: website host vs final URL, name, phone, email domain, address, socials, logo. Each difference becomes a flag with severity; only changed-hash or redirected partners are examined.
- **Acceptance Criteria**:
  - [ ] CMOD-style rename and domain move produce high-severity flags

## SUC-004: Haiku proposes and the job applies safe updates
Parent: UC-XXX
- **Actor**: `updates` job
- **Main Flow**: Flagged partners go to Haiku (cached by content hash) which returns per-field changes with confidence and reason and an original-wording description. Changes at or above the threshold are applied via `PartnerWriter` (actor `haiku`); then consolidate. `--dry-run` only reports.
- **Acceptance Criteria**:
  - [ ] Never blanks a field; never changes slug/id; per-run cap with remainder reported; old record archived automatically; unchanged content costs no LLM call

## SUC-005: Event-quality report
Parent: UC-XXX
- **Actor**: Maintainer reading `logs/updates/`
- **Main Flow**: The updates report lists per-partner event problems (non-events, duplicates, date/link mismatch, past events, implausible age tags, missing cost, collapsed recurring times) computed from existing scrape output; report-only.
- **Acceptance Criteria**:
  - [ ] No web calls, no LLM; no data modified

## SUC-006: Scheduled operation
Parent: UC-XXX
- **Actor**: Container cron
- **Main Flow**: `run-job profiles` Sunday 03:00, `run-job updates` Sunday 05:00; logs land in `logs/profiles/` and `logs/updates/` with index lines.
- **Acceptance Criteria**:
  - [ ] Preflight requires only DO Spaces keys (+ ANTHROPIC_API_KEY for updates)
