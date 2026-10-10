---
sprint: "046"
status: draft
---

# Architecture Update -- Sprint 046: Update page scrolling polish

## What Changed

- `src/pages/update.astro`: layout/CSS. Desktop chat panel gets bounded height (viewport minus sticky header) as a flex column; transcript is the single scroll region (`overflow-y:auto`, `tabindex=0`, role=log, aria-live kept); input pinned below it. Hints panel `position:sticky`. Under the existing stacking breakpoint, bounds are removed (normal page scroll).
- `src/scripts/update-chat.ts`: remove the "messages left" display; auto-scroll the transcript (not the window) to the newest message unless the user has scrolled up.

- `focus` on page hints flows: hints model/validation -> agent tool schema/prompt -> hints card (`hints-view.mjs`) -> updates proposer and LLM event enrichment (untrusted context, logged).
- Guard (`sidecar/llm.py` prompt, `sidecar/app.py` handling): refinement counts as legitimate; escalation is redirect first, end on clear abuse, high-confidence injection, or second offense. League session added as regression test.

## Why

Issues 85 and 86, SUC-001 to SUC-005.

## Impact on Existing Components

Issue 85 part is client-only. `focus` is an additive optional field (backward compatible); flow is one-directional (hints -> consumers), no cycles. Guard gains per-session offense state in the sidecar.

## Migration Concerns

None.

## Review (self)

Consistency, alignment, cohesion/coupling, anti-patterns, risks: no issues (presentation-only change, two files, no cycles). Verdict: APPROVE. Open questions: none.
