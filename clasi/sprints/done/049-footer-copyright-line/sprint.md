---
id: 049
title: Footer copyright line
status: done
branch: sprint/049-footer-copyright-line
use-cases: []
issues: []
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sprint 049: Footer copyright line

## Goals

Update the site footer copyright to credit Fleet Science Center and The League of Amazing Programmers (issue 89).

## Problem

Footer credits only Fleet Science Center.

## Solution

One-line text change in `src/components/Footer.astro`; keep the build-time year.

## Success Criteria

Footer reads "Copyright © {year} Fleet Science Center and The League of Amazing Programmers. All Rights Reserved."; `npm test` and `npm run build` pass.

## Scope

### In Scope

Footer copyright text.

### Out of Scope

Deployment (manual Deploy workflow, done separately).

## Test Strategy

`npm test` and `npm run build`.

## Architecture Notes

None; text-only change.

## GitHub Issues

None.

## Definition of Ready

Before tickets can be created, all of the following must be true:

- [ ] Sprint planning documents are complete (sprint.md, use cases, architecture)
- [ ] Architecture review passed
- [ ] Stakeholder has approved the sprint plan

## Tickets

| # | Title | Depends On |
|---|-------|------------|
| 001 | Change footer copyright text | none |

Tickets execute serially in the order listed.
