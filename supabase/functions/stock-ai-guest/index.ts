import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.95.0";
import { STOCKRADAR_SYSTEM_CORE, deterministicStockRadarAnswer, normalizeResearchContext, stockRadarMode } from "../_shared/stockradar-core.ts";

const ORIGINS = new Set(["https://stockradar.vn","https://www.stockradar.vn","https://nguyenlinhns-arch.github.io","http://localhost:8000","http://127.0.0.1:8000"]);
const HORIZONS = new Set(["SHORT_TERM","MEDIUM_TERM","LONG_TERM","ACCUMULATION"]);
let providerDisabledUntil = 0;
function cors(origin) { const h={Vary:"Origin","Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}; if(origin&&ORIGINS.has(origin))Object.assign(h,{"Access-Control-Allow-Origin":origin,"Access-Control-Allow-Headers":"apikey, content-type","Access-Control-Allow-Methods":"POST, OPTIONS"}); return h; }
function json(body,status,origin,extra={}) { return new Response(JSON.stringify(body),{status,headers:{...cors(origin),...extra,"Content-Type":"application/json; charset=utf-8"}}); }
function validTicker(v){return /^[A-Z0-9]{3}$/.test(v)&&/[A-Z]/.test(v)}
function clean(v,max=700){return String(v??"").replace(/[\u0000-\u001f\u007f]/g," ").replace(/\s+/g," ").trim().slice(0,max)}
function openAIText(p){if(typeof p?.output_text==='string'&&p.output_text.trim())return p.output_text.trim();const a=[];for(const i of Array.isArray(p?.output)?p.output:[])for(const c of Array.isArray(i?.content)?i.content:[])if(c?.type==='output_text'&&typeof c.text==='string')a.push(c.text);return a.join('\n').trim()}
async function sha(v){const d=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(v));return Array.from(new Uint8Array(d),b=>b.toString(16).padStart(2,'0')).join('')}

Deno.serve(async req=>{
  const origin=req.headers.get('origin');
  if(origin&&!ORIGINS.has(origin))return json({status:'FORBIDDEN_ORIGIN'},403,null);
  if(req.method==='OPTIONS')return new Response(null,{status:204,headers:cors(origin)});
  if(req.method!=='POST')return json({status:'METHOD_NOT_ALLOWED'},405,origin);
  let body; try{body=await req.json()}catch{return json({status:'INVALID_REQUEST',reason:'INVALID_JSON'},400,origin)}
  const ticker=String(body.ticker||'').trim().toUpperCase(),horizon=String(body.horizon||'SHORT_TERM').trim().toUpperCase(),message=clean(body.message),guestId=String(body.guest_id||'').trim();
  if(!validTicker(ticker)||!HORIZONS.has(horizon)||!message||!/^[A-Za-z0-9._:-]{20,128}$/.test(guestId))return json({status:'INVALID_REQUEST'},400,origin);
  const url=Deno.env.get('SUPABASE_URL')||'',serviceKey=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
  if(!url||!serviceKey)return json({status:'SERVICE_UNAVAILABLE'},503,origin);
  const db=createClient(url,serviceKey,{auth:{persistSession:false,autoRefreshToken:false}}),guestHash=await sha(`stockradar-guest-v6|${guestId}`);
  const [{data:raw,error:contextError},{data:quotaRaw,error:quotaError}]=await Promise.all([
    db.rpc('fetch_stockradar_ai_context',{p_ticker:ticker}),
    db.rpc('consume_stockradar_guest_ai_quota',{p_guest_key_hash:guestHash}),
  ]);
  if(quotaError||!quotaRaw)return json({status:'SERVICE_UNAVAILABLE',reason:'GUEST_QUOTA_RPC_FAILED'},503,origin);
  const quota=quotaRaw,remaining=Number.isFinite(Number(quota.remaining))?Number(quota.remaining):null,rate={"X-RateLimit-Limit":"3",...(remaining!=null?{"X-RateLimit-Remaining":String(remaining)}:{})};
  if(quota.allowed!==true){if(Number(quota.retry_after)>0)rate['Retry-After']=String(quota.retry_after);return json({status:'RATE_LIMITED',tier:'GUEST',answer:'Bạn đã dùng đủ 3 câu StockRadar AI hôm nay. Đăng ký Free để dùng 10 câu/ngày.',quota:{limit:3,remaining:0,reset_at:quota.reset_at||null}},429,origin,rate)}
  const context=contextError?null:normalizeResearchContext(raw),researchReady=context?.context_grade==='RESEARCH_READY',referenceReady=Boolean(context)&&!researchReady,mode=stockRadarMode(false,researchReady,referenceReady);
  const fallback=deterministicStockRadarAnswer({mode,researchContext:context,actionContext:[],question:message});
  const source={context_grade:context?.context_grade||null,research_ready:researchReady,reference_ready:referenceReady,snapshot_id:context?.snapshot_id||null,generated_at:context?.generated_at||null,as_of_date:context?.as_of_date||null};
  const base={scope:'ticker',tier:'GUEST',mode,ticker,horizon,quota_consumed:true,source,quota:{limit:3,remaining,reset_at:quota.reset_at||null,reset_timezone:quota.daily_reset_timezone||'Asia/Ho_Chi_Minh'}};
  if(mode==='METHOD_ONLY')return json({status:'READY',...base,answer_engine:'STOCKRADAR_DATA_ENGINE',answer:fallback},200,origin,rate);
  const key=Deno.env.get('OPENAI_API_KEY')?.trim();
  if(!key||Date.now()<providerDisabledUntil)return json({status:'READY_FALLBACK',reason:!key?'OPENAI_KEY_MISSING':'OPENAI_CIRCUIT_OPEN',...base,answer_engine:'STOCKRADAR_DATA_ENGINE',answer:fallback},200,origin,rate);
  let response; try{response=await fetch('https://api.openai.com/v1/responses',{method:'POST',headers:{Authorization:`Bearer ${key}`,'Content-Type':'application/json'},body:JSON.stringify({model:Deno.env.get('OPENAI_MODEL')?.trim()||'gpt-5-mini',instructions:STOCKRADAR_SYSTEM_CORE,input:JSON.stringify({RESPONSE_MODE:mode,ACCESS_TIER:'GUEST',REQUESTED_TICKER:ticker,REQUESTED_HORIZON:horizon,USER_QUESTION:message,RESEARCH_CONTEXT:context}),max_output_tokens:1100,store:false})})}catch{return json({status:'READY_FALLBACK',reason:'OPENAI_NETWORK_ERROR',...base,answer_engine:'STOCKRADAR_DATA_ENGINE',answer:fallback},200,origin,rate)}
  let payload=null; try{payload=await response.json()}catch{}
  if(!response.ok){const code=String(payload?.error?.code||payload?.error?.type||'UNKNOWN').toUpperCase().replace(/[^A-Z0-9_]+/g,'_');if(response.status===429&&/CREDIT|QUOTA|BALANCE/.test(code))providerDisabledUntil=Date.now()+15*60*1000;return json({status:'READY_FALLBACK',reason:`OPENAI_${response.status}_${code}`,...base,answer_engine:'STOCKRADAR_DATA_ENGINE',answer:fallback},200,origin,rate)}
  return json({status:'READY',...base,answer_engine:'MODEL_PLUS_STOCKRADAR_DATA',answer:openAIText(payload)||fallback},200,origin,rate);
});
