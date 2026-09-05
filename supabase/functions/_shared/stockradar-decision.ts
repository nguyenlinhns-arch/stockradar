import { analysisContract } from './stockradar-research-view.ts';

type Data = Record<string, any>;
const obj=(v:any):Data=>v&&typeof v==='object'&&!Array.isArray(v)?v:{};
const num=(v:any):number|null=>v==null||typeof v==='boolean'||typeof v==='object'||String(v).trim()===''?null:Number.isFinite(Number(v))?Number(v):null;
const positive=(v:any)=>{const n=num(v);return n!=null&&n>0?n:null;};
const list=(v:any):string[]=>Array.isArray(v)?v.filter(x=>typeof x==='string'&&x.trim()).slice(0,4):[];
const fold=(v:any)=>String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').toUpperCase();
const DAYS=96*3600*1000;

export function observationFresh(date:any,updated:any,quality:any,now=Date.now()):boolean {
  const at=Date.parse(updated),day=String(date||'');
  const today=new Date(now+7*3600000).toISOString().slice(0,10);
  return /^\d{4}-\d{2}-\d{2}$/.test(day)&&Number.isFinite(at)&&at<=now+300000&&now-at<=DAYS
    && day<=today && Date.parse(today)-Date.parse(day)<=DAYS
    && /^(updated|FRESH)$/i.test(String(quality||''));
}

const holdingQuestion=(question:string)=>/\b(?:BAN|GIU|NAM GIU|CO HANG)\b/.test(fold(question.replace(/bạn/gi,'')));
function reportLane(p:Data,question:string):Data {
  const holding=holdingQuestion(question);
  const lane=obj(obj(p.action_contract)[holding?'holding':'new_position']);
  return {...lane,state:lane.state||p[holding?'holding_state':'new_position_state'],setup:lane.setup||p.setup};
}

export function releasedReport(report:any,now=Date.now(),question=''):boolean {
  const p=obj(report?.payload);
  const lane=reportLane(p,question),state=fold(lane.state);
  if(['BUY','MUA','ADD','TANG'].includes(state)) {
    const low=positive(p.buy_zone_low??p.buy_zone?.[0]??p.buy_zone?.low),high=positive(p.buy_zone_high??p.buy_zone?.[1]??p.buy_zone?.high);
    const stop=positive(p.stop_loss),target=positive(report.horizon==='MEDIUM_TERM'?p.target_3_6m:report.horizon==='LONG_TERM'?p.target_12m:report.horizon==='ACCUMULATION'?p.fair_value:p.target_near??p.target_price);
    const size=positive(p.position_initial_pct??p.position_sizing_pct),rr=positive(p.risk_reward??p.risk_reward_to_base),setup=fold(lane.setup);
    const band=/POCKET/.test(setup)?[15,20]:/EARLY/.test(setup)?[20,30]:/CONFIRMED|RETEST/.test(setup)?[40,60]:null;
    if(!low||!high||!stop||!target||low>high||stop>=low||target<=high||!size||!rr||!band||size<band[0]||size>band[1])return false;
  }
  return report?.status==='READY'&&p.public_release_allowed===true&&p.data_grade==='DECISION_GRADE'
    &&p.data_freshness==='FRESH'&&p.is_mock!==true&&!/SHADOW|BACKTEST|MOCK/.test(String(p.record_mode||''))
    &&Date.parse(report.expires_at)>now&&positive(p.current_price)!=null
    &&observationFresh(p.as_of_date||String(p.source_updated_at||report.generated_at||'').slice(0,10),p.source_updated_at||report.generated_at,'FRESH',now);
}

function actionLabel(action:any,setup:any):string {
  const key=fold(action),s=fold(setup);
  if(key==='BUY'||key==='MUA')return /POCKET/.test(s)?'ĐẠT ĐIỂM MUA – POCKET PIVOT':/EARLY/.test(s)?'ĐẠT ĐIỂM MUA – EARLY BREAKOUT':'ĐẠT ĐIỂM MUA – XÁC NHẬN';
  return ({ADD:'NHỒI LỆNH',HOLD:'GIỮ',REDUCE:'HẠ TỶ TRỌNG',SELL:'CẮT LỖ / BÁN',WAIT:'THEO DÕI',WATCH:'THEO DÕI'})[key]||'THEO DÕI';
}

