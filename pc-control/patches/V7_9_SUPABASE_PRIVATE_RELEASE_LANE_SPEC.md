# V7.9 — Supabase private release lane

Date: 2026-09-09
Status: preferred distribution design; do not deploy until V7.9 maintenance/rollback gates pass

## Decision

Use the existing authenticated PC Control cloud gateway for update discovery and a **private Supabase Storage bucket** for release packages. Keep publisher ECDSA signature as the independent trust root.

Supabase private buckets require authenticated download or a time-limited signed URL. This fits the desired model without publishing PC Control binaries in the current public GitHub repositories.

## Components

### Private storage bucket

Proposed bucket id: `pc-control-releases`

Properties:
- private, never public;
- binary package MIME restricted to ZIP/application/octet-stream as practical;
- object size bounded by the V7 signed package maximum;
- no anonymous SELECT policy;
- client device never receives service-role/secret API credentials.

Object layout is deterministic and derived only from verified signed release metadata:

```text
pc-control-releases/
  preview/
    v7.9.0-rc2/
      ThayLinh-PC-Control-7.9.0-rc2.zip
  stable/
    v7.9.0/
      ThayLinh-PC-Control-7.9.0.zip
```

The signed metadata contains channel, release_id and asset. It does not contain arbitrary bucket/object paths.

### Gateway discovery endpoint

Proposed semantic endpoint under the existing authenticated device gateway:

`POST /device/update/check`

Request is bounded and contains only device/runtime facts needed to select a release:

```json
{
  "current_version": "7.9.0-rc1",
  "channel": "preview",
  "release_epoch": 1,
  "protocol": 2
}
```

The channel must also agree with the locally trusted `update_channel`; a remote caller cannot change the local channel through this request.

Response:

```json
{
  "ok": true,
  "update": {
    "envelope": { "schema": "thaylinh.pc.update-feed.v2" },
    "download": {
      "kind": "supabase_signed_url",
      "url": "<short-lived signed URL>",
      "expires_at": "2026-09-09T12:05:00Z"
    }
  }
}
```

`download` is transport metadata only. It does NOT authorize execution and is not trusted for version/hash/size. The signed publisher envelope remains authority for those fields.

## Server-side package resolution

The gateway performs:

1. authenticate the existing PC device identity;
2. select the server-side channel feed;
3. validate that stored release object identity equals the envelope's channel/release_id/asset;
4. create a short-lived signed Storage URL for exactly that object;
5. return the exact signed publisher envelope plus the temporary URL.

Suggested signed URL lifetime: 5 minutes initially. A failed/expired download may request a fresh URL for the SAME already-verified release identity; it must not silently resolve to a different package.

## Client URL validation

Before using a server-returned signed URL, V7 validates:

- HTTPS only;
- exact expected Supabase project hostname compiled/provisioned through the existing trusted gateway setup;
- path prefix exactly `/storage/v1/object/sign/pc-control-releases/` (or the actual documented signed-download endpoint used by the deployed SDK);
- decoded object path exactly matches the deterministic path derived from verified channel/release_id/asset;
- no username/password, fragment, alternate port, UNC/device syntax or path traversal;
- no redirect to another origin; if a redirect is operationally unavoidable, every final origin must be explicitly allow-listed and no device credential is forwarded.

The client never logs the signed URL or its token/query string.

## Download handling

- stream directly to a new staging temp file;
- enforce Content-Length when present but do not trust it alone;
- hard-stop once received bytes exceed signed expected size or global 700 MB limit;
- exact received byte count must equal signed expected size;
- SHA-256 must equal the publisher-signed hash;
- fsync/flush then atomically rename staged download where appropriate;
- expired/failed partial download is deleted or stored only as an inert `.partial` under the owned staging root;
- never execute or extract an incomplete package.

## Authentication separation

PC device authentication and publisher signing serve different purposes:

- **Device auth**: controls who may discover/download a private release.
- **Storage signed URL**: temporary transport authorization for one package object.
- **Publisher ECDSA signature**: proves the release metadata came from the release publisher trust root.
- **SHA-256 + release inventory**: proves exact package/content integrity.
- **TrustedUpdate**: owns local activation, smoke, commit and rollback.

Compromise of any one transport layer must not be enough to install arbitrary code.

## No long-lived storage credential on PC

Do not put any Supabase service-role/secret key on the controlled PC. Prefer the existing device credential only for the gateway. The gateway/server holds any secret required to create Storage signed URLs.

## Database/feed pointer

A small server-side release registry may map channel to the active signed envelope, for example:

```text
pc_update_releases
- channel
- version
- release_id
- release_epoch
- package_object
- package_sha256
- package_size
- signed_envelope_json
- state (staged/preview/stable/revoked)
- created_at
- published_at
```

This registry is not execution authority by itself. Client signature verification remains mandatory.

The same release_id must never be rebound to another package hash. Publishing a different package requires a new release identity/epoch.

## Revocation / emergency behavior

Because a previously generated Storage signed URL remains usable until its expiry, use short expiry and publisher-envelope expiry. Emergency server revocation should stop issuing new URLs immediately.

A client that already downloaded a package still refuses activation if:
- envelope expired before activation where policy requires freshness;
- release is locally marked rejected/revoked by a separately authenticated revocation mechanism;
- hash/inventory/version/epoch checks fail.

Revocation design must never permit unsigned server metadata to authorize a new package.

## Rollout mode interaction

- `check_only`: call gateway, verify envelope; DO NOT request/download package if the server API permits discovery without URL, or ignore download URL.
- `stage_only`: obtain signed URL and stage exact verified package; current pointer unchanged.
- `auto_apply_preview/stable`: stage as above, wait for idle, enter existing TrustedUpdate transaction.

## Security acceptance

1. Bucket is private; public object URL fails.
2. No service-role/secret key is present in V7 package/data/logs.
3. Invalid device identity cannot get update metadata/package URL.
4. Valid device can get a short-lived URL for only the selected release object.
5. URL for another bucket/object/host is rejected by client.
6. Signed URL/query is redacted from all logs/status/evidence.
7. Tampered envelope -> ECDSA failure before metadata is trusted.
8. Correct envelope + tampered object -> SHA failure; never extract.
9. Correct ZIP + wrong release inventory/version -> reject before activation.
10. Storage/gateway outage does not degrade ordinary local PC-control operation.
11. Expired temporary URL can be refreshed without changing the release identity/idempotency key.
12. `check_only` produces no package write.
13. `stage_only` never changes current.json or running version.
14. Activation still uses existing TrustedUpdate and forced-bad candidate rollback.
