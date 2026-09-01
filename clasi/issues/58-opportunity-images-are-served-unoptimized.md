---
status: pending
---

# Opportunity images are served as unoptimized originals

## Description

The site serves self-hosted event images at whatever size the partner
published them, with no resizing or recompression. The largest is
5184x3456 — a raw camera original — and production currently serves it at
**5.2 MB over the wire** for what renders as a card thumbnail. Verified
live, not inferred:

```
$ curl -sLo /dev/null -w '%{size_download}' \
    .../images/opportunities/8fe151929e7394b0.jpg
5210432
```

The distribution across all 631 images:

| | |
|---|---|
| total | 423 MB |
| mean / median | 655 KB / 303 KB |
| p90 | 1.7 MB |
| largest | 5.0 MB (5184x3456) |
| files over 1 MB | 147, totalling 284 MB — **67% of all bytes** |

`OpportunityCard.astro` renders a plain `<img>` with a path from
`resolveImage()`. There is no `astro:assets` usage, no `<Image>` component,
and no `sharp` in the dependency tree, so nothing resizes at build time
either.

Two separate costs. For visitors it is a straightforward performance
defect — the opportunities index renders many cards, and a phone on cellular
pays multiple megabytes for images displayed a few hundred pixels wide. For
this repo it is 405 MB of tracked content, which is most of a 428 MB `.git`.

**This reframes the hosting question in issue 57.** That issue treats
405 MB as a fixed quantity to be relocated. It is not fixed: 67% of it is
oversized originals. Resizing to a sane web maximum would very likely take
the whole set to well under 50 MB, at which point "where do the images live"
stops being a difficult question. Worth fixing before deciding hosting, not
after.

## Proposed fix

**Resize on fetch — accepted upstream and in progress.** partner-scrape is
adding resizing to `EventImageDownloader`, applying to newly downloaded
images only. That is the better half of the fix: it shrinks the stored
artifact for everyone and means less to transfer however the data ends up
being published.

**The existing 631 stay oversized, and that remains this issue's problem.**
Re-encoding them is explicitly out of the upstream sprint's scope. Until
someone migrates them, production keeps serving the 5.2 MB original and the
other 146 files over 1 MB. So the visitor-facing defect is not fixed by the
upstream change — only prevented from growing.

The migration is not a local edit. The filenames are content-addressed
(16 hex chars), so re-encoding changes every filename, which changes every
`image_src` in `opportunities.json`. Doing it safely means re-encoding and
rewriting the references in one coordinated publish, which is a pipeline
operation rather than something to do by hand in this repo. Worth weighing
against simply letting the oversized set age out as events expire and get
replaced by resized ones — slower, but free and zero-risk.

On the site side, once images arrive at a sane size, consider Astro's
`astro:assets` for responsive `srcset` on the card grid. Lower priority —
the source-size fix captures nearly all of the benefit and this only helps
further.

Do not re-fetch or rewrite existing images purely to shrink them without
checking the filenames first. They are content-addressed (16 hex chars), so
changing bytes changes the filename, which changes every `image_src` in
`opportunities.json`. A resize pass is a data migration, not a local edit.

## References

`src/components/OpportunityCard.astro` (`resolveImage()`, the raw `<img>`);
`src/lib/helpers.ts`. Upstream: partner-scrape's `EventImageDownloader` in
`pipeline.py`, which fetches and quality-gates images but does not resize.
Related: issue 57, whose hosting decision this changes the premise of.
