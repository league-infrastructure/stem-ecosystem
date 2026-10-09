---
id: '043'
title: Partner profile scrape and automatic record updates
status: planning-docs
branch: sprint/043-partner-profile-scrape-and-automatic-record-updates
use-cases:
- SUC-001
- SUC-002
- SUC-003
- SUC-004
- SUC-005
- SUC-006
issues:
- 73-detect-and-record-redirects-on-every-fetch.md
- 74-weekly-scrape-of-partner-home-about-and-contact-pages.md
- 75-post-scrape-partner-record-update-check-with-haiku.md
- 76-per-partner-event-quality-checks-in-the-post-scrape-report.md
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sprint 043: Partner profile scrape and automatic record updates

## Goals

1. Detect and record redirects on every fetch (issue 73).
2. Weekly `profiles` job: fetch home, About and Contact pages of every partner with a website; extract structured facts with no LLM; store per-partner profile snapshots with content hashes (issue 74).
3. Post-scrape `updates` job: no-LLM change check, Haiku proposal for flagged partners only, and automatic, safety-gated application to `data/partners/<slug>/partner.json` through `PartnerWriter` (actor `haiku`), then consolidate (issue 75, option C).
4. Report-only per-partner event-quality checks in the updates report (issue 76).

## Problem

Partner records go stale silently. Motivating case: San Diego Children's Discovery Museum became Children's Museum of Discovery, `sdcdm.org` now 301s to `visitcmod.org`, and nothing noticed. The scraper only fetches event pages, never a partner's home/About/Contact pages, and discards redirect information.

## Solution

Fetchers record `final_url` and `redirect_chain` (cached). A `profiles` job snapshots each partner's public profile facts and content hashes. An `updates` job compares snapshots to records, asks Haiku (only for flagged partners, cached by content hash) for a corrected record, and applies confident changes via the archiving writer (old record auto-archived, change logged). Both jobs run under `run-job`, logging to `logs/profiles/` and `logs/updates/`.

## Success Criteria

- Unit tests: 301 to another host is flagged; http->https and www-only changes are not; no redirect gives `final_url == url`.
- `profiles` produces a snapshot per website-bearing partner; unchanged pages yield identical hashes.
- `updates --dry-run` writes nothing but the report; a real run applies only confident changes, never blanks a field, never changes slug/id, respects the per-run cap.
- Real dry-run then real run in production (team lead) fixes the CMOD record (sdcdm.org -> visitcmod.org).

## Scope

### In Scope

Tickets 001-009 below.

### Out of Scope

- "Audit one partner" Claude skill (separate later issue).
- Fixing extraction problems found by event-quality checks (report-only; follow-up issues).
- Site deploy, GitHub push.

## Test Strategy

pytest with fake fetchers, LocalStore, and a fake Anthropic client (no network, no real `.env`, no real bucket). Bash test (stub commands) for run-job additions. Live redirect check against `http://sdcdm.org` is part of the team-lead checklist, not the unit suite.

## Architecture Notes

See architecture-update.md. Stakeholder decisions (not reopened, Eric 2026-10-08):
- Redirect check on every fetch; notable = host differs ignoring `www.` and http->https.
- Profile snapshots are PRIVATE: `history/profiles/<slug>/profile.json` (latest snapshot, overwritten each run; plus `history/profiles/index.jsonl` not required). Page bodies are not duplicated; they live in the fetch cache.
- Bucket record is the source of truth; `updates` applies changes via `PartnerWriter` with actor `haiku`.
- Model `claude-haiku-4-5-20251001`; descriptions must be original wording.
- Safeguards: confidence threshold (default 0.8), never blank a field, never change `slug`/`id`, per-run cap on records changed (default 20, remainder reported), `--dry-run`.
- Schedule: Sunday 03:00 `profiles`, Sunday 05:00 `updates` (clear of Mon/Thu 03:00 scrape).
- No new secrets. `updates` requires ANTHROPIC_API_KEY (dry-run still calls Haiku to show real proposals; only `--no-llm` waives the key). `profiles` needs DO Spaces keys only.

## GitHub Issues

(None.)

## Team-lead checklist (real-credential operations, after tickets 001-008)

Programmers never read the real `.env`. Ticket 009 is run by the team lead.
1. `dotconfig load prod`; `cd scraper; set -a; source ../.env; set +a`.
2. Live redirect check: fetch `http://sdcdm.org`, confirm `final_url` is visitcmod.org and flagged.
3. `uv run partner-scrape profiles` (real; read-only against records) and review the report.
4. `uv run partner-scrape updates --dry-run`; review proposals (CMOD expected: name, website, socials, description).
5. `uv run partner-scrape updates` (real); verify `history/partners/changes.jsonl` has `haiku` entries and `data/partners.json` is consolidated.
6. Build the amd64 image, push, redeploy the swarm stack (see scraper/docker/README.md); confirm the new crontab entries and `logs/profiles`, `logs/updates` objects after the first scheduled run.

## Definition of Ready

- [x] Sprint planning documents are complete (sprint.md, use cases, architecture)
- [x] Architecture review passed (self-review recorded)
- [ ] Stakeholder has approved the sprint plan (Eric, 2026-10-08, "plan this ... and start executing"; team lead records gate)

## Tickets

| # | Title | Depends On |
|---|-------|------------|
| 001 | Redirect detection on every fetch | none |
| 002 | Profile page discovery and no-LLM fact extraction | none |
| 003 | `profiles` job and private snapshots | 001, 002 |
| 004 | No-LLM change check and flags | 003 |
| 005 | Haiku proposer, content-hash cache, and apply policy | 004 |
| 006 | `updates` job: apply via writer, cap, dry-run, report | 005 |
| 007 | Event-quality checks in the updates report | 006 |
| 008 | run-job, crontab, Dockerfile, and docs for the new jobs | 006, 007 |
| 010 | Tighten the auto-apply policy after the first real dry run | 008 |
| 009 | Production run and redeploy (team-lead run) | 008, 010 |

Tickets execute serially in the order listed.
