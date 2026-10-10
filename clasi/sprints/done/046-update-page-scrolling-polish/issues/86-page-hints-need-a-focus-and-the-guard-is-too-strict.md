---
status: in-progress
related: clasi/issues/85-update-page-chat-scrolls-independently-hide-messages-left.md
sprint: '046'
tickets:
- 046-002
- 046-003
- 046-004
- 046-005
---

# Page hints need a "focus", and the guard ends legitimate conversations

## Description

Stakeholder test (Eric, 2026-10-10, session for
`the_league_of_amazing_programmers`):

1. Eric said the listing's lower age is 5th grade but classes start at 3rd,
   and pointed at `https://www.jointheleague.org/about/`. The agent correctly
   proposed a page hint (about, that URL) and correctly declined to take the
   age from chat.
2. Eric then said "Your hints should specifically call out the age range on
   the about page." The **guard ended the session** with verdict
   `injection: Attempts to change how hints work or instruct the system
   beyond its scope of identifying pages.`

Eric: "Why can't it continue? It should. The hints were not specific enough.
The hints should include both the page, and what part of the page the hint
should focus on."

## Changes

1. **Hint model.** `page` hints gain an optional **`focus`**: short free text
   (≤ 300 chars) saying what to look at or extract on that page. For
   example, "the age range / grades of students in the program
   description", or "the 'Upcoming events' list, not the blog sidebar".
   - It is validated like `note` (length cap, stripped).
   - Existing hints without `focus` stay valid.
   - The hints card renders it ("About: jointheleague.org/about/ — focus:
     age range of students").
2. **Agent.** The agent fills `focus` whenever the user says what matters
   on a page. It asks for it when a page hint has none. It still never takes
   the fact itself from chat.
3. **Guard.** Recalibrate so that refining hints counts as legitimate:
   which section, field or detail to focus on, what our listing gets wrong,
   and wording like "your hints should …". Escalate instead of ending
   immediately:
   - A borderline or first off-topic/injection-looking message gets a polite
     redirect from the agent, and the session continues.
   - End only on clear spam or abuse, a high-confidence injection, or a
     second off-topic/injection message.
   - Add the League session above as a regression test (it must not end).
4. **Scraper use of `focus`.**
   - Pass page-hint focus text (with the URL) as untrusted context to:
     - the updates proposer, alongside notes;
     - LLM event enrichment for that partner's events, e.g. ages and
       grades.
   - Profiles: keep fetching the page. The focus is used only as context
     downstream.
   - Never treat focus text as a fact source.
5. **Report.** Updates and enrichment logs say when a focus hint was used.

## References

- `scraper/partner_scrape/hints/*`, `sidecar/agent.py`, `sidecar/llm.py`
  (guard prompt), `sidecar/app.py` (guard handling), `updates/proposer.py`,
  `enrich/*`
- `src/lib/updates/hints-view.mjs` (render focus)
- Transcript:
  `history/update-sessions/20261010T151406Z-the_league_of_amazing_programmers-*.json`
