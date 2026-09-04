from __future__ import annotations
import argparse, json, math, re
from pathlib import Path
import numpy as np
import pandas as pd

EXPECTED_HOSE=405
FIN_TYPES={'Ngân hàng','Công ty chứng khoán','Công ty bảo hiểm'}
CYCLE_SECTORS={'Vật liệu xây dựng','Khai khoáng','SX Nhựa - Hóa chất'}
SECTOR_OVERRIDES={'ADG':'Truyền thông - Quảng cáo','CLC':'Hàng tiêu dùng','YEG':'Truyền thông - Giải trí'}


def num(s): return pd.to_numeric(s, errors='coerce')
def clip(x,lo=0,hi=100): return np.clip(x,lo,hi)

def scale_series(s, lo, hi, inverse=False):
    x=(num(s)-lo)/(hi-lo)*100
    x=x.clip(0,100)
    return 100-x if inverse else x

def band_score(s, center, width, floor=0):
    x=num(s)
    score=100-(x-center).abs()/width*50
    return score.clip(floor,100)

def group_percentile(df,col,sector_col='sector_v4',higher=True,min_group=8):
    x=num(df[col])
    ranks=x.groupby(df[sector_col]).rank(pct=True, method='average')*100
    if not higher: ranks=100-ranks
    sizes=df.groupby(sector_col)[col].transform(lambda z:z.notna().sum())
    conf=(sizes/min_group).clip(upper=1)
    return 50+(ranks-50)*conf

def weighted_mean(df, pairs, neutral=50):
    total=np.zeros(len(df), dtype=float); weights=np.zeros(len(df),dtype=float); avail=np.zeros(len(df),dtype=float)
    for col,w in pairs:
        vals=num(df[col])
        present=vals.notna().to_numpy()
        total += vals.fillna(neutral).to_numpy()*w
        weights += w
        avail += present*w
    return total/weights, avail/weights*100

def select_metric(df, kind):
    names=df['item_name_vi'].fillna(''); vals=num(df['value'])
    pats={
      'net_income':[r'Lợi nhuận sau thuế của cổ đông của Công ty mẹ',r'Lợi nhuận sau thuế của cổ đông của Ngân hàng mẹ',r'Lợi nhuận sau thuế phân bổ cho chủ sở hữu',r'Lợi nhuận sau thuế thu nhập doanh nghiệp',r'XIII\. Lợi nhuận sau thuế'],
      'cfo':[r'^Lưu chuyển tiền thuần từ hoạt động kinh doanh$',r'I - Lưu chuyển tiền thuần từ hoạt động kinh doanh',r'Lưu chuyển tiền thuần từ hoạt động kinh doanh chứng khoán'],
      'capex':[r'Tiền chi để mua sắm, xây dựng TSCĐ',r'Mua sắm tài sản cố định'],
    }[kind]
    for pat in pats:
        mask=names.str.contains(pat,case=False,na=False,regex=True)&vals.notna()
        if mask.any():
            sub=df.loc[mask].copy(); sub['_v']=num(sub['value']); idx=sub['_v'].abs().idxmax(); return float(sub.loc[idx,'_v'])
    return np.nan

def build_annual(financial):
    f=financial[financial['report_key'].astype(str).str.endswith('_Y_P1')].copy()
    f['year']=num(f['year']); f=f[f.year.between(2022,2025)]
    rows=[]
    for (ticker,year),g in f.groupby(['ticker','year']):
        rows.append({'ticker':ticker,'year':int(year),'net_income':select_metric(g,'net_income'),'cfo':select_metric(g,'cfo'),'capex':select_metric(g,'capex')})
    a=pd.DataFrame(rows); a['owner_earnings']=a['cfo']-a['capex'].abs(); a['fcf_conversion']=a['owner_earnings']/a['net_income'].replace(0,np.nan)
    m=a[a.year>=2023].groupby('ticker').agg(
      oe_years=('owner_earnings','count'),ni_years=('net_income','count'),owner_earnings_median_3y=('owner_earnings','median'),net_income_median_3y=('net_income','median'),
      cfo_median_3y=('cfo','median'),capex_abs_median_3y=('capex',lambda s:s.abs().median()),fcf_conversion_median_3y=('fcf_conversion','median'),
      owner_earnings_positive_years=('owner_earnings',lambda s:int((s>0).sum())),net_income_positive_years=('net_income',lambda s:int((s>0).sum()))).reset_index()
    return a,m

