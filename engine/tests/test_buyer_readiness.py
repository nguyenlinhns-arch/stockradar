import json
import unittest
from pathlib import Path

from engine.stockradar.models import Candidate, DataGrade, MarketRegime, SetupState, UniverseSnapshot
from engine.stockradar.ranking import build_top_hose


ROOT = Path(__file__).resolve().parents[2]


class BuyerReadinessTests(unittest.TestCase):
    def snapshot(self, grade=DataGrade.DECISION_GRADE):
        return UniverseSnapshot(
            snapshot_id="snap-1",
            as_of="2026-09-04T14:15:00+07:00",
            source_timestamp="2026-09-04T14:15:00+07:00",
            exchange="HOSE",
            expected_total=2,
            scanned_count=2,
            valid_count=2,
            excluded_count=0,
            stale_count=0,
            missing_count=0,
            data_grade=grade,
            same_snapshot=True,
            adjusted_basis_consistent=True,
            corporate_action_checked=True,
            source="licensed-raw-test-source",
        )

    def candidate(self, ticker, score, state=SetupState.READY):
        return Candidate(
            ticker=ticker,
            score=score,
            score_coverage_pct=100,
            setup="VCP",
            state=state,
            previous_state=None,
            market_regime=MarketRegime.GREEN,
            current_price=30.0,
            pivot=31.0,
            distance_to_pivot_pct=-3.2,
            extension_pct=0.0,
            liquidity_pass=True,
            event_risk_pass=True,
            reason="qualified",
            is_mock=False,
        )

    def test_top_hose_has_global_and_sector_ranking_only_after_full_gate(self):
        payload = build_top_hose(
            self.snapshot(),
            [self.candidate("AAA", 91), self.candidate("BBB", 84)],
            {"AAA": "Ngân hàng", "BBB": "Công nghệ"},
        )
        self.assertTrue(payload["ranking_valid"])
        self.assertTrue(payload["gate"]["passed"])
        self.assertEqual([item["ticker"] for item in payload["strongest"]], ["AAA", "BBB"])
        self.assertEqual(payload["strongest"][0]["rank"], 1)
        self.assertEqual(payload["by_sector"][0]["items"][0]["sector_rank"], 1)
        self.assertEqual(payload["computation"]["calculation_origin"], "STOCKRADAR_ENGINE")
        self.assertFalse(payload["computation"]["external_scores_accepted"])
        self.assertTrue(all(item["calculated_by"] == "STOCKRADAR_ENGINE" for item in payload["strongest"]))

    def test_reference_or_research_grade_can_never_publish_top_rows(self):
        payload = build_top_hose(
            self.snapshot(DataGrade.RESEARCH_GRADE),
            [self.candidate("AAA", 99), self.candidate("BBB", 98)],
            {"AAA": "Ngân hàng", "BBB": "Công nghệ"},
        )
        self.assertFalse(payload["ranking_valid"])
        self.assertEqual(payload["strongest"], [])
        self.assertEqual(payload["by_sector"], [])
        self.assertEqual(payload["computation"]["calculation_origin"], "STOCKRADAR_ENGINE")

    def test_public_top_contract_is_fail_closed(self):
        payload = json.loads((ROOT / "website/public/data/top-stocks.json").read_text(encoding="utf-8"))
        self.assertFalse(payload["ranking_valid"])
        self.assertEqual(payload["strongest"], [])
        self.assertEqual(payload["by_sector"], [])
        self.assertEqual(payload["method_version"], "STOCKRADAR_SCORE_V1")
        self.assertEqual(payload["computation"]["calculation_origin"], "STOCKRADAR_ENGINE")
        self.assertEqual(payload["computation"]["external_input_role"], "RAW_INPUT_ONLY")
        self.assertFalse(payload["computation"]["external_scores_accepted"])

    def test_buyer_surface_separates_top_hose_from_radar_review_list(self):
        client = (ROOT / "website/assets/buyer-readiness-v1.js").read_text(encoding="utf-8")
        for marker in (
            "Top cổ phiếu HOSE theo tiêu chí StockRadar.vn",
            "Top mạnh nhất",
            "Top theo ngành",
            "Danh sách cổ phiếu theo Radar rà soát",
            "DECISION CARD",
            "StockRadar Score",
            "Xếp hạng HOSE",
            "Buy Zone",
            "Risk/Reward",
        ):
            self.assertIn(marker, client)
        self.assertIn("payload?.ranking_valid === true", client)

    def test_email_stays_inactive_while_checkout_is_enabled(self):
        script = (ROOT / "scripts/apply_buyer_readiness.py").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
        self.assertIn('STOCKRADAR_PRODUCT_EMAIL_READY: "0"', workflow)
        self.assertIn('STOCKRADAR_CHECKOUT_READY: "1"', workflow)
        self.assertIn("shutil.rmtree(checkout)", script)
        self.assertIn("buyer-readiness-v1.js", script)
        self.assertIn("verify_buyer_readiness.py", workflow)


if __name__ == "__main__":
    unittest.main()
