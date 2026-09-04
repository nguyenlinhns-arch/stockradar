import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const RESEND_ENDPOINT = "https://api.resend.com/emails";
const encoder = new TextEncoder();

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

function money(value: unknown) {
  return `${new Intl.NumberFormat("vi-VN").format(Number(value || 0))}đ`;
}

function dateTime(value: unknown) {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat("vi-VN", {
      timeZone: "Asia/Ho_Chi_Minh",
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit", hour12: false,
    }).format(new Date(String(value)));
  } catch (_) {
    return "—";
  }
}

async function sha256Hex(value: string) {
  const digest = await crypto.subtle.digest("SHA-256", encoder.encode(value));
  return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, "0")).join("");
}

function randomToken() {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replaceAll("=", "");
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
  if (!response.ok) throw new Error(`${name}:${response.status}:${text.slice(0, 400)}`);
  return text ? JSON.parse(text) : null;
}

async function sendResend(payload: Record<string, unknown>) {
  const key = String(Deno.env.get("RESEND_API_KEY") || "").trim();
  const from = String(Deno.env.get("STOCKRADAR_EMAIL_FROM") || "").trim();
  const replyTo = String(Deno.env.get("STOCKRADAR_EMAIL_REPLY_TO") || "").trim();
  if (!key || !from) throw new Error("EMAIL_PROVIDER_NOT_CONFIGURED");
  let lastError = "SEND_FAILED";
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    try {
      const response = await fetch(RESEND_ENDPOINT, {
        method: "POST",
        headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
        body: JSON.stringify({ from, ...(replyTo ? { reply_to: replyTo } : {}), ...payload }),
      });
      const text = await response.text();
      if (!response.ok) throw new Error(`RESEND_${response.status}:${text.slice(0, 300)}`);
      const data = text ? JSON.parse(text) : {};
      if (!data?.id) throw new Error("RESEND_MISSING_ID");
      return String(data.id);
    } catch (error) {
      lastError = String(error);
      if (attempt < 3) await new Promise(resolve => setTimeout(resolve, attempt * 500));
    }
  }
  throw new Error(lastError);
}

function baseHtml(title: string, body: string) {
  return `<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)}</title></head><body style="margin:0;background:#f3f6f9;font-family:Arial,sans-serif;color:#0f172a"><div style="max-width:680px;margin:0 auto;padding:28px 14px"><div style="background:#0b1f33;color:#fff;padding:18px 22px;border-radius:16px 16px 0 0"><strong style="font-size:20px">STOCKRADAR</strong><div style="font-size:12px;opacity:.8;margin-top:4px">Xác nhận thanh toán Premium</div></div><div style="background:#fff;border:1px solid #dbe4ee;border-top:0;border-radius:0 0 16px 16px;padding:24px">${body}</div></div></body></html>`;
}

function responseHtml(title: string, body: string, status = 200) {
  return new Response(baseHtml(title, body), {
    status,
    headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" },
  });
}

