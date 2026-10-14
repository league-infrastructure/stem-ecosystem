---
status: draft
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Sprint 051 Use Cases

## SUC-001: Wheel smoke test runs offline
Parent: n/a

- **Actor**: CI
- **Preconditions**: Built wheel, no credentials
- **Main Flow**:
  1. Install wheel in fresh venv with all stores local
  2. Run dry run against a seeded one-partner roster
- **Postconditions**: Job passes, nothing written
- **Acceptance Criteria**:
  - [ ] Passes without credentials or network
