#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.stockradar.production_data import load_and_validate_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a StockRadar production-data manifest before publication."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--max-age-hours",
        type=float,
        default=6.0,
        help="Maximum accepted age for snapshot and required datasets.",
    )
    parser.add_argument(
        "--now",
        help="Optional timezone-aware ISO timestamp for deterministic validation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else None
    if now is not None and now.tzinfo is None:
        raise SystemExit("--now must include a timezone offset")
    if args.max_age_hours <= 0:
        raise SystemExit("--max-age-hours must be positive")

    result = load_and_validate_manifest(
        args.manifest,
        now=now,
        max_age_seconds=int(args.max_age_hours * 3600),
    )
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return 0 if result.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