function approvalEmail(data: Record<string, unknown>, approveUrl: string, rejectUrl: string) {
  return `<!doctype html><html lang="vi"><body style="margin:0;background:#f3f6f9;font-family:Arial,sans-serif;color:#0f172a"><table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:24px 12px"><table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:680px;background:#fff;border:1px solid #dbe4ee;border-radius:16px;overflow:hidden"><tr><td style="padding:20px 24px;background:#0b1f33;color:#fff"><strong style="font-size:19px">STOCKRADAR</strong><div style="font-size:12px;opacity:.8;margin-top:4px">Yêu cầu xác nhận thanh toán Premium</div></td></tr><tr><td style="padding:24px"><h1 style="font-size:24px;margin:0 0 16px">Khách báo đã chuyển khoản</h1><p style="font-size:14px;line-height:1.6;color:#475569">Chỉ xác nhận sau khi anh đã kiểm tra tiền thực nhận trong tài khoản ngân hàng. Việc mở email hoặc mở liên kết không tự kích hoạt Premium.</p><table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:14px;margin:18px 0"><tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">Khách hàng</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">${esc(data.customer_email)}</td></tr><tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">Số tiền</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">${esc(money(data.amount_vnd))}</td></tr><tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">Nội dung CK</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">${esc(data.payment_reference)}</td></tr><tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">Gói</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">${esc(data.plan_code)} · ${esc(data.duration_days)} ngày</td></tr><tr><td style="padding:9px;color:#64748b">Hạn duyệt</td><td style="padding:9px;font-weight:700">${esc(dateTime(data.approval_expires_at))}</td></tr></table><p style="margin:24px 0 10px"><a href="${esc(approveUrl)}" style="display:inline-block;background:#0b6b3a;color:#fff;text-decoration:none;padding:13px 18px;border-radius:9px;font-weight:700">KIỂM TRA & XÁC NHẬN ĐÃ NHẬN TIỀN</a></p><p style="margin:10px 0"><a href="${esc(rejectUrl)}" style="display:inline-block;background:#fff;color:#991b1b;text-decoration:none;padding:11px 16px;border:1px solid #fecaca;border-radius:9px;font-weight:700">CHƯA XÁC MINH / TỪ CHỐI</a></p><p style="font-size:12px;color:#64748b;margin-top:22px">Hai nút trên chỉ mở trang xác nhận cuối. Premium chỉ được kích hoạt sau thao tác xác nhận cuối của anh.</p></td></tr></table></td></tr></table></body></html>`;
}

function customerEmail(result: Record<string, unknown>) {
  const approved = String(result.approval_status || "") === "APPROVED";
  const title = approved ? "StockRadar Premium đã được kích hoạt" : "StockRadar chưa xác minh được thanh toán";
  const message = approved
    ? `Thanh toán ${esc(result.payment_reference)} đã được xác nhận. Quyền Premium của bạn đã được kích hoạt${result.paid_until ? ` đến <strong>${esc(dateTime(result.paid_until))}</strong>` : ""}.`
    : `Yêu cầu thanh toán ${esc(result.payment_reference)} chưa được xác minh. Tài khoản của bạn chưa bị tính phí trên StockRadar và Premium chưa được kích hoạt.`;
  return { title, html: baseHtml(title, `<h1 style="font-size:24px;margin:0 0 14px">${esc(title)}</h1><p style="font-size:14px;line-height:1.7;color:#475569">${message}</p><p style="font-size:13px;color:#64748b;margin-top:20px">Nếu cần đối chiếu, hãy trả lời email này và cung cấp đúng mã chuyển khoản <strong>${esc(result.payment_reference)}</strong>.</p>`) };
}

function decisionForm(data: Record<string, unknown>, token: string, decision: string) {
  const approve = decision === "APPROVE";
  const heading = approve ? "Xác nhận đã nhận tiền?" : "Xác nhận chưa duyệt thanh toán?";
  const button = approve ? "XÁC NHẬN ĐÃ NHẬN TIỀN · KÍCH HOẠT PREMIUM" : "XÁC NHẬN CHƯA XÁC MINH · KHÔNG KÍCH HOẠT";
  const buttonStyle = approve ? "background:#0b6b3a;color:#fff" : "background:#991b1b;color:#fff";
  const status = String(data.approval_status || "");
  if (status !== "PENDING") {
    return responseHtml("Trạng thái thanh toán", `<h1 style="font-size:24px;margin:0 0 14px">Yêu cầu đã được xử lý</h1><p>Trạng thái: <strong>${esc(status)}</strong></p><p>Mã chuyển khoản: <strong>${esc(data.payment_reference)}</strong></p>`);
  }
  return responseHtml(heading, `<h1 style="font-size:24px;margin:0 0 14px">${esc(heading)}</h1><p style="font-size:14px;line-height:1.65;color:#475569">Khách: <strong>${esc(data.customer_email)}</strong><br>Số tiền: <strong>${esc(money(data.amount_vnd))}</strong><br>Nội dung chuyển khoản: <strong>${esc(data.payment_reference)}</strong><br>Hạn duyệt: <strong>${esc(dateTime(data.approval_expires_at))}</strong></p><div style="padding:14px;background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;font-size:13px;line-height:1.6;margin:18px 0"><strong>Kiểm tra tài khoản ngân hàng trước.</strong> Trang này chưa thực hiện thay đổi nào cho đến khi anh bấm nút xác nhận bên dưới.</div><form method="post"><input type="hidden" name="action" value="decision"><input type="hidden" name="token" value="${esc(token)}"><input type="hidden" name="decision" value="${esc(decision)}"><button type="submit" style="border:0;border-radius:9px;padding:13px 18px;font-weight:700;cursor:pointer;${buttonStyle}">${esc(button)}</button></form>`);
}

