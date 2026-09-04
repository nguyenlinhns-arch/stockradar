import unittest

from engine.stockradar.report_contract import ReportContractError, validate_report_payload


class ActionAlertContractTests(unittest.TestCase):
    def base_report(self):
        return {
            "ticker": "AAA",
            "horizon": "SHORT_TERM",
            "data_status": "READY",
            "data_grade": "DECISION_GRADE",
            "data_freshness": "FRESH",
            "public_release_allowed": True,
            "current_price": 25.4,
            "new_position_state": "CHỜ MUA",
            "holding_state": "GIỮ",
            "probability_calibrated": False,
        }

    def action_contract(self, *, eligible=True):
        return {
            "schema_version": "STOCKRADAR_ACTION_V1",
            "alert_eligible": eligible,
            "new_position": {
                "state": "BUY",
                "setup": "EARLY_BREAKOUT",
                "reasons": ["Giá vượt pivot với xác nhận dòng tiền."],
            },
            "holding": {
                "state": "HOLD",
                "reasons": ["Cấu trúc nắm giữ chưa bị phá vỡ."],
            },
        }

    def validate(self, payload):
        return validate_report_payload(
            payload,
            expected_ticker="AAA",
            expected_horizon="SHORT_TERM",
        )

    def test_report_without_action_contract_remains_valid(self):
        payload = self.base_report()
        payload.pop("data_freshness")
        payload.pop("public_release_allowed")
        validated = self.validate(payload)
        self.assertNotIn("action_contract", validated)

    def test_explicit_canonical_action_contract_is_valid(self):
        payload = self.base_report()
        payload["action_contract"] = self.action_contract()
        validated = self.validate(payload)
        self.assertEqual(
            validated["action_contract"]["new_position"]["state"],
            "BUY",
        )

    def test_lowercase_or_fuzzy_state_is_rejected(self):
        payload = self.base_report()
        contract = self.action_contract()
        contract["new_position"]["state"] = "mua"
        payload["action_contract"] = contract
        with self.assertRaisesRegex(ReportContractError, "new_position.state"):
            self.validate(payload)

    def test_holding_lane_cannot_use_buy_state(self):
        payload = self.base_report()
        contract = self.action_contract()
        contract["holding"]["state"] = "BUY"
        payload["action_contract"] = contract
        with self.assertRaisesRegex(ReportContractError, "holding.state"):
            self.validate(payload)

    def test_alert_eligible_requires_public_release(self):
        payload = self.base_report()
        payload["public_release_allowed"] = False
        payload["action_contract"] = self.action_contract()
        with self.assertRaisesRegex(ReportContractError, "public_release_allowed"):
            self.validate(payload)

    def test_alert_eligible_requires_fresh_data(self):
        payload = self.base_report()
        payload["data_freshness"] = "STALE"
        payload["action_contract"] = self.action_contract()
        with self.assertRaisesRegex(ReportContractError, "data_freshness=FRESH"):
            self.validate(payload)

    def test_non_alert_contract_may_be_retained_for_research_display(self):
        payload = self.base_report()
        payload["public_release_allowed"] = False
        payload["data_freshness"] = "STALE"
        payload["action_contract"] = self.action_contract(eligible=False)
        validated = self.validate(payload)
        self.assertFalse(validated["action_contract"]["alert_eligible"])


if __name__ == "__main__":
    unittest.main()
