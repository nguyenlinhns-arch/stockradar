from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

EXPECTED_HOSE=405
BUY_SETUPS={'POCKET_PIVOT','EARLY_BREAKOUT','CONFIRMED_BREAKOUT'}

def n(x): return pd.to_numeric(x, errors='coerce')
def setup_family(value): return str(value or '').strip().upper().removesuffix('_CANDIDATE')
def position_pct(setup): return {'POCKET_PIVOT':17.5,'EARLY_BREAKOUT':25.0,'CONFIRMED_BREAKOUT':50.0}.get(setup_family(setup),0.0)

def horizon_forecasts(frame):
    """A valuation scenario is not a forecast for a holding period."""
    result={}
    for horizon in ('3_6m','12m'):
        verified=frame.get('forecast_'+horizon+'_verified',pd.Series(False,index=frame.index)).eq(True)
        values=n(frame.get('forecast_'+horizon,pd.Series(np.nan,index=frame.index)))
        result['target_'+horizon+'_v5']=values.where(verified & values.gt(0))
    return pd.DataFrame(result,index=frame.index)

def setup_buy_zone(row):
    setup=setup_family(row.candidate_setup)
    price=float(row.price) if pd.notna(row.price) else np.nan
    pivot=float(row.pivot20) if pd.notna(row.pivot20) else np.nan
    ma10=float(row.ma10) if pd.notna(row.ma10) else np.nan
    ma50=float(row.ma50) if pd.notna(row.ma50) else np.nan
    if pd.isna(price): return (np.nan,np.nan)
    if setup=='POCKET_PIVOT':
        anchors=[v for v in (ma10,ma50,price) if pd.notna(v) and v>0]
        anchor=max([v for v in anchors if v<=price*1.03], default=price)
        return anchor*0.99, min(price*1.015,anchor*1.025)
    if setup=='EARLY_BREAKOUT' and pd.notna(pivot) and pivot>0: return pivot*0.99,pivot*1.015
    if setup=='CONFIRMED_BREAKOUT' and pd.notna(pivot) and pivot>0: return pivot,pivot*1.025
    return np.nan,np.nan

def holding_state(row):
    price=row.price; ma50=row.ma50; ma200=row.ma200; stage=str(row.stage); setup=setup_family(row.candidate_setup)
    if pd.isna(price): return 'KHONG_DU_DU_LIEU'
    if stage=='STAGE_4': return 'HA_TY_TRONG_HOAC_BAN'
    if pd.notna(ma200) and price < ma200*0.97: return 'HA_TY_TRONG_HOAC_BAN'
    if pd.notna(ma50) and price < ma50*0.97: return 'HA_TY_TRONG'
    if setup=='CONFIRMED_BREAKOUT' and stage=='STAGE_2': return 'GIU_NHOI_NEU_DANG_CO_LAI_VA_RUI_RO_CHO_PHEP'
    if stage in {'STAGE_2','STAGE_1_TO_2'}: return 'GIU'
    return 'GIU_QUAN_SAT'

