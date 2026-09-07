// PROJECT_AUTORESUME_ROUTING_V1
import { loadProjectBridge, loadProjectContext, projectContextInput, projectBridgeMeta, PROJECT_HANDOFF_RULE } from "../_shared/stockradar-project-context.ts";
// PRIVATE_PROJECT_BRIDGE_V1
import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.95.0";
import { loadProjectKnowledge, projectKnowledgeInstructions, projectKnowledgeMeta } from "../_shared/stockradar-knowledge.ts";
// PROJECT_KNOWLEDGE_BRIDGE_V2

const ORIGINS = new Set([
  "https://stockradar.vn",
  "https://www.stockradar.vn",
  "https://nguyenlinhns-arch.github.io",
  "http://localhost:8000",
  "http://127.0.0.1:8000",
]);
const HORIZONS = new Set(["SHORT_TERM","MEDIUM_TERM","LONG_TERM","ACCUMULATION"]);
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const TICKER_RE = /^[A-Z0-9]{3}$/;
const MAX_STORED_HISTORY = 30;
const MAX_FORWARD_HISTORY = 6;

function cors(origin: string | null) {
  const h: Record<string,string> = {
    Vary: "Origin",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
  };
  if (origin && ORIGINS.has(origin)) Object.assign(h, {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Headers": "authorization, apikey, content-type",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
  });
  return h;
}
function json(body: unknown, status: number, origin: string | null) {
  return new Response(JSON.stringify(body), {status, headers: {...cors(origin), "Content-Type":"application/json; charset=utf-8"}});
}
function clean(value: unknown, max = 700) {
  return String(value ?? "").replace(/[\u0000-\u001f\u007f]/g," ").replace(/\s+/g," ").trim().slice(0,max);
}
function cleanStored(value: unknown, max = 24000) {
  return String(value ?? "")
    .replace(/\r\n/g,"\n")
    .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g," ")
    .trim()
    .slice(0,max);
}
function validTicker(value: unknown) {
  const t = String(value ?? "").trim().toUpperCase();
  return TICKER_RE.test(t) && /[A-Z]/.test(t) ? t : "";
}
function explicitTicker(text) {
  // Canonical lexical extractor, embedded identically in browser/chat/research.
  // This recognizes mentions only: listing, venue and data gates remain server-side.
  const raw = String(text || '').normalize('NFC').slice(0,8000);
  const masked = raw
    .replace(/https?:\/\/\S+|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, s => ' '.repeat(s.length))
    .replace(/\btra\s+(?:cứu|cuu)(?=\s|$|[.,:;!?])/giu, s => ' '.repeat(s.length));
  const technical = new Set(['VPA','VCP','EPS','ROE','ROA','PBT','FCF','DCF','ATR','RSI','MAC','PEG','MOS','GDP','CPI','USD','VND','ETF','NAV','IPO','API','OTP','JWT','URL','CEO','CFO','CTO','LLM','MAI']);
  const words = new Set(['CHI','CHO','GHI','TRA','SAU','TIN','RUI','MOC','MOI','TOP','MUA','BAN','GIU','GIA','NAY','SAO','KHI','NEU','HAY','DAI','HAN','VON','LOI','ROI','THE','NAO','CAN','XEM','HOM','CAC','CUA','VOI','TAI','TOI','NEN','CON','HON','GAN','LAM','VAN','QUA','MOT','HAI','NAM','DAY','DAU','TEN','BAO','LAI','LUC','NOI','NHA','DON','GON','RAT','TAM','TAN','CHU','DAN','DEN','CAP','NET','DAT','TUC','TIE','COI','GI','FOR','AND','THE','NEW','NOW','ALL','GET','SET']);
  const tokens = masked.matchAll(/(?<![\p{L}\p{N}_])([$#]?)([A-Za-z0-9]{3})(?![\p{L}\p{N}_])/gu);
  const tickers = [];
  for (const match of tokens) {
    const ticker = match[2].toUpperCase();
    if (!/[A-Z]/.test(ticker) || technical.has(ticker)) continue;
    const prefix = masked.slice(0,match.index);
    const stockCue = /(?:\bmã|\bma|cổ phiếu|co phieu|\bticker|\bsymbol)\s*[:=]?\s*$/iu.test(prefix);
    const namedCue = match[2] === ticker && (/(?:phân tích|phan tich|so sánh|so sanh|kiểm tra|kiem tra|đánh giá|danh gia)\s*[:=]?\s*$/iu.test(prefix) || (tickers.length > 0 && /(?:\bvà|\bva|\bvới|\bvoi|\bvs|[,/])\s*$/iu.test(prefix)));
    const standalone = masked.trim() === match[0] && match[2] === ticker;
    const command = /^(MUA|BAN|GIU|CHO|GHI|TOP|SAO|KHI|NEU|HAY|TOI|XEM|CAC|CUA|VOI|NAY|ROI|RUI|CHI|THE|FOR|AND|ALL|GET|SET)$/.test(ticker);
    if (command && !match[1]) continue;
    if (words.has(ticker) && !match[1] && !stockCue && !namedCue && !standalone) continue;
    if (!tickers.includes(ticker)) tickers.push(ticker);
    if (tickers.length === 4) break;
  }
  return tickers[0] || "";
}

function explicitHorizon(text) {
  const q = String(text || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[đĐ]/g,'d').toLowerCase();
  if (/tich san|tich luy/.test(q)) return 'ACCUMULATION';
  if (/12\s*thang|dai han/.test(q)) return 'LONG_TERM';
  if (/3\s*[-–]\s*6\s*thang|trung han|6\s*thang/.test(q)) return 'MEDIUM_TERM';
  if (/ngan han|vai phien|vai tuan/.test(q)) return 'SHORT_TERM';
  return '';
}

function portfolioIntent(text: string) {
  return /(danh mục|danh muc|watchlist|mã tôi|ma toi|cổ phiếu của tôi|co phieu cua toi|đang sở hữu|dang so huu|mã đang giữ|ma dang giu|các mã đang giữ|cac ma dang giu)/i.test(text);
}
function scanIntent(text: string) {
  return /(\btop\b|quét|quet|lọc|loc|mã nào|ma nao|cổ phiếu nào|co phieu nao|ngành nào|nganh nao)/i.test(text);
}

function methodologyIntent(text: string) {
  if (explicitTicker(text)) return false;
  if (/(liên thông|lien thong|ngữ cảnh|ngu canh|dự án|du an|chatgpt|cuộc trò chuyện|cuoc tro chuyen)/i.test(text)) return true;
  const method = /(4m|payback|canslim|sepa|vcp|vpa|pocket pivot|ichimoku|bollinger|stage\s*[1-4]|fair value|margin of safety|định giá|dinh gia|phương pháp|phuong phap|quản trị rủi ro|quan tri rui ro)/i.test(text);
  return method && (/(là gì|la gi|giải thích|giai thich|khái niệm|khai niem|hướng dẫn|huong dan|phương pháp|phuong phap)/i.test(text) || /^(4m|payback|canslim|sepa|vcp|vpa|pocket pivot|ichimoku|bollinger)\s*[?.!]*$/i.test(text.trim()));
}

function horizon(value: unknown, fallback = "SHORT_TERM") {
  const h = String(value ?? "").trim().toUpperCase();
  return HORIZONS.has(h) ? h : fallback;
}
function openAIText(payload: any) {
  if (typeof payload?.output_text === "string" && payload.output_text.trim()) return payload.output_text.trim();
  const out: string[] = [];
  for (const item of Array.isArray(payload?.output) ? payload.output : []) {
    for (const part of Array.isArray(item?.content) ? item.content : []) {
      if (part?.type === "output_text" && typeof part.text === "string") out.push(part.text);
    }
  }
  return out.join("\n").trim();
}

async function activeKnowledge(db: any) {
  return await loadProjectKnowledge(db);
}

async function ensureThread(db: any, userId: string, requestedId: unknown, knowledgeVersion: string, forceNew = false) {
  const requested = String(requestedId ?? "").trim();
  if (!forceNew && requested) {
    if (!UUID_RE.test(requested)) throw new Error("INVALID_THREAD_ID");
    const {data,error} = await db.from("stockradar_ai_threads").select("*").eq("id",requested).eq("user_id",userId).eq("status","ACTIVE").maybeSingle();
    if (error) throw new Error("THREAD_READ_FAILED");
    if (!data) throw new Error("THREAD_NOT_FOUND");
    return data;
  }
  if (!forceNew) {
    const {data} = await db.from("stockradar_ai_threads").select("*").eq("user_id",userId).eq("status","ACTIVE")
      .order("last_message_at",{ascending:false}).limit(1).maybeSingle();
    if (data) return data;
  }
  const {data,error} = await db.from("stockradar_ai_threads").insert({user_id:userId,knowledge_version:knowledgeVersion}).select("*").single();
  if (error || !data) throw new Error("THREAD_CREATE_FAILED");
  return data;
}

async function loadMessages(db: any, threadId: string, limit = MAX_STORED_HISTORY) {
  const {data,error} = await db.from("stockradar_ai_messages")
    .select("id,role,content,scope,ticker,horizon,answer_engine,model_status,knowledge_version,created_at")
    .eq("thread_id",threadId).order("id",{ascending:false}).limit(limit);
  if (error) throw new Error("THREAD_HISTORY_FAILED");
  return (data || []).reverse();
}

function forwardHistory(rows: any[], thread: any, knowledge: any) {
  const recent = rows.slice(-5).map(row => ({role:row.role, content:clean(row.content,600)}));
  const memoryBits = [
    `Ngữ cảnh hội thoại lưu trên máy chủ. Knowledge: ${knowledge.version}.`,
    thread.last_ticker ? `Mã gần nhất: ${thread.last_ticker}.` : "",
    thread.last_horizon ? `Khung gần nhất: ${thread.last_horizon}.` : "",
    "Nếu câu hỏi là nối tiếp và không nêu mã mới, tiếp tục theo mã gần nhất; không bắt người dùng gõ lại ticker.",
  ].filter(Boolean).join(" ").slice(0,600);
  return [{role:"assistant",content:memoryBits}, ...recent].slice(-MAX_FORWARD_HISTORY);
}

async function saveExchange(db: any, thread: any, input: {message:string,scope:string,ticker:string,horizon:string}, result: any, knowledgeVersion: string) {
  const answer = cleanStored(result?.answer || "StockRadar AI chưa có nội dung để trả lời.", 24000);
  const now = new Date().toISOString();
  const title = thread.title || (input.ticker ? `${input.ticker} · ${input.message.slice(0,48)}` : input.message.slice(0,64));
  const userInsert = await db.from("stockradar_ai_messages").insert({
    thread_id:thread.id, role:"user", content:input.message, scope:input.scope || null,
    ticker:input.ticker || null, horizon:input.horizon || null, knowledge_version:knowledgeVersion,
  });
  if (userInsert.error) throw new Error("THREAD_SAVE_USER_FAILED");
  const assistantInsert = await db.from("stockradar_ai_messages").insert({
    thread_id:thread.id, role:"assistant", content:answer, scope:result?.scope || input.scope || null,
    ticker:validTicker(result?.ticker) || input.ticker || null, horizon:input.horizon || null,
    answer_engine:clean(result?.answer_engine,120) || null, model_status:clean(result?.model_status,120) || null,
    knowledge_version:knowledgeVersion,
    metadata:{mode:result?.mode || null,status:result?.status || null,source:result?.source || null,project_bridge:result?.project_bridge || null},
  });
  if (assistantInsert.error) throw new Error("THREAD_SAVE_ASSISTANT_FAILED");
  const update = await db.from("stockradar_ai_threads").update({
    title, last_ticker:input.ticker || thread.last_ticker || null, last_scope:input.scope || thread.last_scope || "conversation",
    last_horizon:input.horizon || thread.last_horizon || "SHORT_TERM", knowledge_version:knowledgeVersion,
    updated_at:now,last_message_at:now,
  }).eq("id",thread.id).eq("user_id",thread.user_id);
  if (update.error) throw new Error("THREAD_UPDATE_FAILED");
  return answer;
}

async function consumeKnowledgeQuota(db: any, userId: string, tier: string) {
  const {data:burst,error:burstError} = await db.rpc("consume_stockradar_api_quota",{p_user_id:userId,p_bucket:"stock_ai_burst"});
  if (burstError || !burst || burst.reason === "POLICY_MISSING") return {ok:false,status:503,body:{status:"SERVICE_UNAVAILABLE",reason:"AI_BURST_POLICY_UNAVAILABLE"}};
  if (burst.allowed !== true) return {ok:false,status:429,body:{status:"RATE_LIMITED",reason:"TECHNICAL_RATE_LIMIT",tier,quota_consumed:false,answer:"Bạn đang gửi nhiều yêu cầu liên tiếp. Vui lòng thử lại sau một phút."}};
  const {data,error} = await db.rpc("consume_stockradar_api_quota",{p_user_id:userId,p_bucket:"stock_ai"});
  if (error || !data) return {ok:false,status:503,body:{status:"SERVICE_UNAVAILABLE",reason:"AI_QUOTA_RPC_FAILED"}};
  const quota = {remaining:data.remaining ?? null,limit:data.limit ?? null,unlimited:data.unlimited === true,reset_at:data.reset_at ?? null,reset_timezone:data.daily_reset_timezone ?? null};
  if (data.allowed !== true) return {ok:false,status:429,body:{status:"RATE_LIMITED",tier,quota,answer:tier === "FREE" ? "Bạn đã sử dụng hết lượt AI miễn phí. Nâng cấp StockRadar Pro để sử dụng không giới hạn." : "Hạn mức hiện tại đã dùng hết."}};
  return {ok:true,quota};
}

async function knowledgeAnswer(db: any, userId: string, tier: string, message: string, history: any[], knowledge: any, thread: any, inputHorizon: string, bridge: any) {
  const quotaResult = await consumeKnowledgeQuota(db,userId,tier);
  if (!quotaResult.ok) return {httpStatus:quotaResult.status, payload:{...quotaResult.body,thread_id:thread.id,knowledge_version:knowledge.version}};
  const key = Deno.env.get("OPENAI_API_KEY")?.trim();
  if (!key) return {httpStatus:200,payload:{status:"READY_FALLBACK",reason:"OPENAI_KEY_MISSING",tier,mode:"KNOWLEDGE_ONLY",thread_id:thread.id,knowledge_version:knowledge.version,quota:quotaResult.quota,model_status:"MODEL_CREDIT_BLOCKED",answer_engine:"KNOWLEDGE_CORE",answer:"StockRadar đã lưu được ngữ cảnh hội thoại, nhưng mô hình AI hiện chưa khả dụng. Bạn có thể hỏi trực tiếp một mã HOSE để dùng lớp phân tích dữ liệu hiện hành."}};
  const instructions = projectKnowledgeInstructions("Bạn là StockRadar AI. Trả lời bằng tiếng Việt rõ ràng, liên tục theo hội thoại. Chỉ giải thích phương pháp cho HOSE; không phân tích Crypto/Coin, HNX hoặc UPCoM. Trong nhánh KNOWLEDGE_ONLY, không có dữ liệu thị trường mới: không công bố giá, Buy Zone, Stop, Target, xác suất hay tín hiệu hành động; số trong lịch sử không phải dữ liệu hiện tại.", knowledge) + (projectContextInput(bridge,thread.id) ? PROJECT_HANDOFF_RULE : "");
  const context = {PROJECT_HANDOFF:projectContextInput(bridge,thread.id),USER_QUESTION:message,RECENT_CONVERSATION:history.slice(-12),THREAD_CONTEXT:{last_ticker:thread.last_ticker,last_horizon:thread.last_horizon},REQUESTED_HORIZON:inputHorizon};
  let response: Response;
  try {
    response = await fetch("https://api.openai.com/v1/responses",{
      method:"POST",signal:AbortSignal.timeout(25000),headers:{Authorization:`Bearer ${key}`,"Content-Type":"application/json"},
      body:JSON.stringify({model:Deno.env.get("OPENAI_MODEL")?.trim() || "gpt-5-mini",instructions,input:JSON.stringify(context),max_output_tokens:1400,store:false,reasoning:{effort:"minimal"}}),
    });
  } catch (error) {
    return {httpStatus:200,payload:{status:"READY_FALLBACK",reason:error?.name === "TimeoutError" ? "OPENAI_TIMEOUT" : "OPENAI_NETWORK_ERROR",tier,mode:"KNOWLEDGE_ONLY",thread_id:thread.id,knowledge_version:knowledge.version,quota:quotaResult.quota,model_status:error?.name === "TimeoutError" ? "MODEL_TIMEOUT" : "MODEL_ERROR",answer_engine:"KNOWLEDGE_CORE",answer:"Mô hình AI đang tạm thời chưa phản hồi. Lịch sử hội thoại của bạn vẫn được giữ lại."}};
  }
  let payload: any = null; try { payload = await response.json(); } catch {}
  const text = response.ok && payload?.status === "completed" ? openAIText(payload) : "";
  if (!text) return {httpStatus:200,payload:{status:"READY_FALLBACK",reason:`OPENAI_${response.status}`,tier,mode:"KNOWLEDGE_ONLY",thread_id:thread.id,knowledge_version:knowledge.version,quota:quotaResult.quota,model_status:"MODEL_ERROR",answer_engine:"KNOWLEDGE_CORE",answer:"StockRadar chưa tạo được câu trả lời từ mô hình AI lúc này. Lịch sử hội thoại vẫn được giữ lại."}};
  return {httpStatus:200,payload:{status:"READY",tier,scope:"conversation",mode:"KNOWLEDGE_ONLY",thread_id:thread.id,knowledge_version:knowledge.version,quota:quotaResult.quota,model_status:"MODEL_READY",answer_engine:"MODEL_PLUS_KNOWLEDGE_CORE",...projectKnowledgeMeta(knowledge,true),answer:text}};
}

Deno.serve(async (req: Request) => {
  const origin = req.headers.get("origin");
  try {
    if (origin && !ORIGINS.has(origin)) return json({status:"FORBIDDEN_ORIGIN"},403,null);
    if (req.method === "OPTIONS") return new Response(null,{status:204,headers:cors(origin)});
    if (req.method !== "POST") return json({status:"METHOD_NOT_ALLOWED"},405,origin);

    const authorization = req.headers.get("authorization") || "";
    const token = authorization.toLowerCase().startsWith("bearer ") ? authorization.slice(7).trim() : "";
    if (!token) return json({status:"UNAUTHORIZED"},401,origin);

    const url = Deno.env.get("SUPABASE_URL") || "";
    const anon = Deno.env.get("SUPABASE_ANON_KEY") || "";
    const serviceKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
    if (!url || !anon || !serviceKey) return json({status:"SERVICE_UNAVAILABLE"},503,origin);

    const auth = createClient(url,anon,{global:{headers:{Authorization:`Bearer ${token}`}},auth:{persistSession:false,autoRefreshToken:false}});
    const db = createClient(url,serviceKey,{auth:{persistSession:false,autoRefreshToken:false}});
    const {data:userData,error:userError} = await auth.auth.getUser(token);
    const user = userData?.user;
    if (userError || !user) return json({status:"UNAUTHORIZED"},401,origin);

    let body: any; try { body = await req.json(); } catch { return json({status:"INVALID_REQUEST",reason:"INVALID_JSON"},400,origin); }
    const operation = String(body.operation || "ask").trim().toLowerCase();
    if (!["ask","history","new_thread"].includes(operation) && !["project_bridge","resume_project"].includes(operation)) return json({status:"INVALID_REQUEST",reason:"INVALID_OPERATION"},400,origin);

    const [{data:profile,error:profileError},knowledge] = await Promise.all([
      auth.rpc("get_my_stockradar_access"),
      activeKnowledge(db),
    ]);
    const tier = String(profile?.account_tier || "").toUpperCase();
    if (profileError || String(profile?.account_status || "").toUpperCase() !== "ACTIVE" || !["FREE","TRIAL","PAID"].includes(tier)) return json({status:"FORBIDDEN",reason:"ACCOUNT_INACTIVE"},403,origin);

    const projectBridge = await loadProjectBridge(db,user.id);
    if (operation === "project_bridge") return json({status:"READY",project_bridge:projectBridgeMeta(projectBridge),knowledge_version:knowledge.version},200,origin);
    if (operation === "resume_project") {
      if (!projectBridge) return json({status:"NOT_FOUND",reason:"PROJECT_BRIDGE_NOT_LINKED"},404,origin);
      const linked = await ensureThread(db,user.id,projectBridge.thread_id,knowledge.version,false);
      const messages = await loadMessages(db,linked.id,40);
      return json({status:"READY",thread_id:linked.id,title:linked.title,project_bridge:projectBridgeMeta(projectBridge,linked.id),knowledge_version:knowledge.version,messages},200,origin);
    }
    if (operation === "new_thread") {
      const thread = await ensureThread(db,user.id,null,knowledge.version,true);
      return json({status:"READY",thread_id:thread.id,knowledge_version:knowledge.version,project_bridge:projectBridgeMeta(projectBridge,thread.id),messages:[]},200,origin);
    }

    const thread = await ensureThread(db,user.id,body.thread_id,knowledge.version,false);
    if (operation === "history") {
      const messages = await loadMessages(db,thread.id,40);
      return json({status:"READY",thread_id:thread.id,title:thread.title || null,knowledge_version:knowledge.version,project_bridge:projectBridgeMeta(projectBridge,thread.id),messages},200,origin);
    }

    const message = clean(body.message,700);
    if (!message) return json({status:"INVALID_REQUEST",reason:"EMPTY_MESSAGE"},400,origin);
    const existing = await loadMessages(db,thread.id,MAX_STORED_HISTORY);
    const explicit = explicitTicker(message);
    const requested = validTicker(body.ticker);
    const isMethodQuestion = methodologyIntent(message);
    const canFollowTicker = !isMethodQuestion && !portfolioIntent(message) && !scanIntent(message);
    const resolvedTicker = explicit || requested || (canFollowTicker ? validTicker(thread.last_ticker) : "");
    const explicitTickerNow = explicit || requested;
    const previousTicker = validTicker(thread.last_ticker);
    const tickerChanged = Boolean(explicitTickerNow && previousTicker && explicitTickerNow !== previousTicker);
    const inputHorizon = horizon(explicitHorizon(message) || body.horizon,tickerChanged ? "SHORT_TERM" : (thread.last_horizon || "SHORT_TERM"));
    const scope = resolvedTicker ? "ticker" : portfolioIntent(message) ? "portfolio" : scanIntent(message) ? "scan" : "conversation";

    if (scope === "conversation") {
      const result = await knowledgeAnswer(db,user.id,tier,message,existing,knowledge,thread,inputHorizon,projectBridge);
      result.payload = {...result.payload,project_bridge:projectBridgeMeta(projectBridge,thread.id,result.payload?.model_status === "MODEL_READY")};
      if (result.httpStatus === 200 && result.payload?.answer) {
        await saveExchange(db,thread,{message,scope:"conversation",ticker:"",horizon:inputHorizon},result.payload,knowledge.version);
      }
      return json(result.payload,result.httpStatus,origin);
    }

    const forward = {
      thread_id:thread.id,
      scope,
      ticker: resolvedTicker,
      horizon: inputHorizon,
      message,
      history: forwardHistory(existing,thread,knowledge),
    };
    const upstream = await fetch(`${url.replace(/\/$/,"")}/functions/v1/stock-ai`,{
      method:"POST",signal:AbortSignal.timeout(35000),headers:{Authorization:`Bearer ${token}`,apikey:anon,"Content-Type":"application/json"},body:JSON.stringify(forward),
    });
    let result: any = {}; try { result = await upstream.json(); } catch {}
    if (upstream.ok && result?.answer) {
      await saveExchange(db,thread,{message,scope:result.scope || scope,ticker:validTicker(result.ticker) || resolvedTicker,horizon:inputHorizon},result,result?.knowledge_version || knowledge.version);
    }
    return json({...result,thread_id:thread.id,conversation_persisted:upstream.ok && Boolean(result?.answer),knowledge_version:result?.knowledge_version || knowledge.version},upstream.status,origin);
  } catch (error) {
    if (error?.message === "THREAD_NOT_FOUND") return json({status:"NOT_FOUND",reason:"THREAD_NOT_FOUND"},404,origin);
    if (error?.message === "INVALID_THREAD_ID") return json({status:"INVALID_REQUEST",reason:"INVALID_THREAD_ID"},400,origin);
    console.error("stock-ai-chat","REQUEST_FAILED");
    return json({status:"SERVICE_UNAVAILABLE",answer:"StockRadar AI tạm thời chưa thể phản hồi. Vui lòng thử lại."},503,origin);
  }
});
