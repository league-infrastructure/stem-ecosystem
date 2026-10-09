---
id: '001'
title: UpdateLink component, detail-page placement and footer link
status: open
use-cases: [SUC-001, SUC-002]
depends-on: []
github-issue: ''
issue: 84-update-page-and-request-update-links-on-the-site.md
completes_issue: false
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# UpdateLink component, detail-page placement and footer link

## Description

Add src/components/UpdateLink.astro (block 'Is something here wrong or out of date? Request an update ->', base-aware href to /update?type=&slug=). Place on partner, opportunity (type partner, slug of its partner), team, club and place detail pages (Discovery Lab is a place record). Add footer link 'Need to update a listing?' to /update. First run `npm run fetch-data` and confirm the slug/id fields: partner slug (route uses numeric id), team_id, club_id, place_id; record findings in the ticket.

## Acceptance Criteria

- [ ] UpdateLink on all five detail page types with correct type/slug
- [ ] Opportunity pages resolve to partner type/slug; skip link if partner missing
- [ ] Footer link on all pages, base-path aware
- [ ] Slug-source findings recorded in ticket
- [ ] `npm run build` succeeds

## Testing

- **Existing tests to run**: `npm test`, `npm run build`
- **New tests to write**: Add a small node:test for the href builder if extracted to src/lib; otherwise inspect built HTML.
- **Verification command**: `npm test`