def build(args):
    scanner=pd.read_csv(args.scanner); domain=pd.read_csv(args.domain); operational=pd.read_csv(args.operational)
    if len(scanner)!=EXPECTED_HOSE or scanner.ticker.nunique()!=EXPECTED_HOSE: raise ValueError('scanner must be 405 unique HOSE')
    d=domain.merge(scanner[['ticker','price','pct_change','vol20','rvol_progress_adjusted','same_time_volume_ratio','stage','ma10','ma50','ma150','ma200','pivot20','distance_to_pivot_pct','candidate_setup','pocket_pivot_volume_pass']],on='ticker',how='left',suffixes=('','_scanner'))
    d=d.merge(operational[['ticker','atr20_pct','realized_vol20_pct','max_drawdown60_pct','latest_news_age_days','corporate_action_data_ready']],on='ticker',how='left')
    for col in ['price','vol20','candidate_setup']:
        alt=col+'_scanner'
        if alt in d.columns: d[col]=d[col].where(d[col].notna(),d[alt])
    zones=d.apply(setup_buy_zone,axis=1,result_type='expand'); d['buy_zone_low_v5']=zones[0]; d['buy_zone_high_v5']=zones[1]
    d['entry_reference_v5']=(n(d.buy_zone_low_v5)+n(d.buy_zone_high_v5))/2
    atr=n(d.atr20_pct).fillna(3.5); d['stop_pct_v5']=(1.5*atr/100).clip(lower=.05,upper=.08)
    d['stop_loss_v5']=d.entry_reference_v5*(1-d.stop_pct_v5)
    d['downside_to_stop_pct_v5']=(d.stop_loss_v5/d.entry_reference_v5-1)*100
    d['target_near_rr2_v5']=d.entry_reference_v5+2*(d.entry_reference_v5-d.stop_loss_v5)
    d['research_value_base_v5']=n(d.fair_value_domain_base_v4)
    d['research_value_bull_v5']=n(d.fair_value_domain_bull_v4)
    forecasts=horizon_forecasts(d)
    d['target_3_6m_v5']=forecasts.target_3_6m_v5; d['target_12m_v5']=forecasts.target_12m_v5
    risk=d.entry_reference_v5-d.stop_loss_v5
    d['rr_to_base_v5']=(d.research_value_base_v5-d.entry_reference_v5)/risk.replace(0,np.nan)
    d['upside_from_entry_to_base_pct_v5']=(d.research_value_base_v5/d.entry_reference_v5-1)*100
    d['position_initial_pct_v5']=d.candidate_setup.map(position_pct).fillna(0)
    d['holding_state_v5']=d.apply(holding_state,axis=1)
    d['new_position_state_v5']='THEO_DOI'; reasons=[]
    for idx,r in d.iterrows():
        reason=[]; setup=setup_family(r.candidate_setup)
        if not bool(r.internal_research_candidate_v4): reason.append('FAIL_RESEARCH_QUALITY_GATE')
        if setup not in BUY_SETUPS: reason.append('NO_BUY_SETUP')
        if setup in BUY_SETUPS and not bool(r.intraday_action_gate_v4): reason.append('INTRADAY_NOT_READY')
        if pd.isna(r.entry_reference_v5) or pd.isna(r.stop_loss_v5): reason.append('MISSING_ACTION_MAP')
        if pd.isna(r.valuation_score_confidence_v4) or r.valuation_score_confidence_v4<45: reason.append('VALUATION_CONFIDENCE_LOW')
        if pd.isna(r.upside_from_entry_to_base_pct_v5) or r.upside_from_entry_to_base_pct_v5<10: reason.append('UPSIDE_TOO_LOW')
        if pd.isna(r.rr_to_base_v5) or r.rr_to_base_v5<2: reason.append('RR_BELOW_2')
        if pd.notna(r.price) and pd.notna(r.ma50) and r.price/r.ma50-1>0.10: reason.append('EXTENDED_OVER_MA50')
        if str(r.market_regime)=='RUI_RO_CAO': reason.append('MARKET_RISK_HIGH')
        if not bool(r.corporate_action_data_ready): reason.append('CURRENT_CORPORATE_ACTION_UNVERIFIED')
        pure=[x for x in reason if x!='CURRENT_CORPORATE_ACTION_UNVERIFIED']
        if not pure and setup=='POCKET_PIVOT': state='MUA_SOM_15_20'
        elif not pure and setup=='EARLY_BREAKOUT': state='MUA_THAM_DO_20_30'
        elif not pure and setup=='CONFIRMED_BREAKOUT': state='MUA_HOAC_NHOI_40_60'
        else: state='THEO_DOI_KHONG_HANH_DONG'
        d.loc[idx,'new_position_state_v5']=state; reasons.append('|'.join(reason) if reason else 'PASS_PRIVATE_DECISION_GATE')
    d['decision_block_reasons_v5']=reasons
    d['private_action_candidate_v5']=d.new_position_state_v5.isin({'MUA_SOM_15_20','MUA_THAM_DO_20_30','MUA_HOAC_NHOI_40_60'})
    d['publication_state_v5']='BLOCKED_PENDING_CURRENT_CORPORATE_ACTIONS_DATA_RIGHTS_COMPLIANCE'; d['public_action_allowed_v5']=False
    d['decision_confidence_v5']=(.35*n(d.fundamental_confidence_v4).fillna(0)+.35*n(d.valuation_score_confidence_v4).fillna(0)+.30*n(d.data_quality_score).fillna(0)).round(2)
    keep=['ticker','company_type','business_bucket','sector_v4','price','candidate_setup','radar_rank_score_v4','decision_confidence_v5','new_position_state_v5','holding_state_v5','buy_zone_low_v5','buy_zone_high_v5','position_initial_pct_v5','stop_loss_v5','downside_to_stop_pct_v5','target_near_rr2_v5','target_3_6m_v5','target_12m_v5','upside_from_entry_to_base_pct_v5','rr_to_base_v5','rvol_progress_adjusted','same_time_volume_ratio','stage','market_regime','sector_regime','risk_score','internal_research_candidate_v4','private_action_candidate_v5','decision_block_reasons_v5','publication_state_v5','public_action_allowed_v5']
    keep += ['research_value_base_v5','research_value_bull_v5']
    out=d[keep].sort_values(['private_action_candidate_v5','radar_rank_score_v4'],ascending=[False,False]); Path(args.output).parent.mkdir(parents=True,exist_ok=True); out.to_csv(args.output,index=False,encoding='utf-8-sig')
    summary={'schema_version':'STOCKRADAR_DECISION_V5','canonical_hose':405,'private_action_candidates':int(out.private_action_candidate_v5.sum()),'new_position_states':out.new_position_state_v5.value_counts().to_dict(),'holding_states':out.holding_state_v5.value_counts().to_dict(),'public_action_allowed':False,'required_public_gates':['CURRENT_CORPORATE_ACTIONS','DATA_RIGHTS','COMPLIANCE','ACTIVE_PRODUCTION_MANIFEST'],'risk_policy':'Stop 5-8% adjusted by 1.5x ATR; buy requires R:R to Base Fair Value >=2 and >=10% upside from entry.','position_policy':{'POCKET_PIVOT':'15-20%','EARLY_BREAKOUT':'20-30%','CONFIRMED_BREAKOUT':'40-60%'}}
    Path(args.manifest).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(summary,ensure_ascii=False))

def main():
    p=argparse.ArgumentParser()
    for name in ['scanner','domain','operational','output','manifest']: p.add_argument('--'+name.replace('_','-'),dest=name,required=True)
    build(p.parse_args())
if __name__=='__main__': main()
