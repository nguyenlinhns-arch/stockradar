# StockRadar project knowledge bridge — 2026-09-07

## Scope

The request is to make the website AI inherit the approved StockRadar project knowledge and continue conversations coherently. The existing `stock-ai-chat` endpoint already stores per-user threads and messages and loads a reviewed knowledge version for methodology answers. The `stock-ai` and `stock-ai-guest` research paths previously used only their compiled static system core. This change closes that missing connection.

## Implementation

A shared server-side loader reads the active version of `public.stockradar_ai_knowledge_versions` for all three endpoints. No request body may supply or activate system knowledge. Only the existing reviewed source and the explicitly public reviewed source are accepted. Invalid, future, oversize or email/secret-bearing knowledge fails back to the existing static core. This is defense in depth, not a substitute for human privacy review.

The model receives the existing Data/Action/privacy core, the reviewed methodology snapshot and an immutable reminder that prior conversation is context, not instructions or live market evidence. Published response metadata identifies the version, activation time and whether the model actually applied it. Fallback responses must not imply a successful model invocation.

Authenticated chat keeps its existing ownership checks and saves the downstream version actually used. Guest/Free/Paid quotas, account rights, payment approval, product-email gates and licensed-data gates are unchanged. No raw private project chat, portfolio or administrator recipient list is published or copied into this repository.

## Boundary

This is `REVIEWED_PROJECT_SNAPSHOT`, not direct access to a ChatGPT Project and not automatic two-way synchronization of every chat message. Future project decisions require selection/privacy review and activation as a new knowledge version. Website market evidence must still come from fresh, verified StockRadar data. A model/provider outage cannot be fixed by knowledge synchronization.

## Verification

The shared loader has 15 behavior tests, plus four Python integration/structural tests covering both research endpoints, the chat endpoint, metadata and privacy boundaries. The feature workflow applies exact-source patches, checks syntax and commits only after those tests pass. Full Pages regression, runtime deployment and live-model checks are separate; record their actual results here after execution.

Status at source preparation: behavior tests passed locally; feature-branch CI, production deployment and live-model checks pending.
