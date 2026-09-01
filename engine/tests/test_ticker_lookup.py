import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from engine.stockradar.models import Horizon
from engine.stockradar.monitoring import build_active_intraday_universe, deduplicate_subscribers
from engine.stockradar.personalization import AccountTier, enforce_watchlist_limit
from engine.stockradar.ticker_lookup import (
    DEFAULT_TTL,
    StockReportCache,
    TickerLookupService,
    TickerMaster,
    UnsupportedTickerError,
)


ROOT = Path(__file__).resolve().parents[2]


class TickerLookupV212Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.master = TickerMaster.from_path(ROOT / "engine/fixtures/hose_universe_demo.json")
        self.temp = tempfile.TemporaryDirectory()
        self.cache = StockReportCache(Path(self.temp.name) / "cache.sqlite")

    def tearDown(self) -> None:
        self.cache.close()
        self.temp.cleanup()

    def test_ticker_01_non_original_example_is_resolved_from_master(self) -> None:
        self.assertEqual(self.master.resolve(" vci ").ticker, "VCI")
        suggestions = self.master.autocomplete("H")
        self.assertTrue({"HPG", "HDB", "HCM", "HSG"}.issubset({item.ticker for item in suggestions}))

    def test_ticker_02_03_04_cache_miss_hit_and_stale_refresh(self) -> None:
        calls = []

        def generate(security, horizon):
            calls.append((security.ticker, horizon.value))
            return {"ticker": security.ticker, "horizon": horizon.value, "call": len(calls)}

        service = TickerLookupService(self.master, self.cache, generator=generate)
        now = datetime(2026, 9, 1, tzinfo=timezone.utc)
        first, first_status = service.deep_report("VCI", Horizon.SHORT_TERM, now=now)
        second, second_status = service.deep_report("VCI", Horizon.SHORT_TERM, now=now + timedelta(minutes=30))
        refreshed, refreshed_status = service.deep_report("VCI", Horizon.SHORT_TERM, now=now + timedelta(hours=2))
        self.assertEqual((first_status, second_status, refreshed_status), ("MISS", "HIT", "REFRESH"))
        self.assertEqual((first["call"], second["call"], refreshed["call"]), (1, 1, 2))

    def test_ticker_05_unknown_or_non_hose_ticker_is_not_fabricated(self) -> None:
        with self.assertRaises(UnsupportedTickerError):
            self.master.resolve("ZZZ")

    def test_ticker_06_missing_deep_data_returns_honest_quick_result(self) -> None:
        report = TickerLookupService(self.master, self.cache).quick_report("VCI")
        self.assertEqual(report["data_status"], "INSUFFICIENT")
        self.assertIsNone(report["current_price"])
        self.assertEqual(report["holding_state"], "CHƯA ĐỦ DỮ LIỆU")

    def test_ticker_07_subscriber_fanout_has_one_monitoring_pipeline(self) -> None:
        rows = [("HPG", f"user-{index}") for index in range(1000)]
        subscribers = deduplicate_subscribers(rows)
        self.assertEqual(set(subscribers), {"HPG"})
        self.assertEqual(len(subscribers["HPG"]), 1000)

    def test_ticker_08_free_watchlist_limit_is_enforced_and_deduplicated(self) -> None:
        self.assertEqual(enforce_watchlist_limit(AccountTier.FREE, ["HPG"], "HPG"), ("HPG",))
        with self.assertRaisesRegex(ValueError, "WATCHLIST_LIMIT_REACHED:3"):
            enforce_watchlist_limit(AccountTier.FREE, ["HPG", "MBB", "FPT"], "VCI")

    def test_ticker_09_reference_lookup_cannot_pass_full_universe_gate(self) -> None:
        self.assertFalse(self.master.can_support_full_hose_claim())

    def test_ticker_11_horizon_cache_ttls_are_independent(self) -> None:
        self.assertLess(DEFAULT_TTL[Horizon.SHORT_TERM], DEFAULT_TTL[Horizon.MEDIUM_TERM])
        self.assertLess(DEFAULT_TTL[Horizon.MEDIUM_TERM], DEFAULT_TTL[Horizon.ACCUMULATION])

    def test_active_intraday_universe_is_union_and_deduplicated(self) -> None:
        active = build_active_intraday_universe(
            ["HPG", "MBB"], ["HPG", "VCI"], ["HPG", "FPT"], ["HPG", "FPT"]
        )
        self.assertEqual(set(active), {"HPG", "MBB", "VCI", "FPT"})
        self.assertTrue(active["HPG"].recommendation)
        self.assertEqual(active["HPG"].subscriber_count, 2)


if __name__ == "__main__":
    unittest.main()
