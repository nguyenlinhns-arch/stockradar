#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.stockradar.auto_pipeline import compute_top_from_bundle_auto
from engine.stockradar.raw_pipeline import compute_top_from_bundle, write_pipeline_outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute StockRadar Top HOSE from validated raw inputs using StockRadar-only calculations."
    )
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--descriptor", type=Path, required=True)
    parser.add_argument("--research", type=Path, help="Optional StockRadar-owned manual research override. Omit for automatic internal research.")
    parser.add_argument("--valuation", type=Path, help="Optional StockRadar-owned manual valuation override. Omit for automatic internal assumptions.")
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
    if bool(args.research) != bool(args.valuation):
        raise SystemExit("--research and --valuation must be supplied together, or both omitted for automatic StockRadar mode")

    common = dict(
        bundle_dir=args.bundle_dir,
        descriptor_path=args.descriptor,
        now=now,
        max_age_seconds=args.max_age_seconds,
        strongest_limit=args.strongest_limit,
        per_sector_limit=args.per_sector_limit,
    )
    if args.research and args.valuation:
        result = compute_top_from_bundle(
            **common,
            research_path=args.research,
            valuation_path=args.valuation,
        )
        mode = "STOCKRADAR_MANUAL_INTERNAL"
    else:
        result = compute_top_from_bundle_auto(**common)
        mode = "STOCKRADAR_AUTO_INTERNAL"

    write_pipeline_outputs(
        result,
        public_top_path=args.public_output,
        private_computations_path=args.private_output,
    )
    print(
        f"StockRadar Top HOSE computed: {len(result.computations)} valid HOSE tickers; "
        f"{len(result.top_hose.get('strongest', []))} strongest rows; "
        f"benchmark={result.top_hose.get('benchmark_method')}; mode={mode}"
    )


if __name__ == "__main__":
    main()
