---
id: '046'
title: Update page scrolling polish
status: planning-docs
branch: sprint/046-update-page-scrolling-polish
use-cases:
- SUC-001
- SUC-002
issues:
- 85-update-page-chat-scrolls-independently-hide-messages-left.md
- 86-page-hints-need-a-focus-and-the-guard-is-too-strict.md
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sprint 046: Update page scrolling polish

## Goals

Also (issue 86): page hints gain a `focus` field carried end to end, and the sidecar guard stops ending legitimate hint-refinement conversations.

Make the /update chat scroll independently of the hints panel and drop the "messages left" counter (issue 85, Eric's direct request 2026-10-10).

## Problem

The whole page scrolls with the chat, moving the hints away; the "messages left" line is distracting.

## Solution

Desktop: bounded-height chat panel with a scrolling transcript and pinned input; sticky hints panel. Phones keep the stacked layout. Remove the counter UI. Auto-scroll to newest message unless the user scrolled up.

## Success Criteria

- Desktop transcript scrolls inside the panel; input and hints stay visible.
- No "messages left" text; server-side cap and end message unchanged.
- role=log, aria-live kept; scroll region keyboard-focusable.
- `npm test` and `npm run build` pass.

## Scope

### In Scope

`src/pages/update.astro`, `src/scripts/update-chat.ts`; hints model/validation, agent tool schema and prompt, `src/lib/updates/hints-view.mjs`, sidecar guard (`sidecar/llm.py`, `sidecar/app.py`), updates proposer and event enrichment; tests. Deploy/live re-check by team lead.

### Out of Scope

Server turn-cap logic, phone layout changes.

## Test Strategy

Existing `npm test`, update tests for removed counter; build check; team lead verifies live.

## Architecture Notes

See architecture-update.md.

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
| 001 | Update page: chat scrolls independently, sticky hints, hide messages-left | - |
| 002 | Page-hint focus field: model, agent schema/prompt, hints card | - |
| 003 | Guard recalibration: allow hint refinement, redirect before ending | 002 |
| 004 | Scraper consumes focus: updates proposer and event enrichment | 002 |
| 005 | Team-lead: rebuild/push images, redeploy, live re-check | 001, 002, 003, 004 |

Tickets execute serially in the order listed.
