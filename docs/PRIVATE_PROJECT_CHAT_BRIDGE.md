# Private project conversation bridge

## Purpose and boundaries

The public reviewed methodology store remains unchanged. This bridge adds a separate, explicitly reviewed handoff from the owner's ChatGPT StockRadar project to one private website conversation. It is not a claim of direct API access to ChatGPT Project chat history or an automatic background synchronizer.

The existing `stockradar_ai_user_memory.preferences.project_bridge` stores an opt-in bridge record: `enabled`, `source: CHATGPT_PROJECT_STOCKRADAR`, `thread_id`, `version`, `reviewed_at`, and `summary` (20–6000 characters). The existing memory table has RLS enabled and no anonymous/authenticated Data API grants. The bridge must not be placed in user-editable Auth metadata or the public knowledge store. Provisioning/update is a reviewed operator action through the connected database, never a browser write.

`loadProjectBridge` verifies the authenticated user id, source, date, limits and linked-thread ownership. A handoff is loaded only for its linked thread. New or unrelated chats do not inherit it. Both the methodology path and the signed-in research path receive `PROJECT_HANDOFF` as user context, never current-price evidence, system authority or permission to perform actions. Guest access remains unchanged. There are no credentials or real account identifiers in this repository.

## Website operations

`stock-ai-chat` authenticates and checks account access before accepting `project_bridge` (metadata only) or `resume_project` (read-only restoration of the server-linked, owned conversation). Client-supplied owner ids, handoff content and alternative linked ids have no authority. Invalid or non-owned explicitly requested threads are rejected instead of silently replacing the requested thread with another one.

The signed-in AI workspace displays `Tiếp tục từ dự án` only when the backend reports an available bridge. Resuming does not call the model or consume the question quota. The UI rechecks account identity before restoring history. The shared and frontend ticker parsers also mask the Vietnamese phrase `tra cứu` / `tra cuu` so `tra cứu FPT` does not become a TRA/FPT comparison; the real ticker TRA remains valid.

## ChatGPT-to-website handoff

On an explicit continuation/update request: read the existing owner bridge and latest owned messages first, review the available project decisions, and update only that owner's handoff. Never claim the full unseen chat history was imported. Keep raw transcripts, portfolio holdings, recipient addresses and secrets out of the public repository and public knowledge. Preserve existing preferences and history; use an advisory lock and an idempotent versioned provenance note in the linked private thread. The note must say it is a reviewed summary, not a verbatim user message or a model-generated live answer.

## Website-to-ChatGPT continuation

When the owner asks to continue from the website here, use the connected Supabase tool to resolve the owner account, read the existing bridge's thread id, and fetch only that thread's messages after checking ownership. Record the read cursor in the private bridge record if useful. No export to public GitHub and no email forwarding is needed. New website turns are already saved in that owned thread; they are retrieved here on request, not secretly pushed into ChatGPT.

## Updating safely

Use a new handoff version for a new approved summary. Keep `summary` outside public source control, preserve unrelated preference keys, and append a dated `scope: project_handoff` note with provenance metadata rather than rewriting historical messages. To disable the bridge set its `enabled` field to false; do not delete the user's conversation. This bridge does not change paid grants, bank-transfer approval, mail delivery gates, data licenses, quotas or market/action authorization.

## Verification

The isolated private loader has 22 behavior tests. The full chat handler is exercised with synthetic owned/non-owned accounts, resume/history access, metadata-only reads, private context in methodology input, provider failure, ticker forwarding and ignored client overrides. The feature workflow runs these and the existing Node/Python suites before committing endpoint changes. Runtime deployment, database provisioning, live provider status and frontend Pages deployment must be recorded separately after verification; none are implied by source preparation.
