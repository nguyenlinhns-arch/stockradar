import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const RESEND_ENDPOINT = "https://api.resend.com/emails";
const EMAIL_KINDS = new Set(["DAILY_BRIEF", "EVENT_ALERT", "POST_SESSION_DIGEST", "WEEKLY_REPORT"]);

function escapeHtml(value: unknown) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function safeUrl(base: string, path: string) {
  const root = base.replace(/\/$/, "");
  return `${root}/${path.replace(/^\//, "")}`;
}

function formatValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.map(v => String(v)).join(" · ");
  return String(value);
}

function shell(subject: string, preheader: string, body: string, unsubscribeUrl: string, allUrl: string) {
  return `<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
  <body style="margin:0;background:#f3f6f9;font-family:Arial,sans-serif;color:#0f172a">
  <div style="display:none;max-height:0;overflow:hidden">${escapeHtml(preheader)}</div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f3f6f9"><tr><td align="center" style="padding:24px 12px">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:680px;background:#fff;border:1px solid #dbe4ee;border-radius:16px;overflow:hidden">
  <tr><td style="padding:20px 24px;background:#0b1f33;color:#fff"><strong style="font-size:19px">STOCKRADAR</strong><div style="font-size:12px;opacity:.8;margin-top:4px">Quyết định trước · dữ liệu và dấu thời gian đi kèm</div></td></tr>
  <tr><td style="padding:24px">${body}</td></tr>
  <tr><td style="padding:18px 24px;background:#f8fafc;border-top:1px solid #e2e8f0;font-size:12px;line-height:1.6;color:#64748b">
  Email này không phải lệnh giao dịch tự động và không cam kết lợi nhuận.<br>
  <a href="${escapeHtml(unsubscribeUrl)}" style="color:#334155">Ngừng loại email này</a> · <a href="${escapeHtml(allUrl)}" style="color:#334155">Ngừng toàn bộ email nội dung</a>
  </td></tr></table></td></tr></table></body></html>`;
}

function actionBody(payload: Record<string, unknown>, publicBase: string) {
  const card = (payload.decision_card && typeof payload.decision_card === "object") ? payload.decision_card as Record<string, unknown> : payload;
  const ticker = escapeHtml(card.ticker || payload.ticker || "");
  const previousState = escapeHtml(card.previous_state || payload.previous_state || "");
  const currentState = escapeHtml(card.current_state || payload.current_state || "");
  const reasons = Array.isArray(payload.reasons) ? payload.reasons.slice(0, 4) : [];
  const reportUrl = safeUrl(publicBase, `co-phieu/?ticker=${encodeURIComponent(String(card.ticker || payload.ticker || ""))}`);
  return `<div style="font-size:12px;font-weight:700;color:#64748b">ACTION ALERT</div>
  <h1 style="font-size:28px;line-height:1.15;margin:8px 0 18px">${ticker} · ${previousState} → ${currentState}</h1>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:14px">
    <tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">Đánh giá lúc</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">${escapeHtml(formatValue(card.evaluated_at))}</td></tr>
    <tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">Nếu chưa có</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">${escapeHtml(formatValue(card.new_position_decision))}</td></tr>
    <tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">Nếu đang nắm giữ</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">${escapeHtml(formatValue(card.holding_decision))}</td></tr>
    <tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">Giá tham chiếu</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">${escapeHtml(formatValue(card.reference_price))}</td></tr>
    <tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">Vùng mua</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">${escapeHtml(formatValue(card.buy_zone))}</td></tr>
    <tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">Stop / vô hiệu</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">${escapeHtml(formatValue(card.stop || card.invalidation))}</td></tr>
    <tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">Target</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">${escapeHtml(formatValue(card.target))}</td></tr>
    <tr><td style="padding:9px;color:#64748b">Kiểm tra tiếp</td><td style="padding:9px;font-weight:700">${escapeHtml(formatValue(card.next_review))}</td></tr>
  </table>
  ${reasons.length ? `<h2 style="font-size:17px;margin:22px 0 8px">Vì sao trạng thái đổi?</h2><ul style="padding-left:20px;line-height:1.6">${reasons.map(r => `<li>${escapeHtml(r)}</li>`).join("")}</ul>` : ""}
  <p style="padding:12px 14px;background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;font-size:13px;line-height:1.55"><strong>Điều kiện vô hiệu:</strong> ${escapeHtml(formatValue(card.invalidation))}</p>
  ${payload.no_chase_notice ? `<p style="font-size:13px;line-height:1.55"><strong>${escapeHtml(payload.no_chase_notice)}</strong></p>` : ""}
  <p style="font-size:13px;line-height:1.55;color:#475569">${escapeHtml(payload.late_open_notice || "Nếu mở email muộn, hãy kiểm tra trạng thái mới nhất trước khi hành động.")}</p>
  <p style="margin:22px 0 0"><a href="${escapeHtml(reportUrl)}" style="display:inline-block;background:#0b1f33;color:#fff;text-decoration:none;padding:12px 18px;border-radius:9px;font-weight:700">XEM TRẠNG THÁI MỚI NHẤT</a></p>`;
}

