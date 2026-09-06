"""Synthetic local fixtures; never uploaded to market/cache/provider services."""
from argparse import Namespace
from pathlib import Path
import json
import tempfile
import unittest

import pandas as pd

from scripts.bootstrap_kbs_hose_data import compute_technical
from scripts.validate_intraday_scan_sla import validate


class IntradayObservationTests(unittest.TestCase):
    def setUp(self):
        self.now = pd.Timestamp("2026-09-04T10:35:00+07:00")
        dates = pd.bdate_range(end="2026-09-03", periods=230)
        closes = [100+i % 2 for i in range(230)]
        self.daily = pd.DataFrame(dict(ticker="HPG", timestamp=dates, open=closes,
            high=[v+1 for v in closes], low=[v-1 for v in closes], close=closes, volume=1000.))
        # An old down-volume spike lies outside the last ten sessions.
        self.daily.loc[200, "volume"] = 1000000.
        self.intraday = pd.DataFrame([dict(ticker="HPG", timestamp=f"{d.date()} 10:30:00", volume=100.)
            for d in dates[-20:]]+[dict(ticker="HPG", timestamp="2026-09-04 10:30:00", volume=500.)])
        self.board = pd.DataFrame([dict(ticker="HPG", source_time_ms=int(self.now.timestamp()*1000), price=102., total_volume=999999.)])

    def row(self):
        return compute_technical(self.daily, self.intraday, self.board, now=self.now).iloc[0]

    def test_projection_is_not_pocket_pivot_confirmation(self):
        row = self.row()
        self.assertEqual(row.max_down_volume_10, 1000.)
        self.assertGreater(row.rvol_progress_adjusted, 1.)
        self.assertTrue(row.pocket_pivot_volume_pass_intraday_projection)
        self.assertFalse(row.pocket_pivot_volume_pass)
        self.intraday.loc[len(self.intraday)-1, "volume"] = 1500.
        self.assertTrue(self.row().pocket_pivot_volume_pass)

    def test_previous_session_volume_cannot_be_current_volume(self):
        self.intraday = self.intraday.iloc[:-1]
        row = self.row()
        self.assertIsNone(row.current_cum_volume)
        self.assertIsNone(row.rvol_progress_adjusted)
        self.assertFalse(row.pocket_pivot_volume_pass)

    def test_future_or_stale_intraday_bars_are_not_used(self):
        for timestamp in ("2026-09-04 11:00:00", "2026-09-04 09:00:00"):
            with self.subTest(timestamp=timestamp):
                self.intraday.loc[len(self.intraday)-1, "timestamp"] = timestamp
                self.assertIsNone(self.row().current_cum_volume)

    def test_missing_history_never_uses_naive_full_day_rvol(self):
        self.intraday = self.intraday.iloc[-2:]
        self.assertIsNone(self.row().rvol_progress_adjusted)
        self.assertIsNone(self.row().same_time_volume_ratio)

    def test_current_daily_partial_bar_excluded_from_ma_and_vol20(self):
        expected = self.row()
        self.daily = pd.concat([self.daily, pd.DataFrame([dict(ticker="HPG", timestamp="2026-09-04", open=500, high=501, low=499, close=500, volume=99999999)])])
        actual = self.row()
        for field in ("vol20", "ma10", "ma50", "ma200", "max_down_volume_10"):
            self.assertEqual(actual[field], expected[field])

    def test_missing_or_future_quote_is_labelled_eod_and_cannot_confirm(self):
        for source_time in (None, int((self.now+pd.Timedelta(hours=1)).timestamp()*1000)):
            with self.subTest(source_time=source_time):
                self.board["source_time_ms"] = source_time
                row = self.row()
                self.assertEqual(row.price_snapshot_kind, "EOD_REFERENCE")
                self.assertFalse(row.pocket_pivot_volume_pass)

    def test_invalid_quote_price_never_borrows_fresh_timestamp(self):
        for price in (None, 0, float('inf')):
            self.board['price'] = price
            row = self.row()
            self.assertFalse(row.intraday_quote_fresh)
            self.assertEqual(row.price_snapshot_kind, 'EOD_REFERENCE')

    def test_intraday_pivot_includes_latest_completed_session(self):
        self.daily.loc[self.daily.index[-1], 'high'] = 110.
        self.assertEqual(self.row().pivot20, 110.)


class ScanEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = "2026-09-04T10:35:00+07:00"
        self.args = Namespace(now=self.now, checkpoint="10:30", **{
            k: self.root/(k+".json" if k.endswith("coverage") or k=="scanner_qa" else k+".csv")
            for k in ("market_coverage", "fundamental_coverage", "scanner_qa", "scanner", "intraday", "security_master")})
        self.write_json("market_coverage", dict(as_of=self.now, source="KBS_PUBLIC_BOOTSTRAP_INTERNAL_ONLY", universe_count=2, daily_covered=2, board_covered=2))
        self.write_json("fundamental_coverage", dict(as_of="2026-09-04T09:00:00+07:00", finance_tickers_covered=2))
        self.write_json("scanner_qa", dict(canonical_hose_count=2, public_gate=dict(allowed=False)))
        pd.DataFrame(dict(ticker=["HPG", "C32"], exchange="HOSE")).to_csv(self.args.security_master, index=False)
        pd.DataFrame(dict(ticker=["HPG", "C32"], liquidity_pass_500k=[True, True], source_time_ms=int(pd.Timestamp(self.now).timestamp()*1000))).to_csv(self.args.scanner, index=False)
        self.bars = pd.DataFrame(dict(ticker=["HPG", "C32"], timestamp=["2026-09-04 10:30:00"]*2))

    def write_json(self, key, value):
        getattr(self.args, key).write_text(json.dumps(value), encoding="utf-8")

    def check(self):
        self.bars.to_csv(self.args.intraday, index=False)
        return validate(self.args)

    def test_every_official_checkpoint_can_pass_with_observed_current_bars(self):
        for checkpoint in ("10:30", "11:15", "13:30", "14:15"):
            self.args.checkpoint=checkpoint
            self.args.now=f"2026-09-04T{checkpoint}:00+07:00"
            self.bars.timestamp=f"2026-09-04 {checkpoint}:00"
            frame=pd.read_csv(self.args.scanner)
            frame.source_time_ms=int(pd.Timestamp(self.args.now).timestamp()*1000)
            frame.to_csv(self.args.scanner, index=False)
            self.write_json("market_coverage", dict(as_of=self.args.now, source="KBS", universe_count=2, daily_covered=2, board_covered=2))
            self.assertTrue(self.check()["internal_scan_ready"])

    def test_one_stale_ticker_blocks_even_if_other_ticker_is_fresh(self):
        self.bars.loc[1, "timestamp"]="2026-09-03 14:45:00"
        result=self.check()
        self.assertFalse(result["internal_scan_ready"])
        self.assertEqual(result["stale_liquid_intraday_tickers"], ["C32"])

    def test_future_timestamp_blocks(self):
        self.bars.loc[1,"timestamp"]="2026-09-04 10:36:00"
        self.assertFalse(self.check()["internal_scan_ready"])

    def test_eod_never_impersonates_nearest_checkpoint(self):
        self.args.checkpoint="EOD_RESEARCH"
        result=self.check()
        self.assertTrue(result["internal_research_ready"])
        self.assertFalse(result["internal_scan_ready"])

    def test_early_late_and_weekend_scans_do_not_prove_checkpoint(self):
        for now in ("2026-09-04T10:29:00+07:00", "2026-09-04T11:10:00+07:00", "2026-09-06T10:35:00+07:00"):
            self.args.now=now
            self.assertFalse(self.check()["internal_scan_ready"])

    def test_non_hose_and_mock_sources_block(self):
        pd.DataFrame(dict(ticker=["HPG", "C32"], exchange=["HOSE", "HNX"])).to_csv(self.args.security_master,index=False)
        self.assertFalse(self.check()["internal_scan_ready"])
        self.write_json("market_coverage", dict(as_of=self.now, source="MOCK", universe_count=2, daily_covered=2, board_covered=2))
        self.assertFalse(self.check()["assertions"]["source_identified_non_mock"])

    def test_missing_source_quote_time_blocks(self):
        frame=pd.read_csv(self.args.scanner).drop(columns=["source_time_ms"])
        frame.to_csv(self.args.scanner,index=False)
        self.assertFalse(self.check()["internal_scan_ready"])