Deno.serve(async (req: Request) => {
  const supabase = String(Deno.env.get("SUPABASE_URL") || "").trim();
  const admin = adminCredential();
  if (!supabase || !admin.key) return responseHtml("StockRadar", "<p>Backend chưa sẵn sàng.</p>", 503);

  const url = new URL(req.url);

  if (req.method === "GET") {
    const token = String(url.searchParams.get("token") || "").trim();
    const decision = String(url.searchParams.get("decision") || "").trim().toUpperCase();
    if (!token || !["APPROVE", "REJECT"].includes(decision)) return responseHtml("Liên kết không hợp lệ", "<p>Liên kết xác nhận không hợp lệ.</p>", 400);
    try {
      const tokenHash = await sha256Hex(token);
      const data = await rpc(supabase, admin, "inspect_stockradar_checkout_approval_v1", { p_token_hash: tokenHash });
      return decisionForm(data || {}, token, decision);
    } catch (_) {
      return responseHtml("Liên kết không hợp lệ", "<p>Liên kết đã hết hạn, không tồn tại hoặc không còn hiệu lực.</p>", 410);
    }
  }

  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  const contentType = String(req.headers.get("content-type") || "").toLowerCase();
  if (contentType.includes("application/x-www-form-urlencoded") || contentType.includes("multipart/form-data")) {
    try {
      const form = await req.formData();
      if (String(form.get("action") || "") !== "decision") return responseHtml("Yêu cầu không hợp lệ", "<p>Yêu cầu không hợp lệ.</p>", 400);
      const token = String(form.get("token") || "").trim();
      const decision = String(form.get("decision") || "").trim().toUpperCase();
      if (!token || !["APPROVE", "REJECT"].includes(decision)) return responseHtml("Yêu cầu không hợp lệ", "<p>Yêu cầu không hợp lệ.</p>", 400);
      const tokenHash = await sha256Hex(token);
      const result = await rpc(supabase, admin, "resolve_stockradar_checkout_approval_v1", { p_token_hash: tokenHash, p_decision: decision });
      const approved = String(result?.approval_status || "") === "APPROVED";
      let customerMail = "";
      if (result?.customer_email) {
        try {
          const mail = customerEmail(result || {});
          await sendResend({ to: [String(result.customer_email)], subject: `[StockRadar] ${mail.title}`, html: mail.html });
          customerMail = " Email xác nhận đã được gửi cho khách.";
        } catch (_) {
          customerMail = " Premium đã được xử lý; email khách có thể gửi chậm.";
        }
      }
      return responseHtml(approved ? "Đã kích hoạt Premium" : "Đã từ chối xác nhận", `<h1 style="font-size:24px;margin:0 0 14px">${approved ? "Đã kích hoạt Premium" : "Đã ghi nhận chưa xác minh"}</h1><p style="font-size:14px;line-height:1.65;color:#475569">Mã chuyển khoản: <strong>${esc(result?.payment_reference)}</strong><br>Khách: <strong>${esc(result?.customer_email)}</strong><br>Trạng thái: <strong>${esc(result?.approval_status)}</strong>${result?.paid_until ? `<br>Premium đến: <strong>${esc(dateTime(result.paid_until))}</strong>` : ""}</p><p style="font-size:13px;color:#64748b">${esc(customerMail)}</p>`);
    } catch (error) {
      const raw = String(error);
      const expired = raw.includes("APPROVAL_TOKEN_EXPIRED") || raw.includes("APPROVAL_TOKEN_INVALID");
      return responseHtml(expired ? "Liên kết hết hạn" : "Không thể xử lý", `<p>${expired ? "Liên kết xác nhận đã hết hạn hoặc không hợp lệ." : "Không thể xử lý yêu cầu xác nhận. Premium chưa được thay đổi."}</p>`, expired ? 410 : 500);
    }
  }

  try {
    const body = await req.json();
    if (String(body?.action || "") !== "notify") return new Response(JSON.stringify({ ok: false, reason: "INVALID_ACTION" }), { status: 400, headers: { "content-type": "application/json" } });
    const hookToken = String(req.headers.get("x-stockradar-checkout-hook") || "").trim();
    if (!hookToken) return new Response(JSON.stringify({ ok: false, reason: "UNAUTHORIZED" }), { status: 401, headers: { "content-type": "application/json" } });
    const hookHash = await sha256Hex(hookToken);
    const validHook = await rpc(supabase, admin, "verify_stockradar_checkout_hook_v1", { p_token_hash: hookHash });
    if (validHook !== true) return new Response(JSON.stringify({ ok: false, reason: "UNAUTHORIZED" }), { status: 401, headers: { "content-type": "application/json" } });
    const checkoutId = String(body?.checkout_id || "").trim();
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(checkoutId)) {
      return new Response(JSON.stringify({ ok: false, reason: "INVALID_CHECKOUT_ID" }), { status: 400, headers: { "content-type": "application/json" } });
    }
    const rawToken = randomToken();
    const tokenHash = await sha256Hex(rawToken);
    const data = await rpc(supabase, admin, "prepare_stockradar_checkout_approval_v1", { p_checkout_id: checkoutId, p_token_hash: tokenHash, p_ttl_minutes: 1440 });
    if (!data?.should_send) return new Response(JSON.stringify({ ok: true, idempotent: true, status: data?.approval_status || data?.status }), { status: 200, headers: { "content-type": "application/json" } });
    const approvalBase = `${url.origin}${url.pathname}`;
    const approveUrl = `${approvalBase}?token=${encodeURIComponent(rawToken)}&decision=APPROVE`;
    const rejectUrl = `${approvalBase}?token=${encodeURIComponent(rawToken)}&decision=REJECT`;
    try {
      const messageId = await sendResend({
        to: [String(data.approver_email)],
        subject: `[StockRadar] Xác nhận thanh toán ${String(data.payment_reference || "")}`,
        html: approvalEmail(data, approveUrl, rejectUrl),
      });
      await rpc(supabase, admin, "mark_stockradar_checkout_approval_delivery_v1", {
        p_checkout_id: checkoutId, p_token_hash: tokenHash, p_sent: true, p_message_id: messageId, p_error: null,
      });
      return new Response(JSON.stringify({ ok: true, sent: true }), { status: 202, headers: { "content-type": "application/json" } });
    } catch (error) {
      await rpc(supabase, admin, "mark_stockradar_checkout_approval_delivery_v1", {
        p_checkout_id: checkoutId, p_token_hash: tokenHash, p_sent: false, p_message_id: null, p_error: String(error),
      });
      return new Response(JSON.stringify({ ok: false, reason: "EMAIL_SEND_FAILED" }), { status: 503, headers: { "content-type": "application/json" } });
    }
  } catch (error) {
    return new Response(JSON.stringify({ ok: false, reason: "REQUEST_FAILED" }), { status: 500, headers: { "content-type": "application/json" } });
  }
});
