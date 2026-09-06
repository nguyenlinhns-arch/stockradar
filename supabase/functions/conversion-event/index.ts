import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { UUID, FUNNEL_EVENTS, cleanTouch, fingerprints, knownBot } from "../_shared/funnel.ts";

const ALLOWED_ORIGINS = new Set([
  "https://stockradar.vn",
  "https://www.stockradar.vn",
  "https://nguyenlinhns-arch.github.io",
  "http://localhost:8000",
  "http://localhost:8765",
  "http://127.0.0.1:8765",
]);

const NON_PRODUCTION_ORIGINS = new Set([
  "http://localhost:8000",
  "http://localhost:8765",
  "http://127.0.0.1:8765",
]);

const ALLOWED_EVENTS = new Set([
  "home_view",
  "ticker_lookup_submit",
  "stock_report_view",
  "premium_preview_view",
  "premium_sample_view",
  "pricing_view",
  "performance_proof_view",
  "signup_view",
  "signup_premium_view",
  "signup_submit",
  "checkout_view",
  "conversion_click",
]);

function responseHeaders(origin: string) {
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Headers": "content-type, x-client-info",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Cache-Control": "no-store",
    "Content-Type": "application/json; charset=utf-8",
    "Vary": "Origin",
  };
}

function json(origin: string, status: number, body: Record<string, unknown>) {
  return new Response(JSON.stringify(body), { status, headers: responseHeaders(origin) });
}

async function sha256Hex(value: string) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
}

function cleanText(value: unknown, maxLength: number) {
  return typeof value === "string"
    ? value.trim().replace(/[\r\n\t]/g, "").slice(0, maxLength)
    : "";
}

