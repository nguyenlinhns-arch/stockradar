# Native conversation capability probe — not a completed automatic bridge

## Exact hypothesis

OpenAI documents `window.openai.sendFollowUpMessage` and the MCP Apps `ui/message` bridge for components hosted inside ChatGPT. We need to test whether an explicitly opted-in delayed component message creates a new turn and model response in the CURRENT Project conversation. An external StockRadar web page cannot call this host API. An HTTP MCP response or synthetic test cannot prove native-host behavior.

This minimal vanilla-widget probe renders one public, static tool. The user must opt in and click once. It waits three seconds, sends at most one harmless random marker, and stops on cancel, uncheck, hiding or unloading. It never reads database rows, private website questions, account tokens or full Project history. There is no paid model API request. A native ChatGPT turn, if accepted, still uses the user's own ChatGPT plan limits.

The standard MCP Apps bridge is attempted first. The ChatGPT-specific alias is only used when initialization is unavailable or a send returns an explicit method-not-found error. An ambiguous timeout is never retried to avoid duplicate messages. Acknowledgment is described as host acceptance, not successful inference. The real success criterion is a new native chat message AND a model reply containing the generated marker in the same Project.

## Hosting boundary

The static probe is isolated on `/functions/v1/stock-ai-guest/native-probe/mcp` and `/health`, with no database functionality. The existing guest function already uses its established custom request handling with JWT verification disabled. Its ordinary origin, no-model-API and account-independent handoff behavior is byte-preserved outside these exact routes. This does not expose any new private action or disable authentication on a private route. A fresh MCP server/transport is created for each request. Request bodies are capped at 8 KB. No new subscription, API credential or database privilege is introduced.

## Connection required

The probe needs to be installed as a custom MCP app/plugin in ChatGPT and invoked from the current Project. A public HTTPS endpoint alone cannot install itself into a user's ChatGPT account. The presently connected browser tools can navigate/read but have no click/type/create action; the plugin-management tools cannot create an arbitrary custom MCP app from its URL. Do not fake installation or silently invoke internal ChatGPT endpoints.

Only after real host validation should a separate opt-in private queue monitor be designed. Polling, closed-tab behavior, delivery retries, cross-account isolation and subscription terms still require review. This probe does not claim website-initiated automatic processing or 24/7 service, and does not publish a shared owner-subscription backend.

## Primary documentation reviewed

- https://developers.openai.com/plugins/build/chatgpt-ui
- https://developers.openai.com/plugins/reference
- https://developers.openai.com/plugins/quickstart
- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/plugins/deploy/connect-chatgpt
- https://modelcontextprotocol.io/extensions/apps/overview

Archetype: vanilla-widget. Starting point: official single-widget MCP Apps quickstart, reduced to a single no-data render tool. SDK pinned to 1.26.0; a per-request server avoids sharing transport state.

## Actual verification checkpoint

Ten local VM tests on the widget passed before source preparation. CI also tests static-server boundaries and preserves existing guest handler behavior. Those tests simulate a host and are NOT proof that the real ChatGPT host accepts delayed messages. Deployment, protocol checks, user connection and native turn verification must be recorded as separate checkpoints. No queued website question was waiting at the start of this work.