export function buildDecisionCards(contexts:Data[],reports:Data[],horizon:string,question='',now=Date.now()):Data[] {
  const tickers=[...new Set([...contexts.map(c=>c.ticker),...reports.filter(r=>r.horizon===horizon).map(r=>r.ticker)])];
  return tickers.map(ticker=>{
    const c=contexts.find(c=>c.ticker===ticker),r=reports.find(r=>r.ticker===ticker&&r.horizon===horizon&&releasedReport(r,now,question));
    const a=c?analysisContract(c,[],horizon):{},p=obj(r?.payload),official=Boolean(r);
    const same=c&&(!r||c.snapshot_id===r.snapshot_id),tech=official?{...(same?obj(a.technical):{}),...obj(p.technical),...p}:obj(a.technical);
    const date=official?(p.as_of_date||String(p.source_updated_at||r.generated_at).slice(0,10)):c?.as_of_date;
    const updated=official?(p.source_updated_at||r.generated_at):c?.generated_at;
    const fresh=official||observationFresh(date,updated,c?.data_quality,now);
    const research=fresh&&c?.context_grade==='RESEARCH_READY';
    const lane=reportLane(p,question);
    const state=official?actionLabel(lane.state,lane.setup):research&&!holdingQuestion(question)?'CHƯA MUA':'CHƯA ĐỦ DỮ LIỆU ĐỂ RA QUYẾT ĐỊNH';
    const low=official?positive(p.buy_zone_low??p.buy_zone?.[0]??p.buy_zone?.low):null,high=official?positive(p.buy_zone_high??p.buy_zone?.[1]??p.buy_zone?.high):null;
    const price=official?positive(p.current_price):positive(a.price),stop=official?positive(p.stop_loss):null;
    const targets=official?{short_term:positive(p.target_near??p.target_price),three_to_six_months:positive(p.target_3_6m),twelve_months:positive(p.target_12m)}:{short_term:null,three_to_six_months:null,twelve_months:null};
    const target=horizon==='SHORT_TERM'?targets.short_term:horizon==='MEDIUM_TERM'?targets.three_to_six_months:horizon==='LONG_TERM'?targets.twelve_months:positive(p.fair_value);
    const missing:string[]=[];
    if(!fresh)missing.push('Dữ liệu giá đủ mới, có ngày và thời gian nguồn đã xác minh.');
    if(!official)missing.push(research?'Điểm mua/bán được xác nhận và kế hoạch đủ điều kiện phát hành.':'Bằng chứng doanh nghiệp, tăng trưởng, định giá và kỹ thuật đủ để kết luận.');
    if(official&&(!target||!stop))missing.push('Mục tiêu hoặc điều kiện rủi ro theo đúng thời hạn của báo cáo.');
    const reasons=official?list(lane.reasons||p.thesis):research?(a.four_layers||[]).map((x:any)=>x.text).slice(0,4):missing;
    return {schema_version:'STOCKRADAR_DECISION_CARD_V1',ticker,horizon,conclusion:state,public_action_allowed:official,
      price,data:{status:!fresh?'UNAVAILABLE':official?'DELAYED':'RESEARCH',fresh,as_of_date:date||null,updated_at:updated||null,
        price_time_kind:official?(p.volume_mode==='INTRADAY'?'INTRADAY':'OBSERVATION'):c?.volume_mode||'UNKNOWN',source:'StockRadar',source_status:official?'VERIFIED_RELEASE':research?'RESEARCH_READY':'REFERENCE_ONLY',expires_at:r?.expires_at||null},
      setup:lane.setup||tech.setup||a.setup||null,stage:tech.stage||null,
      moving_averages:{ma10:num(tech.ma10),ma50:num(tech.ma50),ma150:num(tech.ma150),ma200:num(tech.ma200)},
      pivot:positive(tech.pivot||tech.pivot20),volume:official?{current:num(p.volume),vol20:num(p.vol20),rvol:num(p.rvol),mode:p.volume_mode||'UNKNOWN'}:a.volume||{},
      vpa:same?a.vpa||{}:{},buy_zone:{low,high},position_pct:official?num(p.position_initial_pct??p.position_sizing_pct):null,
      stop_loss:stop,targets,upside_pct:price&&target?(target/price-1)*100:null,downside_pct:price&&stop?(stop/price-1)*100:null,
      risk_reward:official?num(p.risk_reward??p.risk_reward_to_base):null,
      expected_holding:official?(p.expected_holding_period||p.expected_holding||null):null,
      conditions:official?list(p.invalidation_conditions):[...missing,...list(a.invalidation)],reasons,missing,
      estimated_plan:!official&&research?a.estimated_plan:null};
  });
}

// The server owns the first conclusion; model prose remains expandable evidence.
export function decisionResponse(body:Data):Data {
  const cards=body.decision_cards;
  if(!Array.isArray(cards)||cards.length!==1||!body.answer||body.scope!=='ticker')return body;
  const first=`KẾT LUẬN: ${cards[0].ticker} — ${cards[0].conclusion}`;
  return {...body,answer:first+'\n\n'+String(body.answer).replace(/^KẾT LUẬN:[^\n]*(?:\n\s*)?/i,'')};
}
