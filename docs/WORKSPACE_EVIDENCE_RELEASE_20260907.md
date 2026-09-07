# Workspace evidence reader and real Project-to-report round trip — 2026-09-07

## Completed data-to-report cycle

A real, authorized StockRadar research-context read was performed in the existing ChatGPT Project. The returned observation was REFERENCE_ONLY, dated 2026-09-04, with public release/action disabled. Numerical comparisons were checked in the Project, and a private diagnostic was written through the existing `save_stockradar_workspace_report` operation. A separate read-back confirmed 3,896 report characters, six evidence records, source CHATGPT_PROJECT_WORKSPACE and status DRAFT. The stored content hash was independently recomputed from its fields and matched.

This diagnostic is not a current-price recommendation. It explicitly states the observation date, unverified valuation assumptions, incomplete inputs and conflicting cached classifications. It contains no released Buy Zone, Stop, Target, probability or trade instruction. No second OpenAI inference API call was used to regenerate the Project's answer. The save returned OWNER_ONLY, published=false and email_sent=false. Private report identifiers, account identifiers, numerical market data and the report body are deliberately excluded from this public audit.

The prior operational note was preserved. The owner can continue requesting data reads and selected report saves from this Project; the website is the private report reader, not a proxy for the owner's ChatGPT subscription.

## Reader improvements

The report interface now includes `Tải lại báo cáo` and `Nguồn và phép kiểm tra`. Supported evidence fields are displayed as text, including the source record, date, verification grade, formula and explanatory note. Evidence does not execute HTML, load images or turn unsafe URL schemes into links. Unknown fields are not dumped into the page.

`Đã lưu` and `Dữ liệu đến` are separate labels. When a report has only a source date, the reader says the source identifies only the day instead of fabricating an intraday timestamp. A later save date never upgrades an older market observation into live data.

Account/session transitions invalidate in-flight report and old-history requests. Logout clears rendered private content, including when old history was opened before the report list. Signing out and back in as the same account does not permit a late response from the previous session to render. Token refresh for the same continuing account does not erase its displayed report. The read-only report query remains owner-filtered under the existing database permissions.

## Verification and merge

Feature run 34079411650 completed successfully, executing the existing regression suites and 12 new tests against the actual browser source. The new cases cover source-date precision, invalid dates, text-only evidence rendering, URL rejection, unknown-field exclusion, owner scoping, logout, delayed cross-account and same-account-reauthentication responses, old-history cleanup, out-of-order refreshes and continued absence of model calls.

PR 89 was merged as commit 6b3397213373984e040d5b3e60b5ee03114121f1 after confirming the tested feature head. Main had received a newer documentation/comment commit while the feature was being verified; it was preserved through a normal merge, not overwritten with a forced ref update.

At this document checkpoint, Pages workflow 34079554823 is still running its browser/publication stages. Final deployment success is not yet claimed here. The report save and database read-back above are complete independently of frontend publication. No backend function was changed in this reader release; the existing no-inference chat function was re-read and remains ACTIVE version 8 on the previously verified no-API source.

## Data-quality follow-up

A separate review of `compute_technical_features` found a potentially incorrect Pocket Pivot down-volume lookback: the loop includes the current bar instead of all ten prior completed sessions. It is tracked in issue 90 with a requested synthetic boundary regression. This reader release does not claim to have fixed that engine issue or revalidated trading outputs. The distinct Vol20 convention averages the prior 20 sessions excluding the current bar; averaging 20 displayed bars including the current day is not an equivalent check.

## Limits retained

The generic `Mở ChatGPT` destination is not a published dedicated StockRadar GPT/App. Visitor questions still need to be pasted into ChatGPT; no raw ChatGPT messages are continuously scraped or automatically imported. The owner workflow uses the authorized connectors available in this Project, not shared browser cookies or a shared Pro account.

No API key, API credit, payment approval, subscription entitlement, email delivery, database policy or public trading gate was changed. The end-to-end private report display was tested with synthetic browser accounts; the owner's actual authenticated browser was not controlled. Some live-page/log retrieval attempts in this turn were blocked by the tool environment, so they are not treated as deployment evidence.
