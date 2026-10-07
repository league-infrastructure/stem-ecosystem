"""One-time backfill: set ACL public-read on every existing data/ object.

Usage (from scraper/, with the bucket env loaded):
    uv run python scripts/backfill_public_read.py --dry-run
    uv run python scripts/backfill_public_read.py

Idempotent. Touches only the data store (PARTNER_SCRAPE_DATA_DIR); the cache
store is never read or modified.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from partner_scrape.storage import S3Store


def backfill(store: S3Store, dry_run: bool = False) -> int:
    """Set public-read on each key in `store`; return the number of objects."""
    keys = store.list("")
    for key in keys:
        if not dry_run:
            store.client.put_object_acl(
                Bucket=store.bucket, Key=store._key(key), ACL="public-read"
            )
    return len(keys)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="count only")
    args = parser.parse_args(argv)

    from partner_scrape.config import get_data_store

    store: Any = get_data_store()
    if not isinstance(store, S3Store):
        print("data store is not an S3 bucket; nothing to do", file=sys.stderr)
        return 1
    n = backfill(store, dry_run=args.dry_run)
    verb = "would set" if args.dry_run else "set"
    print(f"{verb} public-read on {n} objects under {store.bucket}/{store.prefix}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
