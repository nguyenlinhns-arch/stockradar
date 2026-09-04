import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const RESEND_ENDPOINT = "https://api.resend.com/emails";
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

function esc(value: unknown) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function validEmail(value: string) {
  return value.length <= 160 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

async function sendResend(to: string, subject: string, html: string) {
  const key = String(Deno.env.get("RESEND_API_KEY") || "").trim();
  const from = String(Deno.env.get("STOCKRADAR_EMAIL_FROM") || "").trim();
  const replyTo = String(Deno.env.get("STOCKRADAR_EMAIL_REPLY_TO") || "").trim();
  if (!key || !from) throw new Error("EMAIL_PROVIDER_NOT_CONFIGURED");
  const response = await fetch(RESEND_ENDPOINT, {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from, to: [to], subject, html, ...(replyTo ? { reply_to: replyTo } : {}) }),
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`RESEND_${response.status}:${text.slice(0, 300)}`);
  return text ? JSON.parse(text) : {};
}

function emailHtml(plan: "free" | "premium", actionLink: string) {
  const premium = plan === "premium";
  const title = premium ? "Xác minh đăng ký StockRadar Premium" : "Xác minh tài khoản StockRadar Free";
  const next = premium
    ? "Sau khi xác minh, StockRadar sẽ đưa bạn thẳng tới bước thanh toán 199.000đ/30 ngày. Premium chỉ kích hoạt sau khi thanh toán được xác nhận."
    : "Sau khi xác minh, tài khoản Free sẽ được mở với 10 câu StockRadar AI mỗi ngày.";
  return `<!doctype html><html lang="vi"><body style="margin:0;background:#f5f7fb;font-family:Arial,sans-serif;color:#172033"><div style="max-width:620px;margin:0 auto;padding:30px 18px"><div style="background:#fff;border:1px solid #dde3ed;border-radius:16px;overflow:hidden"><div style="padding:24px 28px;background:#0d2b49;color:#fff"><div style="font-size:12px;font-weight:700;letter-spacing:.08em;color:#b9d1e3">STOCKRADAR.VN</div><h1 style="margin:8px 0 0;font-size:24px;line-height:1.3">${esc(title)}</h1></div><div style="padding:28px"><p style="margin:0 0 16px;font-size:14px;line-height:1.7;color:#596579">Không cần nhập mã OTP. Bấm nút dưới đây để xác minh đúng email bạn vừa đăng ký.</p><p style="margin:22px 0"><a href="${esc(actionLink)}" style="display:inline-block;background:#d62535;color:#fff;text-decoration:none;padding:14px 22px;border-radius:10px;font-weight:800">XÁC MINH EMAIL STOCKRADAR</a></p><p style="margin:0;font-size:13px;line-height:1.7;color:#596579">${esc(next)}</p><p style="margin:20px 0 0;font-size:12px;line-height:1.6;color:#7a8494">Nếu bạn không tạo tài khoản StockRadar, có thể bỏ qua email này. StockRadar không bao giờ yêu cầu OTP ngân hàng hoặc OTP tài khoản chứng khoán.</p></div></div></div></body></html>`;
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

    const redirectTo = `https://stockradar.vn/xac-minh-email/?plan=${plan}`;
    const metadata = {
      signup_source: "stockradar_web_link_v1",
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

    const { data, error } = await admin.auth.admin.generateLink({
      type: "signup",
      email,
      password,
      options: { redirectTo, data: metadata },
    });

    if (error || !data?.properties?.action_link) {
      // Keep the browser response deliberately generic to reduce email enumeration.
      return json(origin, { ok: false, reason: "SIGNUP_UNAVAILABLE" }, 409);
    }

    try {
      await sendResend(
        email,
        plan === "premium" ? "[StockRadar] Xác minh đăng ký Premium" : "[StockRadar] Xác minh tài khoản Free",
        emailHtml(plan as "free" | "premium", String(data.properties.action_link)),
      );
    } catch (_) {
      const userId = String(data?.user?.id || "").trim();
      if (userId) {
        try { await admin.auth.admin.deleteUser(userId); } catch (_) {}
      }
      return json(origin, { ok: false, reason: "EMAIL_SEND_FAILED" }, 503);
    }

    return json(origin, { ok: true, sent: true, plan }, 202);
  } catch (_) {
    return json(origin, { ok: false, reason: "REQUEST_FAILED" }, 500);
  }
});
