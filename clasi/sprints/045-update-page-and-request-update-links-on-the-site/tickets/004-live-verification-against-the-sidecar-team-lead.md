---
id: '004'
title: Live verification against the sidecar (team-lead)
status: done
use-cases:
- SUC-001
- SUC-003
- SUC-004
- SUC-005
depends-on:
- '003'
github-issue: ''
issue: 84-update-page-and-request-update-links-on-the-site.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Live verification against the sidecar (team-lead)

## Description

Team-lead verification: run dev server on localhost:4322, exercise a real session against the live sidecar on a real partner with a harmless conversation (do not confirm unless the hint is genuinely useful). Inspect via headless browser (Playwright) at desktop and phone widths, check no-JS view, and record results in the ticket. No deploy, no push.

## Acceptance Criteria

- [x] Real session works end to end from localhost:4322 (CORS ok)
- [x] Screenshots at desktop and mobile widths reviewed
- [x] Defects found are fixed or ticketed; results recorded

## Testing

- **Existing tests to run**: `npm test`, `npm run build`
- **New tests to write**: Manual/headless-browser; record in ticket.
- **Verification command**: `npm test`

## Results (team lead, 2026-10-09)

- **Setup:** dev server on http://localhost:4323 (an allowed origin; 4322 is
  held by main-website). Headless Chromium in the `partner-scrape` image,
  with a loopback forwarder so the page origin stays `http://localhost:4323`.
- **Partner page:** /partners/24 (San Diego Natural History Museum) shows
  "Is something here wrong or out of date? Request an update ->" linking to
  `/update?type=partner&slug=san_diego_natural_history_museum`.
- **Picker:** /update with no params finds the museum.
- **Live session against https://updates.jtlapp.net:**
  - The greeting arrives.
  - The message "events are on https://www.sdnhm.org/calendar/" gets a reply
    explaining Confirm and that the change takes effect at the next
    scheduled scrape.
  - The hints card shows "Events: sdnhm.org/calendar" under Proposed
    changes, and the Confirm button appears.
  - No console errors.
  - **Not confirmed:** the test hint was made up, not supplied by the
    partner.
- **Polish found and fixed during verification:**
  - Scoped styles didn't apply to runtime-created nodes; fixed with
    `is:global`.
  - Site button styles, a full-width textarea, and chat bubbles.
  - Safe minimal markdown (bold, paragraphs, links) without innerHTML.
  - Retry/Start-again showed during an active chat because `.btn` display
    overrode `[hidden]`; fixed.
- **Re-check:** retry and start-again hidden, confirm visible, no console
  errors. The desktop (1280) and phone (390) layouts are correct, and the
  panels stack on phones.
- **Dev-only note:** `dotconfig version bump` rewrites `.env`. Astro dev then
  restarts on its default port 5173, which is not in the sidecar CORS list.
  Restart with `--port 4323`.
