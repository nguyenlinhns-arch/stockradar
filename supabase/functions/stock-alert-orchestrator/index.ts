import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.95.0";

const EXPECTED_ISSUER = "https://token.actions.githubusercontent.com";
const EXPECTED_AUDIENCE = "stockradar-alert-orchestrator";
const EXPECTED_REPOSITORY = "nguyenlinhns-arch/stockradar";
const EXPECTED_REF = "refs/heads/main";
const EXPECTED_WORKFLOW = "nguyenlinhns-arch/stockradar/.github/workflows/process-stockradar-alerts.yml@refs/heads/main";

type JsonObject = Record<string, unknown>;

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}

function base64UrlBytes(value: string): Uint8Array {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(value.length / 4) * 4, "=");
  const binary = atob(normalized);
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

function base64UrlJson(value: string): JsonObject {
  const parsed = JSON.parse(new TextDecoder().decode(base64UrlBytes(value)));
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("INVALID_JWT_JSON");
  return parsed as JsonObject;
}

async function verifyGithubOidc(token: string): Promise<JsonObject> {
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("INVALID_JWT");
  const header = base64UrlJson(parts[0]);
  const claims = base64UrlJson(parts[1]);
  if (header.alg !== "RS256" || typeof header.kid !== "string") throw new Error("INVALID_JWT_HEADER");

  const discoveryResponse = await fetch(`${EXPECTED_ISSUER}/.well-known/openid-configuration`, {
    headers: { Accept: "application/json" },
  });
  if (!discoveryResponse.ok) throw new Error("OIDC_DISCOVERY_FAILED");
  const discovery = await discoveryResponse.json() as JsonObject;
  const jwksUri = String(discovery.jwks_uri || "");
  if (!jwksUri.startsWith(`${EXPECTED_ISSUER}/`)) throw new Error("INVALID_JWKS_URI");

  const jwksResponse = await fetch(jwksUri, { headers: { Accept: "application/json" } });
  if (!jwksResponse.ok) throw new Error("JWKS_FETCH_FAILED");
  const jwks = await jwksResponse.json() as JsonObject;
  const keys = Array.isArray(jwks.keys) ? jwks.keys : [];
  const jwk = keys.find((item) => item && typeof item === "object" && (item as JsonObject).kid === header.kid) as JsonObject | undefined;
  if (!jwk) throw new Error("JWK_NOT_FOUND");

  const key = await crypto.subtle.importKey(
    "jwk",
    jwk as JsonWebKey,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["verify"],
  );
  const signingInput = new TextEncoder().encode(`${parts[0]}.${parts[1]}`);
  const signature = base64UrlBytes(parts[2]);
  const verified = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, signature, signingInput);
  if (!verified) throw new Error("JWT_SIGNATURE_INVALID");

  const now = Math.floor(Date.now() / 1000);
  const exp = Number(claims.exp || 0);
  const nbf = Number(claims.nbf || 0);
  const iat = Number(claims.iat || 0);
  const audRaw = claims.aud;
  const audiences = Array.isArray(audRaw) ? audRaw.map(String) : [String(audRaw || "")];

  if (claims.iss !== EXPECTED_ISSUER) throw new Error("ISSUER_MISMATCH");
  if (!audiences.includes(EXPECTED_AUDIENCE)) throw new Error("AUDIENCE_MISMATCH");
  if (!exp || exp < now - 30) throw new Error("TOKEN_EXPIRED");
  if (nbf && nbf > now + 30) throw new Error("TOKEN_NOT_YET_VALID");
  if (!iat || Math.abs(now - iat) > 900) throw new Error("TOKEN_TOO_OLD");
  if (claims.repository !== EXPECTED_REPOSITORY) throw new Error("REPOSITORY_MISMATCH");
  if (claims.ref !== EXPECTED_REF) throw new Error("REF_MISMATCH");
  if (claims.job_workflow_ref !== EXPECTED_WORKFLOW) throw new Error("WORKFLOW_MISMATCH");
  return claims;
}

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return jsonResponse({ status: "METHOD_NOT_ALLOWED" }, 405);

  const authorization = req.headers.get("authorization") || "";
  const token = authorization.toLowerCase().startsWith("bearer ") ? authorization.slice(7).trim() : "";
  if (!token) return jsonResponse({ status: "UNAUTHORIZED", reason: "MISSING_GITHUB_OIDC" }, 401);

  try {
    await verifyGithubOidc(token);
  } catch (error) {
    console.error("stock-alert-orchestrator oidc", error instanceof Error ? error.message : "UNKNOWN");
    return jsonResponse({ status: "UNAUTHORIZED", reason: "GITHUB_OIDC_INVALID" }, 401);
  }

  let emitNotifications = true;
  let enqueueEmails = true;
  try {
    const body = await req.json() as JsonObject;
    if (typeof body.emit_notifications === "boolean") emitNotifications = body.emit_notifications;
    if (typeof body.enqueue_emails === "boolean") enqueueEmails = body.enqueue_emails;
  } catch (_) {
    // Empty body uses safe production defaults.
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  if (!supabaseUrl || !serviceRoleKey) {
    return jsonResponse({ status: "SERVICE_UNAVAILABLE", reason: "SUPABASE_ADMIN_CONFIG" }, 503);
  }

  const client = createClient(supabaseUrl, serviceRoleKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data, error } = await client.rpc("process_stockradar_alert_transitions_v1", {
    p_emit_notifications: emitNotifications,
    p_enqueue_emails: enqueueEmails,
  });
  if (error) {
    console.error("stock-alert-orchestrator rpc", error.code || "RPC_FAILED");
    return jsonResponse({ status: "PROCESS_FAILED", reason: String(error.code || "RPC_FAILED") }, 500);
  }

  return jsonResponse({
    status: "PROCESSED",
    emit_notifications: emitNotifications,
    enqueue_emails: enqueueEmails,
    result: data,
  });
});