def dcf(cf,shares,g,r,tg,years=10):
    if pd.isna(cf) or pd.isna(shares) or cf<=0 or shares<=0 or r<=tg:return np.nan
    cash=float(cf); pv=0
    for t in range(1,years+1):
        cash*=1+g; pv+=cash/(1+r)**t
    pv+=cash*(1+tg)/(r-tg)/(1+r)**years
    return pv/shares

def ratio_score(curr,med):
    if pd.isna(curr) or pd.isna(med) or curr<=0 or med<=0:return np.nan
    r=curr/med
    return float(np.interp(r,[0.4,0.6,1.0,1.4,1.8,2.5],[100,95,65,30,5,0]))

def payback_score(v,bucket):
    if pd.isna(v) or v<=0:return np.nan
    xs=[3,7,10,14,20,30,50] if bucket in {'BANK','SECURITIES','INSURANCE'} else [3,6,9,14,20,30,60]
    ys=[100,95,82,65,45,25,5]
    return float(np.interp(v,xs,ys,left=100,right=0))

def weighted_values(row, values):
    parts=[]
    for col,w in values:
        v=row.get(col,np.nan)
        if pd.notna(v) and float(v)>0: parts.append((float(v),w))
    if not parts:return np.nan,0
    sw=sum(w for _,w in parts); return sum(v*w for v,w in parts)/sw, sw/sum(w for _,w in values)*100

