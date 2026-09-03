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

Deno.serve(async (req: Request) => {
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

  const url = new URL(req.url);
  const ticker = (url.searchParams.get("ticker") || "").trim().toUpperCase();
  const horizon = (url.searchParams.get("horizon") || "SHORT_TERM").trim().toUpperCase();
  if (!/^[A-Z]{3}$/.test(ticker)) {
    return jsonResponse({ status: "INVALID_REQUEST", reason: "INVALID_TICKER" }, 400, origin);
  }
  if (!HORIZONS.has(horizon)) {
    return jsonResponse({ status: "INVALID_REQUEST", reason: "INVALID_HORIZON" }, 400, origin);
  }

  const serviceClient = createClient(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  const { data: profileData, error: profileError } = await serviceClient
    .from("profiles")
    .select("account_tier,account_status")
    .eq("id", user.id)
    .maybeSingle();
  if (profileError || !profileData || String(profileData.account_status || "").toUpperCase() !== "ACTIVE") {
    return jsonResponse({ status: "FORBIDDEN", reason: "ACCOUNT_INACTIVE" }, 403, origin);
  }
  const accountTier = String(profileData.account_tier || "").toUpperCase();
  if (!PREMIUM_TIERS.has(accountTier)) {
    return jsonResponse({ status: "PREMIUM_REQUIRED", reason: "PREMIUM_REQUIRED" }, 403, origin);
  }

  const { data: quotaData, error: quotaError } = await serviceClient.rpc("consume_stockradar_api_quota", {
    p_user_id: user.id,
    p_bucket: "stock_report",
  });
  if (quotaError || !quotaData) {
    return jsonResponse({ status: "SERVICE_UNAVAILABLE" }, 503, origin);
  }

  const quota = quotaData as Record<string, unknown>;
  const limit = String(quota.limit ?? "");
  const remaining = String(quota.remaining ?? "");
  const retryAfter = Number(quota.retry_after ?? 0);
  const rateHeaders: Record<string, string> = {};
  if (limit) rateHeaders["X-RateLimit-Limit"] = limit;
  if (remaining) rateHeaders["X-RateLimit-Remaining"] = remaining;

  if (quota.allowed !== true) {
    if (retryAfter > 0) rateHeaders["Retry-After"] = String(retryAfter);
    const reason = String(quota.reason || "RATE_LIMITED");
    return jsonResponse(
      { status: reason === "RATE_LIMITED" ? "RATE_LIMITED" : "FORBIDDEN", reason },
      reason === "RATE_LIMITED" ? 429 : 403,
      origin,
      rateHeaders,
    );
  }

  const { data: reportData, error: reportError } = await serviceClient.rpc("fetch_stockradar_cached_report", {
    p_ticker: ticker,
    p_horizon: horizon,
  });
  if (reportError || !reportData) {
    return jsonResponse({ status: "SERVICE_UNAVAILABLE" }, 503, origin, rateHeaders);
  }

  const report = reportData as Record<string, unknown>;
  const reportStatus = String(report.status || "");
  if (reportStatus === "READY") {
    return jsonResponse(report, 200, origin, rateHeaders);
  }
  if (reportStatus === "NOT_FOUND") {
    return jsonResponse(report, 404, origin, rateHeaders);
  }
  if (reportStatus === "INVALID_REQUEST") {
    return jsonResponse(report, 400, origin, rateHeaders);
  }
  return jsonResponse(report, 503, origin, rateHeaders);
});