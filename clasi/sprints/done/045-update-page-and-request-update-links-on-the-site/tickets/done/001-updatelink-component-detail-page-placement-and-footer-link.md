---
id: '001'
title: UpdateLink component, detail-page placement and footer link
status: done
use-cases:
- SUC-001
- SUC-002
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

- [x] UpdateLink on all five detail page types with correct type/slug
- [x] Opportunity pages resolve to partner type/slug; skip link if partner missing
- [x] Footer link on all pages, base-path aware
- [x] Slug-source findings recorded in ticket
- [x] `npm run build` succeeds

## Testing

- **Existing tests to run**: `npm test`, `npm run build`
- **New tests to write**: Add a small node:test for the href builder if extracted to src/lib; otherwise inspect built HTML.
- **Verification command**: `npm test`

## Slug-source findings

Verified against fetched data (`npm run fetch-data`) and `scraper/partner_scrape/sidecar/resolver.py`:

- partner: `slug` field in site `partners.json` (211/211 present and unique); route param is numeric `id`. Matches the bucket's `partners/<slug>/partner.json`.
- opportunity: has own `slug`, but the update link uses the partner (type `partner`), found via `partner_id` -> partners `id` (same lookup as the sidecar's `_partner_slug_for_id`). 15 of 356 opportunities have a `partner_id` with no partner record; they get no link.
- team: `team_id` (route slug); club: `club_id`; place: `place_id` (route slugs are already these ids). Discovery Lab is a place record.
- Note: bucket `partners.json` is `{partners: [...]}` (what the resolver reads); the site's `src/data/partners.json` is a bare list. Both carry `id` and `slug`.

Link format: `<base>/update?type=<partner|team|club|place>&slug=<slug>` (built by `src/lib/updates/link.mjs`); footer links to `<base>/update`.
