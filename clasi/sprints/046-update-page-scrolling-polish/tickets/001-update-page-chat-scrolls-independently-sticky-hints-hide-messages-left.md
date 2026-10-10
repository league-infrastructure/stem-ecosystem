---
id: '001'
title: 'Update page: chat scrolls independently, sticky hints, hide messages-left'
status: open
use-cases: [SUC-001, SUC-002]
depends-on: []
github-issue: ''
issue: 85-update-page-chat-scrolls-independently-hide-messages-left.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Update page: chat scrolls independently, sticky hints, hide messages-left

## Description

On desktop, bound the chat panel height (viewport minus sticky header) with a scrolling transcript, pinned input, and sticky hints panel. Auto-scroll to newest message unless the user scrolled up. Phones keep stacked layout. Remove the 'messages left' display and its code. Files: src/pages/update.astro, src/scripts/update-chat.ts.

## Acceptance Criteria

- [ ] Transcript scrolls inside bounded chat panel on desktop; input stays visible
- [ ] Hints panel sticky
- [ ] Auto-scroll to newest message, respecting user scroll-up
- [ ] Phone breakpoint unchanged (stacked, page scroll)
- [ ] No 'messages left' text or update code; server cap and end message unchanged
- [ ] role=log/aria-live kept; scroll region keyboard-focusable (tabindex)
- [ ] npm test and npm run build pass

## Testing

- **Verification**: `npm test && npm run build` (update tests that referenced the counter)
