---
id: 048
title: Footer scrape and site-update dates
status: planning-docs
branch: sprint/048-footer-scrape-and-site-update-dates
use-cases: [SUC-001]
issues: [88]
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sprint 048: Footer scrape and site-update dates

## Goals

Footer on every page shows when events were last scraped and when the site was last built.

## Problem

Footer shows only "Last updated", which is really the scrape time. Visitors cannot tell scrape date from deploy date. (Issue 88.)

## Solution

Footer renders "Events scraped <date>" from scrape-meta.json last_updated and "Site updated <date>" from a build-time constant, formatted in America/Los_Angeles, as `<time datetime title>`.

## Success Criteria

Live footer shows both dates correctly; npm test and npm run build pass.

## Scope

### In Scope

Footer change; consistency check of /data-access, /for-agents, llms.txt; manual deploy and live verification.

### Out of Scope

Scraper changes.

## Test Strategy

npm test, npm run build, live footer check.

## Architecture Notes

Build-time timestamp via Astro/Vite define or frontmatter `new Date()` at build; never the visitor clock.

## GitHub Issues

(GitHub issues linked to this sprint's tickets. Format: `owner/repo#N`.)

## Definition of Ready

Before tickets can be created, all of the following must be true:

- [ ] Sprint planning documents are complete (sprint.md, use cases, architecture)
- [ ] Architecture review passed
- [ ] Stakeholder has approved the sprint plan

## Tickets

| # | Title | Depends On |
|---|-------|------------|
| 001 | Footer shows scrape and site-update dates | - |
| 002 | Deploy and verify live footer | 001 |

Tickets execute serially in the order listed.
