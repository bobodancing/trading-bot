# Weekly Profit 2026-06-03 Capital / Risk Checklist

Date: 2026-06-03
Branch: `codex/post-promotion-control-20260430`
Status: `CAPITAL_RISK_CHECKLIST_HOLD_PHASE_B_HUMAN_GATE_REQUIRED`

## Summary

- Reviewed V0 canary capital feasibility and risk controls using local code inspection plus the 2026-06-01 and 2026-06-02 evidence reports.
- No runtime defaults were changed; `trader/config.py` remains untouched.
- No live/testnet service state was touched; no order, cancel, hedge-mode, leverage, scanner, strategy, symbol, threshold, process, or credential action was performed.
- Capital feasibility is not blocked by ETH at `100 USDT` under the code-implied notional cap, but BTC is not feasible at `100 USDT` when the 6% max stop distance and `50 USDT` min notional are both respected.
- A practical BTC/ETH canary capital floor is at least `176.47 USDT` under the code-implied notional cap; a more conservative no-leverage cap view raises the BTC floor to `342.70 USDT`.
- V0 remains `Hold` because credentials are missing and authenticated private endpoint / stateful testnet order lifecycle readiness is still unproven.
- `humanpending.md` now contains one explicit open Phase B gate for Ruei.

## Inputs

Evidence inputs:

- `reports/weekly_profit_2026-06-01_week2_checkpoint.md`
- `reports/weekly_profit_2026-06-02_execution_path_readiness.md`
- `plans/2026-05-28_weekly_profit_deadline_schedule.md`

Runtime defaults inspected in `trader/config.py`:

| item | value |
| --- | ---: |
| `RISK_PER_TRADE` | 0.017 |
| `MAX_TOTAL_RISK` | 0.0642 |
| `MAX_POSITION_PERCENT` | 0.1459 |
| `MAX_SL_DISTANCE_PCT` | 0.06 |
| `LEVERAGE` | 3 |
| `SYMBOLS` | `BTC/USDT`, `ETH/USDT` |
| `USE_SCANNER_SYMBOLS` | `False` |
| `SCANNER_UNIVERSE_ENABLED` | `False` |
| `STRATEGY_ROUTER_POLICY` | `fail_closed` |
| `USE_HARD_STOP_LOSS` | `False` |

Phase A public market metadata:

| symbol | min notional | lot min | lot step | price tick | qty precision |
| --- | ---: | ---: | ---: | ---: | ---: |
| `BTCUSDT` | 50 | 0.0001 | 0.0001 | 0.10 | 4 |
| `ETHUSDT` | 20 | 0.001 | 0.001 | 0.01 | 3 |

Code behavior inspected:

- `trader/risk/manager.py`: legacy sizing computes `risk_amount = balance * RISK_PER_TRADE`, `position_value = risk_amount / stop_dist_percent`, then caps notional at `balance * MAX_POSITION_PERCENT * LEVERAGE`.
- `trader/risk/manager.py`: precision helpers read Demo Futures `exchangeInfo` in sandbox futures mode and enforce min cost checks.
- `trader/execution/order_engine.py`: `create_order()` calls `set_leverage()` before placing a market order; Phase B therefore needs explicit stateful testnet approval and must not be confused with Phase A read-only checks.
- `trader/execution/order_engine.py`: hard stop placement is disabled unless `USE_HARD_STOP_LOSS=True`; current config has `False`, so stop behavior remains unproven for V0.

## Capital Feasibility

Definitions:

```text
C = review capital in USDT
r = RISK_PER_TRADE = 0.017
R_total = MAX_TOTAL_RISK = 0.0642
p = MAX_POSITION_PERCENT = 0.1459
L = LEVERAGE = 3
d_max = MAX_SL_DISTANCE_PCT = 0.06
```

Formulas:

```text
risk_amount = C * r
risk_notional_at_max_sl = risk_amount / d_max
code_max_notional = C * p * L
conservative_max_notional = C * p
min_cap_by_code_cap = min_notional / (p * L)
min_cap_by_conservative_cap = min_notional / p
min_cap_by_risk_at_max_sl = min_notional * d_max / r
```

Minimum capital floors:

| symbol | min notional | min cap by code cap | min cap by conservative cap | min cap by risk at 6% SL | floor using code cap | floor using conservative cap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `BTCUSDT` | 50 | 114.23 | 342.70 | 176.47 | 176.47 | 342.70 |
| `ETHUSDT` | 20 | 45.69 | 137.08 | 70.59 | 70.59 | 137.08 |

