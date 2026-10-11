---
id: '002'
title: Screenshot verification and issue completion
status: done
use-cases:
- SUC-001
depends-on:
- '001'
github-issue: ''
issue: 87-update-page-compact-header-and-normal-chat-box.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Screenshot verification and issue completion

## Description

Team-lead ticket. Capture headless viewport screenshots (not full page) at 1280x800 and 390x844 on first load and after 2-3 live turns, confirming the input is visible and layout matches issue 87. Completes the issue.

## Acceptance Criteria

- [x] Screenshots at 1280x800 and 390x844 on first load show input without scrolling
- [x] Screenshots after 2-3 live turns show content-sized transcript with input below
- [x] Issue 87 completed

## Testing

- **Existing tests to run**: `npm test`
- **New tests to write**: None
- **Verification command**: `npm run build`

## Results (team lead, 2026-10-11)

Headless Chromium viewport screenshots (not full page) against the dev
server and the live sidecar, for /update?type=partner&slug=san_diego_natural_history_museum.

- **Compact title bar:** about 60px, "Request an update — San Diego Natural
  History Museum", with a one-line explainer and email. The hero is gone.
- **Desktop 1280x800:** Send button bottom at 592px on first load and 755.7px
  after two exchanges (limit 792). Pass.
- **Phone 390x844:** Send button bottom at 800.1px on first load and 799.8px
  after two exchanges (limit 836). Pass.
- **Hints panel:** sticky beside the chat on desktop, below it on phone.
  Focus is shown on the proposed hint.
- **Fixes made during verification:**
  - e591ab2: available-height transcript sizing.
  - 321180c: the height budget counts the whole input block, and the page
    scrolls the form into view.
- **Known, minor:** the agent's "- item" lines render as text with a
  leading dash rather than bullets, because the safe renderer supports bold,
  paragraphs and links only. On phones the page auto-scrolls on load so the
  input shows, which pushes the title bar slightly out of view.
