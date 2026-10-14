---
id: '052'
title: Publish Events page lead
status: done
branch: sprint/052-publish-events-page-lead
use-cases: []
issues: []
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sprint 052: Publish Events page lead

## Goals

Make the Publish Events page lead with: events are published on the partner's own site and we copy (scrape) them.

## Problem

Stakeholder feedback (2026-10-14, issue 92): the page subtitle is gibberish, the key message is missing, and "What we need" lacks context and exposes internal text.

## Solution

Copy edit of src/pages/publish-events.astro per issue 92 changes 1-4.

## Success Criteria

Page matches issue 92; npm test and npm run build pass.

## Scope

### In Scope

Issue 92 changes 1-4.

### Out of Scope

Changes to the publishing-method sections (iCal, JSON-LD, ...).

## Test Strategy

npm test and npm run build.

## Architecture Notes

None; content-only change.

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
| 001 | Rewrite Publish Events page lead and What we need | none |

Tickets execute serially in the order listed.