function dailyBody(payload: Record<string, unknown>, publicBase: string) {
  const changes = Array.isArray(payload.watchlist_changes) ? payload.watchlist_changes as Record<string, unknown>[] : [];
  const stableCount = Number(payload.stable_watchlist_count || 0);
  const rows = changes.map(item => {
    const previous = item.previous_state ? `${escapeHtml(item.previous_state)} → ` : "";
    return `<tr><td style="padding:10px;border-bottom:1px solid #e2e8f0;font-weight:700">${escapeHtml(item.ticker)}</td><td style="padding:10px;border-bottom:1px solid #e2e8f0">${previous}<strong>${escapeHtml(item.current_state)}</strong></td><td style="padding:10px;border-bottom:1px solid #e2e8f0">${escapeHtml(item.note || (item.owns_stock ? "Đang nắm giữ" : "Đang theo dõi"))}</td></tr>`;
  }).join("");
  return `<div style="font-size:12px;font-weight:700;color:#64748b">PREMIUM DAILY · 09:00</div>
  <h1 style="font-size:26px;line-height:1.2;margin:8px 0 8px">${escapeHtml(payload.headline || (changes.length ? `${changes.length} mã cần chú ý` : "Watchlist ổn định · chưa cần hành động"))}</h1>
  <p style="margin:0 0 18px;color:#475569">Watchlist của bạn trước, bối cảnh thị trường sau.</p>
  ${changes.length ? `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:14px"><tr style="background:#f8fafc"><th align="left" style="padding:10px">Mã</th><th align="left" style="padding:10px">Thay đổi</th><th align="left" style="padding:10px">Bối cảnh của bạn</th></tr>${rows}</table>` : `<div style="padding:14px;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:10px"><strong>Không có thay đổi hành động mới.</strong><div style="font-size:13px;margin-top:4px">${stableCount} mã ổn định vẫn được hệ thống theo dõi.</div></div>`}
  <h2 style="font-size:17px;margin:24px 0 8px">Bối cảnh thị trường</h2><p style="font-size:14px;line-height:1.6">${escapeHtml(formatValue(payload.market_context))}</p>
  <p style="margin:22px 0 0"><a href="${escapeHtml(safeUrl(publicBase,"tai-khoan/"))}" style="display:inline-block;background:#0b1f33;color:#fff;text-decoration:none;padding:12px 18px;border-radius:9px;font-weight:700">MỞ MY STOCKRADAR</a></p>`;
}

function digestBody(payload: Record<string, unknown>, publicBase: string, kind: string) {
  const title = kind === "WEEKLY_REPORT" ? "Tổng kết tuần" : "Tóm tắt cuối phiên";
  const summary = escapeHtml(payload.summary || "Không có thay đổi đáng chú ý được ghi nhận.");
  return `<div style="font-size:12px;font-weight:700;color:#64748b">${escapeHtml(title.toUpperCase())}</div><h1 style="font-size:26px;margin:8px 0 16px">${escapeHtml(title)}</h1><p style="font-size:14px;line-height:1.7">${summary}</p><p><a href="${escapeHtml(safeUrl(publicBase,"tai-khoan/"))}" style="display:inline-block;background:#0b1f33;color:#fff;text-decoration:none;padding:12px 18px;border-radius:9px;font-weight:700">MỞ MY STOCKRADAR</a></p>`;
}

async function rpc(base: string, key: string, name: string, body: Record<string, unknown>) {
  const response = await fetch(`${base}/rest/v1/rpc/${name}`, {
    method: "POST",
    headers: { apikey: key, authorization: `Bearer ${key}`, "content-type": "application/json", accept: "application/json" },
    body: JSON.stringify(body),
  });
  const text = await response.text();
  if (!response.ok) throw new Error(`${name}:${response.status}:${text.slice(0, 300)}`);
  return text ? JSON.parse(text) : null;
}

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
  const serviceRole = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  const resendKey = Deno.env.get("RESEND_API_KEY") || "";
  const emailFrom = Deno.env.get("STOCKRADAR_EMAIL_FROM") || "";
  const replyTo = Deno.env.get("STOCKRADAR_EMAIL_REPLY_TO") || "";
  const publicBase = Deno.env.get("STOCKRADAR_PUBLIC_BASE_URL") || "https://stockradar.vn";
  const authorization = req.headers.get("authorization") || "";

  if (!supabaseUrl || !serviceRole || authorization !== `Bearer ${serviceRole}`) {
    return new Response(JSON.stringify({ ok: false, reason: "UNAUTHORIZED" }), { status: 401, headers: { "content-type": "application/json" } });
  }
  if (!resendKey || !emailFrom) {
    return new Response(JSON.stringify({ ok: false, reason: "PROVIDER_NOT_CONFIGURED" }), { status: 503, headers: { "content-type": "application/json" } });
  }

  let requested = 20;
  try {
    const body = await req.json();
    requested = Math.min(50, Math.max(1, Number(body?.limit || 20)));
  } catch (_) {}

  let claimed: Record<string, unknown>[] = [];
  try {
    claimed = await rpc(supabaseUrl, serviceRole, "claim_stockradar_email_outbox_v1", { p_limit: requested }) || [];
  } catch (error) {
    console.error("email-worker claim failed", String(error));
    return new Response(JSON.stringify({ ok: false, reason: "CLAIM_FAILED" }), { status: 503, headers: { "content-type": "application/json" } });
  }

  let sent = 0;
  let failed = 0;
  for (const item of claimed) {
    const outboxId = String(item.outbox_id || "");
    const userId = String(item.user_id || "");
    const emailKind = String(item.email_kind || "").toUpperCase();
    const recipient = String(item.recipient_email || "");
    const idempotencyKey = String(item.idempotency_key || "");
    const payload = (item.payload && typeof item.payload === "object") ? item.payload as Record<string, unknown> : {};

    if (!outboxId || !userId || !recipient || !EMAIL_KINDS.has(emailKind)) {
      failed++;
      try { await rpc(supabaseUrl, serviceRole, "finish_stockradar_email_outbox_v1", { p_outbox_id: outboxId, p_result: "SUPPRESSED", p_error: "INVALID_CLAIM" }); } catch (_) {}
      continue;
    }

    try {
      const kindToken = await rpc(supabaseUrl, serviceRole, "issue_stockradar_unsubscribe_token_v1", { p_user_id: userId, p_scope: emailKind, p_ttl_days: 90 });
      const allToken = await rpc(supabaseUrl, serviceRole, "issue_stockradar_unsubscribe_token_v1", { p_user_id: userId, p_scope: "ALL", p_ttl_days: 90 });
      const unsubUrl = safeUrl(publicBase, `functions/v1/email-unsubscribe?token=${encodeURIComponent(String(kindToken))}`);
      const allUrl = safeUrl(publicBase, `functions/v1/email-unsubscribe?token=${encodeURIComponent(String(allToken))}`);
      const subject = String(payload.subject || (emailKind === "EVENT_ALERT" ? "[StockRadar] Cảnh báo hành động" : "[StockRadar] Báo cáo"));
      const preheader = String(payload.preheader || "StockRadar · thông tin theo watchlist và trạng thái đã xác nhận.");
      const body = emailKind === "EVENT_ALERT" ? actionBody(payload, publicBase) : emailKind === "DAILY_BRIEF" ? dailyBody(payload, publicBase) : digestBody(payload, publicBase, emailKind);
      const html = shell(subject, preheader, body, unsubUrl, allUrl);

      const send = await fetch(RESEND_ENDPOINT, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${resendKey}`,
          "Content-Type": "application/json",
          "Idempotency-Key": idempotencyKey,
        },
        body: JSON.stringify({
          from: emailFrom,
          to: [recipient],
          subject,
          html,
          ...(replyTo ? { reply_to: replyTo } : {}),
          headers: {
            "List-Unsubscribe": `<${allUrl}>`,
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
            "X-StockRadar-Outbox-ID": outboxId,
          },
          tags: [{ name: "email_kind", value: emailKind.toLowerCase().replaceAll("_", "-") }],
        }),
      });

      const resultText = await send.text();
      if (!send.ok) throw new Error(`RESEND_${send.status}:${resultText.slice(0, 300)}`);
      const result = JSON.parse(resultText);
      if (!result?.id) throw new Error("RESEND_MISSING_MESSAGE_ID");
      await rpc(supabaseUrl, serviceRole, "finish_stockradar_email_outbox_v1", { p_outbox_id: outboxId, p_result: "SENT", p_provider_message_id: result.id, p_error: null });
      sent++;
    } catch (error) {
      failed++;
      console.error("email-worker send failed", outboxId, String(error).slice(0, 300));
      try { await rpc(supabaseUrl, serviceRole, "finish_stockradar_email_outbox_v1", { p_outbox_id: outboxId, p_result: "FAILED", p_provider_message_id: null, p_error: String(error).slice(0, 900) }); } catch (_) {}
    }
  }

  return new Response(JSON.stringify({ ok: true, claimed: claimed.length, sent, failed }), { status: 200, headers: { "content-type": "application/json", "cache-control": "no-store" } });
});
