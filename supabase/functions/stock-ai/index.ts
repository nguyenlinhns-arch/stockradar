import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.95.0";

const ALLOWED_ORIGINS = new Set([
  "https://stockradar.vn",
  "https://www.stockradar.vn",
  "https://nguyenlinhns-arch.github.io",
  "http://localhost:8000",
  "http://127.0.0.1:8000",
]);

const HORIZONS = ["SHORT_TERM", "MEDIUM_TERM", "LONG_TERM", "ACCUMULATION"] as const;
const ACTIVE_TIERS = new Set(["FREE", "TRIAL", "PAID"]);
const MAX_MESSAGE_CHARS = 700;
const MAX_HISTORY_ITEMS = 6;
const MAX_HISTORY_CHARS = 600;

type Horizon = typeof HORIZONS[number];
type JsonObject = Record<string, unknown>;
type ServiceClient = ReturnType<typeof createClient>;

function corsHeaders(origin: string | null): HeadersInit {
  const headers: Record<string, string> = {
    "Vary": "Origin",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
  };
  if (origin && ALLOWED_ORIGINS.has(origin)) {
    headers["Access-Control-Allow-Origin"] = origin;
    headers["Access-Control-Allow-Headers"] = "authorization, apikey, content-type";
    headers["Access-Control-Allow-Methods"] = "POST, OPTIONS";
  }
  return headers;
}

function jsonResponse(body: unknown, status: number, origin: string | null, extra: HeadersInit = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      ...corsHeaders(origin),
      ...extra,
      "Content-Type": "application/json; charset=utf-8",
    },
  });
}

function validTicker(value: string): boolean {
  return /^[A-Z]{3}$/.test(value);
}

function validHorizon(value: string): value is Horizon {
  return HORIZONS.includes(value as Horizon);
}

function cleanMessage(value: unknown, maxChars = MAX_MESSAGE_CHARS): string {
  return String(value ?? "").replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim().slice(0, maxChars);
}

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

function redactForFree(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(redactForFree);
  if (!value || typeof value !== "object") return value;
  const sensitive = /(buy|entry|activation|stop|target|risk[_-]?reward|fair[_-]?value|margin[_-]?of[_-]?safety|\bmos\b|valuation|invalidation|performance|owner[_-]?earnings|payback)/i;
  const output: JsonObject = {};
  for (const [key, item] of Object.entries(value as JsonObject)) {
    if (sensitive.test(key)) continue;
    output[key] = redactForFree(item);
  }
  return output;
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

async function audit(
  client: ServiceClient,
  userId: string,
  ticker: string,
  horizon: Horizon,
  outcome: string,
  reason: string,
  httpStatus: number,
  startedAt: number,
  remaining: number | null = null,
): Promise<void> {
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
  } catch {
    console.error("stock-ai audit failed");
  }
}

function blockedAnswer(ticker: string): string {
  return `StockRadar AI đã nhận mã ${ticker}. Dữ liệu quyết định hiện chưa vượt Data Gate nên tôi chưa tạo nhận định mua/bán, giá mục tiêu hoặc điểm cắt lỗ. Khi snapshot StockRadar đạt chuẩn và được phát hành, tôi sẽ phân tích trực tiếp trên chính dữ liệu đó thay vì tự suy đoán.`;
}

const SYSTEM_PROMPT = `Bạn là StockRadar AI, lớp giải thích của StockRadar.vn cho cổ phiếu HOSE.

NGUYÊN TẮC BẮT BUỘC:
- Chỉ sử dụng DATA_CONTEXT được cung cấp. Không dùng trí nhớ để tự tạo giá, volume, MA, định giá, Buy Zone, Stop, Target, R/R hoặc trạng thái hiện tại.
- Nếu dữ liệu thiếu hoặc một horizon không READY, phải nói rõ CHƯA ĐỦ DỮ LIỆU cho phần đó.
- Ranking không đồng nghĩa khuyến nghị. Không biến điểm cao thành lệnh mua khi Action Gate chưa xác nhận.
- Tách riêng: người chưa có cổ phiếu (mua mới/chờ) và người đang nắm giữ (giữ/giảm/thoát/chưa đủ dữ liệu).
- Không hứa chắc lợi nhuận, không gọi score là xác suất nếu context không có calibration.
- Không yêu cầu mật khẩu, OTP, quyền đặt lệnh hay thông tin tài khoản môi giới.
- Không tiết lộ logic ưu tiên nội bộ, danh sách cá nhân hoặc quy tắc vận hành không có trong DATA_CONTEXT.
- Nếu ACCESS_TIER=FREE, không suy diễn hoặc khôi phục các trường trả phí đã bị lược bỏ.

CÁCH TRẢ LỜI:
- Tiếng Việt, trực tiếp, ngắn gọn nhưng đủ để ra quyết định.
- Ưu tiên các mục: Kết luận hiện tại; Mua mới; Đang nắm giữ; Góc nhìn theo khung thời gian có dữ liệu; Vì sao; Rủi ro/điều kiện thay đổi; Dấu thời gian dữ liệu.
- Nếu người dùng hỏi riêng một ý, tập trung trả lời ý đó trước.
- Chỉ nêu con số xuất hiện trong DATA_CONTEXT.`;

