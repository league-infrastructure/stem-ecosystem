#!/usr/bin/env bash
# Populate this repo's data files from partner-scrape's published `data/`.
#
# The scraper no longer writes into this checkout; it publishes to its own
# `data/` directory and this repo pulls. See clasi/issues/57.
#
# Usage:
#   scripts/fetch-data.sh <path-to-partner-scrape-checkout>
#   scripts/fetch-data.sh              # defaults to ../partner-scrape
#
# CI checks partner-scrape out to a temp path and passes it explicitly.

set -euo pipefail

SRC_REPO="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/../partner-scrape}"
DATA="$SRC_REPO/data"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -d "$DATA" ]; then
  echo "error: no data/ directory at $DATA" >&2
  echo "       pass the partner-scrape checkout as the first argument." >&2
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
