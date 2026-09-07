# StockRadar ChatGPT App — 2026-09-07

Archetype: interactive-decoupled, read-only research connector plus a vanilla widget. ChatGPT performs reasoning under each user's own ChatGPT account; StockRadar supplies compact one-ticker research context. The app never calls an OpenAI model API.

Tools: `search` recognizes explicit three-character HOSE tickers; `fetch` returns a sanitized single-ticker research context; `show_stockradar_card` renders data freshness/setup/gates; `stockradar_methodology` returns public methodology only. No private owner context, watchlist, account tier, email recipient, payment state or raw Project transcript is exposed.

The source is `public.fetch_stockradar_ai_context`, but the app strips full price history and most provider/raw fields before they reach the model. It preserves freshness, context grade, one snapshot quote, selected technical/fundamental/valuation/catalyst summaries and publication/action gates. `public_action_allowed=false`, reference-only/stale data or unverified valuation assumptions must remain non-actionable. Scores are not probabilities.

Current public data-rights/compliance release gates do not block AI-only research synthesis, but they do block raw-data redistribution and public trading-action publication. This app therefore does not provide bulk OHLC download, full-universe ranking, Buy/Stop/Target generation or an action queue.

Docs used: https://developers.openai.com/plugins/build/mcp-server ; https://developers.openai.com/plugins/build/chatgpt-ui ; https://developers.openai.com/plugins/reference ; https://developers.openai.com/plugins/deploy/submission .

Validation must include branch CI, hosted `/health`, MCP initialize/tools/list, real Developer Mode installation, a real `fetch` or `show_stockradar_card` invocation, and inspection that no raw `history` array reaches the tool output. Public directory submission additionally requires stable metadata, privacy/support URLs, review prompts and organization prerequisites; do not claim public publication before review approval.
