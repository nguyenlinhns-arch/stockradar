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

from engine.stockradar.licensed_intake import (
    LicensedIntakeError,
    load_json_object,
    prepare_licensed_intake,
    write_private_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a licensed raw-data provider package before it enters the StockRadar production-data contract. "
            "This command never enables publication, API gates, or alert delivery."
        )
    )
    parser.add_argument("staging_dir", type=Path, help="Private directory containing raw provider CSV files.")
    parser.add_argument("package", type=Path, help="Provider-neutral package metadata JSON.")
    parser.add_argument("rights", type=Path, help="License/rights evidence metadata JSON; no credentials allowed.")
    parser.add_argument("descriptor_output", type=Path, help="Private output descriptor for build_production_manifest.py.")
    parser.add_argument("report_output", type=Path, help="Private, non-secret intake report JSON.")
    parser.add_argument(
        "--max-age-hours",
        type=float,
        default=6.0,
        help="Freshness threshold used to report whether the resulting bundle is publication-ready.",
    )
    parser.add_argument(
        "--now",
        help="Optional timezone-aware ISO timestamp for deterministic validation/tests.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_age_hours <= 0:
        raise SystemExit("--max-age-hours must be positive")
    now = datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now else None
    if now is not None and now.tzinfo is None:
        raise SystemExit("--now must include a timezone offset")

    try:
        package = load_json_object(args.package)
        rights = load_json_object(args.rights)
        descriptor, result, report = prepare_licensed_intake(
            args.staging_dir,
            package,
            rights,
            repo_root=ROOT,
            now=now,
            max_age_seconds=int(args.max_age_hours * 3600),
        )
        write_private_json(args.descriptor_output, descriptor, repo_root=ROOT)
        write_private_json(args.report_output, report, repo_root=ROOT)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        # Intake acceptance and publication readiness are intentionally separate.
        # A non-ready snapshot is still useful for reconciliation, but cannot unlock publication.
        return 0 if result.accepted else 2
    except (OSError, json.JSONDecodeError, LicensedIntakeError, ValueError) as error:
        failure = {
            "intake_schema_version": "1.0",
            "accepted": False,
            "publication_ready": False,
            "failures": [str(error)],
            "gate_mutation_performed": False,
            "credentials_persisted": False,
        }
        try:
            write_private_json(args.report_output, failure, repo_root=ROOT)
        except Exception:
            pass
        print(json.dumps(failure, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
