---
id: '001'
title: Footer shows scrape and site-update dates
status: open
use-cases: [SUC-001]
depends-on: []
github-issue: ''
issue: 88-footer-shows-last-scrape-and-site-update-dates.md
completes_issue: true
---

# Footer shows scrape and site-update dates

## Description

Footer shows "Events scraped <date>" (scrape-meta.json last_updated) and "Site updated <date>" (build-time timestamp). Assignee: programmer. Source: issue 88.

## Acceptance Criteria

- [ ] Both dates shown, labelled, muted, on every page
- [ ] Formatted in America/Los_Angeles
- [ ] `<time datetime>` with full timestamp in title
- [ ] Site date is a build-time constant, not the visitor clock
- [ ] /data-access, /for-agents, llms.txt checked for "last updated" wording and made consistent
- [ ] npm test and npm run build pass

## Implementation Plan

Approach: add build-time constant (Astro/Vite define or build-time Date) and update the footer component. Files: footer component, astro config, possibly data-access / for-agents pages and llms.txt. Testing: npm test (add a formatting test if a test setup exists), npm run build and inspect dist HTML. Docs: none.
