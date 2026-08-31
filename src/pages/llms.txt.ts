import type { APIRoute } from 'astro';

// Served at /llms.txt. Generated rather than kept as a static file in
// public/ so the absolute URLs below derive from the build-time origin
// (`import.meta.env.SITE` + `BASE_URL`) instead of being hardcoded. This
// page tree is built for several origins from one codebase -- production
// Pages, the beta's build-time checkout under /partner-scrape, and the
// Docker beta -- and a static file could only ever name one of them.
//
// See src/pages/for-agents.astro for why the www domain must not be
// hardcoded here: it currently serves a frameset, a registrar/DNS-level
// misconfiguration tracked outside this codebase.
export const GET: APIRoute = () => {
  const base = import.meta.env.BASE_URL.replace(/\/+$/, '');
  const origin = `${import.meta.env.SITE.replace(/\/+$/, '')}${base}`;

  const body = `# SD STEM Ecosystem

> A directory of STEM learning opportunities (camps, out-of-school programs,
> work-based learning) run by San Diego-area partner organizations. The
> underlying data is published as plain, statically-served JSON: no auth, no
> API key, no rate limit imposed by us.

## Data

- [partners.json](${origin}/data/partners.json): Partner roster envelope (\`generated_at\`, \`partner_count\`, \`partners[]\`). Each partner entry has a \`slug\`, \`events_url\`, and \`past_events_url\` (both relative to \`.../data/\`).
- Per-partner events, one pair per partner listed in \`partners.json\`: \`${origin}/data/partners/<slug>/events.json\` and \`${origin}/data/partners/<slug>/past-events.json\`. \`current\`/\`past\` is a true partition — undated records land in \`past-events.json\`, nothing is dropped.
- [teams.json](${origin}/data/teams.json): FIRST/VEX robotics teams directory for San Diego County: id, league, grade band, organization, location w/ precision, status, sponsors. Self-describing \`meta\` envelope (\`generated\`, \`total\`, \`by_league\`, \`by_location_precision\`).

## Documentation

- [How to Consume Our Data](${origin}/data-access/): Full file shapes, the complete event field schema, the reconstruction contract, and a worked example of both files.
- [For Agents](${origin}/for-agents/): Terse, link-dense landing page for an LLM/agent — the same data URLs above, self-sufficient if reached directly.

## Publishing

- [Publish Your Events](${origin}/publish-events/): How a partner organization can publish events so this scraper ingests them well — several standard methods, ordered easiest-adoption-first.
`;

  return new Response(body, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
};
