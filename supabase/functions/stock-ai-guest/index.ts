import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.95.0";
import { STOCKRADAR_SYSTEM_CORE, deterministicStockRadarAnswer, normalizeResearchContext, stockRadarMode, hasResearchFramework } from "../_shared/stockradar-core.ts";
import { appendResearchSnapshot, buildResearchSnapshot, analysisContract } from "../_shared/stockradar-research-view.ts";

import { parseResearchQuery, loadResearchQuery, guestQuotaIdentity } from "../_shared/stockradar-query.ts";
import { buildDecisionCards, decisionResponse, releasedReport, observationFresh } from "../_shared/stockradar-decision.ts";

const ORIGINS = new Set(["https://stockradar.vn","https://www.stockradar.vn","https://nguyenlinhns-arch.github.io","http://localhost:8000","http://127.0.0.1:8000"]);
const HORIZONS = ["SHORT_TERM","MEDIUM_TERM","LONG_TERM","ACCUMULATION"];
const MAX_HISTORY_ITEMS = 6;
let providerDisabledUntil = 0;

function cors(origin) {
  const h={Vary:"Origin","Cache-Control":"no-store","X-Content-Type-Options":"nosniff"};
  if(origin&&ORIGINS.has(origin))Object.assign(h,{"Access-Control-Allow-Origin":origin,"Access-Control-Allow-Headers":"apikey, content-type","Access-Control-Allow-Methods":"POST, OPTIONS"});
  return h;
}
function json(body,status,origin,extra={}) { return new Response(JSON.stringify(decisionResponse(body)),{status,headers:{...cors(origin),...extra,"Content-Type":"application/json; charset=utf-8"}}); }
function validTicker(v){return /^[A-Z0-9]{3}$/.test(v)&&/[A-Z]/.test(v)}
function validHorizon(v){return HORIZONS.includes(v)}
function clean(v,max=700){return String(v??"").replace(/[\u0000-\u001f\u007f]/g," ").replace(/\s+/g," ").trim().slice(0,max)}
function cleanHistory(value){
  if(!Array.isArray(value))return[];
  return value.slice(-MAX_HISTORY_ITEMS).flatMap(item=>{
    if(!item||typeof item!=="object")return[];
    const role=item.role==="assistant"?"assistant":item.role==="user"?"user":null,content=clean(item.content,600);
    return role&&content?[{role,content}]:[];
  });
}
function normReport(r){return{status:r.status,ticker:r.ticker,horizon:r.horizon,snapshot_id:r.snapshot_id,generated_at:r.generated_at,expires_at:r.expires_at,payload:r.payload}}
function openAIText(p){if(typeof p?.output_text==='string'&&p.output_text.trim())return p.output_text.trim();const a=[];for(const i of Array.isArray(p?.output)?p.output:[])for(const c of Array.isArray(i?.content)?i.content:[])if(c?.type==='output_text'&&typeof c.text==='string')a.push(c.text);return a.join('\n').trim()}
function errCode(p){const e=p&&typeof p==="object"?p.error:null;return String(e?.code||e?.type||"UNKNOWN").toUpperCase().replace(/[^A-Z0-9_]+/g,"_").slice(0,80)}
async function sha(v){const d=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(v));return Array.from(new Uint8Array(d),b=>b.toString(16).padStart(2,'0')).join('')}

