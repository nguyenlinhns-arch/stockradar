import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.95.0";
import { STOCKRADAR_SYSTEM_CORE, deterministicStockRadarAnswer, normalizeResearchContext, stockRadarMode } from "../_shared/stockradar-core.ts";

const ORIGINS = new Set(["https://stockradar.vn","https://www.stockradar.vn","https://nguyenlinhns-arch.github.io","http://localhost:8000","http://127.0.0.1:8000"]);
const HORIZONS = ["SHORT_TERM","MEDIUM_TERM","LONG_TERM","ACCUMULATION"];
const TIERS = new Set(["FREE","TRIAL","PAID"]), PREMIUM = new Set(["TRIAL","PAID"]);
const MAX_WATCH = 20;

function cors(origin) {
  const h = { Vary:"Origin", "Cache-Control":"no-store", "X-Content-Type-Options":"nosniff" };
  if (origin && ORIGINS.has(origin)) Object.assign(h, { "Access-Control-Allow-Origin":origin, "Access-Control-Allow-Headers":"authorization, apikey, content-type", "Access-Control-Allow-Methods":"POST, OPTIONS" });
  return h;
}
function json(body, status, origin, extra={}) { return new Response(JSON.stringify(body), { status, headers:{...cors(origin),...extra,"Content-Type":"application/json; charset=utf-8"} }); }
function validTicker(v){ return /^[A-Z0-9]{3}$/.test(v) && /[A-Z]/.test(v); }
function validHorizon(v){ return HORIZONS.includes(v); }
function clean(v,max=700){ return String(v??"").replace(/[\u0000-\u001f\u007f]/g," ").replace(/\s+/g," ").trim().slice(0,max); }
function history(v){ if(!Array.isArray(v))return[]; return v.slice(-6).flatMap(x=>{ if(!x||typeof x!=="object")return[]; const role=x.role==="assistant"?"assistant":x.role==="user"?"user":null, content=clean(x.content,600); return role&&content?[{role,content}]:[]; }); }
function pos(v,min,max=Infinity){ if(v==null||v==="")return null; const n=Number(v); return Number.isFinite(n)&&n>=min&&n<=max?n:null; }
function explicitHorizon(v){ return /(tích sản|tich san|2\s*[-–]\s*5\s*năm|12\s*tháng|12\s*thang|6\s*[-–]\s*18\s*tháng|dài hạn|dai han|3\s*[-–]\s*6\s*tháng|1\s*[-–]\s*6\s*tháng|trung hạn|trung han|6\s*tháng|6\s*thang|ngắn hạn|ngan han|5\s*[-–]\s*20\s*phiên)/i.test(v); }
function normReport(r){ return {status:r.status,ticker:r.ticker,horizon:r.horizon,snapshot_id:r.snapshot_id,generated_at:r.generated_at,expires_at:r.expires_at,payload:r.payload}; }
function openAIText(p){ if(!p||typeof p!=="object")return""; if(typeof p.output_text==="string"&&p.output_text.trim())return p.output_text.trim(); const out=[]; for(const i of Array.isArray(p.output)?p.output:[]) for(const c of Array.isArray(i?.content)?i.content:[]) if(c?.type==="output_text"&&typeof c.text==="string")out.push(c.text); return out.join("\n").trim(); }
function errCode(p){ const e=p&&typeof p==="object"?p.error:null; return String(e?.code||e?.type||"UNKNOWN").toUpperCase().replace(/[^A-Z0-9_]+/g,"_").slice(0,80); }
function latest(xs){ const a=xs.map(x=>String(x||"")).filter(Boolean).sort(); return a.at(-1)||null; }
function appendPosition(answer,scope,ticker,watch){
  if(scope==="ticker"){
    const x=watch.find(r=>r.ticker===ticker&&r.owns_stock); if(!x)return answer; const bits=[];
    if(x.cost_basis!=null)bits.push(`giá vốn tự khai báo ${x.cost_basis.toLocaleString("vi-VN")}đ`); if(x.portfolio_weight_pct!=null)bits.push(`tỷ trọng tự khai báo ${x.portfolio_weight_pct.toLocaleString("vi-VN",{maximumFractionDigits:1})}%`);
    return bits.length?`${answer}\n\nVỊ THẾ CỦA BẠN: ${bits.join(" · ")}.`:answer;
  }
  const own=watch.filter(r=>r.owns_stock&&(r.cost_basis!=null||r.portfolio_weight_pct!=null)); if(!own.length)return answer;
  return `${answer}\n\nDỮ LIỆU VỊ THẾ BẠN ĐÃ KHAI BÁO:\n${own.slice(0,10).map(r=>`- ${r.ticker}: ${[r.cost_basis!=null?`giá vốn ${r.cost_basis.toLocaleString("vi-VN")}đ`:"",r.portfolio_weight_pct!=null?`tỷ trọng ${r.portfolio_weight_pct.toLocaleString("vi-VN",{maximumFractionDigits:1})}%`:""].filter(Boolean).join(" · ")}`).join("\n")}`;
}
async function audit(client,userId,ticker,horizon,outcome,reason,httpStatus,started,remaining=null){ try{ await client.rpc("record_stockradar_api_request_event",{p_user_id:userId,p_ticker:ticker,p_horizon:horizon,p_outcome:outcome,p_reason:reason,p_http_status:httpStatus,p_latency_ms:Math.max(0,Math.round(performance.now()-started)),p_rate_limit_remaining:remaining}); }catch{ console.error("stock-ai audit failed"); } }

