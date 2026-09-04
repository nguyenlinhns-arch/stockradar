import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.95.0";
import {
  STOCKRADAR_SYSTEM_CORE,
  deterministicStockRadarAnswer,
  normalizeResearchContext,
  stockRadarMode,
} from "../_shared/stockradar-core.ts";

const ALLOWED_ORIGINS = new Set([
  "https://stockradar.vn",
  "https://www.stockradar.vn",
  "https://nguyenlinhns-arch.github.io",
  "http://localhost:8000",
  "http://127.0.0.1:8000",
]);
const HORIZONS = ["SHORT_TERM", "MEDIUM_TERM", "LONG_TERM", "ACCUMULATION"] as const;
const MAX_HISTORY_ITEMS = 6;
type JsonObject = Record<string, unknown>;
type Horizon = typeof HORIZONS[number];

function corsHeaders(origin: string | null): HeadersInit {
  const headers: Record<string, string> = { "Vary": "Origin", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" };
  if (origin && ALLOWED_ORIGINS.has(origin)) {
    headers["Access-Control-Allow-Origin"] = origin;
    headers["Access-Control-Allow-Headers"] = "apikey, content-type";
    headers["Access-Control-Allow-Methods"] = "POST, OPTIONS";
  }
  return headers;
}
function jsonResponse(body: unknown, status: number, origin: string | null, extra: HeadersInit = {}): Response {
  return new Response(JSON.stringify(body), { status, headers: { ...corsHeaders(origin), ...extra, "Content-Type": "application/json; charset=utf-8" } });
}
function validTicker(value: string): boolean { return /^[A-Z0-9]{3}$/.test(value) && /[A-Z]/.test(value); }
function validHorizon(value: string): value is Horizon { return HORIZONS.includes(value as Horizon); }
function cleanText(value: unknown, max = 700): string { return String(value ?? "").replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim().slice(0, max); }
function cleanHistory(value: unknown): Array<{ role: "user" | "assistant"; content: string }> {
  if (!Array.isArray(value)) return [];
  return value.slice(-MAX_HISTORY_ITEMS).flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const row = item as JsonObject;
    const role = row.role === "assistant" ? "assistant" : row.role === "user" ? "user" : null;
    const content = cleanText(row.content, 600);
    return role && content ? [{ role, content }] : [];
  });
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
    if (!item || typeof item !== "object" || !Array.isArray((item as JsonObject).content)) continue;
    for (const part of (item as JsonObject).content as unknown[]) {
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
async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, "0")).join("");
}

