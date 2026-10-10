---
id: '002'
title: 'Page-hint focus field: model, agent schema/prompt, hints card'
status: open
use-cases: [SUC-003]
depends-on: []
github-issue: ''
issue: 86-page-hints-need-a-focus-and-the-guard-is-too-strict.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Page-hint focus field: model, agent schema/prompt, hints card

## Description

Add optional `focus` (<=300 chars, stripped, validated like `note`) to page hints in the scraper hints model, the sidecar agent tool schema and prompt (fill focus when user says what matters; ask when missing; never take the fact from chat), and render it in src/lib/updates/hints-view.mjs. Existing hints stay valid.

## Acceptance Criteria

- [ ] focus accepted/validated with length cap; absent focus still valid
- [ ] Agent schema and prompt updated
- [ ] Hints card renders 'focus: ...'
- [ ] Tests in scraper (uv run pytest) and site (npm test) pass

## Testing

- **Verification**: `cd scraper && uv run pytest`; `npm test && npm run build`
