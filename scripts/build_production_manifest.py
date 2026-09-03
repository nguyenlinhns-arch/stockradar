#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.stockradar.production_bundle import (
    ProductionBundleError,
    build_manifest_from_descriptor,
    load_descriptor,
    write_manifest,
)
from engine.stockradar.production_data import validate_production_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assemble and validate a StockRadar production manifest from a licensed CSV bundle."
    )
    parser.add_argument("bundle_dir", type=Path)
    parser.add_argument("descriptor", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--max-age-hours",
        type=float,
        default=6.0,
        help="Freshness threshold used for validation after assembly.",
    )
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="Write the manifest even if publication gates remain blocked. Useful for rights review/reconciliation only.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_age_hours <= 0:
        raise SystemExit("--max-age-hours must be positive")
    try:
        descriptor = load_descriptor(args.descriptor)
        manifest = build_manifest_from_descriptor(args.bundle_dir, descriptor)
        result = validate_production_manifest(
            manifest,
            max_age_seconds=int(args.max_age_hours * 3600),
        )
        if not result.passed and not args.allow_blocked:
            print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2), file=sys.stderr)
            return 2
        write_manifest(args.output, manifest)
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0 if result.passed else 2
    except (OSError, json.JSONDecodeError, ProductionBundleError, ValueError) as error:
        print(f"Production bundle assembly failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
