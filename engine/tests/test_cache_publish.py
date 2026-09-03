import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from engine.stockradar.cache_publish import (
    CachePublishError,
    load_cache_batch,
    publish_cache_records,
)


NOW = datetime(2026, 9, 3, 5, 0, tzinfo=timezone.utc)
SNAPSHOT_ID = "hose-production-2026-09-03-104500-vn"
TIMESTAMP = "2026-09-03T10:45:00+07:00"
CHECKSUM = "a" * 64


def manifest_payload():
    def dataset(rows, covered=None):
        result = {
            "present": True,
            "snapshot_id": SNAPSHOT_ID,
            "as_of": TIMESTAMP,
            "sha256": CHECKSUM,
            "row_count": rows,
        }
        if covered is not None:
            result["covered_tickers"] = covered
        return result

    return {
        "contract_version": "1.0",
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
            "source": "LICENSED_PROVIDER",
            "exclusion_log": [],
        },
        "rights": {
            "publication_allowed": True,
            "redistribution_allowed": True,
            "source_terms_reviewed": True,
            "evidence_ref": "CONTRACT-001",
        },
        "active_status": {
            "semantics_resolved": True,
            "market_status_checked": True,
        },
        "datasets": {
            "security_master": dataset(3, 3),
            "ohlcv": dataset(750, 3),
            "fundamentals": dataset(3, 3),
            "corporate_actions": dataset(0),
            "events": dataset(0),
        },
    }


def batch_payload():
    return {
        "contract_version": "1.0",
        "snapshot_id": SNAPSHOT_ID,
        "items": [
            {
                "ticker": "MBB",
                "horizon": "SHORT_TERM",
                "generated_at": "2026-09-03T11:45:00+07:00",
                "expires_at": "2026-09-03T12:45:00+07:00",
                "payload": {
                    "ticker": "MBB",
                    "horizon": "SHORT_TERM",
                    "data_status": "READY",
                    "score": 82,
                },
            },
            {
                "ticker": "HPG",
                "horizon": "MEDIUM_TERM",
                "generated_at": "2026-09-03T11:45:00+07:00",
                "expires_at": "2026-09-03T12:45:00+07:00",
                "payload": {
                    "ticker": "HPG",
                    "horizon": "MEDIUM_TERM",
                    "data_status": "READY",
                    "score": 79,
                },
            },
        ],
    }


class FakeResponse:
    status = 204

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class CachePublishTests(unittest.TestCase):
    def write_fixture(self, root: Path):
        manifest = root / "stockradar.production-manifest.json"
        batch = root / "cache-batch.json"
        manifest.write_text(json.dumps(manifest_payload()), encoding="utf-8")
        batch.write_text(json.dumps(batch_payload()), encoding="utf-8")
        return manifest, batch

    def test_valid_batch_is_bound_to_manifest_hash(self):
        with TemporaryDirectory() as directory:
            manifest, batch = self.write_fixture(Path(directory))
            manifest_ref, records = load_cache_batch(manifest, batch, now=NOW)
            self.assertTrue(manifest_ref.startswith("sha256:"))
            self.assertEqual(len(manifest_ref), 71)
            self.assertEqual(len(records), 2)
            self.assertTrue(all(record.snapshot_id == SNAPSHOT_ID for record in records))
            self.assertTrue(all(record.source_manifest_ref == manifest_ref for record in records))

    def test_snapshot_mismatch_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, batch = self.write_fixture(root)
            payload = batch_payload()
            payload["snapshot_id"] = "different-snapshot"
            batch.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(CachePublishError, "snapshot does not match"):
                load_cache_batch(manifest, batch, now=NOW)

    def test_duplicate_ticker_horizon_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, batch = self.write_fixture(root)
            payload = batch_payload()
            payload["items"].append(dict(payload["items"][0]))
            batch.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(CachePublishError, "duplicate cache item"):
                load_cache_batch(manifest, batch, now=NOW)

    def test_secret_shaped_report_field_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, batch = self.write_fixture(root)
            payload = batch_payload()
            payload["items"][0]["payload"]["access_token"] = "forbidden"
            batch.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(CachePublishError, "forbidden secret-shaped field"):
                load_cache_batch(manifest, batch, now=NOW)

    def test_invalid_time_window_is_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, batch = self.write_fixture(root)
            payload = batch_payload()
            payload["items"][0]["expires_at"] = payload["items"][0]["generated_at"]
            batch.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(CachePublishError, "expires_at must be after"):
                load_cache_batch(manifest, batch, now=NOW)

    def test_publish_requires_environment_secret_and_never_cli_secret(self):
        with TemporaryDirectory() as directory:
            manifest, batch = self.write_fixture(Path(directory))
            _, records = load_cache_batch(manifest, batch, now=NOW)
            with patch.dict("os.environ", {}, clear=True):
                with self.assertRaisesRegex(CachePublishError, "SUPABASE_URL"):
                    publish_cache_records(records)

    def test_publish_calls_service_role_rpc_without_logging_secret(self):
        with TemporaryDirectory() as directory:
            manifest, batch = self.write_fixture(Path(directory))
            _, records = load_cache_batch(manifest, batch, now=NOW)
            with patch("engine.stockradar.cache_publish.urlopen", return_value=FakeResponse()) as mocked:
                published = publish_cache_records(
                    records,
                    supabase_url="https://example.supabase.co",
                    service_role_key="test-service-key",
                )
            self.assertEqual(published, 2)
            self.assertEqual(mocked.call_count, 2)
            first_request = mocked.call_args_list[0].args[0]
            self.assertTrue(first_request.full_url.endswith("/rest/v1/rpc/upsert_stockradar_cached_report"))
            self.assertNotIn(b"test-service-key", first_request.data)


if __name__ == "__main__":
    unittest.main()
