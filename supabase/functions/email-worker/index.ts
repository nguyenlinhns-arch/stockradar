import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const RESEND_ENDPOINT = "https://api.resend.com/emails";
const KINDS = new Set(["DAILY_BRIEF","EVENT_ALERT","POST_SESSION_DIGEST","WEEKLY_REPORT"]);
const esc = (v: unknown) => String(v ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;").replaceAll("'","&#039;");
const fmt = (v: unknown) => v === null || v === undefined || v === "" ? "—" : Array.isArray(v) ? v.join(" · ") : String(v);
const joinUrl = (base: string, path: string) => `${base.replace(/\/$/,"")}/${path.replace(/^\//,"")}`;

type AdminCredential = { key: string; legacy: boolean };

function adminCredential(): AdminCredential {
  try {
    const keys = JSON.parse(Deno.env.get("SUPABASE_SECRET_KEYS") || "{}");
    const current = String(keys?.default || "").trim();
    if (current.startsWith("sb_secret_")) return { key: current, legacy: false };
  } catch (_) {}
  return { key: String(Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "").trim(), legacy: true };
}

async function sha256Hex(value: string) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2,"0")).join("");
}

async function rpc(base: string, admin: AdminCredential, name: string, body: Record<string, unknown>) {
  const headers: Record<string,string> = {
    apikey: admin.key,
    "content-type":"application/json",
    accept:"application/json",
  };
  if (admin.legacy) headers.authorization = `Bearer ${admin.key}`;
  const res = await fetch(`${base}/rest/v1/rpc/${name}`, { method:"POST", headers, body:JSON.stringify(body) });
  const text = await res.text();
  if (!res.ok) throw new Error(`${name}:${res.status}:${text.slice(0,240)}`);
  return text ? JSON.parse(text) : null;
}

async function authorizedServiceRequest(req: Request, supabase: string, admin: AdminCredential) {
  if (admin.legacy && req.headers.get("authorization") === `Bearer ${admin.key}`) return true;
  const schedulerToken = String(req.headers.get("x-stockradar-scheduler") || "").trim().toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(schedulerToken)) return false;
  try {
    const valid = await rpc(supabase, admin, "verify_stockradar_email_scheduler_token_v1", {
      p_token_hash: await sha256Hex(schedulerToken),
    });
    return valid === true;
  } catch (_) {
    return false;
  }
}

function shell(preheader: string, body: string, unsub: string, allUnsub: string) {
  return `<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0;background:#f3f6f9;font-family:Arial,sans-serif;color:#0f172a"><div style="display:none;max-height:0;overflow:hidden">${esc(preheader)}</div><table role="presentation" width="100%" cellspacing="0" cellpadding="0"><tr><td align="center" style="padding:24px 12px"><table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:680px;background:#fff;border:1px solid #dbe4ee;border-radius:16px;overflow:hidden"><tr><td style="padding:20px 24px;background:#0b1f33;color:#fff"><strong style="font-size:19px">STOCKRADAR</strong><div style="font-size:12px;opacity:.8;margin-top:4px">Quyết định trước · dữ liệu và dấu thời gian đi kèm</div></td></tr><tr><td style="padding:24px">${body}</td></tr><tr><td style="padding:18px 24px;background:#f8fafc;border-top:1px solid #e2e8f0;font-size:12px;line-height:1.6;color:#64748b">Email này không phải lệnh giao dịch tự động và không cam kết lợi nhuận.<br><a href="${esc(unsub)}" style="color:#334155">Ngừng loại email này</a> · <a href="${esc(allUnsub)}" style="color:#334155">Ngừng toàn bộ email nội dung</a></td></tr></table></td></tr></table></body></html>`;
}

