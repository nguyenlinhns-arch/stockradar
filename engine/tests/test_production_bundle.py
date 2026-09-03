import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from engine.stockradar.production_bundle import (
    ProductionBundleError,
    build_manifest_from_descriptor,
    inspect_csv_dataset,
)
from engine.stockradar.production_data import validate_production_manifest


NOW = datetime(2026, 9, 3, 5, 0, tzinfo=timezone.utc)
TIMESTAMP = "2026-09-03T11:45:00+07:00"
SNAPSHOT_ID = "hose-licensed-2026-09-03-114500-vn"


def write_csv(path: Path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def snapshot():
    return {
        "snapshot_id": SNAPSHOT_ID,
        "as_of": TIMESTAMP,
        "source_timestamp": TIMESTAMP,
        "exchange": "HOSE",
        "expected_total": 3,
        "scanned_count": 3,
        "valid_count": 3,
        "excluded_count": 0,
        "stale_count": 0,
        "missing_count": 0,
        "data_grade": "DECISION_GRADE",
        "same_snapshot": True,
        "adjusted_basis_consistent": True,
        "corporate_action_checked": True,
        "source": "LICENSED_PROVIDER",
        "exclusion_log": [],
    }


def descriptor():
    return {
        "contract_version": "1.0",
        "snapshot": snapshot(),
        "rights": {
            "publication_allowed": True,
            "redistribution_allowed": True,
            "source_terms_reviewed": True,
            "evidence_ref": "CONTRACT-001",
        },
        "active_status": {
            "semantics_resolved": True,
            "market_status_checked": True,
        },
        "datasets": {
            "security_master": {"path": "security_master.csv", "ticker_column": "ticker"},
            "ohlcv": {"path": "ohlcv.csv", "ticker_column": "ticker"},
            "fundamentals": {"path": "fundamentals.csv", "ticker_column": "ticker"},
            "corporate_actions": {"path": "corporate_actions.csv"},
            "events": {"path": "events.csv"},
        },
    }


class ProductionBundleTests(unittest.TestCase):
    def populate(self, root: Path):
        tickers = ["MBB", "HPG", "ACB"]
        write_csv(root / "security_master.csv", ["ticker", "name"], [{"ticker": t, "name": t} for t in tickers])
        write_csv(root / "ohlcv.csv", ["ticker", "date", "close"], [{"ticker": t, "date": "2026-09-03", "close": "1"} for t in tickers])
        write_csv(root / "fundamentals.csv", ["ticker", "roe"], [{"ticker": t, "roe": "0.1"} for t in tickers])
        write_csv(root / "corporate_actions.csv", ["event_id"], [])
        write_csv(root / "events.csv", ["event_id"], [])

    def test_licensed_csv_bundle_builds_publishable_manifest(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            manifest = build_manifest_from_descriptor(root, descriptor())
            result = validate_production_manifest(manifest, now=NOW)
            self.assertTrue(result.passed, result.failures)
            self.assertEqual(manifest["datasets"]["security_master"]["covered_tickers"], 3)
            self.assertEqual(manifest["datasets"]["ohlcv"]["row_count"], 3)
            self.assertEqual(len(manifest["datasets"]["ohlcv"]["sha256"]), 64)

    def test_blocked_rights_remain_blocked_after_assembly(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            payload = descriptor()
            payload["rights"]["redistribution_allowed"] = False
            result = validate_production_manifest(
                build_manifest_from_descriptor(root, payload),
                now=NOW,
            )
            self.assertFalse(result.passed)
            self.assertIn("rights_redistribution_allowed_false", result.failures)

    def test_bundle_rejects_path_traversal(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            payload = descriptor()
            payload["datasets"]["events"]["path"] = "../outside.csv"
            with self.assertRaisesRegex(ProductionBundleError, "escapes bundle directory"):
                build_manifest_from_descriptor(root, payload)

    def test_coverage_dataset_requires_ticker_column(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            payload = descriptor()
            del payload["datasets"]["ohlcv"]["ticker_column"]
            with self.assertRaisesRegex(ProductionBundleError, "ticker_column is required"):
                build_manifest_from_descriptor(root, payload)

    def test_invalid_ticker_is_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            write_csv(path, ["ticker"], [{"ticker": "BTC"}, {"ticker": "AB12"}])
            with self.assertRaisesRegex(ProductionBundleError, "invalid ticker"):
                inspect_csv_dataset(path, ticker_column="ticker")

    def test_non_csv_format_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            payload = descriptor()
            payload["datasets"]["events"]["format"] = "parquet"
            with self.assertRaisesRegex(ProductionBundleError, "unsupported dataset format"):
                build_manifest_from_descriptor(root, payload)


if __name__ == "__main__":
    unittest.main()
