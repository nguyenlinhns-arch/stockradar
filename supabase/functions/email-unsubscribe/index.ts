import "jsr:@supabase/functions-js/edge-runtime.d.ts";

function headers(contentType: string) {
  return {
    "Content-Type": contentType,
    "Cache-Control": "no-store, max-age=0",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
  };
}

function page(title: string, message: string, token: string, showButton: boolean) {
  const safeToken = token.replace(/[^a-f0-9]/gi, "");
  return `<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title} — StockRadar</title></head>
  <body style="margin:0;background:#f3f6f9;font-family:Arial,sans-serif;color:#0f172a"><main style="max-width:620px;margin:50px auto;padding:0 16px"><section style="background:#fff;border:1px solid #dbe4ee;border-radius:16px;padding:28px"><strong style="font-size:20px">STOCKRADAR</strong><h1 style="font-size:25px;margin:18px 0 10px">${title}</h1><p style="line-height:1.65;color:#475569">${message}</p>${showButton ? `<form method="post" action="?token=${safeToken}"><input type="hidden" name="List-Unsubscribe" value="One-Click"><button type="submit" style="border:0;border-radius:9px;background:#0b1f33;color:#fff;font-weight:700;padding:12px 18px;cursor:pointer">Xác nhận ngừng nhận</button></form>` : ""}<p style="font-size:13px;color:#64748b;margin-top:22px">Bạn vẫn có thể quản lý từng loại email trong My StockRadar nếu còn đăng nhập.</p></section></main></body></html>`;
}

async function applyToken(supabaseUrl: string, serviceRole: string, token: string) {
  const response = await fetch(`${supabaseUrl}/rest/v1/rpc/apply_stockradar_unsubscribe_v1`, {
    method: "POST",
    headers: { apikey: serviceRole, authorization: `Bearer ${serviceRole}`, "content-type": "application/json", accept: "application/json" },
    body: JSON.stringify({ p_token: token }),
  });
  if (!response.ok) throw new Error(`unsubscribe rpc ${response.status}`);
  return await response.json();
}

Deno.serve(async (req: Request) => {
  if (req.method !== "GET" && req.method !== "POST") return new Response("Method Not Allowed", { status: 405 });
  const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
  const serviceRole = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  if (!supabaseUrl || !serviceRole) return new Response("Service unavailable", { status: 503, headers: headers("text/plain; charset=utf-8") });

  const url = new URL(req.url);
  const token = String(url.searchParams.get("token") || "").trim().toLowerCase();
  if (!/^[a-f0-9]{64}$/.test(token)) {
    return new Response(page("Liên kết không hợp lệ", "Liên kết ngừng nhận email không hợp lệ hoặc đã hết hạn.", "", false), { status: 400, headers: headers("text/html; charset=utf-8") });
  }

  if (req.method === "GET") {
    return new Response(page("Ngừng nhận email StockRadar", "Xác nhận nếu bạn muốn ngừng loại email tương ứng với liên kết này. Việc này không xóa tài khoản StockRadar.", token, true), { status: 200, headers: headers("text/html; charset=utf-8") });
  }

  try {
    const result = await applyToken(supabaseUrl, serviceRole, token);
    const status = String(result?.status || "");
    if (status === "UNSUBSCRIBED") {
      const scope = String(result?.scope || "EMAIL");
      const oneClick = (req.headers.get("content-type") || "").includes("application/x-www-form-urlencoded") || (await req.text()).includes("List-Unsubscribe=One-Click");
      if (oneClick) return new Response("Unsubscribed", { status: 200, headers: headers("text/plain; charset=utf-8") });
      return new Response(page("Đã cập nhật lựa chọn email", `StockRadar đã ngừng gửi phạm vi ${scope}. Tài khoản và watchlist của bạn không bị xóa.`, token, false), { status: 200, headers: headers("text/html; charset=utf-8") });
    }
    return new Response(page("Liên kết đã hết hiệu lực", "Liên kết này đã được sử dụng hoặc đã hết hạn. Bạn có thể quản lý email trong My StockRadar.", token, false), { status: 410, headers: headers("text/html; charset=utf-8") });
  } catch (error) {
    console.error("email-unsubscribe failed", String(error));
    return new Response(page("Chưa thể cập nhật", "Hệ thống chưa thể cập nhật lựa chọn email lúc này. Vui lòng thử lại sau.", token, false), { status: 503, headers: headers("text/html; charset=utf-8") });
  }
});