function actionBody(payload: Record<string, unknown>, website: string) {
  const c = payload.decision_card && typeof payload.decision_card === "object" ? payload.decision_card as Record<string, unknown> : payload;
  const ticker = String(c.ticker || payload.ticker || "");
  const reasons = Array.isArray(payload.reasons) ? payload.reasons.slice(0,4) : [];
  const report = joinUrl(website, `co-phieu/?ticker=${encodeURIComponent(ticker)}`);
  const row = (label: string, value: unknown) => `<tr><td style="padding:9px;border-bottom:1px solid #e2e8f0;color:#64748b">${esc(label)}</td><td style="padding:9px;border-bottom:1px solid #e2e8f0;font-weight:700">${esc(fmt(value))}</td></tr>`;
  return `<div style="font-size:12px;font-weight:700;color:#64748b">ACTION ALERT</div><h1 style="font-size:28px;line-height:1.15;margin:8px 0 18px">${esc(ticker)} · ${esc(c.previous_state || payload.previous_state)} → ${esc(c.current_state || payload.current_state)}</h1><table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:14px">${row("Đánh giá lúc",c.evaluated_at)}${row("Nếu chưa có",c.new_position_decision)}${row("Nếu đang nắm giữ",c.holding_decision)}${row("Giá tham chiếu",c.reference_price)}${row("Vùng mua",c.buy_zone)}${row("Stop / vô hiệu",c.stop || c.invalidation)}${row("Target",c.target)}${row("Risk/Reward",c.risk_reward)}${row("Kiểm tra tiếp",c.next_review)}</table>${reasons.length ? `<h2 style="font-size:17px;margin:22px 0 8px">Vì sao trạng thái đổi?</h2><ul style="padding-left:20px;line-height:1.6">${reasons.map(r=>`<li>${esc(r)}</li>`).join("")}</ul>`:""}<p style="padding:12px 14px;background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;font-size:13px"><strong>Điều kiện vô hiệu:</strong> ${esc(fmt(c.invalidation))}</p>${payload.no_chase_notice ? `<p style="font-size:13px"><strong>${esc(payload.no_chase_notice)}</strong></p>`:""}<p style="font-size:13px;color:#475569">${esc(payload.late_open_notice || "Nếu mở email muộn, hãy xem trạng thái mới nhất trước khi hành động.")}</p><p style="margin-top:22px"><a href="${esc(report)}" style="display:inline-block;background:#0b1f33;color:#fff;text-decoration:none;padding:12px 18px;border-radius:9px;font-weight:700">XEM TRẠNG THÁI MỚI NHẤT</a></p>`;
}

function dailyBody(payload: Record<string, unknown>, website: string) {
  const changes = Array.isArray(payload.watchlist_changes) ? payload.watchlist_changes as Record<string, unknown>[] : [];
  const rows = changes.map(i=>`<tr><td style="padding:10px;border-bottom:1px solid #e2e8f0;font-weight:700">${esc(i.ticker)}</td><td style="padding:10px;border-bottom:1px solid #e2e8f0">${i.previous_state ? `${esc(i.previous_state)} → `:""}<strong>${esc(i.current_state)}</strong></td><td style="padding:10px;border-bottom:1px solid #e2e8f0">${esc(i.note || (i.owns_stock ? "Đang nắm giữ":"Đang theo dõi"))}</td></tr>`).join("");
  const main = changes.length ? `<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;font-size:14px"><tr style="background:#f8fafc"><th align="left" style="padding:10px">Mã</th><th align="left" style="padding:10px">Thay đổi</th><th align="left" style="padding:10px">Bối cảnh của bạn</th></tr>${rows}</table>` : `<div style="padding:14px;background:#ecfdf5;border:1px solid #a7f3d0;border-radius:10px"><strong>Không có thay đổi hành động mới.</strong><div style="font-size:13px;margin-top:4px">${Number(payload.stable_watchlist_count || 0)} mã ổn định vẫn được theo dõi.</div></div>`;
  return `<div style="font-size:12px;font-weight:700;color:#64748b">PREMIUM DAILY · 09:00</div><h1 style="font-size:26px;line-height:1.2;margin:8px 0">${esc(payload.headline || (changes.length ? `${changes.length} mã cần chú ý` : "Watchlist ổn định · chưa cần hành động"))}</h1><p style="color:#475569">Watchlist của bạn trước, bối cảnh thị trường sau.</p>${main}<h2 style="font-size:17px;margin:24px 0 8px">Bối cảnh thị trường</h2><p style="font-size:14px;line-height:1.6">${esc(fmt(payload.market_context))}</p><p style="margin-top:22px"><a href="${esc(joinUrl(website,"tai-khoan/"))}" style="display:inline-block;background:#0b1f33;color:#fff;text-decoration:none;padding:12px 18px;border-radius:9px;font-weight:700">MỞ MY STOCKRADAR</a></p>`;
}

