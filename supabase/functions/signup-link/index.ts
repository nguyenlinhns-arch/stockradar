import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const ALLOWED_ORIGINS = new Set(["https://stockradar.vn", "https://www.stockradar.vn"]);

function adminKey() {
  try {
    const keys = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") || "{}");
    const current = String(keys?.default || "").trim();
    if (current.startsWith("sb_secret_")) return current;
  } catch (_) {}
  return String(Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "").trim();
}

function cors(origin: string) {
  return {
    "access-control-allow-origin": ALLOWED_ORIGINS.has(origin) ? origin : "https://stockradar.vn",
    "access-control-allow-headers": "authorization, x-client-info, apikey, content-type",
    "access-control-allow-methods": "POST, OPTIONS",
    "vary": "Origin",
  };
}

function json(origin: string, body: Record<string, unknown>, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...cors(origin), "content-type": "application/json; charset=utf-8", "cache-control": "no-store" },
  });
}

function validEmail(value: string) {
  return value.length <= 160 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

Deno.serve(async (req: Request) => {
  const origin = String(req.headers.get("origin") || "").trim();
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(origin) });
  if (req.method !== "POST") return json(origin, { ok: false, reason: "METHOD_NOT_ALLOWED" }, 405);
  if (origin && !ALLOWED_ORIGINS.has(origin)) return json(origin, { ok: false, reason: "ORIGIN_NOT_ALLOWED" }, 403);

  const supabaseUrl = String(Deno.env.get("SUPABASE_URL") || "").trim();
  const secret = adminKey();
  if (!supabaseUrl || !secret) return json(origin, { ok: false, reason: "AUTH_BACKEND_NOT_READY" }, 503);

  try {
    const body = await req.json();
    const email = String(body?.email || "").trim().toLowerCase();
    const password = String(body?.password || "");
    const plan = String(body?.plan || "free").trim().toLowerCase() === "premium" ? "premium" : "free";
    const termsAccepted = body?.terms_accepted === true;
    const privacyAccepted = body?.privacy_accepted === true;

    if (!validEmail(email) || password.length < 8 || password.length > 128 || !termsAccepted || !privacyAccepted) {
      return json(origin, { ok: false, reason: "INVALID_SIGNUP" }, 400);
    }

    const metadata = {
      signup_source: "stockradar_web_direct_v1",
      selected_plan_interest: plan,
      terms_accepted: true,
      terms_version: "2026-09-03",
      privacy_accepted: true,
      privacy_version: "2026-09-04",
      product_email_consent: plan === "premium" && (body?.product_email_daily_brief === true || body?.product_email_event_alerts === true),
      product_email_consent_version: "2026-09-04",
      product_email_daily_brief: plan === "premium" && body?.product_email_daily_brief === true,
      product_email_event_alerts: plan === "premium" && body?.product_email_event_alerts === true,
    };

    const admin = createClient(supabaseUrl, secret, {
      auth: { autoRefreshToken: false, persistSession: false, detectSessionInUrl: false },
    });

    const { data, error } = await admin.auth.admin.createUser({
      email,
      password,
      email_confirm: true,
      user_metadata: metadata,
    });

    if (error || !data?.user?.id) {
      // Keep response generic to reduce account enumeration.
      return json(origin, { ok: false, reason: "SIGNUP_UNAVAILABLE" }, 409);
    }

    return json(origin, { ok: true, created: true, plan }, 201);
  } catch (_) {
    return json(origin, { ok: false, reason: "REQUEST_FAILED" }, 500);
  }
});