def build(args):
    fund=pd.read_csv(args.fundamental); profile=pd.read_csv(args.profile); status=pd.read_csv(args.status); scanner=pd.read_csv(args.scanner); val=pd.read_csv(args.valuation); financial=pd.read_csv(args.financial,compression='infer'); sector=pd.read_csv(args.sector); op=pd.read_csv(args.operational)
    if len(scanner)!=EXPECTED_HOSE or scanner.ticker.nunique()!=EXPECTED_HOSE: raise ValueError('scanner universe !=405')
    status['sector_v4']=status.apply(lambda r:SECTOR_OVERRIDES.get(str(r.ticker),r.sector),axis=1)
    a,m=build_annual(financial)
    cols_s=['ticker','sector_v4']; cols_p=['ticker','company_type','outstanding_shares_profile','audit_firm','institutional_ownership_profile_pct','foreign_ownership_profile_pct','top_shareholder_pct']
    df=fund.merge(profile[cols_p],on='ticker',how='left').merge(status[cols_s],on='ticker',how='left').merge(scanner,on='ticker',how='left',suffixes=('','_scan')).merge(val[['ticker','fv_pe_bootstrap','fv_pb_bootstrap','fair_value_bootstrap_bear','fair_value_bootstrap_base','fair_value_bootstrap_bull','valuation_model_status']],on='ticker',how='left').merge(m,on='ticker',how='left').merge(sector.rename(columns={'sector':'sector_join_v4'})[['sector_join_v4','sector_strength_score','sector_regime']],left_on='sector_v4',right_on='sector_join_v4',how='left').drop(columns=['sector_join_v4']).merge(op[['ticker','market_score','market_regime','risk_score','intraday_5m_ready','data_quality_score']],on='ticker',how='left')
    df['business_bucket']=np.select([df.company_type.eq('Ngân hàng'),df.company_type.eq('Công ty chứng khoán'),df.company_type.eq('Công ty bảo hiểm'),df.sector_v4.eq('Bất động sản'),df.sector_v4.isin(CYCLE_SECTORS)],['BANK','SECURITIES','INSURANCE','REAL_ESTATE','CYCLICAL'],default='GENERAL')
    df['market_cap']=num(df.price)*num(df.outstanding_shares_profile)
    df['normalized_earnings_for_payback']=np.nan; df['payback_model']='UNAVAILABLE'
    general=~df.company_type.isin(FIN_TYPES); oe_good=general&(num(df.oe_years)>=2)&(num(df.owner_earnings_median_3y)>0)&num(df.fcf_conversion_median_3y).between(.25,2.5)
    df.loc[oe_good,'normalized_earnings_for_payback']=df.loc[oe_good,'owner_earnings_median_3y']; df.loc[oe_good,'payback_model']='OWNER_EARNINGS_3Y_MEDIAN'
    fallback=general&~oe_good&(num(df.net_income_median_3y)>0); df.loc[fallback,'normalized_earnings_for_payback']=df.loc[fallback,'net_income_median_3y']; df.loc[fallback,'payback_model']='CORE_EARNINGS_PROXY_CAPEX_DISTORTION'
    finance=df.company_type.isin(FIN_TYPES)&(num(df.net_income_median_3y)>0); df.loc[finance,'normalized_earnings_for_payback']=df.loc[finance,'net_income_median_3y']; df.loc[finance,'payback_model']='CORE_EARNINGS_PROXY_FINANCIAL'
    df['payback_years']=df.market_cap/num(df.normalized_earnings_for_payback); df['payback_score']= [payback_score(v,b) for v,b in zip(df.payback_years,df.business_bucket)]
    for col,higher in [('roe_ttm_avg_8q_pct',True),('roa_ttm_avg_8q_pct',True),('gross_margin_pct',True),('pbt_growth_yoy_pct',True),('pbt_growth_3y_avg_pct',True),('revenue_growth_yoy_pct',True),('revenue_growth_3y_avg_pct',True),('equity_growth_3y_avg_pct',True),('debt_to_equity',False),('bank_cir_pct',False),('bank_operating_profit_growth_yoy_pct',True)]:
        df[col+'_peer_score']=group_percentile(df,col,higher=higher)
    roe_avg=num(df.roe_ttm_avg_8q_pct); roe_now=num(df.roe_ttm_pct); rel=(roe_now-roe_avg).abs()/roe_avg.abs().clip(lower=5)
    df['roe_stability_score']=(100-rel*100).clip(0,100)
    df['audit_evidence_score']=np.where(df.audit_firm.fillna('').str.strip().ne(''),100,np.nan)
    df['management_proxy_score'],df['management_confidence']=weighted_mean(df,[('roe_stability_score',.45),('equity_growth_3y_avg_pct_peer_score',.35),('audit_evidence_score',.20)])
    df['cash_quality_score']=np.nan
    owner=df.payback_model.eq('OWNER_EARNINGS_3Y_MEDIAN'); conv=num(df.fcf_conversion_median_3y)
    conv_score=(100-(conv-1).abs()*80).clip(0,100); pos_year=num(df.owner_earnings_positive_years)/3*100
    df.loc[owner,'cash_quality_score']=(.65*conv_score+.35*pos_year)[owner]
    fb=df.payback_model.eq('CORE_EARNINGS_PROXY_CAPEX_DISTORTION'); ni_pos=num(df.net_income_positive_years)/3*100; cfo_pos=np.where(num(df.cfo_median_3y)>0,75,35)
    df.loc[fb,'cash_quality_score']=(.65*ni_pos+.35*cfo_pos)[fb]
    df['profitability_score']=np.nan; df['growth_score']=np.nan; df['balance_sheet_score']=np.nan; df['moat_proxy_score']=np.nan
    for bucket in df.business_bucket.unique():
        mask=df.business_bucket.eq(bucket)
        if bucket=='BANK':
            p,_=weighted_mean(df,[('roe_ttm_avg_8q_pct_peer_score',.55),('roa_ttm_avg_8q_pct_peer_score',.25),('bank_cir_pct_peer_score',.20)])
            g,_=weighted_mean(df,[('bank_operating_profit_growth_yoy_pct_peer_score',.45),('pbt_growth_3y_avg_pct_peer_score',.30),('equity_growth_3y_avg_pct_peer_score',.25)])
            ldr=band_score(df.bank_ldr_pct,80,25); bal,_=weighted_mean(df.assign(_ldr=ldr),[('_ldr',.35),('bank_cir_pct_peer_score',.30),('roe_stability_score',.35)])
            moat,_=weighted_mean(df,[('roe_ttm_avg_8q_pct_peer_score',.65),('bank_cir_pct_peer_score',.35)])
        else:
            p,_=weighted_mean(df,[('roe_ttm_avg_8q_pct_peer_score',.45),('roa_ttm_avg_8q_pct_peer_score',.25),('gross_margin_pct_peer_score',.30)])
            g,_=weighted_mean(df,[('pbt_growth_yoy_pct_peer_score',.30),('pbt_growth_3y_avg_pct_peer_score',.30),('revenue_growth_yoy_pct_peer_score',.20),('revenue_growth_3y_avg_pct_peer_score',.20)])
            bal,_=weighted_mean(df,[('debt_to_equity_peer_score',.60),('equity_growth_3y_avg_pct_peer_score',.40)])
            moat,_=weighted_mean(df,[('roe_ttm_avg_8q_pct_peer_score',.50),('gross_margin_pct_peer_score',.25),('pbt_growth_3y_avg_pct_peer_score',.25)])
        df.loc[mask,'profitability_score']=p[mask]; df.loc[mask,'growth_score']=g[mask]; df.loc[mask,'balance_sheet_score']=bal[mask]; df.loc[mask,'moat_proxy_score']=moat[mask]
    df['fundamental_domain_score_v4']=np.nan
    nonfin=~df.business_bucket.isin(['BANK','SECURITIES','INSURANCE'])
    comp_non=[('profitability_score',.20),('growth_score',.20),('moat_proxy_score',.15),('cash_quality_score',.15),('balance_sheet_score',.15),('management_proxy_score',.05),('payback_score',.10)]
    comp_fin=[('profitability_score',.30),('growth_score',.25),('moat_proxy_score',.15),('balance_sheet_score',.15),('management_proxy_score',.05),('payback_score',.10)]
    sc,cf=weighted_mean(df,comp_non); df.loc[nonfin,'fundamental_domain_score_v4']=sc[nonfin]; df.loc[nonfin,'fundamental_confidence_v4']=cf[nonfin]
    sc,cf=weighted_mean(df,comp_fin); df.loc[~nonfin,'fundamental_domain_score_v4']=sc[~nonfin]; df.loc[~nonfin,'fundamental_confidence_v4']=cf[~nonfin]
    df['dcf_growth_base_pct']=df[['revenue_growth_3y_avg_pct','pbt_growth_3y_avg_pct']].median(axis=1,skipna=True).clip(0,12)
    for scenario in ['bear','base','bull']: df['owner_earnings_dcf_'+scenario]=np.nan
    for idx,r in df[owner].iterrows():
        g=float(r.dcf_growth_base_pct or 0)/100
        df.loc[idx,'owner_earnings_dcf_bear']=dcf(r.owner_earnings_median_3y,r.outstanding_shares_profile,max(0,g-.04),.14,.02)
        df.loc[idx,'owner_earnings_dcf_base']=dcf(r.owner_earnings_median_3y,r.outstanding_shares_profile,g,.12,.03)
        df.loc[idx,'owner_earnings_dcf_bull']=dcf(r.owner_earnings_median_3y,r.outstanding_shares_profile,min(.15,g+.03),.11,.035)
    bases=[]; confs=[]; bears=[]; bulls=[]
    for _,r in df.iterrows():
        bucket=r.business_bucket
        if bucket=='BANK': weights=[('fv_pe_bootstrap',.20),('fv_pb_bootstrap',.80)]
        elif bucket in {'SECURITIES','INSURANCE'}: weights=[('fv_pe_bootstrap',.40),('fv_pb_bootstrap',.60)]
        elif bucket=='REAL_ESTATE': weights=[('fv_pe_bootstrap',.30),('fv_pb_bootstrap',.70)]
        elif bucket=='CYCLICAL': weights=[('fv_pe_bootstrap',.50),('fv_pb_bootstrap',.35),('owner_earnings_dcf_base',.15)]
        else: weights=[('fv_pe_bootstrap',.50),('fv_pb_bootstrap',.20),('owner_earnings_dcf_base',.30)]
        basev,conf=weighted_values(r,weights); bases.append(basev); confs.append(conf)
        w_b=[(('fair_value_bootstrap_bear' if c in {'fv_pe_bootstrap','fv_pb_bootstrap'} else 'owner_earnings_dcf_bear'),w) for c,w in weights]
        w_u=[(('fair_value_bootstrap_bull' if c in {'fv_pe_bootstrap','fv_pb_bootstrap'} else 'owner_earnings_dcf_bull'),w) for c,w in weights]
        bears.append(weighted_values(r,w_b)[0]); bulls.append(weighted_values(r,w_u)[0])
    df['fair_value_domain_base_v4']=bases; df['fair_value_domain_bear_v4']=bears; df['fair_value_domain_bull_v4']=bulls; df['valuation_domain_confidence_v4']=confs
    df['upside_domain_base_pct_v4']=(df.fair_value_domain_base_v4/num(df.price)-1)*100
    df['pe_discount_score']=[ratio_score(c,m) for c,m in zip(num(df.pe_current_calc),num(df.pe_median_8q_provider))]
    df['pb_discount_score']=[ratio_score(c,m) for c,m in zip(num(df.pb_current_calc),num(df.pb_median_8q_provider))]
    df['multiple_discount_score_v4']=np.nan
    for bucket in df.business_bucket.unique():
        mask=df.business_bucket.eq(bucket)
        weights=[('pe_discount_score',.25),('pb_discount_score',.75)] if bucket=='BANK' else [('pe_discount_score',.40),('pb_discount_score',.60)] if bucket in {'SECURITIES','INSURANCE','REAL_ESTATE'} else [('pe_discount_score',.65),('pb_discount_score',.35)]
        sc,_=weighted_mean(df,weights); df.loc[mask,'multiple_discount_score_v4']=sc[mask]
    df['upside_score_v4']=scale_series(df.upside_domain_base_pct_v4,-20,40)
    df['dividend_score_v4']=scale_series(df.dividend_yield_pct,0,8)
    vscore,vconf=weighted_mean(df,[('upside_score_v4',.45),('multiple_discount_score_v4',.25),('payback_score',.20),('dividend_score_v4',.10)])
    df['valuation_domain_score_v4']=vscore; df['valuation_score_confidence_v4']=vconf*(num(df.valuation_domain_confidence_v4)/100)
    rv=scale_series(df.rvol_progress_adjusted,.6,1.8); same=scale_series(df.same_time_volume_ratio,.6,1.8); pct=scale_series(df['pct_change'],0,3.5); pp=np.where(df.pocket_pivot_volume_pass.fillna(False).astype(bool),100,0)
    df['flow_score_v4']=(.35*rv+.25*same+.20*pct+.20*pp)
    logvol=np.log10(num(df.vol20).clip(lower=1)); df['liquidity_score_v4']=scale_series(logvol,math.log10(100_000),math.log10(5_000_000))
    df['radar_rank_score_v4']=(.23*num(df.technical_score)+.15*df.flow_score_v4+.20*df.fundamental_domain_score_v4+.15*df.valuation_domain_score_v4+.08*num(df.sector_strength_score)+.05*num(df.market_score)+.04*df.liquidity_score_v4+.10*(100-num(df.risk_score))).round(2)
    df['research_quality_gate_v4']=df.full_scan_eligible.fillna(False).astype(bool)&df.liquidity_pass_500k.fillna(False).astype(bool)&(df.fundamental_confidence_v4>=70)&(df.valuation_score_confidence_v4>=45)&(num(df.data_quality_score)>=80)
    actionable=df.candidate_setup.fillna('WATCH').ne('WATCH')
    df['intraday_action_gate_v4']=~actionable|df.intraday_5m_ready.fillna(False).astype(bool)
    df['internal_research_candidate_v4']=df.research_quality_gate_v4&df.intraday_action_gate_v4
    df['publication_gate_v4']='BLOCKED_PENDING_CURRENT_CORPORATE_ACTIONS_DATA_RIGHTS_COMPLIANCE'
    keep=['ticker','company_type','business_bucket','sector_v4','price','vol20','candidate_setup','technical_score','flow_score_v4','fundamental_domain_score_v4','fundamental_confidence_v4','profitability_score','growth_score','moat_proxy_score','cash_quality_score','balance_sheet_score','management_proxy_score','payback_model','payback_years','payback_score','owner_earnings_median_3y','net_income_median_3y','fcf_conversion_median_3y','owner_earnings_dcf_bear','owner_earnings_dcf_base','owner_earnings_dcf_bull','fair_value_domain_bear_v4','fair_value_domain_base_v4','fair_value_domain_bull_v4','upside_domain_base_pct_v4','multiple_discount_score_v4','valuation_domain_score_v4','valuation_score_confidence_v4','sector_strength_score','sector_regime','market_score','market_regime','risk_score','liquidity_score_v4','intraday_5m_ready','data_quality_score','full_scan_eligible','research_quality_gate_v4','intraday_action_gate_v4','internal_research_candidate_v4','radar_rank_score_v4','publication_gate_v4']
    out=df[keep].sort_values(['internal_research_candidate_v4','radar_rank_score_v4'],ascending=[False,False])
    Path(args.output).parent.mkdir(parents=True,exist_ok=True); out.to_csv(args.output,index=False,encoding='utf-8-sig')
    manifest={'schema_version':'STOCKRADAR_DOMAIN_V4','canonical_hose':405,'research_candidates':int(out.internal_research_candidate_v4.sum()),'payback_model_counts':out.payback_model.value_counts().to_dict(),'fundamental_confidence_ge70':int((out.fundamental_confidence_v4>=70).sum()),'valuation_confidence_ge45':int((out.valuation_score_confidence_v4>=45).sum()),'owner_earnings_dcf_coverage':int(out.owner_earnings_dcf_base.notna().sum()),'publication_allowed':False,'notes':['Domain-specific scoring separates banks/securities/insurance/real-estate/cyclicals/general companies.','Owner Earnings uses 3-year median and falls back to core earnings when CAPEX distorts FCF, per project policy.','Management and moat fields are explicit proxies, not qualitative analyst judgments.','Corporate actions/catalyst are not alpha-weighted until current authoritative feeds pass.']}
    Path(args.manifest).write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(manifest,ensure_ascii=False))

def main():
    p=argparse.ArgumentParser()
    for name in ['fundamental','profile','status','scanner','valuation','financial','sector','operational','output','manifest']:
        p.add_argument('--'+name.replace('_','-'),dest=name,required=True)
    build(p.parse_args())
if __name__=='__main__':main()
