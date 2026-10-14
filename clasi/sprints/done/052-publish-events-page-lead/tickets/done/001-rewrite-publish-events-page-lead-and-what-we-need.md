---
id: '001'
title: Rewrite Publish Events page lead and What we need
status: done
use-cases:
- SUC-001
depends-on: []
github-issue: ''
issue: 92-publish-events-page-lead-with-we-copy-from-your-site.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Rewrite Publish Events page lead and What we need

## Description

Implement changes 1-4 of clasi/issues/92-publish-events-page-lead-with-we-copy-from-your-site.md in src/pages/publish-events.astro.

## Acceptance Criteria

- [x] Hero subtitle removed
- [x] First content is a plain-language lead: events are not published on this site; publish on your own website and we automatically copy (scrape) them regularly; events not on your website cannot appear here
- [x] "What we need" rewritten from the partner's view: each event page shows title, date and time, location, cost, short description, link (image optional)
- [x] Removed: "Adapter framework", partner_scrape/adapters/, ADAPTERS table, export.writer.SITE_SCHEMA_FIELDS; link to data reference kept
- [x] Publishing-method sections (iCal, JSON-LD, ...) untouched
- [x] npm test and npm run build pass

## Implementation Plan

Edit src/pages/publish-events.astro only (plus any test asserting its text).

## Testing

- **Existing tests to run**: `npm test`
- **New tests to write**: none required unless existing tests cover page text
- **Verification command**: `npm test && npm run build`
