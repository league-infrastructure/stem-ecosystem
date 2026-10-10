---
status: draft
---

# Sprint 046 Use Cases

## SUC-001: Chat scrolls independently of hints
Parent: UC-XXX

- **Actor**: Visitor using /update
- **Preconditions**: Desktop viewport; conversation longer than the panel
- **Main Flow**:
  1. Visitor sends messages and reads replies.
  2. Transcript scrolls inside the chat panel; input stays at the bottom; hints stay in view.
- **Postconditions**: Page itself does not scroll with the chat; new messages auto-scroll unless the user scrolled up.
- **Acceptance Criteria**:
  - [ ] Transcript scrolls within a bounded panel; input always visible
  - [ ] Hints panel sticky
  - [ ] Phone breakpoint keeps stacked, normal page scroll
  - [ ] role=log/aria-live kept; scroller keyboard-focusable

## SUC-002: No turn counter shown
Parent: UC-XXX

- **Actor**: Visitor using /update
- **Preconditions**: Active conversation
- **Main Flow**:
  1. Visitor chats; no "messages left" line appears.
  2. At the server cap, the existing polite end message shows.
- **Postconditions**: Cap still enforced server-side.
- **Acceptance Criteria**:
  - [ ] Counter element and its update code removed
