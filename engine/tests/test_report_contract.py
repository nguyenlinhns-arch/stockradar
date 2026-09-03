import unittest

from engine.stockradar.report_contract import ReportContractError, validate_report_payload


def valid_payload():
    return {
        "ticker": "MBB",
        "horizon": "SHORT_TERM",
        "data_status": "READY",
        "data_grade": "DECISION_GRADE",
        "current_price": 30.5,
        "new_position_state": "CHỜ MUA",
        "holding_state": "THEO DÕI",
        "score": 82,
        "rvol": 1.4,
        "buy_zone_low": 30.0,
        "buy_zone_high": 30.8,
        "stop_loss": 28.8,
        "target_near": 34.0,
        "upside_pct": 11.5,
        "downside_pct": -5.6,
        "risk_reward": 2.05,
        "probability_calibrated": False,
        "thesis": ["Nền giá đạt chuẩn."],
        "risks": ["Gãy nền làm vô hiệu setup."],
    }


class ReportContractTests(unittest.TestCase):
    def test_decision_grade_report_passes_without_probability_claim(self):
        result = validate_report_payload(
            valid_payload(), expected_ticker="MBB", expected_horizon="SHORT_TERM"
        )
        self.assertEqual(result["ticker"], "MBB")
        self.assertFalse(result["probability_calibrated"])

    def test_ready_and_decision_grade_are_required(self):
        payload = valid_payload()
        payload["data_status"] = "BLOCKED_DATA_GATE"
        with self.assertRaisesRegex(ReportContractError, "data_status must be READY"):
            validate_report_payload(payload, expected_ticker="MBB", expected_horizon="SHORT_TERM")

        payload = valid_payload()
        payload["data_grade"] = "PARTIAL"
        with self.assertRaisesRegex(ReportContractError, "data_grade must be DECISION_GRADE"):
            validate_report_payload(payload, expected_ticker="MBB", expected_horizon="SHORT_TERM")

    def test_uncalibrated_probability_cannot_be_published(self):
        payload = valid_payload()
        payload["probability_pct"] = 82
        with self.assertRaisesRegex(ReportContractError, "uncalibrated probability"):
            validate_report_payload(payload, expected_ticker="MBB", expected_horizon="SHORT_TERM")

    def test_calibrated_probability_requires_oos_sample_method_and_scope(self):
        payload = valid_payload()
        payload.update({
            "probability_calibrated": True,
            "probability_pct": 62,
            "probability_oos": True,
            "probability_method": "isotonic calibration",
            "probability_sample_size": 500,
            "probability_scope": "same setup/regime/horizon/universe",
        })
        result = validate_report_payload(payload, expected_ticker="MBB", expected_horizon="SHORT_TERM")
        self.assertEqual(result["probability_pct"], 62)

        for key in ("probability_oos", "probability_method", "probability_sample_size", "probability_scope"):
            broken = dict(payload)
            broken.pop(key)
            with self.assertRaises(ReportContractError, msg=key):
                validate_report_payload(broken, expected_ticker="MBB", expected_horizon="SHORT_TERM")

    def test_probability_outside_zero_to_one_hundred_is_rejected(self):
        payload = valid_payload()
        payload.update({
            "probability_calibrated": True,
            "probability_pct": 118,
            "probability_oos": True,
            "probability_method": "isotonic calibration",
            "probability_sample_size": 500,
            "probability_scope": "same setup/regime/horizon/universe",
        })
        with self.assertRaisesRegex(ReportContractError, "between 0 and 100"):
            validate_report_payload(payload, expected_ticker="MBB", expected_horizon="SHORT_TERM")

    def test_score_buy_zone_and_signed_risk_metrics_are_validated(self):
        payload = valid_payload()
        payload["score"] = 101
        with self.assertRaisesRegex(ReportContractError, "score must be between"):
            validate_report_payload(payload, expected_ticker="MBB", expected_horizon="SHORT_TERM")

        payload = valid_payload()
        payload["buy_zone_low"] = 31
        payload["buy_zone_high"] = 30
        with self.assertRaisesRegex(ReportContractError, "Buy Zone is invalid"):
            validate_report_payload(payload, expected_ticker="MBB", expected_horizon="SHORT_TERM")

        payload = valid_payload()
        payload["upside_pct"] = -1
        with self.assertRaisesRegex(ReportContractError, "upside_pct must be non-negative"):
            validate_report_payload(payload, expected_ticker="MBB", expected_horizon="SHORT_TERM")

        payload = valid_payload()
        payload["downside_pct"] = 5
        with self.assertRaisesRegex(ReportContractError, "downside_pct must be zero or negative"):
            validate_report_payload(payload, expected_ticker="MBB", expected_horizon="SHORT_TERM")

    def test_payload_identity_must_match_cache_key(self):
        payload = valid_payload()
        payload["ticker"] = "HPG"
        with self.assertRaisesRegex(ReportContractError, "ticker does not match"):
            validate_report_payload(payload, expected_ticker="MBB", expected_horizon="SHORT_TERM")

        payload = valid_payload()
        payload["horizon"] = "LONG_TERM"
        with self.assertRaisesRegex(ReportContractError, "horizon does not match"):
            validate_report_payload(payload, expected_ticker="MBB", expected_horizon="SHORT_TERM")


if __name__ == "__main__":
    unittest.main()