Deno.serve(async req=>{
  const started=performance.now(), origin=req.headers.get("origin");
  if(origin&&!ORIGINS.has(origin))return json({status:"FORBIDDEN_ORIGIN"},403,null);
  if(req.method==="OPTIONS")return new Response(null,{status:204,headers:cors(origin)});
  if(req.method!=="POST")return json({status:"METHOD_NOT_ALLOWED"},405,origin,{Allow:"POST, OPTIONS"});
  const auth=req.headers.get("authorization")||"", token=auth.toLowerCase().startsWith("bearer ")?auth.slice(7).trim():""; if(!token)return json({status:"UNAUTHORIZED"},401,origin);
  const url=Deno.env.get("SUPABASE_URL")||"", anon=Deno.env.get("SUPABASE_ANON_KEY")||"", serviceKey=Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")||""; if(!url||!anon||!serviceKey)return json({status:"SERVICE_UNAVAILABLE"},503,origin);
  const authClient=createClient(url,anon,{auth:{persistSession:false,autoRefreshToken:false}}), service=createClient(url,serviceKey,{auth:{persistSession:false,autoRefreshToken:false}});
  const {data:ud,error:ue}=await authClient.auth.getUser(token), user=ud?.user; if(ue||!user)return json({status:"UNAUTHORIZED"},401,origin);
  let body; try{body=await req.json();}catch{return json({status:"INVALID_REQUEST",reason:"INVALID_JSON"},400,origin);}
  const ticker=String(body.ticker||"").trim().toUpperCase(), scopeRaw=String(body.scope||"auto").trim().toLowerCase(), horizon=String(body.horizon||"SHORT_TERM").trim().toUpperCase(), message=clean(body.message), hist=history(body.history);
  if(!validHorizon(horizon))return json({status:"INVALID_REQUEST",reason:"INVALID_HORIZON"},400,origin); if(!message)return json({status:"INVALID_REQUEST",reason:"EMPTY_MESSAGE"},400,origin); if(!["auto","ticker","portfolio"].includes(scopeRaw))return json({status:"INVALID_REQUEST",reason:"INVALID_SCOPE"},400,origin);
  const scope=scopeRaw==="portfolio"?"portfolio":scopeRaw==="ticker"||ticker?"ticker":"portfolio"; if(scope==="ticker"&&!validTicker(ticker))return json({status:"INVALID_REQUEST",reason:"INVALID_TICKER"},400,origin);

  const [{data:profile,error:pe},{data:prefs},{data:rows}]=await Promise.all([
    service.from("profiles").select("account_tier,account_status").eq("id",user.id).maybeSingle(),
    service.from("user_preferences").select("preferred_horizons,preferred_sectors,updated_at").eq("user_id",user.id).maybeSingle(),
    service.from("watchlist_items").select("ticker,horizon,owns_stock,alert_enabled,cost_basis,portfolio_weight_pct,created_at").eq("user_id",user.id).is("removed_at",null).order("owns_stock",{ascending:false}).order("created_at",{ascending:true}).limit(MAX_WATCH),
  ]);
  const tier=String(profile?.account_tier||"").toUpperCase(), accountStatus=String(profile?.account_status||"").toUpperCase();
  if(pe||accountStatus!=="ACTIVE"||!TIERS.has(tier)){ await audit(service,user.id,ticker,horizon,"FORBIDDEN","ACCOUNT_INACTIVE",403,started); return json({status:"FORBIDDEN",reason:"ACCOUNT_INACTIVE"},403,origin); }
  const preferences={preferred_horizons:Array.isArray(prefs?.preferred_horizons)?prefs.preferred_horizons.map(String).filter(validHorizon):[],preferred_sectors:Array.isArray(prefs?.preferred_sectors)?prefs.preferred_sectors.map(x=>clean(x,80)).filter(Boolean).slice(0,3):[]};
  const watch=(Array.isArray(rows)?rows:[]).flatMap(r=>{const t=String(r.ticker||"").trim().toUpperCase(),h=String(r.horizon||"SHORT_TERM").trim().toUpperCase(); if(!validTicker(t)||!validHorizon(h))return[]; const own=r.owns_stock===true; return[{ticker:t,horizon:h,owns_stock:own,alert_enabled:PREMIUM.has(tier)&&r.alert_enabled===true,cost_basis:own?pos(r.cost_basis,.0001):null,portfolio_weight_pct:own?pos(r.portfolio_weight_pct,0,100):null}];});
  const requested=scope==="ticker"?watch.find(x=>x.ticker===ticker)||null:null, owned=watch.filter(x=>x.owns_stock).length, alerts=watch.filter(x=>x.alert_enabled).length, positionCount=watch.filter(x=>x.owns_stock&&(x.cost_basis!=null||x.portfolio_weight_pct!=null)).length;
  const personalization=scope==="portfolio"?{watchlist_count:watch.length,owned_count:owned,alert_count:alerts,position_context_count:positionCount}:{requested_ticker_configured:!!requested,owns_stock:requested?.owns_stock??null,alert_enabled:requested?.alert_enabled??null,position_context_configured:!!requested&&(requested.cost_basis!=null||requested.portfolio_weight_pct!=null)};
  if(scope==="portfolio"&&!watch.length){ await audit(service,user.id,"",horizon,"NO_WATCHLIST","EMPTY_WATCHLIST",200,started); return json({status:"NO_WATCHLIST",scope,horizon,tier,answer:"KẾT LUẬN: tài khoản chưa có mã trong watchlist. Hãy thêm mã và đánh dấu mã đang sở hữu nếu có để StockRadar AI phân tích đúng danh mục.",personalization,quota_consumed:false},200,origin); }

  const explicit=explicitHorizon(message), reportReq=scope==="ticker"?HORIZONS.map(h=>({ticker,horizon:h})):watch.map(x=>({ticker:x.ticker,horizon:explicit?horizon:x.horizon})), researchTickers=scope==="ticker"?[ticker]:[...new Set(watch.map(x=>x.ticker))];
  const [reports,research]=await Promise.all([
    Promise.all(reportReq.map(async r=>{const {data,error}=await service.rpc("fetch_stockradar_cached_report",{p_ticker:r.ticker,p_horizon:r.horizon}); return{...r,data,error};})),
    Promise.all(researchTickers.map(async t=>{const {data,error}=await service.rpc("fetch_stockradar_internal_research_context",{p_ticker:t}); return{ticker:t,data,error};})),
  ]);
  const ready=reports.filter(r=>!r.error&&r.data?.status==="READY"), researchContexts=research.flatMap(r=>{if(r.error)return[]; const n=normalizeResearchContext(r.data); return n?[n]:[];}), mode=stockRadarMode(ready.length>0,researchContexts.length>0);
  const {data:qraw,error:qe}=await service.rpc("consume_stockradar_api_quota",{p_user_id:user.id,p_bucket:"stock_ai"}), q=qraw||{}; if(qe||!qraw){await audit(service,user.id,scope==="ticker"?ticker:"",horizon,"SERVICE_UNAVAILABLE","AI_QUOTA_RPC_FAILED",503,started);return json({status:"SERVICE_UNAVAILABLE",reason:"AI_QUOTA_RPC_FAILED"},503,origin);}
  const remN=Number(q.remaining),remaining=Number.isFinite(remN)?remN:null,limitN=Number(q.limit),retry=Number(q.retry_after||0),reset=String(q.reset_at||"")||null,rate={}; if(Number.isFinite(limitN))rate["X-RateLimit-Limit"]=String(limitN); if(remaining!=null)rate["X-RateLimit-Remaining"]=String(remaining);
  if(q.allowed!==true){if(retry>0)rate["Retry-After"]=String(retry); await audit(service,user.id,scope==="ticker"?ticker:"",horizon,"RATE_LIMITED","AI_RATE_LIMITED",429,started,remaining); return json({status:"RATE_LIMITED",reason:"AI_RATE_LIMITED",answer:tier==="FREE"?"Bạn đã dùng đủ 10 lượt StockRadar AI hôm nay. Hạn mức Free được làm mới lúc 00:00 giờ Việt Nam.":"Hạn mức StockRadar AI hiện tại đã dùng hết. Hãy thử lại sau khi hạn mức được làm mới.",tier,quota:{remaining:0,limit:Number.isFinite(limitN)?limitN:null,reset_at:reset,reset_timezone:q.daily_reset_timezone||null},retry_after:retry},429,origin,rate);}

  const action=ready.map(r=>normReport(r.data)), researchFallback=scope==="ticker"?(researchContexts[0]||null):researchContexts;
  let fallback=deterministicStockRadarAnswer({mode,researchContext:researchFallback,actionContext:action,question:message}); fallback=appendPosition(fallback,scope,ticker,watch);
  const userContext=scope==="portfolio"?{preferred_horizons:preferences.preferred_horizons,preferred_sectors:preferences.preferred_sectors,watchlist:watch,watchlist_count:watch.length,owned_count:owned,alert_count:alerts,position_context_count:positionCount}:{preferred_horizons:preferences.preferred_horizons,preferred_sectors:preferences.preferred_sectors,requested_ticker:requested};
  const ids=[...new Set([...action.map(x=>String(x.snapshot_id||"")),...researchContexts.map(x=>String(x.snapshot_id||""))].filter(Boolean))],source={action_gate:ready.length?"READY":"PENDING",research_ready:researchContexts.length>0,snapshot_id:ids.length===1?ids[0]:null,snapshot_count:ids.length,generated_at:latest([...action.map(x=>x.generated_at),...researchContexts.map(x=>x.generated_at)]),ready_horizons:scope==="ticker"?ready.map(x=>x.horizon):undefined,ready_reports:ready.length,covered_tickers:scope==="portfolio"?[...new Set(researchContexts.map(x=>String(x.ticker||"")).filter(Boolean))]:undefined}, quota={remaining,limit:Number.isFinite(limitN)?limitN:null,unlimited:q.unlimited===true,reset_at:reset,reset_timezone:q.daily_reset_timezone||null};

  if(mode==="METHOD_ONLY"){await audit(service,user.id,scope==="ticker"?ticker:"",horizon,"AI_READY","STOCKRADAR_CORE_METHOD_ONLY",200,started,remaining);return json({status:"READY",scope,ticker:scope==="ticker"?ticker:null,horizon,tier,mode,answer_engine:"STOCKRADAR_CORE",answer:fallback,personalization,source,quota,quota_consumed:true},200,origin,rate);}
  const key=Deno.env.get("OPENAI_API_KEY")?.trim(); if(!key){await audit(service,user.id,scope==="ticker"?ticker:"",horizon,"AI_READY_FALLBACK","OPENAI_KEY_MISSING",200,started,remaining);return json({status:"READY_FALLBACK",scope,ticker:scope==="ticker"?ticker:null,horizon,tier,mode,answer_engine:"STOCKRADAR_CORE",answer:fallback,personalization,source,quota,quota_consumed:true},200,origin,rate);}
  const context={RESPONSE_MODE:mode,ACCESS_TIER:tier,REQUEST_SCOPE:scope,REQUESTED_TICKER:scope==="ticker"?ticker:null,REQUESTED_HORIZON:horizon,PORTFOLIO_HORIZON_EXPLICIT:scope==="portfolio"?explicit:null,USER_QUESTION:message,RECENT_CONVERSATION:hist,USER_CONTEXT:userContext,ACTION_CONTEXT:action,RESEARCH_CONTEXT:researchContexts};
  const model=Deno.env.get("OPENAI_MODEL")?.trim()||"gpt-5-mini"; let response;
  try{response=await fetch("https://api.openai.com/v1/responses",{method:"POST",headers:{Authorization:`Bearer ${key}`,"Content-Type":"application/json"},body:JSON.stringify({model,instructions:STOCKRADAR_SYSTEM_CORE,input:JSON.stringify(context),max_output_tokens:scope==="portfolio"?1200:1000,store:false})});}catch{await audit(service,user.id,scope==="ticker"?ticker:"",horizon,"AI_READY_FALLBACK","OPENAI_NETWORK_ERROR",200,started,remaining);return json({status:"READY_FALLBACK",reason:"OPENAI_NETWORK_ERROR",scope,ticker:scope==="ticker"?ticker:null,horizon,tier,mode,answer_engine:"STOCKRADAR_CORE",answer:fallback,personalization,source,quota,quota_consumed:true},200,origin,rate);}
  let payload=null; try{payload=await response.json();}catch{} if(!response.ok){const code=errCode(payload);await audit(service,user.id,scope==="ticker"?ticker:"",horizon,"AI_READY_FALLBACK",`OPENAI_${response.status}_${code}`,200,started,remaining);return json({status:"READY_FALLBACK",reason:`OPENAI_${response.status}_${code}`,scope,ticker:scope==="ticker"?ticker:null,horizon,tier,mode,answer_engine:"STOCKRADAR_CORE",answer:fallback,personalization,source,quota,quota_consumed:true},200,origin,rate);}
  const answer=appendPosition(openAIText(payload)||fallback,scope,ticker,watch); await audit(service,user.id,scope==="ticker"?ticker:"",horizon,"AI_READY",scope==="portfolio"?"MODEL_PLUS_STOCKRADAR_CORE_PORTFOLIO":"MODEL_PLUS_STOCKRADAR_CORE",200,started,remaining);
  return json({status:"READY",scope,ticker:scope==="ticker"?ticker:null,horizon,tier,mode,answer_engine:"MODEL_PLUS_STOCKRADAR_CORE",answer,personalization,source,quota,quota_consumed:true},200,origin,rate);
});
