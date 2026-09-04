import csv
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from engine.stockradar.licensed_intake import (
    LicensedIntakeError,
    prepare_licensed_intake,
    write_private_json,
)


NOW = datetime(2026, 9, 4, 3, 0, tzinfo=timezone.utc)
TIMESTAMP = "2026-09-04T09:45:00+07:00"
SNAPSHOT_ID = "hose-licensed-2026-09-04-094500-vn"


def write_csv(path: Path, fieldnames, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def rights():
    return {
        "schema_version": "1.0",
        "mode": "LICENSED",
        "provider_id": "vendor-enterprise-feed",
        "contract_ref": "MSA-2026-001",
        "evidence_ref": "rights-review/2026-09-04",
        "reviewed_at": "2026-09-04T08:00:00+07:00",
        "effective_from": "2026-09-01T00:00:00+07:00",
        "effective_until": "2027-09-01T00:00:00+07:00",
        "permissions": {
            "source_terms_reviewed": True,
            "publication_allowed": True,
            "redistribution_allowed": True,
            "internal_analytics_allowed": True,
            "derived_outputs_allowed": True,
            "customer_display_allowed": True,
        },
    }


def package():
    return {
        "schema_version": "1.0",
        "snapshot": {
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
        },
        "compliance": {
            "review_completed": True,
            "public_recommendation_approved": True,
            "evidence_ref": "COMPLIANCE-TEST-001",
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


class LicensedProviderIntakeTests(unittest.TestCase):
    def populate(self, root: Path):
        tickers = ["MBB", "HPG", "ACB"]
        write_csv(
            root / "security_master.csv",
            ["ticker", "company_name", "exchange"],
            [{"ticker": ticker, "company_name": ticker, "exchange": "HOSE"} for ticker in tickers],
        )
        write_csv(
            root / "ohlcv.csv",
            ["ticker", "date", "open", "high", "low", "close", "volume"],
            [
                {"ticker": ticker, "date": "2026-09-04", "open": "1", "high": "1", "low": "1", "close": "1", "volume": "1000000"}
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
        write_csv(root / "corporate_actions.csv", ["event_id", "event_type"], [])
        write_csv(root / "events.csv", ["event_id", "published_at"], [])

    def test_valid_licensed_raw_package_is_accepted_and_gate_is_only_reported(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            descriptor, result, report = prepare_licensed_intake(root, package(), rights(), now=NOW)
            self.assertTrue(result.accepted)
            self.assertTrue(result.publication_ready, result.failures)
            self.assertTrue(descriptor["rights"]["redistribution_allowed"])
            self.assertTrue(descriptor["rights"]["derived_outputs_allowed"])
            self.assertTrue(descriptor["compliance"]["public_recommendation_approved"])
            self.assertEqual(report["dataset_rows"]["ohlcv"], 3)
            self.assertEqual(len(report["dataset_checksums"]["ohlcv"]), 64)
            self.assertFalse(report["gate_mutation_performed"])
            self.assertFalse(report["credentials_persisted"])

    def test_research_only_source_cannot_enter_licensed_intake(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            policy = rights()
            policy["mode"] = "RESEARCH_ONLY"
            with self.assertRaisesRegex(LicensedIntakeError, "mode must be LICENSED"):
                prepare_licensed_intake(root, package(), policy, now=NOW)

    def test_every_commercial_permission_is_explicitly_required(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            policy = rights()
            policy["permissions"]["customer_display_allowed"] = False
            with self.assertRaisesRegex(LicensedIntakeError, "customer_display_allowed"):
                prepare_licensed_intake(root, package(), policy, now=NOW)

    def test_expired_license_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            policy = rights()
            policy["effective_until"] = "2026-09-03T00:00:00+07:00"
            with self.assertRaisesRegex(LicensedIntakeError, "license has expired"):
                prepare_licensed_intake(root, package(), policy, now=NOW)

    def test_vendor_derived_score_or_indicator_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            write_csv(
                root / "ohlcv.csv",
                ["ticker", "date", "open", "high", "low", "close", "volume", "ma50", "signal"],
                [
                    {"ticker": ticker, "date": "2026-09-04", "open": "1", "high": "1", "low": "1", "close": "1", "volume": "100", "ma50": "1", "signal": "BUY"}
                    for ticker in ["MBB", "HPG", "ACB"]
                ],
            )
            with self.assertRaisesRegex(LicensedIntakeError, "external providers may supply raw inputs only"):
                prepare_licensed_intake(root, package(), rights(), now=NOW)

    def test_secret_material_in_metadata_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            policy = rights()
            policy["api_key"] = "sk-this-must-never-be-stored"
            with self.assertRaisesRegex(LicensedIntakeError, "secret material is forbidden"):
                prepare_licensed_intake(root, package(), policy, now=NOW)

    def test_non_hose_package_is_rejected_before_manifest(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            payload = package()
            payload["snapshot"]["exchange"] = "HNX"
            with self.assertRaisesRegex(LicensedIntakeError, "only accepts HOSE"):
                prepare_licensed_intake(root, payload, rights(), now=NOW)

    def test_stale_but_licensed_package_can_be_reconciled_without_becoming_publishable(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            payload = package()
            payload["snapshot"]["as_of"] = "2026-09-03T09:45:00+07:00"
            payload["snapshot"]["source_timestamp"] = "2026-09-03T09:45:00+07:00"
            for dataset in payload["datasets"].values():
                dataset["as_of"] = "2026-09-03T09:45:00+07:00"
            _, result, report = prepare_licensed_intake(root, payload, rights(), now=NOW)
            self.assertTrue(result.accepted)
            self.assertFalse(result.publication_ready)
            self.assertIn("snapshot_stale", result.failures)
            self.assertFalse(report["production_gate"]["publication_allowed"])

    def test_missing_compliance_is_rejected_before_manifest(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.populate(root)
            payload = package()
            del payload["compliance"]
            with self.assertRaisesRegex(LicensedIntakeError, "package.compliance object is required"):
                prepare_licensed_intake(root, payload, rights(), now=NOW)

    def test_public_web_staging_and_outputs_are_rejected(self):
        repo_root = Path(__file__).resolve().parents[2]
        public_dir = repo_root / "website" / "public" / "licensed-intake-test"
        public_dir.mkdir(parents=True, exist_ok=True)
        try:
            self.populate(public_dir)
            with self.assertRaisesRegex(LicensedIntakeError, "outside public website"):
                prepare_licensed_intake(public_dir, package(), rights(), repo_root=repo_root, now=NOW)
            with self.assertRaisesRegex(LicensedIntakeError, "outside public website"):
                write_private_json(public_dir / "report.json", {"accepted": False}, repo_root=repo_root)
        finally:
            for child in public_dir.iterdir():
                child.unlink()
            public_dir.rmdir()


if __name__ == "__main__":
    unittest.main()