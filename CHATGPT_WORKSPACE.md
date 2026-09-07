# StockRadar — ChatGPT is the analysis workspace

## Approved operating mode (2026-09-07)

Use the owner's existing StockRadar ChatGPT Project for reasoning and the connected Supabase tool for reading data and saving selected results. Do not call OpenAI API again merely to regenerate a ChatGPT answer. The website prepares a question, links to ordinary ChatGPT and displays private saved reports. No custom public StockRadar GPT/app has been published by this change. Do not expose an internal GPT or a private Project link to visitors. Customers use their own ChatGPT account and its limits, not the owner's subscription.

The deployed AI endpoints run in CHATGPT_WORKSPACE mode. Missing or unrecognized server configuration also defaults to this mode. Legacy API code remains for an explicitly approved rollback only; fixtures explicitly opt into API to test it. Do not turn API back on, add a key, reset quotas, change subscription rights or buy credit without a new instruction. A handoff is not model output and must not count as inference success.

## How to work in this Project

1. Read current backend records before analysis. Resolve the owner through the authorized connector, not a hardcoded UUID in public files. For market input use the existing `fetch_stockradar_ai_context(p_ticker)` and current official/approved sources. Keep timestamp, source grade, coverage and missing-data warnings. A bridge/knowledge activation date never refreshes prices.
2. Analyze here using the approved 4M/Payback → CANSLIM → valuation → technical/volume → risk pipeline. Do not substitute a score or an invented probability for evidence. No stock action is authorized by saving a report.
3. When asked to save a selected answer, call `public.save_stockradar_workspace_report` through the connected database. Required fields: verified owner id, title, report body, stable idempotency key. Optional fields: ticker, horizon, data_as_of, evidence array, source. Never put an owner UUID, report body or private portfolio in public GitHub.
4. The RPC writes only DRAFT / OWNER_ONLY. Read back the returned id, hash, source and body length to confirm. Retry the same exact content/key safely; a different content with the same key must fail, not overwrite history.
5. Publication or email is a separate explicit decision and requires the existing review/data/privacy gates. This release provides no public publishing or sending action for workspace reports. Do not write into action queues or public recommendations merely because a private report was saved.

## SQL call shape (use parameters / SQL-safe literals)

`select public.save_stockradar_workspace_report(p_owner_id => <resolved_verified_owner>, p_title => <title>, p_body => <selected_report>, p_idempotency_key => <unique_source_event>, p_ticker => <ticker_or_null>, p_horizon => <horizon_or_null>, p_data_as_of => <evidence_time_or_null>, p_evidence => <evidence_json_array>, p_source => 'CHATGPT_PROJECT_WORKSPACE');`

`select id,title,status,source,content_hash,length(body),created_at from public.stockradar_workspace_reports where id=<returned_id> and user_id=<resolved_owner>;`

Only the connected trusted server role can save; browser and anonymous write access is not granted. The report page uses authenticated, owner-scoped SELECT under RLS. Do not fabricate Auth tokens to exercise production.

## Public visitor flow

The website's prompt preparation is local to the browser and contains only what the visitor types plus public methodological guidance. No background model request, raw project transcript, watchlist or credentials are appended. ChatGPT opens with a plain URL without query/history/token parameters. The current launch button is labelled `Mở ChatGPT`, not a claim of a published dedicated GPT. No ChatGPT answer is automatically scraped or imported.

## Costs and limits

The website handoff and connected report storage do not call the OpenAI inference API. ChatGPT usage remains subject to the user's plan; database, data-provider, hosting and email costs remain separate. This is not a shared Pro-account backend, browser-cookie proxy or native automatic synchronization of all ChatGPT messages.

## Verification record

Implementation/production evidence belongs in `docs/CHATGPT_WORKSPACE_RELEASE_20260907.md`. Source preparation alone is not evidence of deployment or of successful private report reads in a real logged-in browser.
