import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.95.0";
import { STOCKRADAR_SYSTEM_CORE, deterministicStockRadarAnswer, normalizeResearchContext, stockRadarMode } from "../_shared/stockradar-core.ts";
import { appendResearchSnapshot, buildResearchSnapshot, analysisContract } from "../_shared/stockradar-research-view.ts";

import { parseResearchQuery, loadResearchQuery, guestQuotaIdentity } from "../_shared/stockradar-query.ts";

const ORIGINS = new Set(["https://stockradar.vn","https://www.stockradar.vn","https://nguyenlinhns-arch.github.io","http://localhost:8000","http://127.0.0.1:8000"]);
const HORIZONS = ["SHORT_TERM","MEDIUM_TERM","LONG_TERM","ACCUMULATION"];
const TIERS = new Set(["FREE","TRIAL","PAID"]);
const MAX_WATCH = 20;
let providerDisabledUntil = 0;

function cors(origin){
  const h={Vary:"Origin","Cache-Control":"no-store","X-Content-Type-Options":"nosniff"};
  if(origin&&ORIGINS.has(origin))Object.assign(h,{"Access-Control-Allow-Origin":origin,"Access-Control-Allow-Headers":"authorization, apikey, content-type","Access-Control-Allow-Methods":"POST, OPTIONS"});
  return h;
}
function json(body,status,origin,extra={}){return new Response(JSON.stringify(body),{status,headers:{...cors(origin),...extra,"Content-Type":"application/json; charset=utf-8"}})}
function validTicker(v){return /^[A-Z0-9]{3}$/.test(v)&&/[A-Z]/.test(v)}
function validHorizon(v){return HORIZONS.includes(v)}
function clean(v,max=700){return String(v??"").replace(/[\u0000-\u001f\u007f]/g," ").replace(/\s+/g," ").trim().slice(0,max)}
function history(v){if(!Array.isArray(v))return[];return v.slice(-6).flatMap(x=>{if(!x||typeof x!=="object")return[];const role=x.role==="assistant"?"assistant":x.role==="user"?"user":null,content=clean(x.content,600);return role&&content?[{role,content}]:[]})}
function normReport(r){return{status:r.status,ticker:r.ticker,horizon:r.horizon,snapshot_id:r.snapshot_id,generated_at:r.generated_at,expires_at:r.expires_at,payload:r.payload}}
function openAIText(p){if(typeof p?.output_text==='string'&&p.output_text.trim())return p.output_text.trim();const a=[];for(const i of Array.isArray(p?.output)?p.output:[])for(const c of Array.isArray(i?.content)?i.content:[])if(c?.type==='output_text'&&typeof c.text==='string')a.push(c.text);return a.join('\n').trim()}
function errCode(p){const e=p&&typeof p==="object"?p.error:null;return String(e?.code||e?.type||"UNKNOWN").toUpperCase().replace(/[^A-Z0-9_]+/g,"_").slice(0,80)}
function latest(xs){const a=xs.map(x=>String(x||"")).filter(Boolean).sort();return a.at(-1)||null}
function appendPosition(answer,scope,ticker,watch){
  if(scope!=='ticker')return answer;
  const item=watch.find(r=>r.ticker===ticker&&r.owns_stock);
  if(!item)return answer;
  const bits=[];
  if(item.cost_basis!=null&&Number.isFinite(Number(item.cost_basis)))bits.push(`giá vốn tự khai báo ${Number(item.cost_basis).toLocaleString('vi-VN')}đ`);
  if(item.portfolio_weight_pct!=null&&Number.isFinite(Number(item.portfolio_weight_pct)))bits.push(`tỷ trọng ${Number(item.portfolio_weight_pct).toLocaleString('vi-VN',{maximumFractionDigits:1})}%`);
  return bits.length?`${answer}\n\nVỊ THẾ CỦA BẠN: ${bits.join(' · ')}.`:answer;
}
async function audit(client,userId,ticker,horizon,outcome,reason,httpStatus,started,remaining=null){
  try{await client.rpc('record_stockradar_api_request_event',{p_user_id:userId,p_ticker:ticker,p_horizon:horizon,p_outcome:outcome,p_reason:reason,p_http_status:httpStatus,p_latency_ms:Math.max(0,Math.round(performance.now()-started)),p_rate_limit_remaining:remaining})}catch{console.error('stock-ai audit failed')}
}

