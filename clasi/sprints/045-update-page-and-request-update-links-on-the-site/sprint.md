---
id: '045'
title: Update page and request-update links on the site
status: ticketing
branch: sprint/045-update-page-and-request-update-links-on-the-site
use-cases: [SUC-001, SUC-002, SUC-003, SUC-004, SUC-005]
issues: ["84"]
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sprint 045: Update page and request-update links on the site

## Goals

Give the live update-agent sidecar (sprint 044, https://updates.jtlapp.net) a front end: "Request an update" links on every detail page and in the footer, and a `/update` page with a chat and a live scraping-hints card.

## Problem

Partners have no way to tell us a listing is wrong or how to scrape their site better. The sidecar API exists but nothing on the site calls it. Source: clasi/issues/84.

## Solution

A shared `UpdateLink` component placed on partner, opportunity, team, club and place detail pages (Discovery Lab is a place record, so place pages cover it) plus a footer link. A static `/update` Astro page with explainer and email fallback (works without JS), a listing picker when no query params, and a client-side module (pure `api-client` and `hints-view` logic, thin DOM glue) for chat, hints card and confirm. API base from `PUBLIC_UPDATES_API_URL`, default https://updates.jtlapp.net.

## Success Criteria

- Every detail page links to `/update?type=&slug=` with the right keys.
- A real session against the live sidecar from localhost:4322 renders the greeting, replies and a hints card; errors map to friendly messages.
- `npm test` passes with new unit tests (fake fetch).
- Verified in a headless browser at desktop and phone widths.

## Scope

### In Scope

Tickets 001-004 below; no-JS fallback; accessibility; mobile stacking.

### Out of Scope

Sidecar changes; Turnstile widget (off; client sends token only if configured, deferred); site deploy (deploy.yml stays manual); GitHub push; confirming a hint during verification unless genuinely useful.

## Test Strategy

node:test unit tests for the API client (fake fetch, every error code) and hint rendering/formatting. Manual/headless-browser verification in ticket 004. No browser test framework is added.

## Architecture Notes

See architecture-update.md.

## GitHub Issues

None.

## Definition of Ready

Before tickets can be created, all of the following must be true:

- [x] Sprint planning documents are complete (sprint.md, use cases, architecture)
- [x] Architecture review passed
- [x] Stakeholder has approved the sprint plan (Eric approved 2026-10-09; team lead records gate)

## Tickets

| # | Title | Depends On |
|---|-------|------------|
| 001 | UpdateLink component, detail-page placement and footer link | |
| 002 | /update page shell: explainer, no-JS fallback, listing picker | 001 |
| 003 | Client chat, hints panel and API client with unit tests | 002 |
| 004 | Live verification against the sidecar (team-lead) | 003 |

Tickets execute serially in the order listed.
