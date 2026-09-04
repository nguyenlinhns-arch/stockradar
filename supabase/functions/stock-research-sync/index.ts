import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2.95.0";

const EXPECTED_ISSUER = "https://token.actions.githubusercontent.com";
const EXPECTED_AUDIENCE = "stockradar-supabase-sync";
const EXPECTED_REPOSITORY = "nguyenlinhns-arch/stockradar";
const EXPECTED_REF = "refs/heads/main";
const EXPECTED_WORKFLOW = "nguyenlinhns-arch/stockradar/.github/workflows/sync-stockradar-research-cache.yml@refs/heads/main";
const EXPECTED_HOSE_UNIVERSE = 405;
const ACCEPTED_DATA_ROLES = new Set([
  "INTERNAL_BACKEND_RESEARCH",
  "INTERNAL_BACKEND_RESEARCH_POSTCLOSE",
  "INTERNAL_RESEARCH",
]);

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
  const text = new TextDecoder().decode(base64UrlBytes(value));
  const parsed = JSON.parse(text);
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("INVALID_JWT_JSON");
  return parsed as JsonObject;
}

async function verifyGithubOidc(token: string): Promise<JsonObject> {
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("INVALID_JWT");
  const header = base64UrlJson(parts[0]);
  const claims = base64UrlJson(parts[1]);
  if (header.alg !== "RS256" || typeof header.kid !== "string") throw new Error("INVALID_JWT_HEADER");

  const configResponse = await fetch(`${EXPECTED_ISSUER}/.well-known/openid-configuration`, { headers: { Accept: "application/json" } });
  if (!configResponse.ok) throw new Error("OIDC_DISCOVERY_FAILED");
  const config = await configResponse.json() as JsonObject;
  const jwksUri = String(config.jwks_uri || "");
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

async function sha256Hex(value: Uint8Array): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", value);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function validTicker(value: string): boolean {
  return /^[A-Z0-9]{3}$/.test(value) && /[A-Z]/.test(value);
}

