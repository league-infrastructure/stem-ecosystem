---
sprint: "047"
status: draft
---

# Architecture Update -- Sprint 047: Update page compact layout

## What Changed

Presentation-only changes to the update page (`src/pages/update.astro`) and its chat script (`src/scripts/update-chat.ts`): compact header replacing the hero, one-line explainer, content-sized transcript with a max-height, and hints panel placement (sticky beside chat on desktop, below on phone). No new modules.

## Why

Stakeholder feedback (issue 87): the hero and reserved chat height hide the input below the fold.

## Impact on Existing Components

None outside the two files. Chat protocol, backend, and other pages are untouched. Dependencies unchanged.

## Migration Concerns

None.

## Design Review

Verdict: APPROVE. Cohesion and coupling unchanged; no anti-patterns; risk limited to CSS regressions, covered by screenshots.

## Open Questions

None.
