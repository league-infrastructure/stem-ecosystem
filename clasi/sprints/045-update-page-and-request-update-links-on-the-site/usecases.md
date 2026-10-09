---
status: done
---

# Sprint 045 Use Cases

## SUC-001: Request an update from a detail page
Parent: issue 84

- **Actor**: Partner staff or visitor
- **Preconditions**: Viewing a partner, opportunity, team, club or place page
- **Main Flow**:
  1. Sees "Is something here wrong or out of date? Request an update".
  2. Follows the link to `/update?type=<type>&slug=<slug>`.
- **Postconditions**: /update opens bound to that listing (opportunities resolve to their partner)
- **Acceptance Criteria**:
  - [ ] All five detail page types carry the link with correct type/slug
  - [ ] Discovery Lab (a place record) is covered by place pages

## SUC-002: Reach the update page generally
Parent: issue 84

- **Actor**: Visitor
- **Main Flow**: Clicks "Need to update a listing?" in the footer; picks a listing on `/update`.
- **Postconditions**: Session starts for the chosen listing
- **Acceptance Criteria**:
  - [ ] Footer link on every page
  - [ ] Picker lists partners/places/teams/clubs searchable by name

## SUC-003: Describe a problem to the assistant and see proposed hints
Parent: issue 84

- **Actor**: Partner staff
- **Main Flow**: Reads explainer, chats; hints card re-renders after each turn in readable form.
- **Acceptance Criteria**:
  - [ ] Greeting shown on start; each reply updates the card (e.g. "Events: visitcmod.org/calendar", "Skip: ...")
  - [ ] Notices (rejected hints) displayed

## SUC-004: Confirm hints
Parent: issue 84

- **Actor**: Partner staff
- **Main Flow**: Presses Confirm; sees saved summary and "takes effect after the next scheduled scrape".
- **Acceptance Criteria**:
  - [ ] saved:false shows "no changes to save"

## SUC-005: Handle failures and non-JS users gracefully
Parent: issue 84

- **Actor**: Any visitor
- **Main Flow**: Rate limit, spend cap, expiry, ended session, upstream failure, or no JavaScript.
- **Acceptance Criteria**:
  - [ ] Each error code gives a plain message plus the email fallback; guard/turn-cap end shows stop message
  - [ ] No-JS shows explainer and partners@sdstemecosystem.org
  - [ ] Keyboard and screen-reader usable; panels stack on phones
