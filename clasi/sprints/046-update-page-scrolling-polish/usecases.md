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

## SUC-003: Hint carries a focus
Parent: UC-XXX

- **Actor**: Visitor refining a page hint
- **Main Flow**: Visitor says what matters on a page; agent records it as `focus` (<=300 chars); hints card shows "focus: ...".
- **Acceptance Criteria**:
  - [ ] `focus` optional, validated like `note`; old hints stay valid
  - [ ] Agent fills/asks for focus, never takes the fact from chat
  - [ ] Hints card renders focus

## SUC-004: Guard allows hint refinement
Parent: UC-XXX

- **Actor**: Visitor
- **Main Flow**: "Your hints should call out the age range on the about page" is accepted. Borderline/first off-topic message gets a polite redirect; session ends only on clear abuse, high-confidence injection, or a second offense.
- **Acceptance Criteria**:
  - [ ] League transcript is a regression test and does not end

## SUC-005: Scraper uses focus as context
Parent: UC-XXX

- **Actor**: Scraper (updates proposer, event enrichment)
- **Main Flow**: Focus text plus URL passed as untrusted context; page still fetched; logs say a focus hint was used.
- **Acceptance Criteria**:
  - [ ] Focus never treated as a fact source
  - [ ] Logs report focus use