Deno.serve(async (req: Request) => {
  if (req.method !== "POST") return jsonResponse({ status: "METHOD_NOT_ALLOWED" }, 405);
  const authorization = req.headers.get("authorization") || "";
  const token = authorization.toLowerCase().startsWith("bearer ") ? authorization.slice(7).trim() : "";
  if (!token) return jsonResponse({ status: "UNAUTHORIZED", reason: "MISSING_GITHUB_OIDC" }, 401);

  try {
    await verifyGithubOidc(token);
  } catch (error) {
    console.error("stock-research-sync oidc", error instanceof Error ? error.message : "UNKNOWN");
    return jsonResponse({ status: "UNAUTHORIZED", reason: "GITHUB_OIDC_INVALID" }, 401);
  }

  const raw = new Uint8Array(await req.arrayBuffer());
  if (!raw.length || raw.length > 12_000_000) return jsonResponse({ status: "INVALID_REQUEST", reason: "BUNDLE_SIZE" }, 400);
  let bundle: JsonObject;
  try {
    bundle = JSON.parse(new TextDecoder().decode(raw)) as JsonObject;
  } catch {
    return jsonResponse({ status: "INVALID_REQUEST", reason: "INVALID_JSON" }, 400);
  }

  if (String(bundle.exchange || "").toUpperCase() !== "HOSE") return jsonResponse({ status: "INVALID_REQUEST", reason: "EXCHANGE_NOT_HOSE" }, 400);
  if (!ACCEPTED_DATA_ROLES.has(String(bundle.data_role || "").toUpperCase())) return jsonResponse({ status: "INVALID_REQUEST", reason: "INVALID_DATA_ROLE" }, 400);
  if (bundle.public_release_allowed !== false || bundle.public_action_allowed !== false) {
    return jsonResponse({ status: "INVALID_REQUEST", reason: "PUBLIC_RELEASE_NOT_CLOSED" }, 400);
  }
  if (bundle.catalyst_alpha_weight_allowed !== false || bundle.institutional_alpha_weight_allowed !== false) {
    return jsonResponse({ status: "INVALID_REQUEST", reason: "ALPHA_GATE_NOT_CLOSED" }, 400);
  }

  const tickers = bundle.tickers;
  if (!tickers || typeof tickers !== "object" || Array.isArray(tickers)) return jsonResponse({ status: "INVALID_REQUEST", reason: "TICKERS_MISSING" }, 400);
  const tickerRows = tickers as Record<string, unknown>;
  const expectedCount = Number(bundle.universe_count || 0);
  if (expectedCount !== EXPECTED_HOSE_UNIVERSE || Object.keys(tickerRows).length !== EXPECTED_HOSE_UNIVERSE) {
    return jsonResponse({ status: "INVALID_REQUEST", reason: "CANONICAL_HOSE_UNIVERSE_MISMATCH" }, 400);
  }

  const generatedAt = String(bundle.generated_at_vn || bundle.generated_at || "").trim();
  const asOfDate = String(bundle.as_of_date || "").trim();
  const priceStatus = String(bundle.price_snapshot_status || "").trim();
  if (!generatedAt || !/^\d{4}-\d{2}-\d{2}$/.test(asOfDate) || !priceStatus) return jsonResponse({ status: "INVALID_REQUEST", reason: "FRESHNESS_METADATA_MISSING" }, 400);

  const eligible: Array<{ ticker: string; payload: JsonObject }> = [];
  for (const [rawTicker, rawRow] of Object.entries(tickerRows)) {
    const ticker = rawTicker.trim().toUpperCase();
    if (!validTicker(ticker) || !rawRow || typeof rawRow !== "object" || Array.isArray(rawRow)) continue;
    const row = rawRow as JsonObject;
    const release = row.release && typeof row.release === "object" && !Array.isArray(row.release) ? row.release as JsonObject : {};
    if (release.internal_research_ready !== true || release.public_action_allowed !== false) continue;
    eligible.push({ ticker, payload: row });
  }

  const supabaseUrl = Deno.env.get("SUPABASE_URL") || "";
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";
  if (!supabaseUrl || !serviceRoleKey) return jsonResponse({ status: "SERVICE_UNAVAILABLE", reason: "SUPABASE_ADMIN_CONFIG" }, 503);
  const serviceClient = createClient(supabaseUrl, serviceRoleKey, { auth: { persistSession: false, autoRefreshToken: false } });
  const digest = await sha256Hex(raw);
  const snapshotId = `github-stockradar-${asOfDate.replaceAll("-", "")}-${digest.slice(0, 16)}`;
  const sourceRef = `internal-bundle:github-actions:sha256:${digest}`;

  let synced = 0;
  const failures: Array<{ ticker: string; code: string }> = [];
  const concurrency = 16;
  for (let start = 0; start < eligible.length; start += concurrency) {
    const batch = eligible.slice(start, start + concurrency);
    const results = await Promise.all(batch.map(async ({ ticker, payload }) => {
      const { error } = await serviceClient.rpc("upsert_stockradar_internal_research_context", {
        p_ticker: ticker,
        p_snapshot_id: snapshotId,
        p_generated_at: generatedAt,
        p_as_of_date: asOfDate,
        p_price_snapshot_status: priceStatus,
        p_payload: payload,
        p_source_ref: sourceRef,
      });
      return { ticker, error };
    }));
    for (const result of results) {
      if (result.error) failures.push({ ticker: result.ticker, code: String(result.error.code || "RPC_FAILED") });
      else synced += 1;
    }
  }

  if (failures.length) {
    console.error("stock-research-sync partial failure", failures.slice(0, 10));
    return jsonResponse({
      status: "PARTIAL",
      snapshot_id: snapshotId,
      universe_count: expectedCount,
      eligible_rows: eligible.length,
      synced_rows: synced,
      failed_rows: failures.length,
      failed_tickers: failures.slice(0, 20),
      prune_performed: false,
    }, 500);
  }

  const allowedTickers = eligible.map(({ ticker }) => ticker);
  const { data: prunedRows, error: pruneError } = await serviceClient.rpc("prune_stockradar_internal_research_context", {
    p_allowed_tickers: allowedTickers,
  });
  if (pruneError) {
    console.error("stock-research-sync prune failure", pruneError.code || "RPC_FAILED");
    return jsonResponse({
      status: "PRUNE_FAILED",
      snapshot_id: snapshotId,
      universe_count: expectedCount,
      eligible_rows: eligible.length,
      synced_rows: synced,
      prune_performed: false,
      reason: String(pruneError.code || "RPC_FAILED"),
    }, 500);
  }

  return jsonResponse({
    status: "SYNCED",
    snapshot_id: snapshotId,
    source_sha256: digest,
    as_of_date: asOfDate,
    price_snapshot_status: priceStatus,
    universe_count: expectedCount,
    eligible_rows: eligible.length,
    synced_rows: synced,
    pruned_rows: Number(prunedRows || 0),
    cache_replace_complete: true,
  });
});
