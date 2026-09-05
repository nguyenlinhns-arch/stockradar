import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const RESEND_ENDPOINT = "https://api.resend.com/emails";

type AdminCredential = { key: string; legacy: boolean };

function adminCredential(): AdminCredential {
  try {
    const keys = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") || "{}");
    const current = String(keys?.default || "").trim();
    if (current.startsWith("sb_secret_")) return { key: current, legacy: false };
  } catch (_) {}
  return { key: String(Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "").trim(), legacy: true };
}

function esc(value: unknown) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function dateTime(value: unknown) {
  if (!value) return "—";
  const date = new Date(String(value));
  if (!Number.isFinite(date.getTime())) return "—";
  return new Intl.DateTimeFormat("vi-VN", {
    timeZone: "Asia/Ho_Chi_Minh",
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).format(date) + " (giờ VN)";
}

async function sha256Hex(value: string) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, "0")).join("");
}

async function rpc(base: string, admin: AdminCredential, name: string, body: Record<string, unknown>) {
  const headers: Record<string, string> = {
    apikey: admin.key,
    "content-type": "application/json",
    accept: "application/json",
  };
  if (admin.legacy) headers.authorization = `Bearer ${admin.key}`;
  const response = await fetch(`${base.replace(/\/$/, "")}/rest/v1/rpc/${name}`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`${name}:${response.status}:${text.slice(0, 300)}`);
  return text ? JSON.parse(text) : null;
}

