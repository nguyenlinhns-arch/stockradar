import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.95.0";
import { STOCKRADAR_SYSTEM_CORE, normalizeResearchContext, stockRadarMode } from "../_shared/stockradar-core.ts";

const ALLOWED_ORIGINS = new Set([
  "https://stockradar.vn",
  "https://www.stockradar.vn",
  "https://nguyenlinhns-arch.github.io",
  "http://localhost:8000",
  "http://127.0.0.1:8000",
]);
const HORIZONS = ["SHORT_TERM", "MEDIUM_TERM", "LONG_TERM", "ACCUMULATION"] as const;
const ACTIVE_TIERS = new Set(["FREE", "TRIAL", "PAID"]);
const PREMIUM_TIERS = new Set(["TRIAL", "PAID"]);
const MAX_MESSAGE_CHARS = 700;
const MAX_HISTORY_ITEMS = 6;
const MAX_HISTORY_CHARS = 600;
const MAX_PORTFOLIO_TICKERS = 20;

type Horizon = typeof HORIZONS[number];
type RequestScope = "ticker" | "portfolio";
type JsonObject = Record<string, unknown>;
type ServiceClient = ReturnType<typeof createClient>;
type WatchItem = {
  ticker: string;
  horizon: Horizon;
  owns_stock: boolean;
  alert_enabled: boolean;
  cost_basis: number | null;
  portfolio_weight_pct: number | null;
};

function corsHeaders(origin: string | null): HeadersInit {
  const headers: Record<string, string> = { "Vary": "Origin", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" };
  if (origin && ALLOWED_ORIGINS.has(origin)) {
    headers["Access-Control-Allow-Origin"] = origin;
    headers["Access-Control-Allow-Headers"] = "authorization, apikey, content-type";
    headers["Access-Control-Allow-Methods"] = "POST, OPTIONS";
  }
  return headers;
}
function jsonResponse(body: unknown, status: number, origin: string | null, extra: HeadersInit = {}): Response {
  return new Response(JSON.stringify(body), { status, headers: { ...corsHeaders(origin), ...extra, "Content-Type": "application/json; charset=utf-8" } });
}
function validTicker(value: string): boolean { return /^[A-Z0-9]{3}$/.test(value) && /[A-Z]/.test(value); }
function validHorizon(value: string): value is Horizon { return HORIZONS.includes(value as Horizon); }
function cleanMessage(value: unknown, maxChars = MAX_MESSAGE_CHARS): string { return String(value ?? "").replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim().slice(0, maxChars); }
function cleanHistory(value: unknown): Array<{ role: "user" | "assistant"; content: string }> {
  if (!Array.isArray(value)) return [];
  return value.slice(-MAX_HISTORY_ITEMS).flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const row = item as JsonObject;
    const role = row.role === "assistant" ? "assistant" : row.role === "user" ? "user" : null;
    const content = cleanMessage(row.content, MAX_HISTORY_CHARS);
    return role && content ? [{ role, content }] : [];
  });
}
function positionNumber(value: unknown, min: number, max = Number.POSITIVE_INFINITY): number | null {
  if (value == null || value === "") return null;
  const number = Number(value);
  if (!Number.isFinite(number) || number < min || number > max) return null;
  return number;
}
function messageHasExplicitHorizon(value: string): boolean {
  return /(tích sản|tich san|2\s*[-–]\s*5\s*năm|12\s*tháng|12\s*thang|6\s*[-–]\s*18\s*tháng|dài hạn|dai han|3\s*[-–]\s*6\s*tháng|1\s*[-–]\s*6\s*tháng|trung hạn|trung han|6\s*tháng|6\s*thang|ngắn hạn|ngan han|5\s*[-–]\s*20\s*phiên)/i.test(value);
}
function normalizeReport(raw: JsonObject): JsonObject {
  return { status: raw.status, ticker: raw.ticker, horizon: raw.horizon, snapshot_id: raw.snapshot_id, generated_at: raw.generated_at, expires_at: raw.expires_at, payload: raw.payload };
}
function extractOpenAIText(payload: unknown): string {
  if (!payload || typeof payload !== "object") return "";
  const data = payload as JsonObject;
  if (typeof data.output_text === "string" && data.output_text.trim()) return data.output_text.trim();
  if (!Array.isArray(data.output)) return "";
  const pieces: string[] = [];
  for (const item of data.output) {
    if (!item || typeof item !== "object") continue;
    const content = (item as JsonObject).content;
    if (!Array.isArray(content)) continue;
    for (const part of content) {
      if (!part || typeof part !== "object") continue;
      const row = part as JsonObject;
      if (row.type === "output_text" && typeof row.text === "string") pieces.push(row.text);
    }
  }
  return pieces.join("\n").trim();
}
function providerErrorCode(payload: unknown): string {
  if (!payload || typeof payload !== "object") return "UNKNOWN";
  const error = (payload as JsonObject).error;
  if (!error || typeof error !== "object") return "UNKNOWN";
  const row = error as JsonObject;
  return String(row.code || row.type || "UNKNOWN").toUpperCase().replace(/[^A-Z0-9_]+/g, "_").slice(0, 80);
}
async function audit(client: ServiceClient, userId: string, ticker: string, horizon: Horizon, outcome: string, reason: string, httpStatus: number, startedAt: number, remaining: number | null = null): Promise<void> {
  try {
    await client.rpc("record_stockradar_api_request_event", {
      p_user_id: userId,
      p_ticker: ticker,
      p_horizon: horizon,
      p_outcome: outcome,
      p_reason: reason,
      p_http_status: httpStatus,
      p_latency_ms: Math.max(0, Math.round(performance.now() - startedAt)),
      p_rate_limit_remaining: remaining,
    });
  } catch { console.error("stock-ai audit failed"); }
}
function latestTimestamp(values: unknown[]): string | null {
  const clean = values.map((value) => String(value || "")).filter(Boolean).sort();
  return clean.length ? clean[clean.length - 1] : null;
}

