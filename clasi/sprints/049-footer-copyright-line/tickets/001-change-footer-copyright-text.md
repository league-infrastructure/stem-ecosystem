---
id: '001'
title: Change footer copyright text
status: open
use-cases: [SUC-001]
depends-on: []
github-issue: ''
issue: 89-footer-copyright-fleet-and-the-league.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Change footer copyright text

## Description

In `src/components/Footer.astro` (line ~55) change the copyright line to "Copyright &copy; {year} Fleet Science Center and The League of Amazing Programmers. All Rights Reserved." Keep the build-time `new Date().getFullYear()`. Source: issue 89.

## Acceptance Criteria

- [ ] Footer text updated as described
- [ ] `npm test` passes
- [ ] `npm run build` passes

## Testing

- **Existing tests to run**: `npm test`
- **New tests to write**: None unless an existing test asserts footer text
- **Verification command**: `npm test && npm run build`
