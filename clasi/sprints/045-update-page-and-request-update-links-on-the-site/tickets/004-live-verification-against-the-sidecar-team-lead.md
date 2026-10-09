---
id: '004'
title: Live verification against the sidecar (team-lead)
status: open
use-cases: [SUC-001, SUC-003, SUC-004, SUC-005]
depends-on: ["003"]
github-issue: ''
issue: 84-update-page-and-request-update-links-on-the-site.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Live verification against the sidecar (team-lead)

## Description

Team-lead verification: run dev server on localhost:4322, exercise a real session against the live sidecar on a real partner with a harmless conversation (do not confirm unless the hint is genuinely useful). Inspect via headless browser (Playwright) at desktop and phone widths, check no-JS view, and record results in the ticket. No deploy, no push.

## Acceptance Criteria

- [ ] Real session works end to end from localhost:4322 (CORS ok)
- [ ] Screenshots at desktop and mobile widths reviewed
- [ ] Defects found are fixed or ticketed; results recorded

## Testing

- **Existing tests to run**: `npm test`, `npm run build`
- **New tests to write**: Manual/headless-browser; record in ticket.
- **Verification command**: `npm test`
