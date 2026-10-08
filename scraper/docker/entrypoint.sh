#!/usr/bin/env bash
# Container entrypoint.
#
#   (no args) | cron      run the scheduler (supercronic) on the crontab
#   run-job JOB [args]    run one job now, with preflight and result logging
#   anything else         passed to partner-scrape (legacy one-shot)
#
# CRON_CRONTAB overrides the crontab path (used by tests).
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
crontab="${CRON_CRONTAB:-$here/crontab}"

if [ $# -eq 0 ] || [ "$1" = cron ]; then
  # shellcheck source=load-secrets
  . "$here/load-secrets" || { echo "entrypoint: could not load secrets" >&2; exit 1; }
  echo "entrypoint: starting supercronic with schedule:"
  grep -vE '^[[:space:]]*(#|$)' "$crontab" | sed 's/^/  /'
  exec supercronic "$crontab"
fi

if [ "$1" = run-job ]; then
  shift
  exec "$here/run-job" "$@"
fi

exec partner-scrape "$@"
