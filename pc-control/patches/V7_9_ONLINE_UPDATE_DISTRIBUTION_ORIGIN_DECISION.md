# V7.9 online update — distribution origin decision

Date: 2026-09-09
Status: supersedes any V7.9 auto-update text that assumes the current `stockradar` GitHub repository is a production binary feed.

## Finding

The currently owned GitHub repositories, including `nguyenlinhns-arch/stockradar`, are PUBLIC. They may remain useful for review/spec/source artifacts, but production ThayLinh PC Control binaries MUST NOT be published there by default.

Publisher signature protects integrity; it does not provide confidentiality. A public release origin would make the entire binary package publicly downloadable.

## Preferred production distribution lane

Use a fixed authenticated **PC Control release gateway + private object storage** lane, separate from the public development repository.

Preferred deployment shape:

1. Existing authenticated PC Control device identity contacts a fixed update endpoint under the already trusted gateway origin.
2. Gateway returns the signed update-feed v2 envelope for the device's locally selected channel.
3. Client verifies publisher ECDSA P-256 signature, schema, expiry, version, epoch and package hash before trusting any package metadata.
4. Package is stored in a private release bucket/object store.
5. Client obtains package bytes through either:
   - a fixed authenticated storage path constructed from verified `release_id + asset`; or
   - a short-lived server-issued download URL only when its scheme/host/path match a compiled allow-list and the verified release identity.
6. Client still verifies exact signed size + SHA-256 before extraction.
7. Staging/activation/rollback continue through existing TrustedUpdate.

## Why this lane is preferred

- avoids publishing PC Control binaries through the public StockRadar repository;
- reuses the existing device-authenticated cloud relationship instead of introducing a permanent GitHub PAT on the PC;
- publisher signature remains independent of gateway/storage compromise;
- no caller/ChatGPT-supplied URL enters the updater;
- private storage access can be revoked without rotating the publisher signing key;
- local hash-pinned recovery remains available when cloud access fails.

## URL policy

Public tools never provide a URL.

If the backend returns a temporary storage URL, the updater must validate before any request:

- `https` only;
- no username/password component;
- host in the compiled release-storage allow-list;
- port restricted to expected TLS endpoint;
- normalized path exactly matches the verified release id/asset namespace;
- no path traversal, percent-encoded escape, query-controlled alternate object path, fragment, or cross-origin redirect;
- final redirect target remains allow-listed;
- credentials are never forwarded to another origin.

The package is untrusted until its signed expected size and SHA-256 verify, regardless of transport authentication.

## Separation of concerns

### Public development repository
May contain:
- review diffs;
- schemas/specifications;
- non-secret signer/verifier tooling;
- public test fixtures/public keys;
- acceptance templates.

Must not contain:
- production publisher private key;
- device/cloud secrets;
- production signed URLs/tokens;
- production package unless the user explicitly decides the binary may be public.

### Private release storage
Contains:
- signed update envelopes;
- exact release ZIP/package;
- immutable release inventory/evidence needed by the client;
- channel pointers/metadata as applicable.

### Offline/protected publisher
Contains:
- production ECDSA P-256 private signing key;
- release-signing action only.

The private signing key is not required on the controlled PC for update verification.

## Fallback alternatives

A dedicated PRIVATE GitHub releases repository can be used later if desired, but it requires a carefully scoped read-only credential or GitHub App installation on the PC and adds token lifecycle/redirect handling. It is not the default while all current repositories are public.

Google Drive can remain a human recovery/snapshot channel, not the primary unattended update protocol, unless a dedicated OAuth/device-token design is reviewed separately.

## Acceptance additions

Before `STAGE_ONLY` is accepted:

1. A public `stockradar` release path is rejected as a production binary origin by configuration tests.
2. Unauthenticated package fetch from the chosen private origin fails.
3. Authenticated manifest fetch succeeds without exposing device credentials in logs.
4. Valid signed metadata + valid private package downloads and hashes correctly.
5. Temporary URL to unlisted host/path is rejected even when returned by the gateway.
6. Gateway/storage compromise simulation with a different package fails SHA/signature/inventory gates.
7. Cloud release origin outage leaves current PC Control fully operational and local recovery intact.
