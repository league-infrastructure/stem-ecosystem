"""Run-log capture: upload a job's output and index it in the bucket.

`docker/run-job` tees a job's stdout+stderr to a temp file and, on exit,
calls ``partner-scrape logs upload`` which lands here. Each run produces

* ``logs/<type>/<UTC ts>-<job>.log`` -- the full output (secret values
  redacted), and
* one line appended to ``logs/index.jsonl`` -- job, start, end, exit code,
  duration, log path, and headline counts when parseable.

The logs store is always **private** (never ``public_read``): logs may carry
internal detail and must not be world-readable like ``data/``.

Index append is read-modify-write (read the object, add a line, write it
back). That is not safe for concurrent writers, but jobs are scheduled days
apart and run serially, so a lost update would need two jobs to finish within
the same second; accepted and documented.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from partner_scrape.storage import Store

INDEX_KEY = "index.jsonl"

#: Job -> log type directory. ``profiles``/``updates`` are reserved.
LOG_TYPES = {"scrape": "scrape", "teams": "teams", "directory": "directory"}

_SECRET_NAME = re.compile(r"KEY|SECRET|TOKEN|PASSWORD|BUNDLE|B64", re.I)
_MIN_SECRET_LEN = 4


def log_type(job: str) -> str:
    return LOG_TYPES.get(job, job)


def redact(text: str, environ: dict[str, str] | None = None) -> str:
    """Replace values of secret-looking environment variables with ***."""
    env = os.environ if environ is None else environ
    values = sorted(
        {v for k, v in env.items() if _SECRET_NAME.search(k) and len(v) >= _MIN_SECRET_LEN},
        key=len,
        reverse=True,
    )
    for v in values:
        text = text.replace(v, "***")
    return text


def parse_counts(text: str) -> dict[str, int]:
    """Best-effort headline counts from job output (only keys that parse)."""
    counts: dict[str, int] = {}
    m = re.search(r"partner-scrape[^:\n]*: wrote (\d+) ", text)
    if m:
        counts["events_written"] = int(m.group(1))
    m = re.search(r"(\d+) sources?\b", text)
    if m:
        counts["sources"] = int(m.group(1))
    counts["errors"] = len(
        re.findall(r"^(?:ERROR\b|Traceback \(most recent call last\))", text, re.M)
    )
    return counts


def append_index(store: Store, entry: dict[str, Any]) -> None:
    """Append one JSON line to ``index.jsonl`` (read-modify-write; see module doc)."""
    existing = store.read_text(INDEX_KEY) or ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    store.write_text(
        INDEX_KEY, existing + json.dumps(entry, sort_keys=True) + "\n", "application/x-ndjson"
    )


def upload_log(
    store: Store,
    *,
    job: str,
    log_file: Path,
    start: str,
    end: str,
    exit_code: int,
    duration: int,
) -> str:
    """Upload the log and append its index line; return the log key."""
    text = redact(Path(log_file).read_text(encoding="utf-8", errors="replace"))
    stamp = re.sub(r"[^0-9A-Za-z]", "", start) or "unknown"
    key = f"{log_type(job)}/{stamp}-{job}.log"
    store.write_text(key, text, "text/plain; charset=utf-8")
    entry: dict[str, Any] = {
        "job": job,
        "start": start,
        "end": end,
        "exit_code": exit_code,
        "duration_s": duration,
        "log": f"logs/{key}",
    }
    entry.update(parse_counts(text))
    append_index(store, entry)
    return key