Deno.serve(async req=>{
  try {
  const started=performance.now(),origin=req.headers.get('origin');
  if(origin&&!ORIGINS.has(origin))return json({status:'FORBIDDEN_ORIGIN'},403,null);
  if(req.method==='OPTIONS')return new Response(null,{status:204,headers:cors(origin)});
  if(req.method!=='POST')return json({status:'METHOD_NOT_ALLOWED'},405,origin,{Allow:'POST, OPTIONS'});
  const authorization=req.headers.get('authorization')||'',token=authorization.toLowerCase().startsWith('bearer ')?authorization.slice(7).trim():'';
  if(!token)return json({status:'UNAUTHORIZED'},401,origin);
  const url=Deno.env.get('SUPABASE_URL')||'',anon=Deno.env.get('SUPABASE_ANON_KEY')||'',serviceKey=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
  if(!url||!anon||!serviceKey)return json({status:'SERVICE_UNAVAILABLE'},503,origin);
  const auth=createClient(url,anon,{global:{headers:{Authorization:`Bearer ${token}`}},auth:{persistSession:false,autoRefreshToken:false}}),db=createClient(url,serviceKey,{auth:{persistSession:false,autoRefreshToken:false}});
  const {data:userData,error:userError}=await auth.auth.getUser(token),user=userData?.user;
  if(userError||!user)return json({status:'UNAUTHORIZED'},401,origin);
  let body;try{body=await req.json()}catch{return json({status:'INVALID_REQUEST',reason:'INVALID_JSON'},400,origin)}
  const requestedTicker=String(body.ticker||'').trim().toUpperCase(),scopeRaw=String(body.scope||'auto').trim().toLowerCase(),horizon=String(body.horizon||'SHORT_TERM').trim().toUpperCase(),message=clean(body.message),hist=history(body.history);
  if(!validHorizon(horizon)||!message||!['auto','ticker','portfolio','scan','compare'].includes(scopeRaw))return json({status:'INVALID_REQUEST'},400,origin);
  const query=parseResearchQuery(message,requestedTicker);
  const ticker=query.scope==='ticker'?query.tickers[0]:'';
  const scope=scopeRaw==='portfolio'?'portfolio':query.scope;
  query.scope=scope;
  if(scope==='ticker'&&!validTicker(query.tickers[0]))return json({status:'INVALID_REQUEST',reason:'INVALID_TICKER'},400,origin);

  const [{data:profile,error:profileError},{data:watchRows}]=await Promise.all([
    auth.rpc('get_my_stockradar_access'),
    db.from('watchlist_items').select('ticker,horizon,owns_stock,alert_enabled,cost_basis,portfolio_weight_pct,created_at').eq('user_id',user.id).is('removed_at',null).order('owns_stock',{ascending:false}).order('created_at',{ascending:true}).limit(MAX_WATCH),
  ]);
  const tier=String(profile?.account_tier||'').toUpperCase();
  if(profileError||String(profile?.account_status||'').toUpperCase()!=='ACTIVE'||!TIERS.has(tier)){
    await audit(db,user.id,ticker,horizon,'FORBIDDEN','ACCOUNT_INACTIVE',403,started);
    return json({status:'FORBIDDEN',reason:'ACCOUNT_INACTIVE'},403,origin);
  }
  const watch=(Array.isArray(watchRows)?watchRows:[]).flatMap(row=>{
    const wt=String(row.ticker||'').trim().toUpperCase(),wh=String(row.horizon||'SHORT_TERM').trim().toUpperCase();
    if(!validTicker(wt)||!validHorizon(wh))return[];
    return[{ticker:wt,horizon:wh,owns_stock:row.owns_stock===true,alert_enabled:row.alert_enabled===true,cost_basis:row.cost_basis==null?null:Number(row.cost_basis),portfolio_weight_pct:row.portfolio_weight_pct==null?null:Number(row.portfolio_weight_pct)}];
  });
  if(scope==='portfolio'&&!watch.length)return json({status:'NO_WATCHLIST',scope,tier,answer:'Tài khoản chưa có danh mục. Bạn có thể hỏi một mã HOSE, so sánh hai mã hoặc yêu cầu quét Top cổ phiếu.',quota_consumed:false,research_data:[]},200,origin);

  if(scope==='portfolio') query.tickers=[...new Set(watch.map(x=>x.ticker))];
  const requestedTickers=query.tickers;
  const reportReq=scope==='ticker'?HORIZONS.map(itemHorizon=>({ticker:query.tickers[0],horizon:itemHorizon})):[];
  const [contextRows,reportRows]=await Promise.all([
    loadResearchQuery(db,query),
    Promise.all(reportReq.map(async r=>{const{data,error}=await db.rpc('fetch_stockradar_cached_report',{p_ticker:r.ticker,p_horizon:r.horizon});return{...r,data,error}})),
  ]);
  const contexts=contextRows.filter(Boolean),researchContexts=contexts;
  const tickerContext=scope==='ticker'?(contexts[0]||null):null;
  const researchData=scope==='ticker'?buildResearchSnapshot(tickerContext):contexts.map(buildResearchSnapshot).filter(Boolean);
  const ready=reportRows.filter(r=>!r.error&&r.data?.status==='READY'),action=ready.map(r=>normReport(r.data));
  const hasResearch=contexts.some(c=>c.context_grade==='RESEARCH_READY'),hasReference=contexts.length>0,mode=stockRadarMode(ready.length>0,hasResearch,hasReference);

  const {data:quotaRaw,error:quotaError}=await db.rpc('consume_stockradar_api_quota',{p_user_id:user.id,p_bucket:'stock_ai'});
  if(quotaError||!quotaRaw){await audit(db,user.id,scope==='ticker'?ticker:'',horizon,'SERVICE_UNAVAILABLE','AI_QUOTA_RPC_FAILED',503,started);return json({status:'SERVICE_UNAVAILABLE',reason:'AI_QUOTA_RPC_FAILED'},503,origin)}
  const quotaData=quotaRaw,remaining=quotaData.remaining != null && Number.isFinite(Number(quotaData.remaining))?Number(quotaData.remaining):null,limit=quotaData.limit != null && Number.isFinite(Number(quotaData.limit))?Number(quotaData.limit):null,rate={...(limit!=null?{'X-RateLimit-Limit':String(limit)}:{}),...(remaining!=null?{'X-RateLimit-Remaining':String(remaining)}:{})};
  if(quotaData.allowed!==true){
    if(Number(quotaData.retry_after)>0)rate['Retry-After']=String(quotaData.retry_after);
    await audit(db,user.id,scope==='ticker'?ticker:'',horizon,'RATE_LIMITED','AI_RATE_LIMITED',429,started,remaining);
    return json({status:'RATE_LIMITED',tier,answer:tier==='FREE'?'Bạn đã sử dụng hết lượt AI miễn phí. Nâng cấp StockRadar Pro để sử dụng không giới hạn.':'Hạn mức hiện tại đã dùng hết.',quota:{remaining:0,limit,reset_at:quotaData.reset_at||null}},429,origin,rate);
  }

  const researchForAnswer=scope==='ticker'?tickerContext:contexts;
  let fallback=scope==='scan'&&!contexts.length?'Chưa có mã HOSE đủ dữ liệu mới và đạt bộ lọc này. Chưa đủ dữ liệu để xác nhận tín hiệu.':deterministicStockRadarAnswer({mode,researchContext:researchForAnswer,actionContext:action,question:message});
  fallback=appendPosition(fallback,scope,ticker,watch);
  if(scope==='ticker')fallback=appendResearchSnapshot(fallback,tickerContext,message);
  const modelWatch=(scope==='ticker'?watch.filter(x=>x.ticker===query.tickers[0]):scope==='portfolio'?watch:[]).map(x=>({...x,cost_basis:x.owns_stock&&Number.isFinite(x.cost_basis)?x.cost_basis:null,portfolio_weight_pct:x.owns_stock&&Number.isFinite(x.portfolio_weight_pct)?x.portfolio_weight_pct:null}));
  const userContext={watchlist:modelWatch,owned_count:modelWatch.filter(x=>x.owns_stock).length};
  const ids=[...new Set([...action.map(x=>String(x.snapshot_id||'')),...contexts.map(x=>String(x.snapshot_id||''))].filter(Boolean))];
  const source={action_gate:ready.length?'READY':'PENDING',context_grades:{research_ready:contexts.filter(c=>c.context_grade==='RESEARCH_READY').length,reference_only:contexts.filter(c=>c.context_grade!=='RESEARCH_READY').length,requested:requestedTickers.length},snapshot_id:ids.length===1?ids[0]:null,snapshot_count:ids.length,generated_at:latest([...action.map(x=>x.generated_at),...contexts.map(c=>c.generated_at)]),as_of_date:latest(contexts.map(c=>c.as_of_date)),ready_horizons:scope==='ticker'?ready.map(x=>x.horizon):undefined};
  const quota={remaining,limit,unlimited:quotaData.unlimited===true,reset_at:quotaData.reset_at||null,reset_timezone:quotaData.daily_reset_timezone||null};
  const base={scope,ticker:scope==='ticker'?ticker:null,horizon,tier,mode,source,quota,quota_consumed:true,research_data:researchData,analysis:contexts.map(c=>analysisContract(c,action,horizon))};
  const fullResearchContext={RESEARCH_CONTEXT:researchContexts};

  if(mode==="METHOD_ONLY"){
    await audit(db,user.id,scope==='ticker'?ticker:'',horizon,'AI_READY','STOCKRADAR_CORE_METHOD_ONLY',200,started,remaining);
    return json({status:'READY',...base,answer_engine:'STOCKRADAR_CORE',answer:fallback},200,origin,rate);
  }
  const key=Deno.env.get('OPENAI_API_KEY')?.trim();
  if(!key||Date.now()<providerDisabledUntil)return json({status:'READY_FALLBACK',reason:!key?'OPENAI_KEY_MISSING':'OPENAI_CIRCUIT_OPEN',...base,answer_engine:'STOCKRADAR_CORE',answer:fallback},200,origin,rate);
  const context={...fullResearchContext,RESPONSE_MODE:mode,ACCESS_TIER:tier,REQUEST_SCOPE:scope,REQUESTED_TICKER:scope==='ticker'?ticker:null,REQUESTED_HORIZON:horizon,USER_QUESTION:message,RECENT_CONVERSATION:hist,USER_CONTEXT:userContext,ACTION_CONTEXT:action,RESEARCH_CONTEXT:scope==='ticker'?tickerContext:contexts};
  let response;
  try{response=await fetch('https://api.openai.com/v1/responses',{method:'POST',signal:AbortSignal.timeout(25000),headers:{Authorization:`Bearer ${key}`,'Content-Type':'application/json'},body:JSON.stringify({model:Deno.env.get('OPENAI_MODEL')?.trim()||'gpt-5-mini',instructions:STOCKRADAR_SYSTEM_CORE,input:JSON.stringify(context),max_output_tokens:scope==='portfolio'?1200:1000,store:false,reasoning:{effort:"minimal"}})})}
  catch{return json({status:'READY_FALLBACK',reason:'OPENAI_NETWORK_ERROR',...base,answer_engine:'STOCKRADAR_CORE',answer:fallback},200,origin,rate)}
  let payload=null;try{payload=await response.json()}catch{}
  if(!response.ok){const code=errCode(payload);if(response.status===429&&/CREDIT|QUOTA|BALANCE/.test(code))providerDisabledUntil=Date.now()+15*60*1000;return json({status:'READY_FALLBACK',reason:`OPENAI_${response.status}_${code}`,...base,answer_engine:'STOCKRADAR_CORE',answer:fallback},200,origin,rate)}
  const modelText=payload?.status==='completed'?openAIText(payload):'';
  const answer=modelText?(scope==='ticker'?appendResearchSnapshot(appendPosition(modelText,scope,ticker,watch),tickerContext,message):appendPosition(modelText,scope,ticker,watch)):fallback;
  await audit(db,user.id,scope==='ticker'?ticker:'',horizon,'AI_READY',scope==='portfolio'?'MODEL_PLUS_STOCKRADAR_CORE_PORTFOLIO':'MODEL_PLUS_STOCKRADAR_CORE',200,started,remaining);
  return json({status:modelText?"READY":"READY_FALLBACK",...base,answer_engine:modelText?"MODEL_PLUS_STOCKRADAR_CORE":"STOCKRADAR_CORE",answer},200,origin,rate);
  } catch { return json({status:'SERVICE_UNAVAILABLE',answer:'StockRadar AI tạm thời chưa thể phản hồi. Vui lòng thử lại.'},503,req.headers.get('origin')); }
});
