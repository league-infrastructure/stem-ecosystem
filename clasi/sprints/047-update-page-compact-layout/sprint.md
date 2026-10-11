---
id: '047'
title: Update page compact layout
status: planning-docs
branch: sprint/047-update-page-compact-layout
use-cases:
- SUC-001
issues:
- 87-update-page-compact-header-and-normal-chat-box.md
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sprint 047: Update page compact layout

## Goals

Make the /update page compact: small title bar, one-line explainer, and a normal content-sized chat with the input visible on first load.

## Problem

After sprint 046 the page has a full hero banner, a long explainer, and a chat panel with reserved height that pushes the input below the fold (Eric, 2026-10-10, issue 87).

## Solution

Presentation-only changes to src/pages/update.astro and src/scripts/update-chat.ts: compact header, one-line explainer, content-sized transcript with max-height scroll, hints sticky beside chat on desktop and below on phones.

## Success Criteria

Input visible without scrolling at 1280x800 and 390x844; transcript sizes to content; screenshots confirm on first load and after 2-3 turns.

## Scope

### In Scope

Layout and styling of the update page; keep role=log/aria-live, keyboard use, auto-scroll, no-JS fallback.

### Out of Scope

Chat backend, agent behavior, other pages.

## Test Strategy

npm test, npm run build, and headless screenshots (viewport, not full page) at 1280x800 and 390x844.

## Architecture Notes

Presentation only; no new modules. See architecture-update.md.

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
| 001 | Compact header and content-sized chat layout | - |
| 002 | Screenshot verification and issue completion | 001 |

Tickets execute serially in the order listed.