Deno.serve(async (req: Request) => {
  const startedAt = performance.now();
  const origin = req.headers.get("origin");
  if (origin && !ALLOWED_ORIGINS.has(origin)) return jsonResponse({ status: "FORBIDDEN_ORIGIN" }, 403, null);
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(origin) });
  if (req.method !== "POST") return jsonResponse({ status: "METHOD_NOT_ALLOWED" }, 405, origin, { Allow: "POST, OPTIONS" });

  const authorization = req.headers.get("authorization") || "";
  const token = authorization.toLowerCase().startsWith("bearer ") ? authorization.slice(7).trim() : "";
  if (!token) return jsonResponse({ status: "UNAUTHORIZED" }, 401, origin);

  const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY") || "";
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  if (!supabaseUrl || !anonKey || !serviceRoleKey) return jsonResponse({ status: "SERVICE_UNAVAILABLE" }, 503, origin);

  const authClient = createClient(supabaseUrl, anonKey, { auth: { persistSession: false, autoRefreshToken: false } });
  const { data: userData, error: userError } = await authClient.auth.getUser(token);
  const user = userData?.user;
  if (userError || !user) return jsonResponse({ status: "UNAUTHORIZED" }, 401, origin);

  let body: JsonObject;
  try { body = await req.json(); } catch { return jsonResponse({ status: "INVALID_REQUEST", reason: "INVALID_JSON" }, 400, origin); }
  const ticker = String(body.ticker || "").trim().toUpperCase();
  const scopeRaw = String(body.scope || "auto").trim().toLowerCase();
  const horizonRaw = String(body.horizon || "SHORT_TERM").trim().toUpperCase();
  const message = cleanMessage(body.message);
  const history = cleanHistory(body.history);
  if (!validHorizon(horizonRaw)) return jsonResponse({ status: "INVALID_REQUEST", reason: "INVALID_HORIZON" }, 400, origin);
  const horizon = horizonRaw as Horizon;
  if (!message) return jsonResponse({ status: "INVALID_REQUEST", reason: "EMPTY_MESSAGE" }, 400, origin);
  if (!new Set(["auto", "ticker", "portfolio"]).has(scopeRaw)) return jsonResponse({ status: "INVALID_REQUEST", reason: "INVALID_SCOPE" }, 400, origin);

  let scope: RequestScope;
  if (scopeRaw === "portfolio") scope = "portfolio";
  else if (scopeRaw === "ticker" || ticker) scope = "ticker";
  else scope = "portfolio";
  if (scope === "ticker" && !validTicker(ticker)) return jsonResponse({ status: "INVALID_REQUEST", reason: "INVALID_TICKER" }, 400, origin);

  const serviceClient = createClient(supabaseUrl, serviceRoleKey, { auth: { persistSession: false, autoRefreshToken: false } });
  const [{ data: profile, error: profileError }, { data: preferenceRows }, { data: watchRows }] = await Promise.all([
    serviceClient.from("profiles").select("account_tier,account_status").eq("id", user.id).maybeSingle(),
    serviceClient.from("user_preferences").select("preferred_horizons,preferred_sectors,updated_at").eq("user_id", user.id).maybeSingle(),
    serviceClient.from("watchlist_items").select("ticker,horizon,owns_stock,alert_enabled,cost_basis,portfolio_weight_pct,created_at").eq("user_id", user.id).is("removed_at", null).order("owns_stock", { ascending: false }).order("created_at", { ascending: true }).limit(MAX_PORTFOLIO_TICKERS),
  ]);

  const tier = String(profile?.account_tier || "").toUpperCase();
  const accountStatus = String(profile?.account_status || "").toUpperCase();
  if (profileError || accountStatus !== "ACTIVE" || !ACTIVE_TIERS.has(tier)) {
    await audit(serviceClient, user.id, ticker, horizon, "FORBIDDEN", "ACCOUNT_INACTIVE", 403, startedAt);
    return jsonResponse({ status: "FORBIDDEN", reason: "ACCOUNT_INACTIVE" }, 403, origin);
  }

  const preferences = {
    preferred_horizons: Array.isArray(preferenceRows?.preferred_horizons) ? preferenceRows.preferred_horizons.map((value: unknown) => String(value)).filter(validHorizon) : [],
    preferred_sectors: Array.isArray(preferenceRows?.preferred_sectors) ? preferenceRows.preferred_sectors.map((value: unknown) => cleanMessage(value, 80)).filter(Boolean).slice(0, 3) : [],
  };
  const watchlist: WatchItem[] = (Array.isArray(watchRows) ? watchRows : []).flatMap((row: JsonObject) => {
    const itemTicker = String(row.ticker || "").trim().toUpperCase();
    const itemHorizon = String(row.horizon || "SHORT_TERM").trim().toUpperCase();
    if (!validTicker(itemTicker) || !validHorizon(itemHorizon)) return [];
    const ownsStock = row.owns_stock === true;
    return [{
      ticker: itemTicker,
      horizon: itemHorizon as Horizon,
      owns_stock: ownsStock,
      alert_enabled: PREMIUM_TIERS.has(tier) && row.alert_enabled === true,
      cost_basis: ownsStock ? positionNumber(row.cost_basis, 0.0001) : null,
      portfolio_weight_pct: ownsStock ? positionNumber(row.portfolio_weight_pct, 0, 100) : null,
    }];
  });
  const ownedCount = watchlist.filter((item) => item.owns_stock).length;
  const alertCount = watchlist.filter((item) => item.alert_enabled).length;
  const positionContextCount = watchlist.filter((item) => item.owns_stock && (item.cost_basis !== null || item.portfolio_weight_pct !== null)).length;
  const requestedWatchItem = scope === "ticker" ? (watchlist.find((item) => item.ticker === ticker) || null) : null;
  const personalizationSummary = scope === "portfolio"
    ? { watchlist_count: watchlist.length, owned_count: ownedCount, alert_count: alertCount, position_context_count: positionContextCount }
    : { requested_ticker_configured: requestedWatchItem !== null, owns_stock: requestedWatchItem?.owns_stock ?? null, alert_enabled: requestedWatchItem?.alert_enabled ?? null, position_context_configured: Boolean(requestedWatchItem?.cost_basis !== null || requestedWatchItem?.portfolio_weight_pct !== null) };

  if (scope === "portfolio" && !watchlist.length) {
    await audit(serviceClient, user.id, "", horizon, "NO_WATCHLIST", "EMPTY_WATCHLIST", 200, startedAt);
    return jsonResponse({ status: "NO_WATCHLIST", scope, horizon, tier, answer: "Tài khoản hiện chưa có mã trong watchlist. Hãy thêm mã và đánh dấu mã đang sở hữu nếu có; StockRadar AI sẽ dùng đúng danh sách đó cho câu hỏi về danh mục.", personalization: personalizationSummary, quota_consumed: false }, 200, origin);
  }

  const explicitPortfolioHorizon = messageHasExplicitHorizon(message);
  const reportRequests = scope === "ticker"
    ? HORIZONS.map((itemHorizon) => ({ ticker, horizon: itemHorizon }))
    : watchlist.map((item) => ({ ticker: item.ticker, horizon: explicitPortfolioHorizon ? horizon : item.horizon }));
  const researchTickers = scope === "ticker" ? [ticker] : [...new Set(watchlist.map((item) => item.ticker))];

  const [reportRows, researchRows] = await Promise.all([
    Promise.all(reportRequests.map(async (request) => {
      const { data, error } = await serviceClient.rpc("fetch_stockradar_cached_report", { p_ticker: request.ticker, p_horizon: request.horizon });
      return { ...request, data: data as JsonObject | null, error };
    })),
    Promise.all(researchTickers.map(async (researchTicker) => {
      const { data, error } = await serviceClient.rpc("fetch_stockradar_internal_research_context", { p_ticker: researchTicker });
      return { ticker: researchTicker, data: data as JsonObject | null, error };
    })),
  ]);

  const readyRows = reportRows.filter((row) => !row.error && row.data?.status === "READY");
  const researchContexts = researchRows.flatMap((row) => {
    if (row.error) return [];
    const normalized = normalizeResearchContext(row.data);
    return normalized ? [normalized] : [];
  });
  const mode = stockRadarMode(readyRows.length > 0, researchContexts.length > 0);

  const openAIKey = Deno.env.get("OPENAI_API_KEY")?.trim();
  if (!openAIKey) {
    await audit(serviceClient, user.id, scope === "ticker" ? ticker : "", horizon, "AI_CONFIG_PENDING", "OPENAI_KEY_MISSING", 200, startedAt);
    return jsonResponse({ status: "AI_CONFIG_PENDING", scope, ticker: scope === "ticker" ? ticker : null, horizon, tier, mode, answer: "StockRadar AI đã nối tới lõi phân tích nhưng lớp model production chưa được kích hoạt.", personalization: personalizationSummary, quota_consumed: false }, 200, origin);
  }

  const { data: quotaRaw, error: quotaError } = await serviceClient.rpc("consume_stockradar_api_quota", { p_user_id: user.id, p_bucket: "stock_ai" });
  const quota = (quotaRaw || {}) as JsonObject;
  if (quotaError || !quotaRaw) {
    await audit(serviceClient, user.id, scope === "ticker" ? ticker : "", horizon, "SERVICE_UNAVAILABLE", "AI_QUOTA_RPC_FAILED", 503, startedAt);
    return jsonResponse({ status: "SERVICE_UNAVAILABLE", reason: "AI_QUOTA_RPC_FAILED" }, 503, origin);
  }
  const remainingNumber = Number(quota.remaining ?? Number.NaN);
  const remaining = Number.isFinite(remainingNumber) ? remainingNumber : null;
  const limit = Number(quota.limit ?? Number.NaN);
  const retryAfter = Number(quota.retry_after ?? 0);
  const resetAt = String(quota.reset_at || "") || null;
  const rateHeaders: Record<string, string> = {};
  if (Number.isFinite(limit)) rateHeaders["X-RateLimit-Limit"] = String(limit);
  if (remaining !== null) rateHeaders["X-RateLimit-Remaining"] = String(remaining);
  if (quota.allowed !== true) {
    if (retryAfter > 0) rateHeaders["Retry-After"] = String(retryAfter);
    await audit(serviceClient, user.id, scope === "ticker" ? ticker : "", horizon, "RATE_LIMITED", "AI_RATE_LIMITED", 429, startedAt, remaining);
    const rateAnswer = tier === "FREE" ? "Bạn đã dùng đủ 10 lượt StockRadar AI hôm nay. Hạn mức Free được làm mới lúc 00:00 theo giờ Việt Nam." : "Bạn đã dùng hết lượt StockRadar AI trong cửa sổ hiện tại. Hãy thử lại sau khi hạn mức được làm mới.";
    return jsonResponse({ status: "RATE_LIMITED", reason: "AI_RATE_LIMITED", answer: rateAnswer, tier, quota: { remaining: 0, limit: Number.isFinite(limit) ? limit : null, window_seconds: Number(quota.window_seconds || 0) || null, reset_at: resetAt, reset_timezone: quota.daily_reset_timezone || null }, retry_after: retryAfter }, 429, origin, rateHeaders);
  }

  const actionContext = readyRows.map((row) => normalizeReport(row.data as JsonObject));
  const userContext = scope === "portfolio"
    ? {
        preferred_horizons: preferences.preferred_horizons,
        preferred_sectors: preferences.preferred_sectors,
        watchlist: watchlist.map((item) => ({ ticker: item.ticker, horizon: item.horizon, owns_stock: item.owns_stock, alert_enabled: item.alert_enabled, cost_basis: item.cost_basis, portfolio_weight_pct: item.portfolio_weight_pct })),
        watchlist_count: watchlist.length,
        owned_count: ownedCount,
        alert_count: alertCount,
        position_context_count: positionContextCount,
      }
    : {
        preferred_horizons: preferences.preferred_horizons,
        preferred_sectors: preferences.preferred_sectors,
        requested_ticker: requestedWatchItem ? { ticker: requestedWatchItem.ticker, horizon: requestedWatchItem.horizon, owns_stock: requestedWatchItem.owns_stock, alert_enabled: requestedWatchItem.alert_enabled, cost_basis: requestedWatchItem.cost_basis, portfolio_weight_pct: requestedWatchItem.portfolio_weight_pct } : null,
      };

  const context = {
    RESPONSE_MODE: mode,
    ACCESS_TIER: tier,
    REQUEST_SCOPE: scope,
    REQUESTED_TICKER: scope === "ticker" ? ticker : null,
    REQUESTED_HORIZON: horizon,
    PORTFOLIO_HORIZON_EXPLICIT: scope === "portfolio" ? explicitPortfolioHorizon : null,
    USER_QUESTION: message,
    RECENT_CONVERSATION: history,
    USER_CONTEXT: userContext,
    ACTION_CONTEXT: actionContext,
    RESEARCH_CONTEXT: scope === "ticker" ? (researchContexts[0] || null) : researchContexts,
  };

  const model = Deno.env.get("OPENAI_MODEL")?.trim() || "gpt-5-mini";
  let aiResponse: Response;
  try {
    aiResponse = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: { "Authorization": `Bearer ${openAIKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model, instructions: STOCKRADAR_SYSTEM_CORE, input: JSON.stringify(context), max_output_tokens: scope === "portfolio" ? 1500 : 1100, store: false }),
    });
  } catch {
    await audit(serviceClient, user.id, scope === "ticker" ? ticker : "", horizon, "AI_UPSTREAM_ERROR", "OPENAI_NETWORK_ERROR", 502, startedAt, remaining);
    return jsonResponse({ status: "AI_UPSTREAM_ERROR", mode, answer: "Lớp AI tạm thời không phản hồi. Dữ liệu StockRadar không bị thay thế bằng nguồn khác." }, 502, origin, rateHeaders);
  }

  let aiPayload: unknown = null;
  try { aiPayload = await aiResponse.json(); } catch { aiPayload = null; }
  if (!aiResponse.ok) {
    const code = providerErrorCode(aiPayload);
    console.error("stock-ai upstream", aiResponse.status, code);
    await audit(serviceClient, user.id, scope === "ticker" ? ticker : "", horizon, "AI_UPSTREAM_ERROR", `OPENAI_${aiResponse.status}_${code}`, 502, startedAt, remaining);
    return jsonResponse({ status: "AI_UPSTREAM_ERROR", reason: `OPENAI_${aiResponse.status}_${code}`, provider_status: aiResponse.status, provider_code: code, mode, answer: "Lớp AI tạm thời chưa thể diễn giải dữ liệu." }, 502, origin, rateHeaders);
  }

  const answer = extractOpenAIText(aiPayload);
  if (!answer) {
    await audit(serviceClient, user.id, scope === "ticker" ? ticker : "", horizon, "AI_UPSTREAM_ERROR", "EMPTY_AI_RESPONSE", 502, startedAt, remaining);
    return jsonResponse({ status: "AI_UPSTREAM_ERROR", mode, answer: "Lớp AI không trả về nội dung hợp lệ." }, 502, origin, rateHeaders);
  }

  const selectedReport = scope === "ticker" ? (readyRows.find((row) => row.horizon === horizon)?.data || readyRows[0]?.data || {}) : (readyRows[0]?.data || {});
  const selected = selectedReport as JsonObject;
  const snapshotIds = [...new Set([
    ...readyRows.map((row) => String(row.data?.snapshot_id || "")),
    ...researchContexts.map((row) => String(row.snapshot_id || "")),
  ].filter(Boolean))];
  const coveredTickers = [...new Set([
    ...readyRows.map((row) => row.ticker),
    ...researchContexts.map((row) => String(row.ticker || "")),
  ].filter(Boolean))];
  const generatedAt = latestTimestamp([
    ...readyRows.map((row) => row.data?.generated_at),
    ...researchContexts.map((row) => row.generated_at),
  ]);

  const auditReason = mode === "ACTION_READY" ? (scope === "portfolio" ? "ACTION_AND_RESEARCH_PORTFOLIO" : "ACTION_AND_RESEARCH_TICKER") : mode === "RESEARCH_ONLY" ? "RESEARCH_CONTEXT" : "METHOD_ONLY";
  await audit(serviceClient, user.id, scope === "ticker" ? ticker : "", horizon, "AI_READY", auditReason, 200, startedAt, remaining);
  return jsonResponse({
    status: "READY",
    scope,
    ticker: scope === "ticker" ? ticker : null,
    horizon,
    tier,
    mode,
    answer,
    personalization: personalizationSummary,
    source: {
      action_gate: readyRows.length ? "READY" : "PENDING",
      action_ready_reports: readyRows.length,
      research_ready: researchContexts.length > 0,
      research_ready_count: researchContexts.length,
      snapshot_id: snapshotIds.length === 1 ? snapshotIds[0] : (selected.snapshot_id || null),
      snapshot_count: snapshotIds.length,
      generated_at: generatedAt || selected.generated_at || null,
      expires_at: selected.expires_at || null,
      ready_horizons: scope === "ticker" ? readyRows.map((row) => row.horizon) : undefined,
      covered_tickers: scope === "portfolio" ? coveredTickers : undefined,
    },
    quota: {
      remaining,
      limit: Number.isFinite(limit) ? limit : null,
      unlimited: quota.unlimited === true,
      window_seconds: Number(quota.window_seconds || 0) || null,
      reset_at: resetAt,
      reset_timezone: quota.daily_reset_timezone || null,
    },
  }, 200, origin, rateHeaders);
});
