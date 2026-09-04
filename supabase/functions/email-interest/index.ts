import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const ALLOWED_ORIGINS = new Set([
  "https://stockradar.vn",
  "https://www.stockradar.vn",
  "https://nguyenlinhns-arch.github.io",
  "http://localhost:8000",
]);
const INTENT_KIND = "PREMIUM_EMAIL_INTEREST";

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

function textField(payload: Record<string, unknown>, key: string, maxLength: number) {
  const value = typeof payload[key] === "string" ? String(payload[key]).trim() : "";
  return value.replace(/[\r\n\t]/g, "").slice(0, maxLength);
}

Deno.serve(async (req: Request) => {
  const origin = req.headers.get("origin") || "";
  if (!ALLOWED_ORIGINS.has(origin)) {
    return json("null", 403, { accepted: false, message: "Nguồn yêu cầu không được phép." });
  }

  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: responseHeaders(origin) });
  }
  if (req.method !== "POST") {
    return json(origin, 405, { accepted: false, message: "Phương thức không được hỗ trợ." });
  }

  const contentType = req.headers.get("content-type") || "";
  const contentLength = Number(req.headers.get("content-length") || "0");
  if (!contentType.toLowerCase().includes("application/json") || contentLength > 4096) {
    return json(origin, 400, { accepted: false, message: "Yêu cầu không hợp lệ." });
  }

  let payload: Record<string, unknown>;
  try {
    payload = await req.json();
  } catch {
    return json(origin, 400, { accepted: false, message: "Yêu cầu không hợp lệ." });
  }

  // Honeypot: bots get a generic accepted response but no database write.
  if (typeof payload.company === "string" && payload.company.trim()) {
    return json(origin, 202, { accepted: true, status: "PENDING_VERIFICATION", intent_kind: INTENT_KIND });
  }

  const email = typeof payload.email === "string" ? payload.email.trim().toLowerCase() : "";
  const dailyBrief = payload.daily_brief === true;
  const eventAlerts = payload.event_alerts === true;
  const consentVersion = typeof payload.consent_version === "string" ? payload.consent_version : "";
  const privacyAccepted = payload.privacy_accepted === true;
  const sourcePathRaw = textField(payload, "source_path", 256);
  const sourcePath = sourcePathRaw.startsWith("/") ? sourcePathRaw : "";
  const utmSource = textField(payload, "utm_source", 120);
  const utmCampaign = textField(payload, "utm_campaign", 160);
  const referrerHost = textField(payload, "referrer_host", 253)
    .toLowerCase()
    .replace(/[^a-z0-9.:-]/g, "");

  if (
    email.length < 3 || email.length > 160 ||
    !/^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$/.test(email) ||
    (!dailyBrief && !eventAlerts) ||
    !privacyAccepted ||
    !/^\d{4}-\d{2}-\d{2}$/.test(consentVersion)
  ) {
    return json(origin, 400, {
      accepted: false,
      message: "Vui lòng nhập email hợp lệ, chọn ít nhất một loại email và đồng ý lưu thông tin đăng ký.",
    });
  }

  const forwarded = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim();
  const clientIp = req.headers.get("cf-connecting-ip") || forwarded || "unknown";
  const userAgent = req.headers.get("user-agent") || "unknown";
  const day = new Date().toISOString().slice(0, 10);
  const ipHash = await sha256Hex(`${day}|${clientIp}|${userAgent}|stockradar-email-interest-v2`);

  const supabaseUrl = Deno.env.get("SUPABASE_URL");
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!supabaseUrl || !serviceRoleKey) {
    console.error("email-interest: missing server environment");
    return json(origin, 503, { accepted: false, message: "Dịch vụ đăng ký email đang tạm thời chưa sẵn sàng." });
  }

  const rpc = await fetch(`${supabaseUrl}/rest/v1/rpc/capture_email_subscription_interest_v2`, {
    method: "POST",
    headers: {
      apikey: serviceRoleKey,
      authorization: `Bearer ${serviceRoleKey}`,
      "content-type": "application/json",
      accept: "application/json",
    },
    body: JSON.stringify({
      p_email: email,
      p_daily_brief: dailyBrief,
      p_event_alerts: eventAlerts,
      p_consent_version: consentVersion,
      p_ip_hash: ipHash,
      p_source_path: sourcePath || null,
      p_utm_source: utmSource || null,
      p_utm_campaign: utmCampaign || null,
      p_referrer_host: referrerHost || null,
    }),
  });

  if (!rpc.ok) {
    const detail = (await rpc.text()).toLowerCase();
    if (detail.includes("rate limit exceeded")) {
      return json(origin, 429, { accepted: false, message: "Có quá nhiều yêu cầu từ thiết bị này. Vui lòng thử lại sau." });
    }
    if (detail.includes("invalid email") || detail.includes("select at least one") || detail.includes("consent version mismatch")) {
      return json(origin, 400, { accepted: false, message: "Thông tin đăng ký chưa hợp lệ hoặc phiên đồng ý đã thay đổi. Vui lòng tải lại trang." });
    }
    console.error("email-interest RPC failed", rpc.status);
    return json(origin, 503, { accepted: false, message: "Chưa thể ghi nhận đăng ký email lúc này." });
  }

  return json(origin, 202, {
    accepted: true,
    status: "PENDING_VERIFICATION",
    intent_kind: INTENT_KIND,
    message: "Đã ghi nhận nhu cầu email Premium ở trạng thái chờ xác minh. Bước này chưa tạo quyền nhận email và chưa phải quyền gửi email. Product email chỉ được gửi khi tài khoản Trial/Paid đã xác minh, có đồng ý nhận hiện hành, không bị suppression và delivery gate production đã được kích hoạt.",
  });
});
