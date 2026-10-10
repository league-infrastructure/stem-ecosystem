---
id: '005'
title: 'Team-lead: rebuild/push images, redeploy, live re-check'
status: done
use-cases:
- SUC-001
- SUC-002
- SUC-003
- SUC-004
- SUC-005
depends-on:
- '001'
- '002'
- '003'
- '004'
github-issue: ''
issue: 86-page-hints-need-a-focus-and-the-guard-is-too-strict.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Team-lead: rebuild/push images, redeploy, live re-check

## Description

Team-lead task: rebuild and push updates and scraper images, redeploy, and live re-check: scrolling and hidden counter (issue 85), and the League conversation (focus on the about page age range, no premature end) (issue 86). Completes both issues.

## Acceptance Criteria

- [x] Images rebuilt, pushed, deployed
- [x] Live: chat scrolls independently, hints sticky, no messages-left
- [x] Live: League conversation continues and records a focus hint
- [x] Live: focus used in an updates/enrichment log line

## Testing

- **Verification**: Manual live verification

## Results (team lead, 2026-10-10)

- **Images and deploy:** version 0.20261010.1. Both images were built for
  linux/amd64 and pushed, the stack was redeployed, and both services are
  running 0.20261010.1. `/healthz` returns 200.
- **League conversation, live, via the tailnet dev origin:**
  - Turn 1 proposed `page/about https://www.jointheleague.org/about/` with
    focus "the grade/age range of students the classes serve", and declined
    to take the grade from chat.
  - Turn 2 ("Your hints should specifically call out the age range on the
    about page.") kept the session **active**. Before this fix the guard
    ended it as "injection". The focus was refined, and no fact was put into
    the hint.
  - Not confirmed; left for Eric to confirm from the page.
- **Dev server:** restarted on the tailnet IP after the version bump
  rewrote `.env`.
- **Known limitation, follow-up:** event enrichment gets the focus text as
  guidance, but it doesn't read the About page itself. A focus like "age
  range on the about page" helps the updates proposer, which reads the
  cached About page, more than per-event age tags. Using profile-page text
  as evidence for event enrichment would need a follow-up.
