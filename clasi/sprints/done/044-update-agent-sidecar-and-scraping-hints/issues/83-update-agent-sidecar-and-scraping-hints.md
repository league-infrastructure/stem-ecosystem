---
status: in-progress
sprint: '044'
tickets:
- 044-001
- 044-002
- 044-003
- 044-004
- 044-005
- 044-006
- 044-007
- 044-008
---

# Update-agent sidecar: a chat that produces scraping hints

## Description

Stakeholder design (Eric, 2026-10-09). Partners (or anyone) who want a
listing changed talk to an AI agent. The agent **does not take facts from
the conversation**: everything we publish must come from the partner's own
website. What the conversation produces is **scraping hints**, which tell
the scraper where to look or what to skip on that website. Hints apply
automatically and take effect at the next scheduled scrape. There is an
email fallback for anything else.

This issue covers the backend: the sidecar service, the hint model and
storage, and the scraper using the hints. Issue 84 covers the website
pages.

## Decisions (Eric, 2026-10-09)

- **Apply automatically:** hints apply with no human review. Every change
  is versioned and logged.
- **Anyone can submit.** There is no identity verification.
- **Hints are private,** not in the public partner record. The update link
  and page are public.
- **Timing:** changes show up after the **next scheduled scrape**. There is
  no on-demand re-scrape.
- **Models:**
  - **guard:** a cheap model screens every user message. Haiku
    (`claude-haiku-4-5-20251001`) by default, with an OpenRouter cheap model
    as an option.
  - **agent:** a more capable model converses and edits the hints. Sonnet
    (`claude-sonnet-5-5`).
- **Hosting:** the sidecar is a new service in this repo, deployed to the
  League swarm like the scraper, behind Caddy with its own `*.jtlapp.net`
  hostname (e.g. `updates.jtlapp.net`).

## Sidecar service

- A small HTTP API (Python, sharing the `partner_scrape` package for
  records, stores and the writer). The site's JavaScript calls it.
  - **Start a session** for `{type, slug}`. type is partner, opportunity,
    team, club or place; non-partner entities resolve to their partner or
    entity record. Returns the session id and the current hints.
  - **Send a message.** It returns the agent reply plus the current
    **proposed hints**, so the page can show them live.
  - **Confirm** the proposed hints, which writes them.
  - **Get** the session state.
- **Guard.** Each user message first goes to the guard model, which
  classifies it as a legitimate update request about this listing, or
  off-topic, spam, abuse, prompt injection or an attempt to supply
  content. If it isn't legitimate, the session ends with a polite message
  and the email fallback, and a short reason is logged.
- **Agent.**
  - It explains the rule ("we only publish what's on your website; tell us
    where it is").
  - It edits the proposed hints only through a structured tool, so the page
    always shows exactly what would be saved.
  - It is given the entity's current record, the latest profile snapshot
    and recent scraped events, so it can say what we currently see.
- **Abuse and cost controls.** CORS is restricted to the site origin, but
  that is not security on its own, so there are also:
  - per-IP and per-listing rate limits;
  - a cap on turns per session;
  - a maximum message length;
  - a **daily spend cap** across all sessions (the sidecar refuses new
    sessions once it is reached);
  - optional Cloudflare Turnstile, off unless keys are configured.
- **Secrets:** a swarm secret holding the Anthropic key (and optionally an
  OpenRouter key), using the same base64-bundle pattern as the scraper.
- **Transcripts:** stored privately at
  `history/update-sessions/<UTC ts>-<slug>-<id>.json`, with messages, guard
  verdicts, the hints proposed and confirmed, IP hash and costs.

## Hint model and storage

- Hints are stored privately per entity at `hints/<slug>.json` in the
  bucket (no public-read). They are versioned through an archiving writer
  like PartnerWriter:
  - the old version goes to `history/hints/<slug>/<ts>.json`;
  - a line is appended to `history/hints/changes.jsonl` with actor
    `update-agent:<session>`.
- **Hint kinds** (validated server-side):
  - `page`: `{role: about|contact|events|camps|programs|other, url}`. The
    URL **must be on the partner's own domain(s)**.
  - `exclude`: `{match: title substring/regex, reason}`, for events or
    items to skip, e.g. "Member's Only Hours".
  - `note`: free text guidance passed to LLM extraction and enrichment for
    this partner, e.g. "ages are on the /visit page".
  - `identity`: `{name?, website?}`. This says that the site now shows a
    new name or domain. A new domain is accepted only if the record's
    website actually redirects there (verified at write time). It is a
    pointer for the updates job, never a direct record edit.
- **Safety property:** a hint can never supply a published fact. It only
  steers where we look and what we skip. Off-domain URLs and unverifiable
  domain moves are rejected, and the agent explains why and offers the
  email fallback.

## The scraper uses the hints

- `profiles`: `page` hints for about, contact or other override
  discovery.
- `updates`:
  - `note`/`identity` hints are passed to the Haiku proposer as context;
  - an `identity` hint counts as rebrand evidence for name/description
    only together with the existing redirect or title evidence;
  - it never bypasses policy.
- **Event scrape:**
  - `exclude` hints drop matching events for that partner at normalize
    time (reported in the run log);
  - `page` hints with role events, camps or programs are surfaced in the
    updates report as "add or adjust source" items, plus an automatic
    generic source for the partner when it has none. The planner decides
    the scope.
- Weekly `updates` and run logs report which hints were used.

## Out of scope

Website pages and links (issue 84), on-demand re-scrape, identity
verification, OpenRouter beyond an optional guard backend.
