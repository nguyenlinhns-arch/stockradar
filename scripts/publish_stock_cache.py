#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.stockradar.cache_publish import (
    CachePublishError,
    load_cache_batch,
    publish_cache_records,
)
from engine.stockradar.production_data import ProductionDataGateError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a StockRadar report batch against an approved production manifest and optionally publish it to the private Supabase cache."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("batch", type=Path)
    parser.add_argument(
        "--max-age-hours",
        type=float,
        default=6.0,
        help="Maximum accepted age of the licensed production manifest.",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish after validation. Requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the environment.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_age_hours <= 0:
        print("--max-age-hours must be positive", file=sys.stderr)
        return 2
    try:
        manifest_ref, records = load_cache_batch(
            args.manifest,
            args.batch,
            max_age_seconds=int(args.max_age_hours * 3600),
        )
        if not args.publish:
            print(f"DRY_RUN_OK records={len(records)} manifest_ref={manifest_ref}")
            return 0
        published = publish_cache_records(records)
        print(f"PUBLISHED records={published} manifest_ref={manifest_ref}")
        return 0
    except (OSError, ValueError, CachePublishError, ProductionDataGateError) as error:
        print(f"Cache publish blocked: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
