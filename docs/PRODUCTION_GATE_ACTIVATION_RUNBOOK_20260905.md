# StockRadar Production Gate Activation Runbook — 2026-09-05

## Principle

Fail closed. Do not enable public action reports or outbound product email until the relevant external evidence and technical checks pass.

## Current capabilities

- Internal Research AI: operational on fresh internal research cache.
- Public Action API: blocked pending DATA_RIGHTS + COMPLIANCE approval evidence and fresh manifest-bound reports.
- Product email: blocked pending verified sender domain + sending credential + delivery/compliance gate activation.
- Email webhook: deployed; signing secret is stored in Supabase Vault and the function can fall back to Vault.

## Gate A — DATA_RIGHTS

Required evidence:

1. Written commercial agreement or written provider approval that explicitly covers StockRadar.vn.
2. Public/paid-user display rights.
3. Derived-data rights for rankings, scores, signals, buy zones, stop/target, research recommendations and email alerts.
4. Cache/retention rights and permitted refresh frequency.
5. Territory, attribution and redistribution restrictions.
6. Dataset scope: HOSE universe, intraday/EOD OHLCV, corporate actions, fundamentals and any market/flow layers used by Action Reports.

Do not infer rights from public accessibility, API access or a consumer subscription.

When evidence is received:

- Record immutable evidence reference.
- Build a licensed production manifest with a sha256 manifest reference.
- Publish fresh manifest-bound reports to private.stock_report_cache.
- Record DATA_RIGHTS approval via record_stockradar_api_approval only after reviewer confirmation.

## Gate B — COMPLIANCE

Required evidence:

1. Named Vietnamese legal/compliance reviewer.
2. Reviewed product scope and artifact/version references.
3. Written conclusion on research/education vs regulated securities-investment advisory boundaries.
4. Conditions for paid alerts, watchlist/personalization, buy zone/stop/target/RR outputs, marketing claims and track record.
5. Required disclaimers, terms, consent, billing/refund, privacy and complaint/correction process.
6. Review/expiry date and unresolved conditions.

When evidence is received:

- Implement every stated condition before approval.
- Record COMPLIANCE approval against the same manifest_ref + snapshot_id as DATA_RIGHTS.

## Gate C — PUBLIC ACTION API

Activation prerequisites enforced by database:

- current DATA_RIGHTS approval = true;
- current COMPLIANCE approval = true;
- at least one fresh report bound to the approved manifest and snapshot;
- production report payload must be DECISION_GRADE and public_release_allowed=true;
- action contract must remain fail-closed.

Activation:

- call activate_stockradar_api(manifest_ref, snapshot_id, evidence_ref);
- verify runtime health returns public_action=READY;
- run regression and one non-action + one action test before exposing UI.

## Gate D — RESEND DOMAIN

Required DNS records for stockradar.vn (values are maintained in the Resend domain configuration):

- DKIM TXT at resend._domainkey;
- Return-Path MX at send;
- SPF TXT at send.

Do not mark sender_domain_verified until Resend reports VERIFIED.

After verification:

1. Confirm sending-only API key exists and is restricted to stockradar.vn.
2. Store the key only in Supabase Edge Secrets/Vault; never GitHub or migration SQL.
3. Configure a sender such as alerts@stockradar.vn only after domain verification.
4. Confirm unsubscribe, bounce/complaint and suppression handling.
5. Send a transactional test to an authorized internal mailbox.
6. Confirm webhook delivery events are written to private.email_delivery_events.

## Gate E — EMAIL DELIVERY

Only enable sending when all are true:

- provider_configured;
- sender_domain_verified;
- unsubscribe_ready;
- bounce_complaint_ready;
- compliance_approved;
- sending credential present;
- worker preflight passes.

Then enable scheduler, send a test, verify SENT -> DELIVERED, and only then set sending_enabled=true for product mail.

## Monitoring

Runtime health must expose independently:

- research_ai;
- public_action;
- email_delivery;
- email_scheduler;
- cache freshness/contamination;
- outbox queue/failures;
- notification/action-event activity.

No gate may be promoted based on verbal assumptions or stale evidence.
