import os
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import build_pages


class PagesProductionGateTests(unittest.TestCase):
    def test_fail_closed_payloads_do_not_require_manifest(self):
        payloads = [
            (Path("radar.json"), {"data_status": "BLOCKED_DATA_GATE", "is_top5_hose": False}),
            (Path("ticker-universe.json"), {"data_status": "BLOCKED_DATA_GATE", "full_universe": False}),
        ]
        with patch.dict(os.environ, {}, clear=True):
            build_pages.enforce_production_data_gate(payloads)

    def test_production_looking_payload_is_rejected_without_manifest(self):
        payloads = [
            (
                Path("radar.json"),
                {
                    "data_status": "READY",
                    "is_top5_hose": True,
                    "snapshot": {"snapshot_id": "S1"},
                },
            )
        ]
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "STOCKRADAR_PRODUCTION_MANIFEST"):
                build_pages.enforce_production_data_gate(payloads)

    def test_production_approved_recommendations_require_manifest(self):
        payloads = [
            (
                Path("recommendations.json"),
                {
                    "data_status": "READY",
                    "recommendation_mode": "PRODUCTION_APPROVED",
                },
            )
        ]
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                build_pages.enforce_production_data_gate(payloads)


if __name__ == "__main__":
    unittest.main()
