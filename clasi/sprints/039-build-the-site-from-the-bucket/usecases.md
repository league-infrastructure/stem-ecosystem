---
status: done
---

# Sprint 039 Use Cases

## SUC-001: Anonymous read of published data
- **Actor**: Site build (local or CI), no credentials
- **Preconditions**: Scraper has published to the bucket
- **Main Flow**:
  1. Build issues plain HTTPS GETs against the bucket's `data/` prefix.
  2. Every file the site needs is returned 200.
- **Postconditions**: Data is obtainable without secrets or aws CLI; `cache/` still 403.
- **Acceptance Criteria**:
  - [ ] Anonymous GET of `data/scrape-meta.json`, a partner file and an image returns 200
  - [ ] Anonymous GET of a `cache/` object returns 403
  - [ ] New scraper writes under `data/` are public-read

## SUC-002: Build the site from fresh clone
- **Actor**: Developer / CI
- **Preconditions**: Network access only
- **Main Flow**:
  1. `npm ci && npm run build` (or `npm run dev`).
  2. `pre*` hook fetches data into gitignored `src/data`, `public/data`, `public/images/opportunities`.
  3. Astro builds from them.
- **Postconditions**: `dist/` has same `/data/**` and `/images/opportunities/**` URLs as before.
- **Acceptance Criteria**:
  - [ ] Fetch failure or missing referenced image fails the build loudly
  - [ ] `--local <dir>` populates from a local scraper output
  - [ ] Hand-curated `src/data/partners.json` never overwritten

## SUC-003: Repo no longer carries scraped data
- **Actor**: Maintainer
- **Main Flow**: generated files untracked and ignored; data refreshes produce no diffs.
- **Acceptance Criteria**:
  - [ ] `git ls-files` lists no generated data/image file
  - [ ] README and `/data-access` describe the new flow

## SUC-004: Deploy is manual-only
- **Actor**: Maintainer
- **Main Flow**: the maintainer manually dispatches the Deploy workflow (Actions -> Deploy -> Run workflow, or `gh workflow run deploy.yml`); it fetches the current data from the bucket and builds. Scheduled and scrape-triggered deploys are retired; scraping runs from a container cron (issue 70) and any rebuild cron is a separate, independently controlled job later.
- **Acceptance Criteria**:
  - [ ] deploy.yml triggers on workflow_dispatch only (no push, no schedule)
  - [ ] No GitHub scheduled scrape workflow remains
