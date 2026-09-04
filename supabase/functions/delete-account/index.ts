import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const ALLOWED_ORIGINS = new Set([
  "https://nguyenlinhns-arch.github.io",
  "https://stockradar.vn",
  "https://www.stockradar.vn",
]);
const SESSION_ID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function corsHeaders(origin: string | null): Record<string, string> {
  const headers: Record<string, string> = {
    "Vary": "Origin",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
  };
  if (origin && ALLOWED_ORIGINS.has(origin)) {
    headers["Access-Control-Allow-Origin"] = origin;
    headers["Access-Control-Allow-Headers"] = "authorization, x-client-info, apikey, content-type";
    headers["Access-Control-Allow-Methods"] = "POST, OPTIONS";
  }
  return headers;
}

function json(origin: string | null, status: number, body: Record<string, unknown>): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders(origin), "Content-Type": "application/json; charset=utf-8" },
  });
}

function parseKeySet(name: string): Record<string, string> {
  try {
    const raw = Deno.env.get(name);
    return raw ? JSON.parse(raw) : {};
  } catch (_) {
    return {};
  }
}

function verifiedJwtPayload(token: string): Record<string, unknown> {
  const payload = token.split(".")[1] || "";
  if (!payload) return {};
  try {
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
    return JSON.parse(atob(padded));
  } catch (_) {
    return {};
  }
}

Deno.serve(async (req: Request) => {
  const origin = req.headers.get("origin");
  if (origin && !ALLOWED_ORIGINS.has(origin)) {
    return json(null, 403, { error: "ORIGIN_NOT_ALLOWED" });
  }
  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders(origin) });
  }
  if (req.method !== "POST") {
    return json(origin, 405, { error: "METHOD_NOT_ALLOWED" });
  }

  const contentType = req.headers.get("content-type") || "";
  if (!contentType.toLowerCase().includes("application/json")) {
    return json(origin, 400, { error: "INVALID_REQUEST" });
  }

  let body: Record<string, unknown>;
  try {
    const rawBody = await req.text();
    if (rawBody.length > 4096) return json(origin, 413, { error: "REQUEST_TOO_LARGE" });
    body = JSON.parse(rawBody || "{}");
  } catch (_) {
    return json(origin, 400, { error: "INVALID_REQUEST" });
  }
  if (body.confirm !== "DELETE_ACCOUNT") {
    return json(origin, 400, { error: "CONFIRMATION_REQUIRED" });
  }

  const authHeader = req.headers.get("authorization") || "";
  const token = authHeader.toLowerCase().startsWith("bearer ") ? authHeader.slice(7).trim() : "";
  if (!token) return json(origin, 401, { error: "UNAUTHORIZED" });

  const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
  const publishableKeys = parseKeySet("SUPABASE_PUBLISHABLE_KEYS");
  const secretKeys = parseKeySet("SUPABASE_SECRET_KEYS");
  const publicKey = publishableKeys.default || Deno.env.get("SUPABASE_ANON_KEY") || "";
  const adminKey = secretKeys.default || Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  if (!supabaseUrl || !publicKey || !adminKey) {
    console.error("delete-account server configuration missing");
    return json(origin, 503, { error: "SERVICE_UNAVAILABLE" });
  }

  try {
    const userClient = createClient(supabaseUrl, publicKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
    const { data: userData, error: userError } = await userClient.auth.getUser(token);
    const user = userData?.user;
    if (userError || !user) return json(origin, 401, { error: "UNAUTHORIZED" });

    // The JWT payload is read only after getUser(token) has authenticated the token.
    // session_id is then checked against auth.sessions by a service-role-only RPC.
    const claims = verifiedJwtPayload(token);
    const sessionId = String(claims.session_id || "");
    if (!SESSION_ID_RE.test(sessionId)) {
      return json(origin, 403, { error: "RECENT_REAUTH_REQUIRED" });
    }

    const admin = createClient(supabaseUrl, adminKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    });
    const { data: recentSession, error: recentSessionError } = await admin.rpc(
      "verify_stockradar_recent_session",
      {
        p_user_id: user.id,
        p_session_id: sessionId,
        p_max_age_seconds: 300,
      },
    );
    if (recentSessionError || recentSession !== true) {
      return json(origin, 403, { error: "RECENT_REAUTH_REQUIRED" });
    }

    const { error: deleteError } = await admin.auth.admin.deleteUser(user.id);
    if (deleteError) {
      console.error("delete-account delete failed", deleteError.code || "UNKNOWN");
      return json(origin, 500, { error: "DELETE_FAILED" });
    }

    return json(origin, 200, { status: "deleted" });
  } catch (_) {
    console.error("delete-account unexpected failure");
    return json(origin, 500, { error: "UNEXPECTED_ERROR" });
  }
});
