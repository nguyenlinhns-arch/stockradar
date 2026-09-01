# StockRadar Recommendation Lifecycle V2.1.2

## State sequence

`CANDIDATE → GATE_EVALUATED → PUBLISHED/UNACTIVATED → ACTIVATED/OPEN → REVIEWED* → CLOSED`.

Research states such as WATCH, WAIT_BUY and EXTENDED do not imply publication or a filled entry. A failed gate may remain a ranked research item but cannot become a recommendation.

## Events

| Event | Rule |
| --- | --- |
| `PUBLISHED` | freezes publication timestamp, publication price, buy zone, target, risk, thesis and version |
| `ACTIVATED` | first eligible trade strictly after publication enters/touches the frozen buy zone |
| `OBSERVED` | adds current price and open return without changing the original record |
| `SCORE_CHANGED` / `TARGET_CHANGED` | appends old/new values and the reason; never edits an older event |
| `REVIEWED` | required by `review_due_at`; records CONTINUE, ADJUST, NO_LONGER_ELIGIBLE or CLOSE |
| `TARGET_REACHED` / `STOP_REACHED` / `INVALIDATED` / `EXPIRED` | records a terminal reason candidate |
| `CLOSED` | freezes close price/time/reason and final return |
| `CORRECTION` | explains source/processing error and points to a replacement; does not erase history |

## Activation rule

- ignore all bars at or before publication;
- if a later bar opens inside the zone, entry is its open;
- a first touch from below uses the lower zone boundary;
- a first touch from above uses the upper zone boundary;
- do not use the session low/high to choose a more attractive fill;
- no eligible touch means `UNACTIVATED` and no P/L.

## Closure

Closure is explicit, idempotent and horizon-aware. Once closed, later prices cannot update the final result. Manual override requires actor, timestamp, old/new value, reason and approval/audit reference.

## No forced recommendation

If no candidate passes the Recommendation Gate, publication returns an empty list and the public message “HÔM NAY KHÔNG CÓ KHUYẾN NGHỊ MỚI ĐẠT TIÊU CHUẨN.” Ranking strength never forces a buy record.
