import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const ALLOWED_EVENTS = new Set([
  "email.sent","email.delivered","email.delivery_delayed","email.bounced","email.complained",
  "email.opened","email.clicked","email.failed","email.scheduled","email.suppressed",
]);

function b64ToBytes(value: string) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized + "=".repeat((4 - normalized.length % 4) % 4);
  const raw = atob(padded);
  return Uint8Array.from(raw, c => c.charCodeAt(0));
}

function bytesToB64(bytes: Uint8Array) {
  let raw = "";
  bytes.forEach(b => raw += String.fromCharCode(b));
  return btoa(raw);
}

function constantTimeEqual(a: string, b: string) {
  const aa = new TextEncoder().encode(a);
  const bb = new TextEncoder().encode(b);
  if (aa.length !== bb.length) return false;
  let diff = 0;
  for (let i = 0; i < aa.length; i++) diff |= aa[i] ^ bb[i];
  return diff === 0;
}

async function verifySvix(rawBody: string, headers: Headers, secret: string) {
  const id = headers.get("svix-id") || headers.get("webhook-id") || "";
  const timestamp = headers.get("svix-timestamp") || headers.get("webhook-timestamp") || "";
  const signatureHeader = headers.get("svix-signature") || headers.get("webhook-signature") || "";
  if (!id || !timestamp || !signatureHeader || !secret.startsWith("whsec_")) return false;

  const timestampNumber = Number(timestamp);
  if (!Number.isFinite(timestampNumber) || Math.abs(Math.floor(Date.now() / 1000) - timestampNumber) > 300) return false;

  const keyBytes = b64ToBytes(secret.slice("whsec_".length));
  const key = await crypto.subtle.importKey("raw", keyBytes, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const signed = `${id}.${timestamp}.${rawBody}`;
  const signature = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(signed)));
  const expected = bytesToB64(signature);

  return signatureHeader.split(" ").some(part => {
    const [version, candidate] = part.split(",", 2);
    return version === "v1" && Boolean(candidate) && constantTimeEqual(candidate, expected);
  });
}

async function sha256Hex(value: string) {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, "0")).join("");
}

async function recordEvent(supabaseUrl: string, serviceRole: string, body: Record<string, unknown>) {
  const response = await fetch(`${supabaseUrl}/rest/v1/rpc/record_stockradar_email_delivery_event_v1`, {
    method: "POST",
    headers: { apikey: serviceRole, authorization: `Bearer ${serviceRole}`, "content-type": "application/json", accept: "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`delivery-event rpc ${response.status}:${(await response.text()).slice(0, 300)}`);
  return await response.json();
}

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });

  const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
  const serviceRole = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  const webhookSecret = Deno.env.get("RESEND_WEBHOOK_SECRET") || "";
  if (!supabaseUrl || !serviceRole || !webhookSecret) {
    return new Response(JSON.stringify({ ok: false, reason: "WEBHOOK_NOT_CONFIGURED" }), { status: 503, headers: { "content-type": "application/json" } });
  }

  const contentLength = Number(req.headers.get("content-length") || "0");
  if (contentLength > 131072) return new Response("Payload Too Large", { status: 413 });
  const rawBody = await req.text();
  if (!(await verifySvix(rawBody, req.headers, webhookSecret))) {
    return new Response(JSON.stringify({ ok: false, reason: "INVALID_SIGNATURE" }), { status: 401, headers: { "content-type": "application/json" } });
  }

  let event: Record<string, unknown>;
  try { event = JSON.parse(rawBody); } catch { return new Response("Invalid JSON", { status: 400 }); }
  const type = String(event.type || "").toLowerCase();
  if (!ALLOWED_EVENTS.has(type)) return new Response(JSON.stringify({ ok: true, ignored: true }), { status: 200, headers: { "content-type": "application/json" } });

  const data = (event.data && typeof event.data === "object") ? event.data as Record<string, unknown> : {};
  const providerMessageId = String(data.email_id || "").trim();
  const eventId = req.headers.get("svix-id") || req.headers.get("webhook-id") || "";
  const createdAt = String(event.created_at || data.created_at || new Date().toISOString());
  const digest = await sha256Hex(rawBody);
  const eventMeta: Record<string, unknown> = {};

  if (type === "email.bounced" && data.bounce && typeof data.bounce === "object") {
    const bounce = data.bounce as Record<string, unknown>;
    eventMeta.bounce_type = String(bounce.type || "").slice(0, 80);
    eventMeta.bounce_subtype = String(bounce.subType || "").slice(0, 120);
  }

  try {
    await recordEvent(supabaseUrl, serviceRole, {
      p_provider_name: "RESEND",
      p_provider_event_id: eventId,
      p_provider_message_id: providerMessageId || null,
      p_event_type: type,
      p_event_at: createdAt,
      p_payload_digest: digest,
      p_event_meta: eventMeta,
    });
  } catch (error) {
    console.error("email-webhook record failed", String(error));
    return new Response(JSON.stringify({ ok: false, reason: "RECORD_FAILED" }), { status: 503, headers: { "content-type": "application/json" } });
  }

  return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json", "cache-control": "no-store" } });
});
