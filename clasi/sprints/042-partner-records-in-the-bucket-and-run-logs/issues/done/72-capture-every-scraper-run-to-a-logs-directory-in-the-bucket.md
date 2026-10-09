---
status: done
sprint: '042'
tickets:
- 042-001
---

# Capture every scraper run to a logs directory in the bucket

## Description

Stakeholder direction (Eric, 2026-10-08): every scrape process should
capture its output into a `logs` directory. The team lead (an agent) is
the main reader and interprets them, so the layout can be whatever is most
useful to read.

Today the swarm container (`stem-ecosystem_scraper`, see
`scraper/docker/README.md`) writes only to `docker logs`. That output is
lost when the task is replaced, and it can only be read with swarm access.

## Proposal

- Each `run-job` invocation (scheduled or manual) tees its full output
  (stdout and stderr) to a file. When the job ends, the file is uploaded
  to the bucket at `s3://jtl-stem-ecosystem-scrape/logs/<type>/<UTC timestamp>-<job>.log`.
- Types:
  - `scrape`, `teams`, `directory` (the existing jobs);
  - `profiles` (the weekly profile-page fetch, issue 74);
  - `updates` (the post-scrape partner-record checks and changes,
    issue 75).
- The START/SUCCESS/FAILURE summary line is still printed to
  `docker logs`.
  - Also keep a small rolling index, `logs/index.jsonl`: one line per run
    with job, start, end, exit code, duration, log path, and headline
    counts (sources, events written, errors).
  - With it, the reader can see "when did each job last run, and did it
    work" without opening every log.
- `logs/` stays **private**: no public-read ACL, like `cache/`.
- Retention: keep everything for now (they are small). Revisit if the
  prefix grows.
- No secret values ever go in a log. The jobs already never print them;
  add a test asserting the upload path does not either.

## Acceptance

- A manual `run-job directory` in the container produces a log object
  under `logs/directory/` and an index line.
- A failed job still uploads its log, with the failure recorded in the
  index.
- If the log upload itself fails, it doesn't change the job's exit code.
  It is reported on stdout.

## References

- `scraper/docker/run-job`, `scraper/docker/README.md`
- `scraper/partner_scrape/storage.py` (S3Store; data-store `public_read`
  must not apply to `logs/`)
