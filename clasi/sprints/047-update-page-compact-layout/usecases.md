---
status: draft
---

# Sprint 047 Use Cases

## SUC-001: Request an update from a compact page
Parent: UC-update-request

- **Actor**: Listing partner
- **Preconditions**: Partner opens /update
- **Main Flow**:
  1. Page shows a compact title bar and a one-line explainer.
  2. Chat panel and message input are visible without scrolling.
  3. Partner sends messages; transcript grows with content, scrolling internally past max height.
  4. Hints panel sits beside the chat (desktop) or below it (phone).
- **Postconditions**: Partner submitted their update request
- **Acceptance Criteria**:
  - [ ] Input visible on first load at 1280x800 and 390x844
  - [ ] No reserved empty space; transcript content-sized
  - [ ] Accessibility and no-JS fallback preserved