function emailHtml(payload: Record<string, unknown>, website: string) {
  const verified = payload.email_confirmed === true ? "Đã xác minh email" : "Chưa xác minh email";
  return `<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0;background:#f3f6f9;font-family:Arial,sans-serif;color:#0f172a"><table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:24px 12px"><table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:680px;background:#fff;border:1px solid #dbe4ee;border-radius:16px;overflow:hidden"><tr><td style="padding:20px 24px;background:#0b1f33;color:#fff"><strong style="font-size:19px">STOCKRADAR</strong><div style="font-size:12px;opacity:.8;margin-top:4px">Thông báo quản trị · người dùng mới</div></td></tr><tr><td style="padding:24px"><div style="font-size:12px;font-weight:700;color:#64748b">ĐĂNG KÝ FREE MỚI</div><h1 style="font-size:24px;margin:8px 0 18px">Có người dùng mới đăng ký StockRadar</h1><table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:14px"><tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">Email</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">${esc(payload.new_user_email)}</td></tr><tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">Gói</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">Free</td></tr><tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">Thời gian đăng ký</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">${esc(dateTime(payload.registered_at))}</td></tr><tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">Trạng thái email</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">${esc(verified)}</td></tr><tr><td style="padding:9px;color:#64748b">User ID</td><td style="padding:9px;font-size:12px">${esc(payload.new_user_id)}</td></tr></table><p style="margin:22px 0 0"><a href="${esc(website)}" style="display:inline-block;background:#0b1f33;color:#fff;text-decoration:none;padding:12px 18px;border-radius:9px;font-weight:700">MỞ STOCKRADAR.VN</a></p><p style="font-size:12px;color:#64748b;margin-top:18px">Đây là email quản trị nội bộ. Email này không thay đổi quyền Free/Premium của người đăng ký.</p></td></tr></table></td></tr></table></body></html>`;
}

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  const supabase = String(Deno.env.get("SUPABASE_URL") || "").trim();
  const admin = adminCredential();
  const website = String(Deno.env.get("STOCKRADAR_PUBLIC_BASE_URL") || "https://stockradar.vn").trim();
  if (!supabase || !admin.key) {
    return new Response(JSON.stringify({ ok: false, reason: "BACKEND_NOT_READY" }), { status: 503, headers: { "content-type": "application/json" } });
  }

  const hookToken = String(req.headers.get("x-stockradar-checkout-hook") || "").trim();
  if (!hookToken) {
    return new Response(JSON.stringify({ ok: false, reason: "UNAUTHORIZED" }), { status: 401, headers: { "content-type": "application/json" } });
  }

  try {
    const valid = await rpc(supabase, admin, "verify_stockradar_checkout_hook_v1", { p_token_hash: await sha256Hex(hookToken) });
    if (valid !== true) {
      return new Response(JSON.stringify({ ok: false, reason: "UNAUTHORIZED" }), { status: 401, headers: { "content-type": "application/json" } });
    }
  } catch (_) {
    return new Response(JSON.stringify({ ok: false, reason: "UNAUTHORIZED" }), { status: 401, headers: { "content-type": "application/json" } });
  }

  let resend = String(Deno.env.get("RESEND_API_KEY") || "").trim();
  let from = String(Deno.env.get("STOCKRADAR_EMAIL_FROM") || "").trim();
  const replyTo = String(Deno.env.get("STOCKRADAR_EMAIL_REPLY_TO") || "").trim();
  if (!resend || !from) {
    try {
      const provider = await rpc(supabase, admin, "get_stockradar_email_provider_config_v1", {});
      resend ||= String(provider?.api_key || "").trim();
      from ||= String(provider?.from_address || "").trim();
    } catch (_) {}
  }
  if (!resend || !from) {
    return new Response(JSON.stringify({ ok: false, reason: "PROVIDER_NOT_CONFIGURED" }), { status: 503, headers: { "content-type": "application/json" } });
  }

  let input: Record<string, unknown> = {};
  try { input = await req.json(); } catch (_) {}
  const limit = Math.min(50, Math.max(1, Number(input.limit) || 20));

  let claimed: Record<string, unknown>[] = [];
  try {
    claimed = await rpc(supabase, admin, "claim_stockradar_admin_signup_outbox_v1", { p_limit: limit }) || [];
  } catch (error) {
    console.error("admin signup claim failed", String(error));
    return new Response(JSON.stringify({ ok: false, reason: "CLAIM_FAILED" }), { status: 503, headers: { "content-type": "application/json" } });
  }

  let sent = 0;
  let failed = 0;
  let suppressed = 0;

  for (const item of claimed) {
    const outboxId = String(item.outbox_id || "");
    const recipient = String(item.recipient_email || "").trim();
    const idem = String(item.idempotency_key || "").trim();
    const kind = String(item.email_kind || "").toUpperCase();
    let payload = item.payload && typeof item.payload === "object" ? item.payload as Record<string, unknown> : {};

    if (!outboxId || !recipient || !idem || kind !== "ADMIN_FREE_SIGNUP") {
      failed += 1;
      if (outboxId) {
        try { await rpc(supabase, admin, "finish_stockradar_email_outbox_v1", { p_outbox_id: outboxId, p_result: "SUPPRESSED", p_provider_message_id: null, p_error: "INVALID_ADMIN_SIGNUP_CLAIM" }); } catch (_) {}
      }
      continue;
    }

    try {
      const preflight = await rpc(supabase, admin, "preflight_stockradar_admin_signup_outbox_v1", { p_outbox_id: outboxId });
      if (!preflight?.allowed) {
        suppressed += 1;
        continue;
      }
      if (preflight.payload && typeof preflight.payload === "object") payload = preflight.payload;

      const response = await fetch(RESEND_ENDPOINT, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${resend}`,
          "Content-Type": "application/json",
          "Idempotency-Key": idem,
        },
        body: JSON.stringify({
          from,
          to: [recipient],
          subject: "StockRadar · Có người dùng Free mới đăng ký",
          html: emailHtml(payload, website),
          ...(replyTo ? { reply_to: replyTo } : {}),
          headers: { "X-StockRadar-Outbox-ID": outboxId },
          tags: [{ name: "email_kind", value: "admin-free-signup" }],
        }),
      });

      const text = await response.text();
      if (!response.ok) throw new Error(`RESEND_${response.status}:${text.slice(0, 300)}`);
      const result = text ? JSON.parse(text) : {};
      if (!result?.id) throw new Error("RESEND_MISSING_MESSAGE_ID");

      await rpc(supabase, admin, "finish_stockradar_email_outbox_v1", {
        p_outbox_id: outboxId,
        p_result: "SENT",
        p_provider_message_id: String(result.id),
        p_error: null,
      });
      sent += 1;
    } catch (error) {
      failed += 1;
      console.error("admin signup email failed", outboxId, String(error).slice(0, 300));
      try {
        await rpc(supabase, admin, "finish_stockradar_email_outbox_v1", {
          p_outbox_id: outboxId,
          p_result: "FAILED",
          p_provider_message_id: null,
          p_error: String(error).slice(0, 900),
        });
      } catch (_) {}
    }
  }

  return new Response(JSON.stringify({ ok: true, claimed: claimed.length, sent, failed, suppressed }), {
    status: 200,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
});
