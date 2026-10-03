#!/usr/bin/env bash
# Populate the site's data files from the scraper's published data.
#
# The scraper (scraper/) publishes to the DigitalOcean Spaces bucket; this
# script pulls that output into src/data and public/data.
#
# Usage:
#   scripts/fetch-data.sh                     # pull from the Spaces bucket (default)
#   scripts/fetch-data.sh --bucket            # same, explicitly
#   scripts/fetch-data.sh --local <data-dir>  # copy from a local data directory,
#                                             # e.g. scraper/data when the scraper ran
#                                             # with PARTNER_SCRAPE_DATA_DIR=./data
#
# Bucket mode syncs s3://jtl-stem-ecosystem-scrape/data/ (DigitalOcean Spaces,
# sfo3) into a temp directory with the aws CLI, then runs the same explicit
# copy list and image check as local mode. Credentials come from the
# environment: DO_SPACES_ACCESS_KEY / DO_SPACES_SECRET_KEY (mapped to the
# AWS_* variables the CLI reads), or pre-set AWS_ACCESS_KEY_ID /
# AWS_SECRET_ACCESS_KEY. Bucket data/ also holds SCHEMA.md; it is never copied.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUCKET_URL="s3://jtl-stem-ecosystem-scrape/data/"
SPACES_ENDPOINT="https://sfo3.digitaloceanspaces.com"

if [ "${1:-}" = "--local" ]; then
  DATA="${2:-}"
  if [ -z "$DATA" ] || [ ! -d "$DATA" ]; then
    echo "error: --local needs an existing data directory (got: ${DATA:-nothing})." >&2
    exit 1
  fi
elif [ -z "${1:-}" ] || [ "${1:-}" = "--bucket" ]; then
  if [ -n "${DO_SPACES_ACCESS_KEY:-}" ] && [ -n "${DO_SPACES_SECRET_KEY:-}" ]; then
    export AWS_ACCESS_KEY_ID="$DO_SPACES_ACCESS_KEY"
    export AWS_SECRET_ACCESS_KEY="$DO_SPACES_SECRET_KEY"
  fi
  if [ -z "${AWS_ACCESS_KEY_ID:-}" ] || [ -z "${AWS_SECRET_ACCESS_KEY:-}" ]; then
    echo "error: bucket mode needs credentials in the environment:" >&2
    echo "       DO_SPACES_ACCESS_KEY and DO_SPACES_SECRET_KEY, or" >&2
    echo "       AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY." >&2
    exit 1
  fi
  if ! command -v aws >/dev/null 2>&1; then
    echo "error: the aws CLI is required for bucket mode." >&2
    exit 1
  fi
  DATA="$(mktemp -d)"
  trap 'rm -rf "$DATA"' EXIT
  export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
  echo "syncing $BUCKET_URL -> temp dir"
  aws s3 sync "$BUCKET_URL" "$DATA/" --endpoint-url "$SPACES_ENDPOINT" --only-show-errors
else
  echo "error: unknown argument: $1 (use --bucket or --local <data-dir>)" >&2
  exit 1
fi

# Copy an explicit list, never a glob. `data/partners.json` is the GENERATED
# roster envelope and belongs only in public/data/; `src/data/partners.json`
# is the hand-curated array this repo authors and the pipeline only reads.
# They share a basename and have different shapes, so a glob would overwrite
# the one file here that cannot be regenerated upstream.
SRC_ONLY=(opportunities.json scrape-meta.json ads.json yield-history.json)
BOTH=(teams.json places.json clubs.json)

mkdir -p "$ROOT/src/data" "$ROOT/public/data" "$ROOT/public/images/opportunities"

for f in "${SRC_ONLY[@]}"; do
  cp "$DATA/$f" "$ROOT/src/data/$f"
done

for f in "${BOTH[@]}"; do
  cp "$DATA/$f" "$ROOT/src/data/$f"
  cp "$DATA/$f" "$ROOT/public/data/$f"
done

cp "$DATA/partners.json" "$ROOT/public/data/partners.json"

# --delete on both: this repo mirrors what the pipeline publishes rather
# than accumulating. Without it, a partner renamed upstream leaves its old
# slug directory behind forever, and dropped images pile up unreferenced.
# The integrity check below is what makes deleting safe.
rsync -a --delete "$DATA/partners/" "$ROOT/public/data/partners/"
rsync -a --delete "$DATA/images/opportunities/" "$ROOT/public/images/opportunities/"

# Referential integrity: every image the data references must be present.
# A missing image is a silently broken page, so fail the build instead.
python3 - "$ROOT" <<'PY'
import json, os, sys, glob
root = sys.argv[1]
img = os.path.join(root, "public/images/opportunities")
have = set(os.listdir(img)) if os.path.isdir(img) else set()

refs = set()
opp = json.load(open(os.path.join(root, "src/data/opportunities.json")))
refs |= {os.path.basename(o["image_src"]) for o in opp if o.get("image_src")}
for f in glob.glob(os.path.join(root, "public/data/partners/*/*.json")):
    for e in json.load(open(f)).get("events", []):
        if e.get("image_src"):
            refs.add(os.path.basename(e["image_src"]))

missing = sorted(refs - have)
if missing:
    print(f"error: {len(missing)} referenced images are missing, e.g. {missing[:5]}", file=sys.stderr)
    sys.exit(1)

print(f"fetched: {len(opp)} opportunities, {len(have)} images, {len(refs)} referenced, 0 missing")
PY
