#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.stockradar.raw_pipeline import compute_top_from_bundle, write_pipeline_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute StockRadar Top HOSE strictly from validated raw inputs and internal StockRadar methodology."
    )
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--descriptor", type=Path, required=True)
    parser.add_argument("--research", type=Path, required=True)
    parser.add_argument("--valuation", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    parser.add_argument("--private-output", type=Path)
    parser.add_argument("--max-age-seconds", type=int, default=21_600)
    parser.add_argument("--strongest-limit", type=int, default=30)
    parser.add_argument("--per-sector-limit", type=int, default=3)
    parser.add_argument(
        "--now",
        help="Optional timezone-aware ISO-8601 timestamp used for deterministic validation/tests.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else None
    if now is not None and now.tzinfo is None:
        raise SystemExit("--now must include a timezone offset")
    result = compute_top_from_bundle(
        bundle_dir=args.bundle_dir,
        descriptor_path=args.descriptor,
        research_path=args.research,
        valuation_path=args.valuation,
        now=now,
        max_age_seconds=args.max_age_seconds,
        strongest_limit=args.strongest_limit,
        per_sector_limit=args.per_sector_limit,
    )
    write_pipeline_outputs(
        result,
        public_top_path=args.public_output,
        private_computations_path=args.private_output,
    )
    print(
        f"StockRadar Top HOSE computed: {len(result.computations)} valid HOSE tickers; "
        f"{len(result.top_hose.get('strongest', []))} strongest rows; "
        f"benchmark={result.top_hose.get('benchmark_method')}"
    )


if __name__ == "__main__":
    main()