function digestBody(payload: Record<string, unknown>, website: string, kind: string) {
  const title = kind === "WEEKLY_REPORT" ? "Tổng kết tuần" : "Tóm tắt cuối phiên";
  return `<div style="font-size:12px;font-weight:700;color:#64748b">${esc(title.toUpperCase())}</div><h1 style="font-size:26px;margin:8px 0 16px">${esc(title)}</h1><p style="font-size:14px;line-height:1.7">${esc(payload.summary || "Không có thay đổi đáng chú ý được ghi nhận.")}</p><p><a href="${esc(joinUrl(website,"tai-khoan/"))}" style="display:inline-block;background:#0b1f33;color:#fff;text-decoration:none;padding:12px 18px;border-radius:9px;font-weight:700">MỞ MY STOCKRADAR</a></p>`;
}

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return new Response("Method Not Allowed",{status:405});
  const supabase = Deno.env.get("SUPABASE_URL") || "";
  const admin = adminCredential();
  const resend = Deno.env.get("RESEND_API_KEY") || "";
  const from = Deno.env.get("STOCKRADAR_EMAIL_FROM") || "";
  const replyTo = Deno.env.get("STOCKRADAR_EMAIL_REPLY_TO") || "";
  const website = Deno.env.get("STOCKRADAR_PUBLIC_BASE_URL") || "https://stockradar.vn";
  const functionsBase = Deno.env.get("STOCKRADAR_FUNCTIONS_BASE_URL") || `${supabase.replace(/\/$/,"")}/functions/v1`;

  if (!supabase || !admin.key || !(await authorizedServiceRequest(req, supabase, admin))) {
    return new Response(JSON.stringify({ok:false,reason:"UNAUTHORIZED"}),{status:401,headers:{"content-type":"application/json"}});
  }
  if (!resend || !from) return new Response(JSON.stringify({ok:false,reason:"PROVIDER_NOT_CONFIGURED"}),{status:503,headers:{"content-type":"application/json"}});

  let limit=20; try { const b=await req.json(); limit=Math.min(50,Math.max(1,Number(b?.limit||20))); } catch(_){}
  let claimed: Record<string, unknown>[]=[];
  try { claimed=await rpc(supabase,admin,"claim_stockradar_email_outbox_v1",{p_limit:limit}) || []; }
  catch(e){ console.error("email-worker claim failed",String(e)); return new Response(JSON.stringify({ok:false,reason:"CLAIM_FAILED"}),{status:503,headers:{"content-type":"application/json"}}); }

  let sent=0,failed=0,suppressed=0;
  for (const item of claimed) {
    const outboxId=String(item.outbox_id||""), userId=String(item.user_id||""), kind=String(item.email_kind||"").toUpperCase(), recipient=String(item.recipient_email||""), idem=String(item.idempotency_key||"");
    const payload=item.payload && typeof item.payload === "object" ? item.payload as Record<string, unknown> : {};
    if(!outboxId||!userId||!recipient||!KINDS.has(kind)){ failed++; try{await rpc(supabase,admin,"finish_stockradar_email_outbox_v1",{p_outbox_id:outboxId,p_result:"SUPPRESSED",p_error:"INVALID_CLAIM"});}catch(_){} continue; }
    try {
      const preflight=await rpc(supabase,admin,"preflight_stockradar_email_outbox_v1",{p_outbox_id:outboxId});
      if(!preflight?.allowed){ suppressed++; continue; }
      const kindToken=await rpc(supabase,admin,"issue_stockradar_unsubscribe_token_v1",{p_user_id:userId,p_scope:kind,p_ttl_days:90});
      const allToken=await rpc(supabase,admin,"issue_stockradar_unsubscribe_token_v1",{p_user_id:userId,p_scope:"ALL",p_ttl_days:90});
      const unsub=joinUrl(functionsBase,`email-unsubscribe?token=${encodeURIComponent(String(kindToken))}`);
      const allUnsub=joinUrl(functionsBase,`email-unsubscribe?token=${encodeURIComponent(String(allToken))}`);
      const subject=String(payload.subject || (kind==="EVENT_ALERT"?"[StockRadar] Cảnh báo hành động":"[StockRadar] Báo cáo"));
      const preheader=String(payload.preheader || "StockRadar · watchlist và trạng thái đã xác nhận.");
      const body=kind==="EVENT_ALERT"?actionBody(payload,website):kind==="DAILY_BRIEF"?dailyBody(payload,website):digestBody(payload,website,kind);
      const res=await fetch(RESEND_ENDPOINT,{method:"POST",headers:{Authorization:`Bearer ${resend}`,"Content-Type":"application/json","Idempotency-Key":idem},body:JSON.stringify({from,to:[recipient],subject,html:shell(preheader,body,unsub,allUnsub),...(replyTo?{reply_to:replyTo}:{}),headers:{"List-Unsubscribe":`<${allUnsub}>`,"List-Unsubscribe-Post":"List-Unsubscribe=One-Click","X-StockRadar-Outbox-ID":outboxId},tags:[{name:"email_kind",value:kind.toLowerCase().replaceAll("_","-")} ]})});
      const text=await res.text(); if(!res.ok) throw new Error(`RESEND_${res.status}:${text.slice(0,240)}`); const result=JSON.parse(text); if(!result?.id) throw new Error("RESEND_MISSING_MESSAGE_ID");
      await rpc(supabase,admin,"finish_stockradar_email_outbox_v1",{p_outbox_id:outboxId,p_result:"SENT",p_provider_message_id:result.id,p_error:null}); sent++;
    } catch(e) { failed++; console.error("email-worker send failed",outboxId,String(e).slice(0,240)); try{await rpc(supabase,admin,"finish_stockradar_email_outbox_v1",{p_outbox_id:outboxId,p_result:"FAILED",p_provider_message_id:null,p_error:String(e).slice(0,900)});}catch(_){} }
  }
  return new Response(JSON.stringify({ok:true,claimed:claimed.length,sent,failed,suppressed}),{status:200,headers:{"content-type":"application/json","cache-control":"no-store"}});
});
