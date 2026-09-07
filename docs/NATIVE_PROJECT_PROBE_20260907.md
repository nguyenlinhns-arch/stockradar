# Native conversation capability probe — deployed, host validation pending

## Exact hypothesis

OpenAI documents `window.openai.sendFollowUpMessage` and the MCP Apps `ui/message` bridge for components hosted inside ChatGPT. The remaining question is whether an explicitly opted-in component message can create a new turn and model response in the CURRENT StockRadar Project conversation. An external StockRadar web page cannot call this host API directly. An HTTP MCP response or synthetic test alone does not prove native-host behavior.

This minimal vanilla-widget probe renders one public, static tool. The user must opt in and click once. It waits three seconds, sends at most one harmless random marker, and stops on cancel, uncheck, hiding or unloading. It never reads database rows, private website questions, account tokens or full Project history. There is no paid model API request. A native ChatGPT turn, if accepted, still uses the user's own ChatGPT plan limits.

The standard MCP Apps bridge is attempted first. The ChatGPT-specific alias is only used when initialization is unavailable or a send returns an explicit method-not-found error. An ambiguous timeout is never retried to avoid duplicate messages. Acknowledgment is described as host acceptance, not successful inference. The real success criterion is a new native chat message AND a model reply containing the generated marker in the same Project.

## Isolated production endpoint

The earlier attempt to add probe subroutes to the existing guest function was blocked by the connected deployment safety check and was not released. The safer replacement is a separate Edge Function named `stockradar-native-probe`, with no database client, account access or model API.

Public endpoints:

- `https://xamviatbxufjlpiwhebb.supabase.co/functions/v1/stockradar-native-probe/health`
- `https://xamviatbxufjlpiwhebb.supabase.co/functions/v1/stockradar-native-probe/mcp`

The separate function is ACTIVE. Connected production probes returned HTTP 200 for `/health`, MCP `initialize`, `tools/list`, and `resources/list`. The health response states `model_api_used=false`, `database_access=false`, and `native_model_reply_verified=false`. The tool list contains only `show_stockradar_native_probe`; the resource list contains only the reviewed widget. This confirms protocol reachability, not a ChatGPT model turn.

The existing `stock-ai-guest` production function remains unchanged on its prior no-API source. This experiment has not been merged into main as a completed feature.

## ChatGPT connection gate

Official OpenAI documentation currently states that Pro users can connect read/fetch MCPs in Developer Mode; full MCP write/modify support is limited to Business and Enterprise/Edu. Pro still requires Developer Mode to use a custom app. The probe is intentionally read-only/render-only and does not attempt write actions against external systems.

The real-host test therefore requires the user's ChatGPT account to enable Developer Mode and add the remote MCP endpoint above as a custom app, then invoke `show_stockradar_native_probe` from the intended StockRadar Project. This is a product/account permission step. The browser connector available in this session can navigate/read pages but exposes no click/type/create-app action, and Plugin Management cannot install an arbitrary custom MCP URL. Do not bypass this by scraping cookies or invoking undocumented ChatGPT endpoints.

A draft PR remains open only as an experiment. Do not merge it until the real ChatGPT host accepts the app and the generated marker appears in an actual model reply in the current Project.

## Scheduled-task fallback was tested and failed

A one-time Scheduled Task was created to process a clearly labelled `AUTOMATION_VERIFICATION` queue record through the connected Supabase tools. After its scheduled time the record remained WAITING, so there is no evidence that Scheduled Tasks can use this custom Supabase processing path in the current account configuration. The fixture was then explicitly completed from the live Project with a failure note, so it cannot be misread as automation success. The earlier recurring queue task is paused and is not treated as a production processor.

This rules out claiming that the current Scheduled Tasks configuration already closes the automatic-trigger gap.

## Existing two-way channel retained

The production website channel remains deployed and tested: the linked owner can submit a private question to StockRadar, this Project can read/claim/answer it via the authorized connector, and the website can poll and display the returned answer under the original question. It still does not awaken ChatGPT automatically.

## Primary documentation reviewed

- https://developers.openai.com/plugins/build/chatgpt-ui
- https://developers.openai.com/plugins/reference
- https://developers.openai.com/plugins/quickstart
- https://developers.openai.com/plugins/build/mcp-server
- https://developers.openai.com/plugins/deploy/connect-chatgpt
- https://help.openai.com/en/articles/12584461
- https://modelcontextprotocol.io/extensions/apps/overview

Archetype: vanilla-widget. Starting point: official single-widget MCP Apps quickstart, reduced to one no-data render tool. SDK pinned to 1.26.0; the deployed service is isolated from the production website AI endpoints.

## Current completion boundary

Completed: public two-way data channel, private answer return, no duplicate model API, isolated MCP probe deployment, successful MCP protocol checks, and bounded local/CI probe tests.

Not yet verified: Developer Mode connection in the actual Pro account, invocation inside this StockRadar Project, native follow-up creation, model reply containing the marker, behavior while the Project/tab is closed, and any automatic website-to-Project trigger.

Do not represent the bridge as fully automatic until those real-host checks pass.