# Native queue bridge 0.4.0 — 2026-09-15

## Change scope
Existing `stockradar-native-probe` function and its isolated widget only. No new
OpenAI inference calls, account changes, public Project access, database grants,
email or trading actions. The existing pending endpoint still exposes only its
boolean signal, not questions, user IDs, claim tokens, answers or history.

## Implemented fixes
- Follow MCP Apps `ui/initialize` and `ui/message`; use the detected ChatGPT
  compatibility alias only after a definitive method-not-found response.
- Add an explicit one-shot native queue check, including when the queue is empty.
- A stable positive signal is latched rather than re-sent every 45 seconds.
  Only a subsequently observed valid negative signal rearms automatic sending.
- Preserve the latch across widget renders when host widget-state storage exists.
- A message timeout or rejection stops automatic sending. No blind delivery retry.
- Abort signal reads on Stop/hide; invalidate late responses after Stop/page close.
- Pause hidden cards. Restoring a page from bfcache requires fresh activation.
- Reject unavailable/malformed signals; never label an outage as an empty queue.
- Distinguish resource deployment, host message acceptance and database delivery.
- Keep v1/v2/v3 resource URI aliases to serve updated UI to cached tool metadata.

## Verification
`node --test tests/native_bridge_v4.test.mjs`: 19/19 local mocked-host regression
cases passed. Tests execute the exact JavaScript embedded in `widget.ts`.
They test the real controller against fake host/timer/network interfaces, not the
production ChatGPT UI, and do not prove native delivery in a live conversation.
A Chromium test with a mocked parent host accepted one explicit native request,
correctly labelled website delivery as unverified, and showed no horizontal
overflow at 390px and 960px. This too is not a real ChatGPT-host verification.

A read of the live authorized Project inbox at the start of this change returned
zero pending records. No visitor or owner message was fabricated to fill it.

## Boundaries remaining
Native messaging must still be verified in the real current conversation with an
explicitly activated card. A saved ANSWERED record must be read back before claiming
website delivery. A visible, retained widget is required; this is not an always-on
server worker and does not run after ChatGPT unloads it. The boolean signal cannot
identify requests or prove completion. A backlog that stays positive without an
observed clear transition intentionally needs a manual check rather than a blind
repeat. Separate simultaneously enabled cards can still each request processing;
the trusted database claim/lease remains the authority preventing double work.

This connects owner-scoped selected questions and answers; it does not import every
native message or expose this private Project to all website customers.

## Official host interface reference
https://developers.openai.com/plugins/build/chatgpt-ui
https://developers.openai.com/plugins/reference
