from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "connector"))

from mxh_contract import mxh_action_risk, parse_mxh_bridge
from connector.adapter import MxhHubAdapter


class DirectFakeAdapter(MxhHubAdapter):
    def __init__(self, *, already_verified: bool = False):
        super().__init__()
        self.calls = []
        self.facebook_verified = already_verified

    def _request(self, method, path, *, body=None, headers=None):
        self.calls.append((method, path, body, headers or {}))
        if path == "/api/status":
            return {"ok": True, "service": "automation-hub"}
        if path == "/api/workflows":
            return {"workflows": [{"id": "video.native_schedule"}]}
        if path == "/api/capabilities":
            return {"videoPublish": True, "mxhVideoTools": True}
        if path.startswith("/api/mxh-video-tools/edited-videos"):
            return {"entries": [{
                "id": "mxh-edited:abc",
                "path": r"C:\Videos\target.mp4",
                "name": "20260926-073142__Tiêu đề chuẩn__edited.mp4",
                "sha256": "a" * 64,
                "title": "Tiêu đề chuẩn",
            }]}
        if path.startswith("/api/gpt-control?video_sha256="):
            return {"content": {"title": "Tiêu đề chuẩn", "caption": "Nội dung chuẩn"}}
        if path.startswith("/api/gpt-control?plan_id="):
            rows = [
                {"platform": "tiktok", "status": "scheduled", "scheduleVerified": True},
                {"platform": "facebook", "status": "scheduled", "scheduleVerified": self.facebook_verified},
            ]
            return {"nativeSchedules": {"platforms": rows}}
        if path == "/api/dashboard/csrf":
            return "csrf-token-1234"
        if path == "/api/video-publish/plans":
            self.assert_plan(body, headers)
            return {"id": "plan-1"}
        if path == "/api/jobs":
            assert body["workflowId"] == "video.native_schedule"
            assert body["input"]["platforms"] == ["facebook"]
            self.facebook_verified = True
            return {"job": {"id": "job-1", "status": "queued"}}
        if path == "/api/jobs/job-1":
            return {"id": "job-1", "status": "succeeded"}
        raise AssertionError(f"unexpected request: {method} {path}")

    @staticmethod
    def assert_plan(body, headers):
        assert body["title"] == "Tiêu đề chuẩn"
        assert body["caption"] == "Nội dung chuẩn"
        assert body["titleLocked"] is True
        assert body["captionLocked"] is True
        assert body["flowId"] == 2
        assert headers["x-hub-csrf"] == "csrf-token-1234"
        assert headers["idempotency-key"].startswith("v7-mxh-")


class DirectControlV2Tests(unittest.TestCase):
    def test_contract_exposes_fast_actions_with_correct_risk(self):
        value = parse_mxh_bridge(
            'MXH_V1:{"action":"readiness","arguments":{"limit":5}}'
        )
        self.assertEqual(value, ("readiness", {"limit": 5}))
        self.assertEqual(mxh_action_risk("readiness"), "READ")
        self.assertEqual(mxh_action_risk("schedule_exact_title"), "MODIFY")

    def test_readiness_proves_hub_and_mxh_catalog_path(self):
        adapter = DirectFakeAdapter()
        result = adapter.execute("readiness", {"limit": 5})["result"]
        self.assertEqual(result["bridge"], "V7_HUB_DIRECT_V2")
        self.assertTrue(result["hub_ready"])
        self.assertTrue(result["catalog_ready"])
        self.assertEqual(result["edited_count"], 1)
        self.assertEqual(result["sample_titles"], ["Tiêu đề chuẩn"])

    def test_one_call_schedules_only_unverified_platform_and_reads_receipt(self):
        adapter = DirectFakeAdapter(already_verified=False)
        result = adapter.execute("schedule_exact_title", {
            "title": "Tiêu đề chuẩn",
            "flow_id": 2,
            "platforms": ["tiktok", "facebook"],
            "scheduled_at": "2026-09-29T02:00:00Z",
            "timezone": "Asia/Ho_Chi_Minh",
            "wait_seconds": 0,
        })["result"]

        self.assertEqual(result["status"], "SCHEDULED_VERIFIED")
        self.assertTrue(result["schedule_verified"])
        self.assertEqual(result["submitted_platforms"], ["facebook"])
        self.assertEqual(result["verified_platforms"], ["facebook", "tiktok"])
        self.assertEqual(result["video"]["title"], "Tiêu đề chuẩn")
        job_posts = [call for call in adapter.calls if call[1] == "/api/jobs"]
        self.assertEqual(len(job_posts), 1)

    def test_verified_plan_is_not_scheduled_again(self):
        adapter = DirectFakeAdapter(already_verified=True)
        result = adapter.execute("schedule_exact_title", {
            "title": "Tiêu đề chuẩn",
            "flow_id": 2,
            "platforms": ["tiktok", "facebook"],
            "scheduled_at": "2026-09-29T02:00:00Z",
            "wait_seconds": 0,
        })["result"]

        self.assertEqual(result["status"], "SCHEDULED_VERIFIED")
        self.assertFalse(result["submitted"])
        self.assertEqual(result["submitted_platforms"], [])
        self.assertFalse(any(call[1] == "/api/jobs" for call in adapter.calls))


if __name__ == "__main__":
    unittest.main()
