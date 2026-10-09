---
id: '007'
title: Real migration, cutover, redeploy (team-lead run)
status: open
use-cases: [SUC-004]
depends-on: ["001", "004", "005", "006"]
github-issue: "77-per-partner-records-in-the-bucket-as-the-source-of-truth.md"
issue: 77-per-partner-records-in-the-bucket-as-the-source-of-truth.md
completes_issue: true
---
<!-- CLASI: Before changing code or making plans, review the SE process in CLAUDE.md -->

# Real migration, cutover, redeploy (team-lead run)

## Description

Team-lead-run: the real-credential cutover. Follow the checklist in sprint.md. Programmers do not run this ticket and never read the real .env.

## Acceptance Criteria

- [ ] Dry-run report reviewed, then real migration run; verify-migration clean (only logo_src differs)
- [ ] `cache/partner_log` copied to `history/partner_log`; the old prefix is left in place (deletion is a follow-up)
- [ ] Site build via fetch-data succeeds and matches the pre-migration build
- [ ] src/data/partners.json and public/images/logos/* removed from git and gitignored
- [ ] New amd64 image built, pushed, and the swarm stack redeployed BEFORE the old image's Monday 03:00 PT scrape; partner_log copy re-run after redeploy if the old image wrote in the interim
- [ ] Follow-up issue filed: delete cache/partner_log after the new image is verified
- [ ] Bucket versioning note recorded for league-network services/spaces

## Implementation Plan

Checklist: see sprint.md (updated to include image build, push and swarm redeploy as part of this ticket). Use scraper/docker/README.md swarm deploy docs from sprint 041. No GitHub push of the sprint and no site deploy.

## Testing

- **Existing tests to run**: `cd scraper && uv run pytest` (and `npm test`/node tests for ticket 006)
- **New tests to write**: as listed in the plan
- **Verification command**: `cd scraper && uv run pytest`
