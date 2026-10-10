---
sprint: "046"
status: draft
---

# Architecture Update -- Sprint 046: Update page scrolling polish

## What Changed

- `src/pages/update.astro`: layout/CSS. Desktop chat panel gets bounded height (viewport minus sticky header) as a flex column; transcript is the single scroll region (`overflow-y:auto`, `tabindex=0`, role=log, aria-live kept); input pinned below it. Hints panel `position:sticky`. Under the existing stacking breakpoint, bounds are removed (normal page scroll).
- `src/scripts/update-chat.ts`: remove the "messages left" display; auto-scroll the transcript (not the window) to the newest message unless the user has scrolled up.

## Why

Issue 85, SUC-001 and SUC-002.

## Impact on Existing Components

Client-only. No API, server turn-cap, or data model change. No new dependencies or module boundaries.

## Migration Concerns

None.

## Review (self)

Consistency, alignment, cohesion/coupling, anti-patterns, risks: no issues (presentation-only change, two files, no cycles). Verdict: APPROVE. Open questions: none.
