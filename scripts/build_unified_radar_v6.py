from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

EXPECTED=405
WEIGHTS={'technical_score':.21,'flow_score_v4':.14,'fundamental_domain_score_v4':.20,'valuation_domain_score_v4':.15,'sector_strength_score':.08,'market_score':.05,'supply_demand_score_v1':.05,'liquidity_score_v4':.03,'inverse_risk_score':.09}

def num(x): return pd.to_numeric(x,errors='coerce')
def build(args):
    d=pd.read_csv(args.domain); decision=pd.read_csv(args.decision); supply=pd.read_csv(args.supply); op=pd.read_csv(args.operational)
    if len(d)!=EXPECTED or d.ticker.nunique()!=EXPECTED: raise ValueError('domain !=405')
    keep_dec=['ticker','new_position_state_v5','holding_state_v5','buy_zone_low_v5','buy_zone_high_v5','position_initial_pct_v5','stop_loss_v5','downside_to_stop_pct_v5','target_near_rr2_v5','target_3_6m_v5','target_12m_v5','upside_from_entry_to_base_pct_v5','rr_to_base_v5','private_action_candidate_v5','decision_block_reasons_v5','decision_confidence_v5']
    keep_sup=['ticker','free_float_proxy_pct','float_turnover20_pct','supply_demand_score_v1','ownership_quality_score','institutional_context_ready','institutional_context_note']
    keep_op=['ticker','atr20_pct','realized_vol20_pct','max_drawdown60_pct','latest_news_age_days','latest_news_title','catalyst_data_ready','corporate_action_data_ready']
    x=d.merge(decision[keep_dec],on='ticker',how='left').merge(supply[keep_sup],on='ticker',how='left').merge(op[keep_op],on='ticker',how='left')
    x['inverse_risk_score']=100-num(x.risk_score); total=np.zeros(len(x)); covered=np.zeros(len(x)); contributions={}
    for col,w in WEIGHTS.items():
        v=num(x[col]); present=v.notna(); neutral=v.fillna(50).clip(0,100); c=neutral*w; total+=c; covered+=present.astype(float)*w
        name='contribution_'+col; x[name]=c.round(3); contributions[col]=name
    x['radar_score_v6']=total.round(2); x['factor_coverage_pct_v6']=(covered*100).round(2)
    x['catalyst_alpha_weight_v6']=0.0; x['institutional_alpha_weight_v6']=0.0; x['corporate_action_is_gate_v6']=True
    x['operational_research_ready_v6']=x.internal_research_candidate_v4.fillna(False).astype(bool)&(x.factor_coverage_pct_v6>=90)&x.supply_demand_score_v1.notna()
    x['private_action_candidate_v6']=x.private_action_candidate_v5.fillna(False).astype(bool)&x.operational_research_ready_v6
    x['public_action_allowed_v6']=False; x['public_gate_v6']='BLOCKED_PENDING_CURRENT_EVENTS_DATA_RIGHTS_COMPLIANCE_ACTIVE_MANIFEST'
    x['radar_status_v6']=np.select([x.private_action_candidate_v6,x.operational_research_ready_v6 & x.candidate_setup.astype(str).ne('WATCH'),x.operational_research_ready_v6,x.full_scan_eligible.fillna(False).astype(bool)],['PRIVATE_ACTION_CANDIDATE','SETUP_BLOCKED_BY_DECISION_GATE','RESEARCH_READY_WATCH','FULL_SCAN_ONLY'],default='DATA_OR_LIQUIDITY_BLOCKED')
    order=['ticker','company_type','business_bucket','sector_v4','price','candidate_setup','radar_score_v6','radar_status_v6','factor_coverage_pct_v6','new_position_state_v5','holding_state_v5','buy_zone_low_v5','buy_zone_high_v5','position_initial_pct_v5','stop_loss_v5','downside_to_stop_pct_v5','target_near_rr2_v5','target_3_6m_v5','target_12m_v5','upside_from_entry_to_base_pct_v5','rr_to_base_v5','technical_score','flow_score_v4','fundamental_domain_score_v4','fundamental_confidence_v4','valuation_domain_score_v4','valuation_score_confidence_v4','sector_strength_score','sector_regime','market_score','market_regime','supply_demand_score_v1','free_float_proxy_pct','float_turnover20_pct','institutional_context_ready','institutional_context_note','liquidity_score_v4','risk_score','atr20_pct','realized_vol20_pct','max_drawdown60_pct','latest_news_age_days','latest_news_title','catalyst_data_ready','corporate_action_data_ready','decision_confidence_v5','decision_block_reasons_v5','operational_research_ready_v6','private_action_candidate_v6','public_action_allowed_v6','public_gate_v6']+list(contributions.values())
    out=x[order].sort_values(['operational_research_ready_v6','radar_score_v6'],ascending=[False,False]); Path(args.output).parent.mkdir(parents=True,exist_ok=True); out.to_csv(args.output,index=False,encoding='utf-8-sig')
    manifest={'schema_version':'STOCKRADAR_UNIFIED_V6','canonical_hose':405,'weights':WEIGHTS,'institutional_alpha_weight':0,'catalyst_alpha_weight':0,'corporate_action_policy':'GATE_NOT_ALPHA','operational_research_ready':int(out.operational_research_ready_v6.sum()),'private_action_candidates':int(out.private_action_candidate_v6.sum()),'radar_status_counts':out.radar_status_v6.value_counts().to_dict(),'factor_coverage_ge90':int((out.factor_coverage_pct_v6>=90).sum()),'public_action_allowed':False,'publication_blockers':['CURRENT_AUTHORITATIVE_CORPORATE_ACTIONS','DEEP_CURRENT_CATALYSTS','DATA_RIGHTS','COMPLIANCE','ACTIVE_PRODUCTION_MANIFEST'],'note':'Ranking and recommendation are separate. Catalyst and institutional alpha remain zero until evidence depth/freshness passes; corporate actions are a gate.'}
    Path(args.manifest).write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(manifest,ensure_ascii=False))

def main():
    p=argparse.ArgumentParser()
    for k in ['domain','decision','supply','operational','output','manifest']: p.add_argument('--'+k,required=True)
    build(p.parse_args())
if __name__=='__main__':main()
