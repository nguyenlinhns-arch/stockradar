import unittest
import pandas as pd
from scripts.build_decision_layer_v5 import horizon_forecasts

class HorizonForecastTests(unittest.TestCase):
    def test_base_and_bull_are_not_automatically_assigned_holding_periods(self):
        result=horizon_forecasts(pd.DataFrame([{'fair_value_domain_base_v4':24117,'fair_value_domain_bull_v4':29122}]))
        self.assertTrue(result.isna().all().all())

    def test_each_horizon_requires_its_own_verified_forecast(self):
        result=horizon_forecasts(pd.DataFrame([
            {'forecast_3_6m':24000,'forecast_3_6m_verified':True,'forecast_12m':30000,'forecast_12m_verified':False},
            {'forecast_3_6m':24000,'forecast_3_6m_verified':False,'forecast_12m':30000,'forecast_12m_verified':True}]))
        self.assertEqual(result.iloc[0].target_3_6m_v5,24000)
        self.assertTrue(pd.isna(result.iloc[0].target_12m_v5))
        self.assertTrue(pd.isna(result.iloc[1].target_3_6m_v5))
        self.assertEqual(result.iloc[1].target_12m_v5,30000)
