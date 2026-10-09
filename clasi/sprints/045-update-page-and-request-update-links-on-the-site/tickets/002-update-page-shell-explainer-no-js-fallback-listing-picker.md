---
id: '002'
title: '/update page shell: explainer, no-JS fallback, listing picker'
status: open
use-cases: [SUC-002, SUC-005]
depends-on: ["001"]
github-issue: ''
issue: 84-update-page-and-request-update-links-on-the-site.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# /update page shell: explainer, no-JS fallback, listing picker

## Description

Create src/pages/update.astro using BaseLayout: explainer (we only publish what is on your own website; tell the assistant where to find info and what is wrong; next scheduled scrape picks it up), email fallback partners@sdstemecosystem.org, noscript message, listing picker (searchable select/list built from inline JSON of partners/places/teams/clubs) shown when no type/slug params, and empty chat/hints containers with data attributes incl. PUBLIC_UPDATES_API_URL.

## Acceptance Criteria

- [ ] Explainer and email visible without JS
- [ ] Picker lists listings and navigates to /update?type=&slug=
- [ ] Containers carry API base URL from env (default https://updates.jtlapp.net)
- [ ] Two-panel layout, stacks under 768px
- [ ] Headings/landmarks and labels accessible

## Testing

- **Existing tests to run**: `npm test`, `npm run build`
- **New tests to write**: Build and inspect output HTML.
- **Verification command**: `npm test`
