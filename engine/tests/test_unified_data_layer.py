from datetime import datetime, timezone
import unittest
import pandas as pd

from engine.stockradar.data_layer import keyed, number, validate_history


class UnifiedDataLayerTests(unittest.TestCase):
    def bars(self):
        return pd.DataFrame([dict(ticker='HPG', timestamp='2026-09-01',open=20,high=22,low=19,close=21,volume=500000)])

    def test_missing_numbers_remain_missing(self):
        for value in (None,'',True,False,float('nan'),float('inf'),'unknown'):
            self.assertIsNone(number(value))
        self.assertEqual(number(0),0)

    def test_duplicate_date_and_non_hose_are_blocked(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE_TRADING_DATE'):
            validate_history(pd.concat([self.bars(),self.bars()]),{'HPG'},'2026-09-01')
        with self.assertRaisesRegex(ValueError,'NON_HOSE_TICKER'):
            validate_history(self.bars(),{'FPT'},'2026-09-01')

    def test_invalid_ohlcv_quarantined(self):
        for key,value in [('high',18),('open',23),('close',18),('volume',-1),('close',float('nan'))]:
            frame=self.bars();frame[key]=value
            valid,issues=validate_history(frame,{'HPG'},'2026-09-01')
            self.assertTrue(valid.empty)
            self.assertEqual(len(issues),1)

    def test_future_and_missing_timestamp_blocked(self):
        with self.assertRaisesRegex(ValueError,'FUTURE_TRADING_DATE'):
            validate_history(self.bars(),{'HPG'},'2026-08-31')
        frame=self.bars();frame['timestamp']=None
        with self.assertRaisesRegex(ValueError,'MISSING_OR_INVALID_TIMESTAMP'):
            validate_history(frame,{'HPG'},'2026-09-01')

    def test_duplicate_detail_ticker_blocked(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE_TICKER'):
            keyed(pd.DataFrame([{'ticker':'HPG'},{'ticker':'HPG'}]),{'HPG'})