Deno.serve(async (req: Request) => {
  const startedAt = performance.now();
  const origin = req.headers.get("origin");
  if (origin && !ALLOWED_ORIGINS.has(origin)) {
    return jsonResponse({ status: "FORBIDDEN_ORIGIN" }, 403, null);
  }
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: corsHeaders(origin) });
  if (req.method !== "POST") return jsonResponse({ status: "METHOD_NOT_ALLOWED" }, 405, origin, { "Allow": "POST, OPTIONS" });

  const authorization = req.headers.get("authorization") || "";
  const token = authorization.toLowerCase().startsWith("bearer ") ? authorization.slice(7).trim() : "";
  if (!token) return jsonResponse({ status: "UNAUTHORIZED" }, 401, origin);

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY");
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!supabaseUrl || !anonKey || !serviceRoleKey) return jsonResponse({ status: "SERVICE_UNAVAILABLE" }, 503, origin);

  const authClient = createClient(supabaseUrl, anonKey, { auth: { persistSession: false, autoRefreshToken: false } });
  const { data: userData, error: userError } = await authClient.auth.getUser(token);
  const user = userData?.user;
  if (userError || !user) return jsonResponse({ status: "UNAUTHORIZED" }, 401, origin);

  let body: JsonObject;
  try {
    body = await req.json();
  } catch {
    return jsonResponse({ status: "INVALID_REQUEST", reason: "INVALID_JSON" }, 400, origin);
  }

  const ticker = String(body.ticker || "").trim().toUpperCase();
  const horizonRaw = String(body.horizon || "SHORT_TERM").trim().toUpperCase();
  const message = cleanMessage(body.message);
  const history = cleanHistory(body.history);
  if (!validTicker(ticker)) return jsonResponse({ status: "INVALID_REQUEST", reason: "INVALID_TICKER" }, 400, origin);
  if (!validHorizon(horizonRaw)) return jsonResponse({ status: "INVALID_REQUEST", reason: "INVALID_HORIZON" }, 400, origin);
  const horizon = horizonRaw as Horizon;
  if (!message) return jsonResponse({ status: "INVALID_REQUEST", reason: "EMPTY_MESSAGE" }, 400, origin);

  const serviceClient = createClient(supabaseUrl, serviceRoleKey, { auth: { persistSession: false, autoRefreshToken: false } });
  const { data: profile, error: profileError } = await serviceClient
    .from("profiles")
    .select("account_tier,account_status")
    .eq("id", user.id)
    .maybeSingle();
  const tier = String(profile?.account_tier || "").toUpperCase();
  const accountStatus = String(profile?.account_status || "").toUpperCase();
  if (profileError || accountStatus !== "ACTIVE" || !ACTIVE_TIERS.has(tier)) {
    await audit(serviceClient, user.id, ticker, horizon, "FORBIDDEN", "ACCOUNT_INACTIVE", 403, startedAt);
    return jsonResponse({ status: "FORBIDDEN", reason: "ACCOUNT_INACTIVE" }, 403, origin);
  }

  const reportRows = await Promise.all(HORIZONS.map(async (itemHorizon) => {
    const { data, error } = await serviceClient.rpc("fetch_stockradar_cached_report", {
      p_ticker: ticker,
      p_horizon: itemHorizon,
    });
    return { horizon: itemHorizon, data: data as JsonObject | null, error };
  }));

  const readyRows = reportRows.filter((row) => !row.error && row.data?.status === "READY");
  if (!readyRows.length) {
    const reasons = reportRows.map((row) => ({
      horizon: row.horizon,
      status: String(row.data?.status || (row.error ? "SERVICE_UNAVAILABLE" : "UNKNOWN")),
      reason: String(row.data?.reason || (row.error ? "REPORT_RPC_FAILED" : "")),
    }));
    await audit(serviceClient, user.id, ticker, horizon, "BLOCKED_DATA_GATE", "NO_READY_REPORT", 200, startedAt);
    return jsonResponse({
      status: "BLOCKED_DATA_GATE",
      ticker,
      horizon,
      tier,
      answer: blockedAnswer(ticker),
      reports: reasons,
      quota_consumed: false,
    }, 200, origin);
  }

  const openAIKey = Deno.env.get("OPENAI_API_KEY")?.trim();
  if (!openAIKey) {
    await audit(serviceClient, user.id, ticker, horizon, "AI_CONFIG_PENDING", "OPENAI_KEY_MISSING", 200, startedAt);
    return jsonResponse({
      status: "AI_CONFIG_PENDING",
      ticker,
      horizon,
      tier,
      answer: `Dữ liệu StockRadar cho ${ticker} đã có phần đạt chuẩn, nhưng lớp diễn giải AI trên máy chủ chưa được kích hoạt. Tôi không tự thay thế bằng dữ liệu bên ngoài.`,
      quota_consumed: false,
    }, 200, origin);
  }

  const { data: quotaRaw, error: quotaError } = await serviceClient.rpc("consume_stockradar_api_quota", {
    p_user_id: user.id,
    p_bucket: "stock_ai",
  });
  const quota = (quotaRaw || {}) as JsonObject;
  if (quotaError || !quotaRaw) {
    await audit(serviceClient, user.id, ticker, horizon, "SERVICE_UNAVAILABLE", "AI_QUOTA_RPC_FAILED", 503, startedAt);
    return jsonResponse({ status: "SERVICE_UNAVAILABLE", reason: "AI_QUOTA_RPC_FAILED" }, 503, origin);
  }
  const remainingNumber = Number(quota.remaining ?? Number.NaN);
  const remaining = Number.isFinite(remainingNumber) ? remainingNumber : null;
  const limit = Number(quota.limit ?? Number.NaN);
  const retryAfter = Number(quota.retry_after ?? 0);
  const rateHeaders: Record<string, string> = {};
  if (Number.isFinite(limit)) rateHeaders["X-RateLimit-Limit"] = String(limit);
  if (remaining !== null) rateHeaders["X-RateLimit-Remaining"] = String(remaining);
  if (quota.allowed !== true) {
    if (retryAfter > 0) rateHeaders["Retry-After"] = String(retryAfter);
    await audit(serviceClient, user.id, ticker, horizon, "RATE_LIMITED", "AI_RATE_LIMITED", 429, startedAt, remaining);
    return jsonResponse({
      status: "RATE_LIMITED",
      reason: "AI_RATE_LIMITED",
      answer: "Bạn đã dùng hết lượt StockRadar AI trong cửa sổ hiện tại. Hãy thử lại sau khi hạn mức được làm mới.",
      retry_after: retryAfter,
    }, 429, origin, rateHeaders);
  }

  const reports = readyRows.map((row) => {
    const raw = row.data as JsonObject;
    const normalized = {
      status: raw.status,
      ticker: raw.ticker,
      horizon: raw.horizon,
      snapshot_id: raw.snapshot_id,
      generated_at: raw.generated_at,
      expires_at: raw.expires_at,
      payload: raw.payload,
    };
    return tier === "FREE" ? redactForFree(normalized) : normalized;
  });

  const context = {
    ACCESS_TIER: tier,
    REQUESTED_TICKER: ticker,
    REQUESTED_HORIZON: horizon,
    USER_QUESTION: message,
    RECENT_CONVERSATION: history,
    DATA_CONTEXT: reports,
  };

  const model = Deno.env.get("OPENAI_MODEL")?.trim() || "gpt-5-mini";
  let aiResponse: Response;
  try {
    aiResponse = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${openAIKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model,
        instructions: SYSTEM_PROMPT,
        input: JSON.stringify(context),
        max_output_tokens: 900,
        store: false,
      }),
    });
  } catch {
    await audit(serviceClient, user.id, ticker, horizon, "AI_UPSTREAM_ERROR", "OPENAI_NETWORK_ERROR", 502, startedAt, remaining);
    return jsonResponse({ status: "AI_UPSTREAM_ERROR", answer: "Lớp AI tạm thời không phản hồi. Dữ liệu StockRadar không bị thay thế bằng nguồn khác." }, 502, origin, rateHeaders);
  }

  let aiPayload: unknown = null;
  try { aiPayload = await aiResponse.json(); } catch { aiPayload = null; }
  if (!aiResponse.ok) {
    console.error("stock-ai upstream status", aiResponse.status);
    await audit(serviceClient, user.id, ticker, horizon, "AI_UPSTREAM_ERROR", `OPENAI_${aiResponse.status}`, 502, startedAt, remaining);
    return jsonResponse({ status: "AI_UPSTREAM_ERROR", answer: "Lớp AI tạm thời chưa thể diễn giải báo cáo. StockRadar không tự tạo nhận định thay thế." }, 502, origin, rateHeaders);
  }

  const answer = extractOpenAIText(aiPayload);
  if (!answer) {
    await audit(serviceClient, user.id, ticker, horizon, "AI_UPSTREAM_ERROR", "EMPTY_AI_RESPONSE", 502, startedAt, remaining);
    return jsonResponse({ status: "AI_UPSTREAM_ERROR", answer: "Lớp AI không trả về nội dung hợp lệ. Hãy mở báo cáo StockRadar của mã để xem dữ liệu gốc." }, 502, origin, rateHeaders);
  }

  const selectedReport = readyRows.find((row) => row.horizon === horizon)?.data || readyRows[0]?.data || {};
  const selected = selectedReport as JsonObject;
  await audit(serviceClient, user.id, ticker, horizon, "AI_READY", "GROUNDED_REPORT", 200, startedAt, remaining);
  return jsonResponse({
    status: "READY",
    ticker,
    horizon,
    tier,
    answer,
    source: {
      snapshot_id: selected.snapshot_id || null,
      generated_at: selected.generated_at || null,
      expires_at: selected.expires_at || null,
      ready_horizons: readyRows.map((row) => row.horizon),
    },
    quota: {
      remaining,
      limit: Number.isFinite(limit) ? limit : null,
      window_seconds: Number(quota.window_seconds || 0) || null,
    },
  }, 200, origin, rateHeaders);
});
