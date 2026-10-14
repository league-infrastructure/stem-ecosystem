---
id: '050'
title: About page developer credit
status: done
branch: sprint/050-about-page-developer-credit
use-cases: []
issues: []
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sprint 050: About page developer credit

## Goals

Credit The League of Amazing Programmers as the site developer on the About page (issue 90).

## Problem

The About page names the host (Fleet Science Center) but not the developer.

## Solution

Add one sentence to `src/pages/about.astro` linking https://www.jointheleague.org/.

## Success Criteria

Sentence renders on the About page; `npm test` and `npm run build` pass.

## Scope

### In Scope

One sentence in about.astro.

### Out of Scope

Deployment (manual Deploy workflow, separate step).

## Test Strategy

`npm test` and `npm run build`.

## Architecture Notes

None; content-only change.

## GitHub Issues

None. Source: clasi/issues/90-about-page-credits-the-league-as-site-developer.md

## Definition of Ready

Before tickets can be created, all of the following must be true:

- [ ] Sprint planning documents are complete (sprint.md, use cases, architecture)
- [ ] Architecture review passed
- [ ] Stakeholder has approved the sprint plan

## Tickets

| # | Title | Depends On |
|---|-------|------------|
| 001 | Add developer credit sentence to About page | none |

Tickets execute serially in the order listed.