Deno.serve(async (req: Request) => {
  const origin = req.headers.get("origin");
  if (origin && !ALLOWED_ORIGINS.has(origin)) return jsonResponse({ status: "FORBIDDEN_ORIGIN" }, 403, null);
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(origin) });
  if (req.method !== "POST") return jsonResponse({ status: "METHOD_NOT_ALLOWED" }, 405, origin, { Allow: "POST, OPTIONS" });

  let body: JsonObject;
  try { body = await req.json(); } catch { return jsonResponse({ status: "INVALID_REQUEST", reason: "INVALID_JSON" }, 400, origin); }
  const ticker = String(body.ticker || "").trim().toUpperCase();
  const horizonRaw = String(body.horizon || "SHORT_TERM").trim().toUpperCase();
  const message = cleanText(body.message);
  const history = cleanHistory(body.history);
  const guestId = String(body.guest_id || "").trim();
  if (!validTicker(ticker)) return jsonResponse({ status: "INVALID_REQUEST", reason: "INVALID_TICKER" }, 400, origin);
  if (!validHorizon(horizonRaw)) return jsonResponse({ status: "INVALID_REQUEST", reason: "INVALID_HORIZON" }, 400, origin);
  if (!message) return jsonResponse({ status: "INVALID_REQUEST", reason: "EMPTY_MESSAGE" }, 400, origin);
  if (!/^[A-Za-z0-9._:-]{20,128}$/.test(guestId)) return jsonResponse({ status: "INVALID_REQUEST", reason: "INVALID_GUEST_ID" }, 400, origin);
  const horizon = horizonRaw as Horizon;

  const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  if (!supabaseUrl || !serviceRoleKey) return jsonResponse({ status: "SERVICE_UNAVAILABLE" }, 503, origin);
  const serviceClient = createClient(supabaseUrl, serviceRoleKey, { auth: { persistSession: false, autoRefreshToken: false } });

  const [reportRows, researchResult] = await Promise.all([
    Promise.all(HORIZONS.map(async (itemHorizon) => {
      const { data, error } = await serviceClient.rpc("fetch_stockradar_cached_report", { p_ticker: ticker, p_horizon: itemHorizon });
      return { horizon: itemHorizon, data: data as JsonObject | null, error };
    })),
    serviceClient.rpc("fetch_stockradar_internal_research_context", { p_ticker: ticker }),
  ]);
  const readyRows = reportRows.filter((row) => !row.error && row.data?.status === "READY");
  const researchContext = researchResult.error ? null : normalizeResearchContext(researchResult.data as JsonObject | null);
  const mode = stockRadarMode(readyRows.length > 0, Boolean(researchContext));

  const guestHash = await sha256Hex(`stockradar-guest-v4|${guestId}`);
  const { data: quotaRaw, error: quotaError } = await serviceClient.rpc("consume_stockradar_guest_ai_quota", { p_guest_key_hash: guestHash });
  const quota = (quotaRaw || {}) as JsonObject;
  if (quotaError || !quotaRaw) return jsonResponse({ status: "SERVICE_UNAVAILABLE", reason: "GUEST_QUOTA_RPC_FAILED" }, 503, origin);
  if (quota.allowed !== true) {
    const retryAfter = Number(quota.retry_after || 0);
    const extra: Record<string, string> = retryAfter > 0 ? { "Retry-After": String(retryAfter) } : {};
    return jsonResponse({ status: "RATE_LIMITED", tier: "GUEST", mode, answer: "Bạn đã dùng đủ 3 câu StockRadar AI hôm nay. Đăng ký Free để dùng 10 câu/ngày.", quota: { limit: 3, remaining: 0, reset_at: quota.reset_at || null, reset_timezone: quota.daily_reset_timezone || "Asia/Ho_Chi_Minh" } }, 429, origin, extra);
  }

  const actionContext = readyRows.map((row) => normalizeReport(row.data as JsonObject));
  const fallbackAnswer = deterministicStockRadarAnswer({
    mode,
    researchContext,
    actionContext,
    question: message,
  });
  const remainingNumber = Number(quota.remaining ?? Number.NaN);
  const remaining = Number.isFinite(remainingNumber) ? remainingNumber : null;
  const generatedTimes = actionContext.map((r) => String(r.generated_at || "")).filter(Boolean);
  if (researchContext?.generated_at) generatedTimes.push(String(researchContext.generated_at));
  generatedTimes.sort();
  const snapshotIds = [...new Set([
    ...actionContext.map((r) => String(r.snapshot_id || "")),
    String(researchContext?.snapshot_id || ""),
  ].filter(Boolean))];
  const source = {
    action_gate: readyRows.length ? "READY" : "PENDING",
    research_ready: Boolean(researchContext),
    snapshot_id: snapshotIds.length === 1 ? snapshotIds[0] : null,
    snapshot_count: snapshotIds.length,
    generated_at: generatedTimes.length ? generatedTimes[generatedTimes.length - 1] : null,
    ready_horizons: readyRows.map((row) => row.horizon),
  };
  const quotaResponse = { limit: 3, remaining, reset_at: quota.reset_at || null, reset_timezone: quota.daily_reset_timezone || "Asia/Ho_Chi_Minh" };
  const rateHeaders = { "X-RateLimit-Limit": "3", ...(remaining !== null ? { "X-RateLimit-Remaining": String(remaining) } : {}) };

  if (mode === "METHOD_ONLY") {
    return jsonResponse({ status: "READY", scope: "ticker", tier: "GUEST", mode, answer_engine: "STOCKRADAR_CORE", ticker, horizon, answer: fallbackAnswer, quota_consumed: true, source, quota: quotaResponse }, 200, origin, rateHeaders);
  }

  const openAIKey = Deno.env.get("OPENAI_API_KEY")?.trim();
  if (!openAIKey) {
    return jsonResponse({ status: "READY_FALLBACK", scope: "ticker", tier: "GUEST", mode, answer_engine: "STOCKRADAR_CORE", ticker, horizon, answer: fallbackAnswer, quota_consumed: true, source, quota: quotaResponse }, 200, origin, rateHeaders);
  }

  const context = {
    RESPONSE_MODE: mode,
    ACCESS_TIER: "GUEST",
    REQUEST_SCOPE: "ticker",
    REQUESTED_TICKER: ticker,
    REQUESTED_HORIZON: horizon,
    USER_QUESTION: message,
    RECENT_CONVERSATION: history,
    USER_CONTEXT: { authenticated: false, portfolio_available: false, watchlist_available: false },
    ACTION_CONTEXT: actionContext,
    RESEARCH_CONTEXT: researchContext,
  };
  const model = Deno.env.get("OPENAI_MODEL")?.trim() || "gpt-5-mini";
  let aiResponse: Response;
  try {
    aiResponse = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: { Authorization: `Bearer ${openAIKey}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model, instructions: STOCKRADAR_SYSTEM_CORE, input: JSON.stringify(context), max_output_tokens: 1000, store: false }),
    });
  } catch {
    return jsonResponse({ status: "READY_FALLBACK", reason: "OPENAI_NETWORK_ERROR", scope: "ticker", tier: "GUEST", mode, answer_engine: "STOCKRADAR_CORE", ticker, horizon, answer: fallbackAnswer, quota_consumed: true, source, quota: quotaResponse }, 200, origin, rateHeaders);
  }

  let payload: unknown = null;
  try { payload = await aiResponse.json(); } catch { payload = null; }
  if (!aiResponse.ok) {
    const code = providerErrorCode(payload);
    console.error("stock-ai-guest upstream", aiResponse.status, code);
    return jsonResponse({ status: "READY_FALLBACK", reason: `OPENAI_${aiResponse.status}_${code}`, scope: "ticker", tier: "GUEST", mode, answer_engine: "STOCKRADAR_CORE", ticker, horizon, answer: fallbackAnswer, quota_consumed: true, source, quota: quotaResponse }, 200, origin, rateHeaders);
  }

  const answer = extractOpenAIText(payload) || fallbackAnswer;
  return jsonResponse({ status: "READY", scope: "ticker", tier: "GUEST", mode, answer_engine: "MODEL_PLUS_STOCKRADAR_CORE", ticker, horizon, answer, quota_consumed: true, source, quota: quotaResponse }, 200, origin, rateHeaders);
});
