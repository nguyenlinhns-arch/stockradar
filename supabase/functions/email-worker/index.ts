import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { actionBody, dailyBody, emailPricePlanError, emailSubject } from "../_shared/email-copy.ts";

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

async function authorizedServiceRequest(req: Request, supabase: string, admin: AdminCredential, diagnostic = false) {
  if (admin.legacy && req.headers.get("authorization") === `Bearer ${admin.key}`) return true;
  const schedulerToken = String(req.headers.get("x-stockradar-scheduler") || "").trim().toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(schedulerToken)) return false;
  try {
    const valid = await rpc(supabase, admin, diagnostic ? "verify_stockradar_email_diagnostic_token_v1" : "verify_stockradar_email_scheduler_token_v1", {
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

function digestBody(payload: Record<string, unknown>, website: string, kind: string) {
  const title = kind === "WEEKLY_REPORT" ? "Tổng kết tuần" : "Tóm tắt cuối phiên";
  return `<div style="font-size:12px;font-weight:700;color:#64748b">${esc(title.toUpperCase())}</div><h1 style="font-size:26px;margin:8px 0 16px">${esc(title)}</h1><p style="font-size:14px;line-height:1.7">${esc(payload.summary || "Không có thay đổi đáng chú ý được ghi nhận.")}</p><p><a href="${esc(joinUrl(website,"tai-khoan/"))}" style="display:inline-block;background:#0b1f33;color:#fff;text-decoration:none;padding:12px 18px;border-radius:9px;font-weight:700">MỞ MY STOCKRADAR</a></p>`;
}

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return new Response("Method Not Allowed",{status:405});
  const supabase = Deno.env.get("SUPABASE_URL") || "";
  const admin = adminCredential();
  let resend = Deno.env.get("RESEND_API_KEY") || "";
  let from = Deno.env.get("STOCKRADAR_EMAIL_FROM") || "";
  const replyTo = Deno.env.get("STOCKRADAR_EMAIL_REPLY_TO") || "";
  const website = Deno.env.get("STOCKRADAR_PUBLIC_BASE_URL") || "https://stockradar.vn";
  const functionsBase = Deno.env.get("STOCKRADAR_FUNCTIONS_BASE_URL") || `${supabase.replace(/\/$/,"")}/functions/v1`;

  let input: Record<string, unknown> = {}; try { input=await req.json(); } catch (_) {}
  const diagnostic = input?.mode === "health";
  if (!supabase || !admin.key || !(await authorizedServiceRequest(req, supabase, admin, diagnostic))) {
    return new Response(JSON.stringify({ok:false,reason:"UNAUTHORIZED"}),{status:401,headers:{"content-type":"application/json"}});
  }
  if (!resend || !from) {
    try {
      const provider=await rpc(supabase,admin,"get_stockradar_email_provider_config_v1",{});
      resend ||= String(provider?.api_key || "");
      from ||= String(provider?.from_address || "");
    } catch (_) {}
  }
  if (diagnostic) return new Response(JSON.stringify({ok:true,provider_configured:!!resend,sender_configured:!!from}),{headers:{"content-type":"application/json","cache-control":"no-store"}});
  if (!resend || !from) return new Response(JSON.stringify({ok:false,reason:"PROVIDER_NOT_CONFIGURED"}),{status:503,headers:{"content-type":"application/json"}});

  const limit=Math.min(50,Math.max(1,Number(input?.limit)||20));
  let claimed: Record<string, unknown>[]=[];
  try { claimed=await rpc(supabase,admin,"claim_stockradar_email_outbox_v1",{p_limit:limit}) || []; }
  catch(e){ console.error("email-worker claim failed",String(e)); return new Response(JSON.stringify({ok:false,reason:"CLAIM_FAILED"}),{status:503,headers:{"content-type":"application/json"}}); }

  let sent=0,failed=0,suppressed=0;
  for (const item of claimed) {
    const outboxId=String(item.outbox_id||""), userId=String(item.user_id||""), kind=String(item.email_kind||"").toUpperCase(), recipient=String(item.recipient_email||""), idem=String(item.idempotency_key||"");
    let payload=item.payload && typeof item.payload === "object" ? item.payload as Record<string, unknown> : {};
    if(!outboxId||!userId||!recipient||!KINDS.has(kind)){ failed++; try{await rpc(supabase,admin,"finish_stockradar_email_outbox_v1",{p_outbox_id:outboxId,p_result:"SUPPRESSED",p_error:"INVALID_CLAIM"});}catch(_){} continue; }
    try {
      const preflight=await rpc(supabase,admin,"preflight_stockradar_email_outbox_v1",{p_outbox_id:outboxId});
      if(!preflight?.allowed){ suppressed++; continue; }
      if (preflight.payload && typeof preflight.payload === 'object') payload = preflight.payload;
      const pricePlanError = emailPricePlanError(payload,kind);
      if (pricePlanError) {
        await rpc(supabase,admin,"finish_stockradar_email_outbox_v1",{p_outbox_id:outboxId,p_result:"SUPPRESSED",p_error:pricePlanError});
        suppressed++; continue;
      }
      const kindToken=await rpc(supabase,admin,"issue_stockradar_unsubscribe_token_v1",{p_user_id:userId,p_scope:kind,p_ttl_days:90});
      const allToken=await rpc(supabase,admin,"issue_stockradar_unsubscribe_token_v1",{p_user_id:userId,p_scope:"ALL",p_ttl_days:90});
      const unsub=joinUrl(functionsBase,`email-unsubscribe?token=${encodeURIComponent(String(kindToken))}`);
      const allUnsub=joinUrl(functionsBase,`email-unsubscribe?token=${encodeURIComponent(String(allToken))}`);
      const subject=kind==='EVENT_ALERT'||kind==='DAILY_BRIEF'?emailSubject(payload,kind):String(payload.subject||'[StockRadar] Báo cáo');
      const preheader=String(payload.preheader || "StockRadar · cổ phiếu và thời gian xác nhận.");
      const body=kind==="EVENT_ALERT"?actionBody(payload,website):kind==="DAILY_BRIEF"?dailyBody(payload,website):digestBody(payload,website,kind);
      const res=await fetch(RESEND_ENDPOINT,{method:"POST",headers:{Authorization:`Bearer ${resend}`,"Content-Type":"application/json","Idempotency-Key":idem},body:JSON.stringify({from,to:[recipient],subject,html:shell(preheader,body,unsub,allUnsub),...(replyTo?{reply_to:replyTo}:{}),headers:{"List-Unsubscribe":`<${allUnsub}>`,"List-Unsubscribe-Post":"List-Unsubscribe=One-Click","X-StockRadar-Outbox-ID":outboxId},tags:[{name:"email_kind",value:kind.toLowerCase().replaceAll("_","-")} ]})});
      const text=await res.text(); if(!res.ok) throw new Error(`RESEND_${res.status}:${text.slice(0,240)}`); const result=JSON.parse(text); if(!result?.id) throw new Error("RESEND_MISSING_MESSAGE_ID");
      await rpc(supabase,admin,"finish_stockradar_email_outbox_v1",{p_outbox_id:outboxId,p_result:"SENT",p_provider_message_id:result.id,p_error:null}); sent++;
    } catch(e) { failed++; console.error("email-worker send failed",outboxId,String(e).slice(0,240)); try{await rpc(supabase,admin,"finish_stockradar_email_outbox_v1",{p_outbox_id:outboxId,p_result:"FAILED",p_provider_message_id:null,p_error:String(e).slice(0,900)});}catch(_){} }
  }
  return new Response(JSON.stringify({ok:true,claimed:claimed.length,sent,failed,suppressed}),{status:200,headers:{"content-type":"application/json","cache-control":"no-store"}});
});
