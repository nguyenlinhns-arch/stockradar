import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const ALLOWED_ORIGINS = new Set([
  "https://stockradar.vn",
  "https://www.stockradar.vn",
  "https://nguyenlinhns-arch.github.io",
  "http://localhost:8000",
  "http://127.0.0.1:8000",
]);
const HORIZONS = new Set(["SHORT_TERM", "MEDIUM_TERM", "LONG_TERM", "ACCUMULATION"]);
const PREMIUM_TIERS = new Set(["TRIAL", "PAID"]);

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
    headers["Access-Control-Allow-Methods"] = "GET, OPTIONS";
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
  return value.length === 3 && /^[A-Z0-9]{3}$/.test(value) && /[A-Z]/.test(value);
}

async function auditedJson(
  client: ServiceClient,
  userId: string,
  startedAt: number,
  ticker: string,
  horizon: string,
  body: Record<string, unknown>,
  status: number,
  origin: string | null,
  extra: Record<string, string> = {},
  outcome?: string,
  reason?: string,
  rateLimitRemaining?: number | null,
): Promise<Response> {
  const latencyMs = Math.max(0, Math.round(performance.now() - startedAt));
  try {
    const { error } = await client.rpc("record_stockradar_api_request_event", {
      p_user_id: userId,
      p_ticker: ticker,
      p_horizon: horizon,
      p_outcome: outcome || String(body.status || "UNKNOWN"),
      p_reason: reason || String(body.reason || ""),
      p_http_status: status,
      p_latency_ms: latencyMs,
      p_rate_limit_remaining: Number.isFinite(rateLimitRemaining) ? rateLimitRemaining : null,
    });
    if (error) console.error("stock-api audit rpc failed", error.code || "UNKNOWN");
  } catch {
    console.error("stock-api audit rpc failed");
  }
  return jsonResponse(body, status, origin, extra);
}