Deno.serve(async (req: Request) => {
  const origin = req.headers.get("origin") || "";
  if (!ALLOWED_ORIGINS.has(origin)) {
    return json("null", 403, { accepted: false });
  }

  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: responseHeaders(origin) });
  }
  if (req.method !== "POST") {
    return json(origin, 405, { accepted: false });
  }

  // Local development and Chromium visual QA may exercise the funnel, but those
  // requests must never pollute production conversion metrics.
  if (NON_PRODUCTION_ORIGINS.has(origin) || knownBot(req)) {
    return json(origin, 202, { accepted: true, recorded: false });
  }

  const contentType = req.headers.get("content-type") || "";
  const contentLength = Number(req.headers.get("content-length") || "0");
  if (!contentType.toLowerCase().includes("application/json") || contentLength > 4096) {
    return json(origin, 400, { accepted: false });
  }

  let payload: Record<string, unknown>;
  try {
    const raw = await req.text();
    if (new TextEncoder().encode(raw).length > 4096) return json(origin, 400, { accepted: false });
    payload = JSON.parse(raw);
  } catch {
    return json(origin, 400, { accepted: false });
  }

  if (payload.schema_version === 'STOCKRADAR_FUNNEL_V2') {
    const name = String(payload.event_name || '');
    if (!FUNNEL_EVENTS.has(name) || name === 'signup_completed' || !UUID.test(String(payload.event_id || ''))
      || !UUID.test(String(payload.session_id || '')) || !/^\/[a-zA-Z0-9_/-]{0,150}$/.test(String(payload.source_path || '')))
      return json(origin, 400, {accepted: false});
    const serverKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') || '', url = Deno.env.get('SUPABASE_URL') || '';
    if (!serverKey || !url) return json(origin, 503, {accepted: false});
    const ids = await fingerprints(req, payload.session_id, serverKey);
    const ticker = String(payload.ticker || '');
    const safe = {
      event_name: name, event_id: payload.event_id, source_path: payload.source_path,
      tier: ['GUEST','FREE','PREMIUM'].includes(String(payload.tier)) ? payload.tier : null,
      ticker: /^[A-Z0-9]{3}$/.test(ticker) && /[A-Z]/.test(ticker) && !['BTC','ETH','USD'].includes(ticker) ? ticker : null,
      horizon: ['SHORT_TERM','MEDIUM_TERM','LONG_TERM','ACCUMULATION'].includes(String(payload.horizon)) ? payload.horizon : 'SHORT_TERM',
      plan_interest: payload.plan_interest === 'PREMIUM' ? 'PREMIUM' : 'FREE',
      model_status: ['MODEL_READY','MODEL_NOT_CALLED','MODEL_CREDIT_BLOCKED','MODEL_TIMEOUT','MODEL_ERROR'].includes(String(payload.model_status)) ? payload.model_status : null,
      first_touch: cleanTouch(payload.first_touch), last_touch: cleanTouch(payload.last_touch),
    };
    try {
      const result = await fetch(`${url}/rest/v1/rpc/capture_conversion_event_v2`, {method: 'POST',signal: AbortSignal.timeout(8000),
        headers: {apikey: serverKey, authorization: `Bearer ${serverKey}`, 'content-type': 'application/json'},
        body: JSON.stringify({p_payload: safe, p_session_hash: ids.session, p_ip_hash: ids.ip})});
      if (!result.ok) {
        const limited = (await result.text()).includes('rate limit exceeded');
        return json(origin, limited ? 429 : 503, {accepted: false});
      }
      return json(origin, 202, {accepted: true, recorded: (await result.json()) === true});
    } catch (_) { return json(origin, 503, {accepted: false}); }
  }
  const eventName = cleanText(payload.event_name, 64).toLowerCase();
  const actionName = cleanText(payload.action_name, 80).toLowerCase();
  const sourcePath = cleanText(payload.source_path, 256);
  const sessionId = cleanText(payload.session_id, 80);
  const ticker = cleanText(payload.ticker, 3).toUpperCase();
  const planInterest = cleanText(payload.plan_interest, 16).toUpperCase();
  const utmSource = cleanText(payload.utm_source, 120);
  const utmCampaign = cleanText(payload.utm_campaign, 160);
  const referrerHost = cleanText(payload.referrer_host, 253)
    .toLowerCase()
    .replace(/[^a-z0-9.:-]/g, "");

  if (!ALLOWED_EVENTS.has(eventName)) return json(origin, 400, { accepted: false });
  if (!sourcePath.startsWith("/") || sourcePath.includes("?") || sourcePath.includes("#")) {
    return json(origin, 400, { accepted: false });
  }
  if (!/^[A-Za-z0-9_-]{16,80}$/.test(sessionId)) return json(origin, 400, { accepted: false });
  if (actionName && !/^[a-z0-9_:-]{1,80}$/.test(actionName)) return json(origin, 400, { accepted: false });
  if (ticker && !/^[A-Z0-9]{3}$/.test(ticker)) return json(origin, 400, { accepted: false });
  if (planInterest && !new Set(["FREE", "PREMIUM"]).has(planInterest)) return json(origin, 400, { accepted: false });

  const forwarded = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  const clientIp = req.headers.get("cf-connecting-ip") || forwarded || "unknown";
  const userAgent = req.headers.get("user-agent") || "unknown";
  const day = new Date().toISOString().slice(0, 10);
  const ipHash = await sha256Hex(`${day}|${clientIp}|${userAgent}|stockradar-conversion-ip-v1`);
  const sessionHash = await sha256Hex(`${day}|${sessionId}|stockradar-conversion-session-v1`);

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!supabaseUrl || !serviceRoleKey) {
    console.error("conversion-event: missing server environment");
    return json(origin, 503, { accepted: false });
  }

  const rpc = await fetch(`${supabaseUrl}/rest/v1/rpc/capture_conversion_event_v1`, {
    method: "POST",
    headers: {
      apikey: serviceRoleKey,
      authorization: `Bearer ${serviceRoleKey}`,
      "content-type": "application/json",
      accept: "application/json",
    },
    body: JSON.stringify({
      p_event_name: eventName,
      p_action_name: actionName || null,
      p_source_path: sourcePath,
      p_ticker: ticker || null,
      p_plan_interest: planInterest || null,
      p_session_hash: sessionHash,
      p_ip_hash: ipHash,
      p_utm_source: utmSource || null,
      p_utm_campaign: utmCampaign || null,
      p_referrer_host: referrerHost || null,
    }),
  });

  if (!rpc.ok) {
    const detail = (await rpc.text()).toLowerCase();
    if (detail.includes("rate limit exceeded")) return json(origin, 429, { accepted: false });
    console.error("conversion-event RPC failed", rpc.status);
    return json(origin, 503, { accepted: false });
  }

  return json(origin, 202, { accepted: true, recorded: true });
});