Scenario table:

| capital | risk/trade | risk notional at 6% SL | code max notional | conservative max notional | total risk budget | BTC feasible, code cap | BTC feasible, conservative cap | ETH feasible, code cap | ETH feasible, conservative cap |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| 100 | 1.70 | 28.33 | 43.77 | 14.59 | 6.42 | NO | NO | YES | NO |
| 250 | 4.25 | 70.83 | 109.43 | 36.48 | 16.05 | YES | NO | YES | YES |
| 500 | 8.50 | 141.67 | 218.85 | 72.95 | 32.10 | YES | YES | YES | YES |
| 1000 | 17.00 | 283.33 | 437.70 | 145.90 | 64.20 | YES | YES | YES | YES |

Interpretation:

- `100 USDT` can fit ETH min notional under the code-implied cap and 6% risk math, but it cannot fit BTC min notional without violating either code cap or per-trade risk at max stop distance.
- `250 USDT` can fit BTC/ETH using the code-implied notional cap, but BTC still fails the conservative no-leverage cap.
- `500 USDT` is the first listed scenario where both BTC and ETH satisfy min notional under both the code-implied and conservative cap views.
- These are arithmetic feasibility checks only. They do not prove slippage safety, fill quality, liquidation buffer, stop reliability, or live expectancy.

## Risk Envelope

Per-trade risk:

| symbol | min notional | risk at 6% SL | minimum capital for min order risk <= 1.7% |
| --- | ---: | ---: | ---: |
| `BTCUSDT` | 50 | 3.00 | 176.47 |
| `ETHUSDT` | 20 | 1.20 | 70.59 |

At `100 USDT`:

- BTC min order at 6% SL risks `3.00 USDT`, or `3.00%` of equity, above the configured `1.70%` per-trade risk.
- ETH min order at 6% SL risks `1.20 USDT`, or `1.20%` of equity, within the configured `1.70%` per-trade risk.

Max total risk:

```text
floor(MAX_TOTAL_RISK / RISK_PER_TRADE)
= floor(0.0642 / 0.017)
= 3 full-risk concurrent entries
```

Four full-risk entries would imply `6.80%`, exceeding `MAX_TOTAL_RISK=6.42%`.

Liquidation / leverage note:

- `LEVERAGE=3` is configured, but Phase A did not authenticate account state and did not verify actual leverage, margin mode, position mode, maintenance margin, liquidation buffer, or exchange-side stop behavior.
- `create_order()` currently calls `set_leverage()` before market order placement. Any Phase B lifecycle that exercises this path is stateful and requires Ruei approval.

Stop behavior note:

- `USE_HARD_STOP_LOSS=False` in config.
- Runtime may use internal stop / risk-plan logic, but exchange-side hard stop lifecycle has not been authenticated or statefully tested in Phase A.
- No canary approval should rely on stop behavior that has not been verified under testnet order lifecycle.

## V0 Canary Checklist

| area | required evidence | current state |
| --- | --- | --- |
| credentials readiness | `secrets.json` exists with `API_KEY` / `API_SECRET` presence, no values printed | BLOCKED: missing in Phase A |
| authenticated private endpoint readiness | balance, position mode, open positions, open orders read through signed GET | BLOCKED: skipped because credentials missing |
| testnet-only stateful order lifecycle | explicit approved tiny testnet order open/observe/close/cancel-path review | BLOCKED: Phase B not approved |
| min order / precision readiness | BTC/ETH exchangeInfo reviewed; sizing handles min notional and lot steps | PARTIAL: public metadata reviewed, not order-tested |
| leverage / liquidation buffer readiness | actual account leverage/margin/position mode/liquidation buffer reviewed | BLOCKED: private account state not authenticated |
| stop behavior readiness | stop placement, monitoring, close/reconcile behavior proven on testnet | BLOCKED: no stateful lifecycle; hard stop disabled by default |
| persistence / reconciliation readiness | positions and orders reconcile after lifecycle and restart-like read | BLOCKED: no Phase B lifecycle; no process restart allowed here |
| runtime process health | dry-run observer alive and config valid | PASS from 6/1 and 6/2 evidence |
| promoted scope | BTC/ETH only, promoted three-leg baseline, scanner runtime disabled | PASS from reports and config |
| canary approval | Ruei explicitly approves risk and scope | BLOCKED |

