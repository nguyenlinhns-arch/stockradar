from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "connector"))

import apply_v7_mxh_integration as patcher
from mxh_contract import MxhContractError, mxh_action_risk, parse_mxh_bridge
from connector.adapter import MxhHubAdapter, MxhHubError, ScheduleRequest


class FakeAdapter(MxhHubAdapter):
    def __init__(self):
        super().__init__()
        self.calls = []

    def _request(self, method, path, *, body=None, headers=None):
        self.calls.append((method, path, body, headers or {}))
        if path == "/api/dashboard/csrf":
            return "csrf-token-1234"
        if path.startswith("/api/mxh-video-tools/edited-videos"):
            return {"entries": [{
                "id": "mxh-edited:abc",
                "path": r"C:\Videos\target.mp4",
                "name": "20260926-073142__Tiêu đề chuẩn__edited.mp4",
                "sha256": "a" * 64,
                "title": "Tiêu đề chuẩn",
            }]}
        if path.startswith("/api/gpt-control"):
            return {"nativeSchedules": {"platforms": [
                {"platform": "tiktok", "status": "scheduled", "scheduleVerified": True},
                {"platform": "facebook", "status": "scheduled", "scheduleVerified": True},
            ]}}
        if path == "/api/video-publish/plans":
            return {"id": "plan-1", "nativeScheduleReady": False}
        if path == "/api/jobs":
            return {"job": {"id": "job-1", "status": "queued"}}
        if path.startswith("/api/jobs/"):
            return {"id": "job-1", "status": "succeeded"}
        if path in ("/api/status", "/api/workflows", "/api/capabilities"):
            return {}
        return {}


class ContractTests(unittest.TestCase):
    def test_contract_matches_v7_pattern(self):
        value = parse_mxh_bridge(
            'MXH_V1:{"action":"resolve_title","arguments":{"title":"Tiêu đề chuẩn"}}'
        )
        self.assertEqual(value, ("resolve_title", {"title": "Tiêu đề chuẩn"}))
        self.assertEqual(mxh_action_risk("resolve_title"), "READ")
        self.assertEqual(mxh_action_risk("native_schedule"), "MODIFY")

    def test_contract_rejects_unknown_field(self):
        with self.assertRaises(MxhContractError):
            parse_mxh_bridge('MXH_V1:{"action":"status","arguments":{},"url":"https://bad"}')

    def test_fixed_loopback_only(self):
        with self.assertRaises(MxhHubError):
            MxhHubAdapter("http://example.com")


class AdapterTests(unittest.TestCase):
    def test_resolve_exact_title(self):
        adapter = FakeAdapter()
        video = adapter.resolve_exact_title("Tiêu đề chuẩn")
        self.assertEqual(video.artifact_job_id, "mxh-edited:abc")
        self.assertEqual(video.sha256, "a" * 64)

    def test_plan_payload_is_locked_and_csrf_protected(self):
        adapter = FakeAdapter()
        result = adapter.create_or_reuse_plan(
            ScheduleRequest(
                artifact_job_id="mxh-edited:abc",
                title="Tiêu đề chuẩn",
                caption="Tiêu đề chuẩn",
                hashtags="#TKV",
                platforms=("tiktok", "facebook"),
                flow_id=2,
                scheduled_at="2026-09-29T02:00:00Z",
            ),
            idempotency_key="idem-key-123",
        )
        self.assertEqual(result["id"], "plan-1")
        post = [call for call in adapter.calls if call[1] == "/api/video-publish/plans"][0]
        self.assertEqual(post[2]["title"], "Tiêu đề chuẩn")
        self.assertTrue(post[2]["titleLocked"])
        self.assertTrue(post[2]["captionLocked"])
        self.assertEqual(post[2]["flowId"], 2)
        self.assertEqual(post[3]["x-hub-csrf"], "csrf-token-1234")
        self.assertEqual(post[3]["idempotency-key"], "idem-key-123")

    def test_native_schedule_contract(self):
        adapter = FakeAdapter()
        adapter.native_schedule(
            "plan-1",
            ("tiktok",),
            idempotency_key="native-key-123",
        )
        post = [call for call in adapter.calls if call[1] == "/api/jobs"][0]
        self.assertEqual(post[2]["workflowId"], "video.native_schedule")
        self.assertEqual(post[2]["mode"], "live")
        self.assertEqual(post[2]["input"]["planId"], "plan-1")
        self.assertEqual(post[2]["input"]["platforms"], ["tiktok"])
        self.assertTrue(post[2]["input"]["resumeIfMissing"])
        self.assertEqual(post[3]["x-hub-ui-intent"], "user-content")

    def test_schedule_verified_requires_provider_readback(self):
        summary = {
            "nativeSchedules": {
                "platforms": [
                    {"platform": "tiktok", "status": "scheduled", "scheduleVerified": True},
                    {"platform": "facebook", "status": "scheduled", "scheduleVerified": True},
                ]
            }
        }
        self.assertTrue(MxhHubAdapter.schedule_verified(summary, ("tiktok", "facebook")))
        summary["nativeSchedules"]["platforms"][1]["scheduleVerified"] = False
        self.assertFalse(MxhHubAdapter.schedule_verified(summary, ("tiktok", "facebook")))


class PatcherTests(unittest.TestCase):
    def test_patch_is_fail_closed_and_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "agent").mkdir()
            (root / "desktop").mkdir()
            semantic = (
                "def parse_capcut_bridge(goal):\n"
                "    return None\n\n"
                "def permission(spec,cfg):\n"
                "    return None\n\n"
                "class Runner:\n"
                "    def execute(self,payload):\n"
                "            bridge=parse_capcut_bridge(payload.get('goal'))\n"
                "            return bridge\n"
            )
            xaml = '<TabControl>\n        <TabItem Header="Cài đặt"></TabItem>\n</TabControl>\n'
            cs = "public partial class MainWindow {\n    void LoadSettings(){}\n}\n"
            targets = {
                "agent/semantic_host.py": semantic,
                "desktop/MainWindow.xaml": xaml,
                "desktop/MainWindow.xaml.cs": cs,
            }
            for relative, value in targets.items():
                path = root / relative
                path.write_text(value, encoding="utf-8")

            old = dict(patcher.EXPECTED_SOURCE_SHA256)
            try:
                patcher.EXPECTED_SOURCE_SHA256.clear()
                for relative in targets:
                    path = root / relative
                    patcher.EXPECTED_SOURCE_SHA256[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
                first = patcher.apply_patch(root, ROOT, run_build=False)
                self.assertFalse(first.already_integrated)
                self.assertIn("MXH_BRIDGE_PREFIX='MXH_V1:'", (root / "agent/semantic_host.py").read_text())
                self.assertIn('Header="MXH PUBLISH"', (root / "desktop/MainWindow.xaml").read_text())
                second = patcher.apply_patch(root, ROOT, run_build=False)
                self.assertTrue(second.already_integrated)
            finally:
                patcher.EXPECTED_SOURCE_SHA256.clear()
                patcher.EXPECTED_SOURCE_SHA256.update(old)


if __name__ == "__main__":
    unittest.main()
