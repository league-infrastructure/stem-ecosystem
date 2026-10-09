#!/usr/bin/env bash
# Entrypoint for the updates sidecar image: load the secrets bundle
# (SCRAPER_SECRETS_FILE / SCRAPER_SECRETS_B64; no-op when neither is set),
# then serve the ASGI app with uvicorn. Extra args are passed to uvicorn.
set -uo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=load-secrets
. "$here/load-secrets" || { echo "sidecar-entrypoint: could not load secrets" >&2; exit 1; }

exec uvicorn --factory partner_scrape.sidecar.app:create_app_from_env \
  --host 0.0.0.0 --port "${UPDATES_PORT:-8000}" --no-server-header "$@"