Deno.serve(async req=>{
  try {
  const origin=req.headers.get('origin');
  if(origin&&!ORIGINS.has(origin))return json({status:'FORBIDDEN_ORIGIN'},403,null);
  if(req.method==='OPTIONS')return new Response(null,{status:204,headers:cors(origin)});
  if(req.method!=='POST')return json({status:'METHOD_NOT_ALLOWED'},405,origin,{Allow:'POST, OPTIONS'});
  let body; try{body=await req.json()}catch{return json({status:'INVALID_REQUEST',reason:'INVALID_JSON'},400,origin)}
  const requestedTicker=String(body.ticker||'').trim().toUpperCase(),horizon=String(body.horizon||'SHORT_TERM').trim().toUpperCase(),message=clean(body.message),guestId=String(body.guest_id||'').trim(),history=cleanHistory(body.history);
  const query=parseResearchQuery(message,requestedTicker);
  const ticker=query.scope==='ticker'?query.tickers[0]:'';
  if(query.scope==='portfolio')return json({status:'INVALID_REQUEST',answer:'Nhập mã HOSE, yêu cầu quét hoặc so sánh cổ phiếu.'},400,origin);
  if(ticker&&!validTicker(ticker))return json({status:'INVALID_REQUEST',reason:'INVALID_TICKER'},400,origin);
  if(!validHorizon(horizon))return json({status:'INVALID_REQUEST',reason:'INVALID_HORIZON'},400,origin);
  if(!message)return json({status:'INVALID_REQUEST',reason:'EMPTY_MESSAGE'},400,origin);
  if(!/^[A-Za-z0-9._:-]{20,128}$/.test(guestId))return json({status:'INVALID_REQUEST',reason:'INVALID_GUEST_ID'},400,origin);
  const url=Deno.env.get('SUPABASE_URL')||'',serviceKey=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
  if(!url||!serviceKey)return json({status:'SERVICE_UNAVAILABLE'},503,origin);
  const db=createClient(url,serviceKey,{auth:{persistSession:false,autoRefreshToken:false}}),guestHash=await guestQuotaIdentity(req,serviceKey);
  if(!guestHash)return json({status:'SERVICE_UNAVAILABLE',answer:'Chưa xác minh được phiên dùng thử. Vui lòng đăng nhập để tiếp tục.'},503,origin);

  const [reportRows,contextResult,quotaResult]=await Promise.all([
    Promise.all((query.scope==='ticker'?HORIZONS:[]).map(async itemHorizon=>{const{data,error}=await db.rpc('fetch_stockradar_cached_report',{p_ticker:ticker,p_horizon:itemHorizon});return{horizon:itemHorizon,data,error};})),
    loadResearchQuery(db,query),
    db.rpc('consume_stockradar_guest_ai_quota',{p_guest_key_hash:guestHash}),
  ]);
  const {data:quotaRaw,error:quotaError}=quotaResult;
  if(quotaError||!quotaRaw)return json({status:'SERVICE_UNAVAILABLE',reason:'GUEST_QUOTA_RPC_FAILED'},503,origin);
  const quota=quotaRaw,remaining=Number.isFinite(Number(quota.remaining))?Number(quota.remaining):null,rate={"X-RateLimit-Limit":"3",...(remaining!=null?{"X-RateLimit-Remaining":String(remaining)}:{})};
  if(quota.allowed!==true){
    if(Number(quota.retry_after)>0)rate['Retry-After']=String(quota.retry_after);
    return json({status:'RATE_LIMITED',tier:'GUEST',answer:'Đăng ký miễn phí để tiếp tục sử dụng AI StockRadar.',quota:{limit:3,remaining:0,reset_at:quota.reset_at||null,reset_timezone:quota.daily_reset_timezone||'Asia/Ho_Chi_Minh'}},429,origin,rate);
  }

  const ready=reportRows.filter(r=>!r.error&&releasedReport(r.data,Date.now(),message)),actionContext=ready.filter(r=>r.horizon===horizon).map(r=>normReport(r.data));
  const contexts=contextResult.filter(c=>c&&observationFresh(c.as_of_date,c.generated_at,c.data_quality));
  const researchContext=contexts[0]||null,researchReady=researchContext?.context_grade==="RESEARCH_READY",referenceReady=Boolean(researchContext),mode=stockRadarMode(actionContext.length>0,researchReady,referenceReady);
  const researchData=query.scope==='ticker'?buildResearchSnapshot(researchContext):contexts.map(buildResearchSnapshot);
  const coreAnswer=deterministicStockRadarAnswer({mode,researchContext:query.scope==='ticker'?researchContext:contexts,actionContext,question:message});
  const fallback=query.scope==='scan'&&!contexts.length?'Chưa có mã HOSE đủ dữ liệu mới và đạt bộ lọc này. Chưa đủ dữ liệu để xác nhận tín hiệu.':query.scope==='ticker'?appendResearchSnapshot(coreAnswer,researchContext,message,mode!=='ACTION_READY'):coreAnswer;
  const ids=[...new Set([...actionContext.map(r=>String(r.snapshot_id||'')),String(researchContext?.snapshot_id||'')].filter(Boolean))];
  const source={action_gate:actionContext.length?'READY':'PENDING',context_grade:researchContext?.context_grade||null,research_ready:Boolean(researchReady),reference_ready:Boolean(researchContext),snapshot_id:ids.length===1?ids[0]:null,snapshot_count:ids.length,generated_at:[...actionContext.map(r=>String(r.generated_at||'')),String(researchContext?.generated_at||'')].filter(Boolean).sort().at(-1)||null,as_of_date:researchContext?.as_of_date||null,ready_horizons:ready.map(r=>r.horizon)};
  const base={scope:query.scope,tier:'GUEST',mode,ticker,horizon,quota_consumed:true,source,research_data:researchData,analysis:contexts.map(c=>analysisContract(c,actionContext,horizon)),decision_cards:buildDecisionCards(contexts.length?contexts:query.scope==='ticker'?[{ticker}]:[],actionContext,horizon,message),quota:{limit:3,remaining,reset_at:quota.reset_at||null,reset_timezone:quota.daily_reset_timezone||'Asia/Ho_Chi_Minh'}};

  if(mode==="METHOD_ONLY")return json({status:'READY',...base,answer_engine:'STOCKRADAR_CORE',answer:fallback},200,origin,rate);
  const key=Deno.env.get('OPENAI_API_KEY')?.trim();
  if(!key||Date.now()<providerDisabledUntil)return json({status:'READY_FALLBACK',reason:!key?'OPENAI_KEY_MISSING':'OPENAI_CIRCUIT_OPEN',...base,answer_engine:'STOCKRADAR_CORE',answer:fallback},200,origin,rate);

  const context={RESPONSE_MODE:mode,ACCESS_TIER:'GUEST',REQUEST_SCOPE:query.scope,REQUESTED_TICKER:ticker,REQUESTED_HORIZON:horizon,USER_QUESTION:message,RECENT_CONVERSATION:history,USER_CONTEXT:{authenticated:false,portfolio_available:false,watchlist_available:false},ACTION_CONTEXT:actionContext,RESEARCH_CONTEXT:query.scope==='ticker'?researchContext:contexts};
  let response;
  try{
    response=await fetch('https://api.openai.com/v1/responses',{method:'POST',signal:AbortSignal.timeout(25000),headers:{Authorization:`Bearer ${key}`,'Content-Type':'application/json'},body:JSON.stringify({model:Deno.env.get('OPENAI_MODEL')?.trim()||'gpt-5-mini',instructions:STOCKRADAR_SYSTEM_CORE,input:JSON.stringify(context),max_output_tokens:2800,store:false,reasoning:{effort:"minimal"}})});
  }catch{return json({status:'READY_FALLBACK',reason:'OPENAI_NETWORK_ERROR',...base,answer_engine:'STOCKRADAR_CORE',answer:fallback},200,origin,rate)}
  let payload=null; try{payload=await response.json()}catch{}
  if(!response.ok){
    const code=errCode(payload);
    if(response.status===429&&/CREDIT|QUOTA|BALANCE/.test(code))providerDisabledUntil=Date.now()+15*60*1000;
    return json({status:'READY_FALLBACK',reason:`OPENAI_${response.status}_${code}`,...base,answer_engine:'STOCKRADAR_CORE',answer:fallback},200,origin,rate);
  }
  const candidateText=payload?.status==='completed'?openAIText(payload):'';
  const modelText=(query.scope==='ticker' && mode!=='ACTION_READY' && !hasResearchFramework(candidateText))?'':candidateText;
  return json({status:modelText?"READY":"READY_FALLBACK",...base,answer_engine:modelText?"MODEL_PLUS_STOCKRADAR_CORE":"STOCKRADAR_CORE",answer:modelText?(query.scope==='ticker'?appendResearchSnapshot(modelText,researchContext,message,mode!=='ACTION_READY'):modelText):fallback},200,origin,rate);
  } catch { return json({status:'SERVICE_UNAVAILABLE',answer:'StockRadar AI tạm thời chưa thể phản hồi. Vui lòng thử lại.'},503,req.headers.get('origin')); }
});
