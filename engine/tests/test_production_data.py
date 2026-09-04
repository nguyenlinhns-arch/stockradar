import unittest
from datetime import datetime, timedelta, timezone

from engine.stockradar.production_data import validate_production_manifest


VN_TZ = timezone(timedelta(hours=7))
NOW = datetime(2026, 9, 3, 11, 0, tzinfo=VN_TZ)
CHECKSUM = "a" * 64


def valid_manifest():
    snapshot_id = "hose-production-2026-09-03-104500-vn"
    timestamp = "2026-09-03T10:45:00+07:00"

    def dataset(row_count, columns, covered_tickers=None):
        value = {
            "present": True,
            "snapshot_id": snapshot_id,
            "as_of": timestamp,
            "sha256": CHECKSUM,
            "row_count": row_count,
            "input_role": "RAW_INPUT_ONLY",
            "columns": columns,
        }
        if covered_tickers is not None:
            value["covered_tickers"] = covered_tickers
        return value

    return {
        "contract_version": "1.0",
        "computation": {
            "calculation_origin": "STOCKRADAR_ENGINE",
            "calculation_policy_version": "1.0",
            "external_input_role": "RAW_INPUT_ONLY",
            "external_scores_accepted": False,
            "method_stack": ["4M_PAYBACK", "CANSLIM", "VALUATION", "SEPA_VCP_STAGE", "VPA"],
        },
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
            "source": "LICENSED_PROVIDER_RAW_INPUT",
            "exclusion_log": [],
        },
        "rights": {
            "publication_allowed": True,
            "redistribution_allowed": True,
            "source_terms_reviewed": True,
            "evidence_ref": "LEGAL-DATA-RIGHTS-2026-09",
        },
        "compliance": {
            "review_completed": True,
            "public_recommendation_approved": True,
            "evidence_ref": "LEGAL-COMPLIANCE-REVIEW-2026-09",
        },
        "active_status": {
            "semantics_resolved": True,
            "market_status_checked": True,
        },
        "datasets": {
            "security_master": dataset(405, ["ticker", "name", "exchange"], 405),
            "ohlcv": dataset(405 * 250, ["ticker", "date", "open", "high", "low", "close", "volume"], 405),
            "fundamentals": dataset(405, ["ticker", "period", "revenue", "net_income", "total_assets", "equity", "operating_cash_flow", "capex", "shares_outstanding"], 405),
            "corporate_actions": dataset(0, ["event_id", "ticker", "event_type", "effective_date"]),
            "events": dataset(0, ["event_id", "ticker", "event_type", "event_date"]),
        },
    }


class ProductionDataContractTests(unittest.TestCase):
    def test_complete_licensed_snapshot_passes(self):
        result = validate_production_manifest(valid_manifest(), now=NOW)
        self.assertTrue(result.passed)
        self.assertEqual(result.failures, ())
        self.assertTrue(result.to_dict()["publication_allowed"])
        self.assertTrue(result.to_dict()["compliance_required"])
        self.assertEqual(result.to_dict()["calculation_origin"], "STOCKRADAR_ENGINE")

    def test_rights_failure_blocks_publication(self):
        payload = valid_manifest()
        payload["rights"]["redistribution_allowed"] = False
        result = validate_production_manifest(payload, now=NOW)
        self.assertFalse(result.passed)
        self.assertIn("rights_redistribution_allowed_false", result.failures)

    def test_missing_compliance_evidence_blocks_publication(self):
        payload = valid_manifest()
        del payload["compliance"]
        result = validate_production_manifest(payload, now=NOW)
        self.assertFalse(result.passed)
        self.assertIn("compliance_evidence_missing", result.failures)

    def test_incomplete_compliance_review_blocks_publication(self):
        payload = valid_manifest()
        payload["compliance"]["review_completed"] = False
        result = validate_production_manifest(payload, now=NOW)
        self.assertFalse(result.passed)
        self.assertIn("compliance_review_completed_false", result.failures)

    def test_unapproved_public_recommendations_block_publication(self):
        payload = valid_manifest()
        payload["compliance"]["public_recommendation_approved"] = False
        result = validate_production_manifest(payload, now=NOW)
        self.assertFalse(result.passed)
        self.assertIn("compliance_public_recommendation_approved_false", result.failures)

    def test_compliance_evidence_reference_is_required(self):
        payload = valid_manifest()
        payload["compliance"]["evidence_ref"] = ""
        result = validate_production_manifest(payload, now=NOW)
        self.assertFalse(result.passed)
        self.assertIn("compliance_evidence_ref_missing", result.failures)

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

    def test_external_scores_or_metrics_are_rejected(self):
        payload = valid_manifest()
        payload["datasets"]["fundamentals"]["columns"].extend(["roe", "pe", "fair_value"])
        result = validate_production_manifest(payload, now=NOW)
        self.assertIn("external_derived_field_forbidden:fundamentals:roe", result.failures)
        self.assertIn("external_derived_field_forbidden:fundamentals:pe", result.failures)
        self.assertIn("external_derived_field_forbidden:fundamentals:fair_value", result.failures)

    def test_non_stockradar_calculation_origin_is_rejected(self):
        payload = valid_manifest()
        payload["computation"]["calculation_origin"] = "EXTERNAL_PROVIDER"
        result = validate_production_manifest(payload, now=NOW)
        self.assertIn("calculation_origin_not_stockradar", result.failures)

    def test_external_score_acceptance_must_remain_false(self):
        payload = valid_manifest()
        payload["computation"]["external_scores_accepted"] = True
        result = validate_production_manifest(payload, now=NOW)
        self.assertIn("external_scores_must_be_rejected", result.failures)


if __name__ == "__main__":
    unittest.main()
