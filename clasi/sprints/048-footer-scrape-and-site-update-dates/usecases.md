---
status: done
---

# Sprint 048 Use Cases

## SUC-001: See data and site freshness in the footer
Parent: none

- **Actor**: Site visitor
- **Preconditions**: Site built with scrape-meta.json present
- **Main Flow**:
  1. Visitor opens any page.
  2. Footer shows "Events scraped <date>" and "Site updated <date>".
- **Postconditions**: Visitor knows data age and deploy age.
- **Acceptance Criteria**:
  - [ ] Scrape date from scrape-meta.json last_updated, Pacific time
  - [ ] Site date from build-time timestamp, Pacific time
  - [ ] `<time datetime>` with full timestamp in title
