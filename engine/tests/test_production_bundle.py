import csv
from datetime import datetime, timezone
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
        "source": "LICENSED_PROVIDER_RAW_INPUT",
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
        "compliance": {
            "review_completed": True,
            "public_recommendation_approved": True,
            "evidence_ref": "COMPLIANCE-001",
        },
        "active_status": {
            "semantics_resolved": True,
            "market_status_checked": True,
        },
        "datasets": {
            "security_master": {
                "path": "security_master.csv",
                "ticker_column": "ticker",
                "exchange_column": "exchange",
            },
            "ohlcv": {"path": "ohlcv.csv", "ticker_column": "ticker"},
            "fundamentals": {"path": "fundamentals.csv", "ticker_column": "ticker"},
            "corporate_actions": {"path": "corporate_actions.csv"},
            "events": {"path": "events.csv"},
        },
    }


class ProductionBundleTests(unittest.TestCase):
    def populate(self, root: Path):
        tickers = ["MBB", "HPG", "ACB"]
        write_csv(
            root / "security_master.csv",
            ["ticker", "name", "exchange"],
            [{"ticker": ticker, "name": ticker, "exchange": "HOSE"} for ticker in tickers],
        )
        write_csv(
            root / "ohlcv.csv",
            ["ticker", "date", "open", "high", "low", "close", "volume"],
            [
                {"ticker": ticker, "date": "2026-09-03", "open": "1", "high": "1", "low": "1", "close": "1", "volume": "1000000"}
                for ticker in tickers
            ],
        )
        write_csv(
            root / "fundamentals.csv",
            ["ticker", "period", "revenue", "net_income", "total_assets", "equity", "operating_cash_flow", "capex", "shares_outstanding"],
            [
                {"ticker": ticker, "period": "2026Q2", "revenue": "100", "net_income": "10", "total_assets": "500", "equity": "200", "operating_cash_flow": "15", "capex": "5", "shares_outstanding": "100"}
                for ticker in tickers
            ],
        )
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
            self.assertEqual(manifest["datasets"]["ohlcv"]["input_role"], "RAW_INPUT_ONLY")
            self.assertEqual(manifest["computation"]["calculation_origin"], "STOCKRADAR_ENGINE")
            self.assertFalse(manifest["computation"]["external_scores_accepted"])
            self.assertTrue(manifest["compliance"]["public_recommendation_approved"])

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

    def test_missing_compliance_object_is_rejected_before_manifest(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            payload = descriptor()
            del payload["compliance"]
            with self.assertRaisesRegex(ProductionBundleError, "compliance object is required"):
                build_manifest_from_descriptor(root, payload)

    def test_unapproved_compliance_remains_blocked_after_assembly(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            payload = descriptor()
            payload["compliance"]["public_recommendation_approved"] = False
            result = validate_production_manifest(
                build_manifest_from_descriptor(root, payload),
                now=NOW,
            )
            self.assertFalse(result.passed)
            self.assertIn("compliance_public_recommendation_approved_false", result.failures)

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

    def test_security_master_requires_exchange_column(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            payload = descriptor()
            del payload["datasets"]["security_master"]["exchange_column"]
            with self.assertRaisesRegex(ProductionBundleError, "exchange_column is required"):
                build_manifest_from_descriptor(root, payload)

    def test_non_hose_security_master_row_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            write_csv(
                root / "security_master.csv",
                ["ticker", "name", "exchange"],
                [
                    {"ticker": "MBB", "name": "MBB", "exchange": "HOSE"},
                    {"ticker": "HPG", "name": "HPG", "exchange": "HOSE"},
                    {"ticker": "AAA", "name": "AAA", "exchange": "HNX"},
                ],
            )
            with self.assertRaisesRegex(ProductionBundleError, "non-HOSE row"):
                build_manifest_from_descriptor(root, descriptor())

    def test_snapshot_exchange_must_be_hose(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            payload = descriptor()
            payload["snapshot"]["exchange"] = "HNX"
            with self.assertRaisesRegex(ProductionBundleError, "exchange must be HOSE"):
                build_manifest_from_descriptor(root, payload)

    def test_ohlcv_ticker_outside_security_master_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            write_csv(
                root / "ohlcv.csv",
                ["ticker", "date", "close"],
                [
                    {"ticker": "MBB", "date": "2026-09-03", "close": "1"},
                    {"ticker": "HPG", "date": "2026-09-03", "close": "1"},
                    {"ticker": "XYZ", "date": "2026-09-03", "close": "1"},
                ],
            )
            with self.assertRaisesRegex(ProductionBundleError, "outside HOSE security_master"):
                build_manifest_from_descriptor(root, descriptor())

    def test_fundamental_ticker_outside_security_master_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            write_csv(
                root / "fundamentals.csv",
                ["ticker", "revenue", "net_income"],
                [
                    {"ticker": "MBB", "revenue": "100", "net_income": "10"},
                    {"ticker": "HPG", "revenue": "100", "net_income": "10"},
                    {"ticker": "XYZ", "revenue": "100", "net_income": "10"},
                ],
            )
            with self.assertRaisesRegex(ProductionBundleError, "outside HOSE security_master"):
                build_manifest_from_descriptor(root, descriptor())

    def test_external_derived_metrics_are_rejected_before_manifest(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            write_csv(
                root / "fundamentals.csv",
                ["ticker", "revenue", "net_income", "roe", "pe", "fair_value"],
                [
                    {"ticker": "MBB", "revenue": "100", "net_income": "10", "roe": "0.2", "pe": "8", "fair_value": "30"},
                    {"ticker": "HPG", "revenue": "100", "net_income": "10", "roe": "0.2", "pe": "8", "fair_value": "30"},
                    {"ticker": "ACB", "revenue": "100", "net_income": "10", "roe": "0.2", "pe": "8", "fair_value": "30"},
                ],
            )
            with self.assertRaisesRegex(ProductionBundleError, "external providers may supply raw inputs only"):
                build_manifest_from_descriptor(root, descriptor())

    def test_external_technical_indicators_are_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            write_csv(
                root / "ohlcv.csv",
                ["ticker", "date", "open", "high", "low", "close", "volume", "ma50", "rvol", "signal"],
                [
                    {"ticker": ticker, "date": "2026-09-03", "open": "1", "high": "1", "low": "1", "close": "1", "volume": "100", "ma50": "1", "rvol": "2", "signal": "BUY"}
                    for ticker in ["MBB", "HPG", "ACB"]
                ],
            )
            with self.assertRaisesRegex(ProductionBundleError, "external providers may supply raw inputs only"):
                build_manifest_from_descriptor(root, descriptor())

    def test_invalid_ticker_is_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            write_csv(path, ["ticker"], [{"ticker": "MBB"}, {"ticker": "AB12"}])
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
