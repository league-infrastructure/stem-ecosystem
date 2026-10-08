---
status: pending
---

# Headless fetch aborts on Wix sites, and one aborted URL drops the whole source

## Description

In the full Docker scrape on 2026-10-07, three `generic_html` sources that
use `fetch_strategy = "headless"` failed outright:

| Source | URL that aborted |
|---|---|
| `xplorstem` | https://www.xplorstem.com/blog/categories/events |
| `climate-science-alliance` | https://www.climatesciencealliance.org/stewardship-pathways/events |
| `techadventurecamp` | https://www.handsontecheducation.com/events/fall-open-house |

Each fails in `HeadlessFetcher.get` (`scraper/partner_scrape/fetch/headless.py`,
the `page.goto(url, timeout=NETWORK_IDLE_TIMEOUT_MS, wait_until="load")`
call) with:

```
playwright._impl._errors.Error: Page.goto: net::ERR_ABORTED at <url>
```

What we know:

- **It is reproducible.** Re-running each source alone
  (`--source <id> --dry-run --no-enrich`) fails the same way every time.
- **The pages are fine.** `curl -L` returns 200 `text/html` for all three
  URLs, with no redirects.
- **All three sites are Wix-hosted** (Wix response headers). The likely
  cause is Wix's client-side routing: the previous Wix page on the shared
  Playwright page starts its own navigation or history change, which aborts
  the `goto` in flight. This is not confirmed yet.
- **It is not Docker-specific, as far as the evidence goes.** These sources
  had 0 to 1 events in the previous yield history too. A host-side comparison
  was not run because headless Chromium is not installed on the dev machine.
- `techadventurecamp` passed a dry run (72 events) earlier the same day,
  then failed in the full run and every rerun after it. The trigger may
  depend on which URL is fetched first or on cache state.

The second problem makes the first much worse. The exception is not handled
per URL: it propagates out of `generic_html.fetch` to
`pipeline._run_one_source`, which drops the entire source. One bad page
costs every event the source would otherwise have yielded.

## Proposed fix

1. **Per-URL isolation:** catch Playwright navigation errors for a single
   URL in the headless fetch path (or in `generic_html`), log a warning, and
   skip that URL. This matches how non-2xx statuses are already handled
   ("returned status 403; skipping"). The source then keeps the rest of its
   URLs.
2. **Wix navigation:** make `goto` robust to aborts. Options:
   - retry once on `ERR_ABORTED`;
   - navigate with `wait_until="commit"` and then wait for load separately;
   - use a fresh page per navigation, or go to `about:blank` first so the
     previous page's scripts cannot interrupt.

   Confirm which one works against the three URLs above.
3. Add a regression test for (1) with a fake page whose `goto` raises.

## References

- Full-run log: the Docker full-scrape run of 2026-10-07 (yield report
  marks all three `[ERROR]`).
- `scraper/partner_scrape/fetch/headless.py` (`HeadlessFetcher.get`)
- `scraper/partner_scrape/pipeline.py` (`_run_one_source`)
- `scraper/partner_scrape/adapters/generic_html.py` (`fetch`)
