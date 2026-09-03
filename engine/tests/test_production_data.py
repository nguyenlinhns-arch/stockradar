import unittest
from datetime import datetime, timedelta, timezone

from engine.stockradar.production_data import validate_production_manifest


VN_TZ = timezone(timedelta(hours=7))
NOW = datetime(2026, 9, 3, 11, 0, tzinfo=VN_TZ)
CHECKSUM = "a" * 64


def valid_manifest():
    snapshot_id = "hose-production-2026-09-03-104500-vn"
    timestamp = "2026-09-03T10:45:00+07:00"

    def dataset(row_count, covered_tickers=None):
        value = {
            "present": True,
            "snapshot_id": snapshot_id,
            "as_of": timestamp,
            "sha256": CHECKSUM,
            "row_count": row_count,
        }
        if covered_tickers is not None:
            value["covered_tickers"] = covered_tickers
        return value

    return {
        "contract_version": "1.0",
        "snapshot": {
            "snapshot_id": snapshot_id,
            "as_of": timestamp,
            "source_timestamp": timestamp,
            "exchange": "HOSE",
            "expected_total": 405,
            "scanned_count": 405,
            "valid_count": 405,
            "excluded_count": 0,
            "stale_count": 0,
            "missing_count": 0,
            "data_grade": "DECISION_GRADE",
            "same_snapshot": True,
            "adjusted_basis_consistent": True,
            "corporate_action_checked": True,
            "source": "LICENSED_PROVIDER",
            "exclusion_log": [],
        },
        "rights": {
            "publication_allowed": True,
            "redistribution_allowed": True,
            "source_terms_reviewed": True,
            "evidence_ref": "LEGAL-DATA-RIGHTS-2026-09",
        },
        "active_status": {
            "semantics_resolved": True,
            "market_status_checked": True,
        },
        "datasets": {
            "security_master": dataset(405, 405),
            "ohlcv": dataset(405 * 250, 405),
            "fundamentals": dataset(405, 405),
            "corporate_actions": dataset(0),
            "events": dataset(0),
        },
    }


class ProductionDataContractTests(unittest.TestCase):
    def test_complete_licensed_snapshot_passes(self):
        result = validate_production_manifest(valid_manifest(), now=NOW)
        self.assertTrue(result.passed)
        self.assertEqual(result.failures, ())
        self.assertTrue(result.to_dict()["publication_allowed"])

    def test_rights_failure_blocks_publication(self):
        payload = valid_manifest()
        payload["rights"]["redistribution_allowed"] = False
        result = validate_production_manifest(payload, now=NOW)
        self.assertFalse(result.passed)
        self.assertIn("rights_redistribution_allowed_false", result.failures)

    def test_unresolved_active_status_blocks(self):
        payload = valid_manifest()
        payload["active_status"]["semantics_resolved"] = False
        result = validate_production_manifest(payload, now=NOW)
        self.assertIn("active_status_semantics_unresolved", result.failures)

    def test_missing_ohlcv_blocks(self):
        payload = valid_manifest()
        payload["datasets"]["ohlcv"]["present"] = False
        result = validate_production_manifest(payload, now=NOW)
        self.assertIn("dataset_missing:ohlcv", result.failures)

    def test_incomplete_universe_reuses_full_universe_gate(self):
        payload = valid_manifest()
        payload["snapshot"]["scanned_count"] = 404
        result = validate_production_manifest(payload, now=NOW)
        self.assertIn("processed_universe_incomplete", result.failures)

    def test_stale_dataset_blocks(self):
        payload = valid_manifest()
        payload["datasets"]["ohlcv"]["as_of"] = "2026-09-02T10:45:00+07:00"
        result = validate_production_manifest(
            payload,
            now=NOW,
            max_age_seconds=6 * 60 * 60,
        )
        self.assertIn("dataset_stale:ohlcv", result.failures)

    def test_coverage_gap_blocks(self):
        payload = valid_manifest()
        payload["datasets"]["fundamentals"]["covered_tickers"] = 404
        result = validate_production_manifest(payload, now=NOW)
        self.assertIn("dataset_coverage_incomplete:fundamentals", result.failures)

    def test_invalid_checksum_blocks(self):
        payload = valid_manifest()
        payload["datasets"]["ohlcv"]["sha256"] = "not-a-sha256"
        result = validate_production_manifest(payload, now=NOW)
        self.assertIn("dataset_checksum_invalid:ohlcv", result.failures)

    def test_secret_shaped_fields_are_rejected(self):
        payload = valid_manifest()
        payload["credentials"] = {"api_key": "must-not-be-here"}
        result = validate_production_manifest(payload, now=NOW)
        self.assertIn("secret_material_forbidden:credentials.api_key", result.failures)

    def test_dataset_snapshot_must_match(self):
        payload = valid_manifest()
        payload["datasets"]["events"]["snapshot_id"] = "different-snapshot"
        result = validate_production_manifest(payload, now=NOW)
        self.assertIn("dataset_snapshot_mismatch:events", result.failures)


if __name__ == "__main__":
    unittest.main()
