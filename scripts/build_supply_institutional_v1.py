from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

EXPECTED=405
ASOF=pd.Timestamp('2026-09-04')

def n(x): return pd.to_numeric(x,errors='coerce')
def pct_rank(s, higher=True):
    x=n(s); r=x.rank(pct=True,method='average')*100
    return r if higher else 100-r

def build(args):
    p=pd.read_csv(args.profile); s=pd.read_csv(args.snapshot); sc=pd.read_csv(args.scanner)
    if len(p)!=EXPECTED or p.ticker.nunique()!=EXPECTED: raise ValueError('profile !=405')
    d=p.merge(s[['ticker','foreign_buy_volume','foreign_sell_volume','total_volume','foreign_ownership','foreign_room']],on='ticker',how='left').merge(sc[['ticker','vol20','liquidity_pass_500k']],on='ticker',how='left')
    d['ownership_asof_dt']=pd.to_datetime(d.ownership_asof,errors='coerce'); d['ownership_age_days']=(ASOF-d.ownership_asof_dt).dt.days
    d['ownership_fresh_18m']=d.ownership_age_days.between(0,548,inclusive='both')
    major=n(d.major_shareholders_reported_pct).clip(0,100); d['free_float_proxy_pct']=(100-major).clip(lower=3,upper=100)
    d['free_float_proxy_shares']=n(d.outstanding_shares_profile)*d.free_float_proxy_pct/100
    d['float_turnover20_pct']=n(d.vol20)/d.free_float_proxy_shares.replace(0,np.nan)*100
    d['foreign_net_volume_snapshot']=n(d.foreign_buy_volume).fillna(0)-n(d.foreign_sell_volume).fillna(0)
    d['foreign_net_flow_pct_volume_snapshot']=d.foreign_net_volume_snapshot/n(d.total_volume).replace(0,np.nan)*100
    scarcity=pct_rank(np.log10(d.free_float_proxy_shares.clip(lower=1)),higher=False); turnover=pct_rank(d.float_turnover20_pct,higher=True)
    flow=((d.foreign_net_flow_pct_volume_snapshot+5)/10*100).clip(0,100).fillna(50); liquid=d.liquidity_pass_500k.fillna(False).astype(bool)
    d['supply_demand_score_v1']=(.45*scarcity+.45*turnover+.10*flow).where(liquid)
    d['ownership_quality_score']=0.0
    d.loc[d.ownership_asof_dt.notna(),'ownership_quality_score']+=25; d.loc[d.ownership_fresh_18m,'ownership_quality_score']+=35
    d.loc[n(d.major_shareholders_reported_pct).between(0,100),'ownership_quality_score']+=20; d.loc[n(d.outstanding_shares_profile)>0,'ownership_quality_score']+=20
    disclosed=(n(d.foreign_ownership_profile_pct)>0)|(n(d.institutional_ownership_profile_pct)>0)
    d['institutional_disclosure_present']=disclosed; d['institutional_context_ready']=d.ownership_fresh_18m&disclosed
    d['institutional_context_note']=np.where(d.institutional_context_ready,'DISCLOSED_OWNERSHIP_CONTEXT_ONLY','INSUFFICIENT_OR_STALE_INSTITUTIONAL_EVIDENCE')
    d['institutional_alpha_weight_allowed']=False
    keep=['ticker','ownership_asof','ownership_age_days','ownership_fresh_18m','foreign_ownership_profile_pct','institutional_ownership_profile_pct','major_shareholders_reported_pct','top_shareholder_pct','free_float_proxy_pct','free_float_proxy_shares','vol20','float_turnover20_pct','foreign_buy_volume','foreign_sell_volume','foreign_net_volume_snapshot','foreign_net_flow_pct_volume_snapshot','supply_demand_score_v1','ownership_quality_score','institutional_disclosure_present','institutional_context_ready','institutional_context_note','institutional_alpha_weight_allowed']
    out=d[keep].sort_values('supply_demand_score_v1',ascending=False,na_position='last'); Path(args.output).parent.mkdir(parents=True,exist_ok=True); out.to_csv(args.output,index=False,encoding='utf-8-sig')
    manifest={'schema_version':'STOCKRADAR_SUPPLY_INSTITUTIONAL_V1','canonical_hose':405,'ownership_fresh_18m':int(out.ownership_fresh_18m.sum()),'institutional_context_ready':int(out.institutional_context_ready.sum()),'supply_demand_score_coverage':int(out.supply_demand_score_v1.notna().sum()),'institutional_alpha_weight_allowed':False,'notes':['Free-float is a proxy derived from reported major shareholder percentage, not an exchange-certified free-float field.','One-snapshot foreign flow is only 10% of S score and is not treated as institutional trend.','Institutional ownership zeros may mean unavailable/undisclosed; missing evidence never becomes a negative institutional score.']}
    Path(args.manifest).write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(manifest,ensure_ascii=False))

def main():
    p=argparse.ArgumentParser()
    for x in ['profile','snapshot','scanner','output','manifest']: p.add_argument('--'+x,required=True)
    build(p.parse_args())
if __name__=='__main__': main()
