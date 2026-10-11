---
id: '001'
title: Compact header and content-sized chat layout
status: done
use-cases:
- SUC-001
depends-on: []
github-issue: ''
issue: 87-update-page-compact-header-and-normal-chat-box.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Compact header and content-sized chat layout

## Description

Programmer ticket. In `src/pages/update.astro` and `src/scripts/update-chat.ts`, per issue 87: replace the hero with a compact title bar (<= ~100px) reading "Request an update" plus the listing name when selected; cut the explainer to one line with the partners@sdstemecosystem.org email (keep no-JS fallback); make the chat a normal content-sized box with the input visible on first load; transcript scrolls internally only past max-height (~60vh desktop); drop or shrink the chat heading; hints panel sticky beside chat on desktop and below on phones. Keep role=log/aria-live, keyboard use, auto-scroll, no "messages left".

## Acceptance Criteria

- [x] Compact header, one-line explainer, no-JS fallback kept
- [x] Transcript sized to content, no reserved empty space; max-height scroll with input visible
- [x] Hints sticky beside chat on desktop, below chat on phone
- [x] Accessibility behaviors preserved
- [x] `npm test` and `npm run build` pass

## Testing

- **Existing tests to run**: `npm test`
- **New tests to write**: Update any tests asserting removed hero/explainer markup
- **Verification command**: `npm test && npm run build`
