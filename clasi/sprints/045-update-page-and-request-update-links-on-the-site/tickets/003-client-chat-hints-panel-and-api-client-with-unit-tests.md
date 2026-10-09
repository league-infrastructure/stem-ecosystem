---
id: '003'
title: Client chat, hints panel and API client with unit tests
status: in-progress
use-cases:
- SUC-003
- SUC-004
- SUC-005
depends-on:
- '002'
github-issue: ''
issue: 84-update-page-and-request-update-links-on-the-site.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Client chat, hints panel and API client with unit tests

## Description

Implement src/lib/updates/api-client.mjs (injected fetch/base; start, send, confirm, get; normalized errors for all codes incl. Retry-After), src/lib/updates/hints-view.mjs (readable lines e.g. 'Events: visitcmod.org/calendar', 'Skip: ...'), and a client script wiring chat, hints card, notices, confirm, ended sessions, session recovery via sessionStorage+GET. Render with textContent only; aria-live for replies; keyboard operable.

## Acceptance Criteria

- [ ] Greeting and replies shown; hints card re-rendered each turn
- [ ] Confirm shows summary and 'takes effect after the next scheduled scrape'; saved:false shows no-changes message
- [ ] Each error code gives friendly message plus fallback email; guard/turn_cap end disables input
- [ ] Unit tests with fake fetch cover all codes and hint formatting; `npm test` passes
- [ ] No innerHTML with server text

## Testing

- **Existing tests to run**: `npm test`, `npm run build`
- **New tests to write**: New scripts/test/update-api-client.test.mjs and hints-view.test.mjs.
- **Verification command**: `npm test`