Allowed symbols for any future approved Phase B:

- `BTC/USDT`
- `ETH/USDT`

Forbidden changes:

- no runtime default changes
- no `trader/config.py` changes
- no scanner runtime universe activation
- no strategy / symbol / threshold promotion
- no live endpoint lifecycle
- no credential value printing or committing
- no router policy or risk default changes
- no process stop/restart/start unless separately approved

## Kill Criteria

Immediate `pause` / no-canary conditions:

- config drift from promoted runtime defaults
- scanner universe feeds runtime selection
- credentials missing, invalid, leaked, or committed
- authenticated private endpoint check fails
- Phase B attempts live endpoint state mutation
- Phase B changes hedge mode, leverage, or margin mode without explicit scope
- order lifecycle creates an untracked or unreconciled position
- open order cannot be observed, closed, or reconciled on testnet
- unprotected position event appears
- execution failure rate or API errors prevent deterministic lifecycle read
- persistence / `positions.json` state cannot be reconciled with exchange state
- runtime process health breaks during evidence collection
- Ruei does not approve Phase B or canary risk

## Blockers

| blocker | status | unblock condition |
| --- | --- | --- |
| credentials | open | provision testnet credentials without printing or committing values |
| authenticated private reads | open | rerun Phase A signed GET checks successfully |
| Phase B stateful lifecycle | open | Ruei approves testnet-only order lifecycle after credentials/read-only auth pass |
| leverage / liquidation buffer | open | account state read and lifecycle review document actual margin/leverage/liquidation context |
| stop behavior | open | testnet lifecycle proves stop/close/reconciliation behavior |
| canary approval | open | Ruei approves canary risk after checklist evidence |

## Verification

- [executed] `Get-Content -Raw AGENTS.md`
- [executed] `git status --short --branch`
- [executed] `git log --oneline -n 12`
- [executed] `Get-Content trader/config.py | Select-Object -First 280`
- [executed] `Get-Content trader/risk/manager.py | Select-Object -First 380`
- [executed] `Get-Content trader/execution/order_engine.py | Select-Object -First 260`
- [executed] `Get-Content reports/weekly_profit_2026-06-01_week2_checkpoint.md`
- [executed] `Get-Content reports/weekly_profit_2026-06-02_execution_path_readiness.md`
- [executed] `Get-Content plans/2026-05-28_weekly_profit_deadline_schedule.md`
- [executed] `if (Test-Path humanpending.md) { Get-Content humanpending.md } else { Write-Output 'NO_HUMANPENDING' }`
- [executed] local read-only `python -` arithmetic script for capital/risk scenario table.
- [inspected] `trader/config.py`
- [inspected] `trader/risk/manager.py`
- [inspected] `trader/execution/order_engine.py`
- [inspected] `reports/weekly_profit_2026-06-01_week2_checkpoint.md`
- [inspected] `reports/weekly_profit_2026-06-02_execution_path_readiness.md`
- [inspected] `plans/2026-05-28_weekly_profit_deadline_schedule.md`
- [assumed] Public metadata from Phase A remains the current metadata for this 2026-06-03 checklist; no fresh exchange call was made in this task.
- [assumed] Capital calculations use max stop distance `6%`; smaller stops increase risk-based notional capacity but do not prove fill or stop safety.

## Contract Impact

- Runtime: no runtime defaults changed; `trader/config.py` untouched.
- Risk: no risk defaults changed; this report only interprets existing caps.
- Scanner: no scanner runtime universe change; scanner remains disabled for runtime selection.
- Research: no strategy, symbol, or threshold promoted; no research lane opened.
- Execution: no live/testnet state touched; no order/cancel/hedge/leverage/process action.
- Docs: added this report and one `humanpending.md` Phase B gate.
- Credentials: no secrets created, copied, modified, or printed.

## Decision

V0 canary: `Hold`

Phase B: `blocked pending Ruei approval + testnet credentials provisioning`

V1 weekly-profit: `No-Go`

Reason:

- Runtime health evidence is acceptable for continued observation, but authenticated execution-path readiness is not proven because credentials are missing.
- Capital math supports a bounded future canary only above the relevant min-order/risk floor, with BTC requiring at least `176.47 USDT` under code-implied notional cap and `342.70 USDT` under conservative no-leverage cap.
- No stateful testnet lifecycle has verified actual account mode, leverage, liquidation buffer, stop behavior, order observation, close/cancel behavior, or persistence reconciliation.
