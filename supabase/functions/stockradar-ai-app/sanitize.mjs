export function validTicker(value='') {
  const t=String(value).trim().toUpperCase();
  return /^[A-Z0-9]{3}$/.test(t)&&/[A-Z]/.test(t)?t:null;
}

function pick(o, keys){const out={};for(const k of keys)if(o&&o[k]!==undefined&&o[k]!==null)out[k]=o[k];return out;}
function bool(v){return v===true;}

export function sanitizeStockContext(raw){
  if(!raw||typeof raw!=='object') return {status:'NOT_FOUND'};
  const p=raw.payload&&typeof raw.payload==='object'?raw.payload:{};
  const technical=p.technical_detail||{};
  const computed=technical.computed_indicators||{};
  const valuation=p.valuation_detail||{};
  const release=p.release||{};
  return {
    status:String(raw.status||'UNKNOWN'), ticker:String(raw.ticker||''), as_of_date:raw.as_of_date||null,
    generated_at:raw.generated_at||null, data_quality:raw.data_quality||'unknown', context_grade:raw.context_grade||'REFERENCE_ONLY',
    price_snapshot_status:raw.price_snapshot_status||null, data_layer_status:raw.data_layer_status||null,
    public_action_allowed:bool(raw.public_action_allowed)&&bool(release.public_action_allowed),
    quote:pick(p.quote,['price','close','volume']), sector:p.sector||null, business_bucket:p.business_bucket||null,
    market:pick(p.market_context,['market_regime','sector_regime','sector_strength_score']),
    setup:pick(p.setup,['candidate_setup','radar_status_v7','new_position_state_v5','holding_state_v5','scan_sla_ready_v7']),
    scores:pick(p.scores,['radar_score_v7','technical_score','fundamental_domain_score_v4','valuation_domain_score_v4','liquidity_score_v4','market_score','sector_strength_score','supply_demand_score_v1','factor_coverage_pct_v6']),
    risk:pick(p.risk,['atr20_pct','max_drawdown60_pct','realized_vol20_pct','decision_block_reasons_v5','execution_block_reasons_v7']),
    technical:{...pick(technical,['ma10','ma50','ma150','ma200','pivot20','rvol','vol20','stage','ichimoku_state','bollinger_middle','bollinger_upper','bollinger_lower','distance_to_pivot_pct','volume_mode']),...pick(computed,['pocket_pivot','early_breakout','confirmed_breakout','trend_template_pass','volume_dry_up','demand_bar','vcp_proxy','extension_pct','volume_ratio20'])},
    fundamental:pick(p.fundamental_detail,['eps_ttm','roe_ttm_pct','roa_ttm_pct','revenue_growth_yoy_pct','revenue_growth_3y_avg_pct','pbt_growth_yoy_pct','pbt_growth_3y_avg_pct','gross_margin_pct','debt_to_equity','equity_growth_yoy_pct']),
    valuation:{...pick(valuation,['pe','pb','ev_ebitda','bear','base','bull','fair_value','mos','upside','model_status']),assumptions_verified:valuation.assumptions_verified===true},
    catalyst:pick(p.catalyst,['official_verified_v3','official_items_30d_v3','official_items_90d_v3','latest_official_time_v3','latest_official_title_v3','verification_state_v3']),
    gates:{public_release_allowed:release.public_release_allowed===true,internal_research_ready:release.internal_research_ready===true,publication_blockers:Array.isArray(release.publication_blockers)?release.publication_blockers.slice(0,8):[],public_gate:release.public_gate||null},
    usage_note:'REFERENCE_RESEARCH_ONLY. Scores are not probabilities. Do not invent current prices, Buy Zone, Stop, Target, probability or action. If data is stale/reference-only, assumptions are unverified, or public_action_allowed is false, explain the limitation and keep the answer non-actionable.'
  };
}

export function extractTickers(query=''){
  const matches=String(query).toUpperCase().match(/\b[A-Z0-9]{3}\b/g)||[];
  return [...new Set(matches.map(validTicker).filter(Boolean))].slice(0,5);
}