Deno.serve(async (req: Request) => {
  const startedAt = performance.now();
  const origin = req.headers.get("origin");
  if (origin && !ALLOWED_ORIGINS.has(origin)) {
    return jsonResponse({ status: "FORBIDDEN_ORIGIN" }, 403, null);
  }
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders(origin) });
  }
  if (req.method !== "GET") {
    return jsonResponse({ status: "METHOD_NOT_ALLOWED" }, 405, origin, { "Allow": "GET, OPTIONS" });
  }

  const authorization = req.headers.get("authorization") || "";
  const token = authorization.toLowerCase().startsWith("bearer ") ? authorization.slice(7).trim() : "";
  if (!token) {
    return jsonResponse({ status: "UNAUTHORIZED" }, 401, origin);
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const anonKey = Deno.env.get("SUPABASE_ANON_KEY");
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!supabaseUrl || !anonKey || !serviceRoleKey) {
    return jsonResponse({ status: "SERVICE_UNAVAILABLE" }, 503, origin);
  }

  const authClient = createClient(supabaseUrl, anonKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data: userData, error: userError } = await authClient.auth.getUser(token);
  const user = userData?.user;
  if (userError || !user) {
    return jsonResponse({ status: "UNAUTHORIZED" }, 401, origin);
  }

  const serviceClient = createClient(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  const url = new URL(req.url);
  const ticker = (url.searchParams.get("ticker") || "").trim().toUpperCase();
  const horizon = (url.searchParams.get("horizon") || "SHORT_TERM").trim().toUpperCase();
  if (!validTicker(ticker)) {
    return await auditedJson(
      serviceClient, user.id, startedAt, ticker, horizon,
      { status: "INVALID_REQUEST", reason: "INVALID_TICKER" },
      400, origin, {}, "INVALID_REQUEST", "INVALID_TICKER",
    );
  }
  if (!HORIZONS.has(horizon)) {
    return await auditedJson(
      serviceClient, user.id, startedAt, ticker, horizon,
      { status: "INVALID_REQUEST", reason: "INVALID_HORIZON" },
      400, origin, {}, "INVALID_REQUEST", "INVALID_HORIZON",
    );
  }

  const { data: profileData, error: profileError } = await serviceClient
    .from("profiles")
    .select("account_tier,account_status")
    .eq("id", user.id)
    .maybeSingle();
  if (profileError || !profileData || String(profileData.account_status || "").toUpperCase() !== "ACTIVE") {
    return await auditedJson(
      serviceClient, user.id, startedAt, ticker, horizon,
      { status: "FORBIDDEN", reason: "ACCOUNT_INACTIVE" },
      403, origin, {}, "FORBIDDEN", "ACCOUNT_INACTIVE",
    );
  }
  const accountTier = String(profileData.account_tier || "").toUpperCase();
  if (!PREMIUM_TIERS.has(accountTier)) {
    return await auditedJson(
      serviceClient, user.id, startedAt, ticker, horizon,
      { status: "PREMIUM_REQUIRED", reason: "PREMIUM_REQUIRED" },
      403, origin, {}, "PREMIUM_REQUIRED", "PREMIUM_REQUIRED",
    );
  }

  const { data: quotaData, error: quotaError } = await serviceClient.rpc("consume_stockradar_api_quota", {
    p_user_id: user.id,
    p_bucket: "stock_report",
  });
  if (quotaError || !quotaData) {
    return await auditedJson(
      serviceClient, user.id, startedAt, ticker, horizon,
      { status: "SERVICE_UNAVAILABLE" },
      503, origin, {}, "SERVICE_UNAVAILABLE", "QUOTA_RPC_FAILED",
    );
  }

  const quota = quotaData as Record<string, unknown>;
  const limit = String(quota.limit ?? "");
  const remainingNumber = Number(quota.remaining ?? Number.NaN);
  const remaining = Number.isFinite(remainingNumber) ? String(remainingNumber) : "";
  const retryAfter = Number(quota.retry_after ?? 0);
  const rateHeaders: Record<string, string> = {};
  if (limit) rateHeaders["X-RateLimit-Limit"] = limit;
  if (remaining) rateHeaders["X-RateLimit-Remaining"] = remaining;

  if (quota.allowed !== true) {
    if (retryAfter > 0) rateHeaders["Retry-After"] = String(retryAfter);
    const reason = String(quota.reason || "RATE_LIMITED");
    const outcome = reason === "RATE_LIMITED" ? "RATE_LIMITED" : "FORBIDDEN";
    const httpStatus = reason === "RATE_LIMITED" ? 429 : 403;
    return await auditedJson(
      serviceClient, user.id, startedAt, ticker, horizon,
      { status: outcome, reason }, httpStatus, origin, rateHeaders,
      outcome, reason, Number.isFinite(remainingNumber) ? remainingNumber : null,
    );
  }

  const { data: reportData, error: reportError } = await serviceClient.rpc("fetch_stockradar_cached_report", {
    p_ticker: ticker,
    p_horizon: horizon,
  });
  if (reportError || !reportData) {
    return await auditedJson(
      serviceClient, user.id, startedAt, ticker, horizon,
      { status: "SERVICE_UNAVAILABLE" }, 503, origin, rateHeaders,
      "SERVICE_UNAVAILABLE", "REPORT_RPC_FAILED",
      Number.isFinite(remainingNumber) ? remainingNumber : null,
    );
  }

  const report = reportData as Record<string, unknown>;
  const reportStatus = String(report.status || "");
  const reportReason = String(report.reason || "");
  const auditRemaining = Number.isFinite(remainingNumber) ? remainingNumber : null;
  if (reportStatus === "READY") {
    return await auditedJson(serviceClient, user.id, startedAt, ticker, horizon, report, 200, origin, rateHeaders, "READY", reportReason, auditRemaining);
  }
  if (reportStatus === "NOT_FOUND") {
    return await auditedJson(serviceClient, user.id, startedAt, ticker, horizon, report, 404, origin, rateHeaders, "NOT_FOUND", reportReason, auditRemaining);
  }
  if (reportStatus === "INVALID_REQUEST") {
    return await auditedJson(serviceClient, user.id, startedAt, ticker, horizon, report, 400, origin, rateHeaders, "INVALID_REQUEST", reportReason, auditRemaining);
  }
  return await auditedJson(
    serviceClient, user.id, startedAt, ticker, horizon, report, 503, origin, rateHeaders,
    reportStatus || "BLOCKED_DATA_GATE", reportReason, auditRemaining,
  );
});
