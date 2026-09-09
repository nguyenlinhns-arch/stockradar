# V7.9 online update — source of truth

Date: 2026-09-09
Status: CURRENT DESIGN SOURCE OF TRUTH

This file resolves overlaps among the V7.9 online-update work products. When older text conflicts, this file and the referenced current artifacts win.

## Current runtime status

- Accepted live runtime remains 7.0.0-rc1.
- V7.9 staging Gate 1 passed.
- V7.9 maintenance Gate 2 is still blocked at the real local Approval A boundary.
- Controlled broken-candidate rollback has not yet been executed.
- Therefore unattended online activation is NOT enabled and MUST NOT be treated as production-ready.

## Required implementation order

1. Finish V7.9 self-maintenance Approval A -> sandbox build/test -> immutable candidate.
2. Separate Approval B -> `TrustedUpdate.ApplyLocalCandidate` staging promotion.
3. Controlled broken candidate -> automatic rollback PASS.
4. Implement online `CHECK_ONLY` using publisher-signed feed v2.
5. Implement `STAGE_ONLY` using private release storage.
6. Enable `AUTO_APPLY_PREVIEW` only after its restart/network gates pass.
7. Enable `AUTO_APPLY_STABLE` only after real reboot/logon/reconnect and required soak pass.

## Trust stack

An online package is eligible for staging/activation only when ALL applicable layers pass:

1. existing authenticated PC device/gateway relationship;
2. fixed private release origin policy;
3. ECDSA P-256 publisher signature over canonical signed metadata;
4. expiry + channel + strict version + monotonic release epoch checks;
5. exact publisher-signed package byte size + SHA-256;
6. safe archive extraction policy;
7. VERSION/release inventory/catalog/dependency validation;
8. locally permitted rollout mode;
9. idle/journal/lease/dedupe/approval safety gates;
10. existing TrustedUpdate activation/smoke/rollback transaction.

No single transport credential or repository permission is sufficient to install code.

## Current artifacts

### Core contract
`V7_9_WP_ONLINE_AUTO_UPDATE_CONTRACT_v1.md`

Despite the historical filename, its document heading is v2. All trust/update/rollback rules remain current EXCEPT any sentence assuming the current public StockRadar GitHub repository is the production binary origin.

### Distribution-origin override
`V7_9_ONLINE_UPDATE_DISTRIBUTION_ORIGIN_DECISION.md`

This supersedes the GitHub-production-origin assumption. Existing owned repositories are currently public, so do not publish production Control PC packages there by default.

### Preferred private lane
`V7_9_SUPABASE_PRIVATE_RELEASE_LANE_SPEC.md`

Preferred current design:
- existing device-authenticated gateway for discovery;
- private `pc-control-releases` Storage bucket;
- short-lived server-generated signed URL for exact object;
- no service-role/secret storage credential on the PC;
- updater independently validates host/path/release identity and signed package hash.

### Feed schema
`V7_9_UPDATE_FEED_V2.schema.json`

Strict schema for publisher-signed update envelope.

### Offline publisher tool
`tools/sign_v79_update_manifest.py`

Offline/no-network P-256 signer. Production private key must remain outside repository and PC-control runtime data. Encrypted PEM with interactive passphrase is supported.

### Cross-language verification fixtures
- `fixtures/v79-update-signature-test-public.pem`
- `fixtures/v79-update-signature-test-envelope.json`
- `fixtures/README_V79_UPDATE_SIGNATURE_FIXTURE.md`

The committed public key is disposable TEST material only, not the production publisher key.

### Overall implementation sequence
`V7_9_NEXT_UPGRADE_SEQUENCE_20260909.md`

After the trust/update path is proven, the next measured performance priorities are Persistent UIA worker, Fast Capture, then remote wake optimization.

## Canonical signed-metadata rule

The signer and .NET verifier must share one explicitly tested canonicalization contract. Do not rely on incidental serializer defaults.

For feed v2:
- UTF-8;
- object keys sorted deterministically using ordinal ASCII ordering;
- no insignificant whitespace;
- signed metadata permits integers but no floating-point numbers;
- signed strings/keys are ASCII only and additionally constrained by the feed schema/typed parser;
- duplicate JSON properties are rejected before signature trust;
- ECDSA P-256 + SHA-256;
- signature encoding: IEEE P1363 fixed-field concatenation (`r || s`), exactly 64 bytes before Base64.

Before production, the .NET verifier MUST pass the committed fixture and mutation-negative tests.

## Rollout-mode default

First install containing online-update support MUST use:

```text
update_mode = check_only
update_channel = preview
```

No remote tool/feed may increase update_mode or change update_channel. More permissive modes are local trusted configuration transitions gated by real acceptance evidence.

## No production claims yet

Do not label V7.9 or online auto-update production-ready until the outstanding maintenance promotion/rollback, restart/network cycles, reboot/logon/reconnect and soak gates are actually evidenced PASS.