# Weekly Profit 2026-06-02 V0 Canary Go / Hold Review

Date: 2026-06-02
Local timestamp: `2026-06-02 09:56:11 +08:00`
Branch: `codex/post-promotion-control-20260430`
Status: `V0_GO_REQUEST_PENDING_RUEI_APPROVAL`

## Executive Verdict

V0 canary decision: `Go Request`, not automatic `Go`.

The branch has enough operational and Demo/Testnet execution-path evidence to
ask Ruei for a constrained V0 canary decision. It does not have enough evidence
to claim weekly profitability, and it does not justify runtime-default changes,
scanner runtime activation, threshold loosening, or broad research.

Current product decision stack:

| area | decision | meaning |
| --- | --- | --- |
| runtime health | `continue` | promoted observer is clean enough to keep using as evidence source |
| participation / economics | `investigate` | two-week participation is still weak and no live-like PnL exists |
| execution path | `passed for Demo/Testnet plumbing` | signed reads plus one tiny ETHUSDT open / observe / reduce-only close completed |
| V0 canary | `Go Request` | ready to ask Ruei for explicit constrained canary approval |
| V1 weekly-profit | `No-Go` | no rolling weekly-profit confidence exists |
| research | `parked` | do not reopen until canary decision or trigger review |

This is the clean split:

```text
V0 = controlled real-market evidence collection, if Ruei accepts the risk.
V1 = proven weekly-profit confidence. Not achieved.
```

## Evidence Ladder

### 1. Runtime Process And Contract

Source evidence: `reports/weekly_profit_2026-06-01_week2_checkpoint.md`

| check | result |
| --- | --- |
| rwUbuntu observer PID | `258894` |
| command | `python3 trader/bot.py --dry-run` |
| branch | `codex/post-promotion-control-20260430` |
| remote `Config.validate()` | pass |
| config drift | `0` |
| scanner feeds runtime | `False` |
| execution failures | `0` |
| unprotected position events | `0` |
| active positions | `0` |

Runtime scope remained the promoted baseline:

- Slot A LONG:
  `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- Slot B LONG:
  `donchian_range_fade_4h_range_width_cv_013`
- Slot B SHORT:
  `donchian_range_fade_4h_range_width_cv_013_short`
- Symbols: `BTC/USDT`, `ETH/USDT`
- Scanner runtime universe: disabled
- Router policy: `fail_closed`

### 2. Participation And Economic Evidence

Source evidence: `reports/weekly_profit_2026-06-01_week2_checkpoint.md`

| metric | result |
| --- | ---: |
| raw ready / dry-run skip events | 674 |
| unique 4h signal windows | 3 |
| contributing slot | Slot B LONG only |
| contributing symbol | `BTC/USDT` only |
| contributing side | `LONG` only |
| execution attempts | 0 |
| fills | 0 |
| exits | 0 |
| `performance.db` trades | 0 |
| realized PnL | 0.0000 |

Interpretation:

- Runtime health is not the bottleneck.
- Weekly participation remains the bottleneck.
- There is no economic proof. Calling this a weekly-profit machine would be
  wrong.
- Low participation does not block a V0 evidence canary by itself, but it means
  the canary should be framed as evidence collection, not expected income.

### 3. Authenticated Readiness And Account State

Source evidence:

- `reports/weekly_profit_2026-06-03_phase_b_read_only_auth_pass.md`
- `reports/weekly_profit_2026-06-03_testnet_account_clean_readiness.md`

Resolved sequence:

| gate | result |
| --- | --- |
| initial credential state | missing, correctly blocked |
| signed Demo/Testnet GET after provisioning | pass |
| initial account state after auth | investigate due to nonzero `BASUSDT` position |
| after Ruei reset account | clean |
| final signed account-clean check | pass |
| final positions | `0` |
| final open orders | `0` |
| endpoint | `https://demo-fapi.binance.com` |

No secrets were printed, copied, modified, or committed in the evidence reports
reviewed here.

### 4. Demo/Testnet Execution-Path Lifecycle

Source evidence:
`reports/weekly_profit_2026-06-02_option_c_tiny_testnet_lifecycle_rerun.md`

Approved HP-003 scope completed:

| item | result |
| --- | --- |
| endpoint | exact `https://demo-fapi.binance.com` |
| symbol | `ETHUSDT` only |
| entry | one `BUY MARKET` |
| entry notional | `20-25 USDT` bucket |
| observation | `positionRisk` showed tiny ETHUSDT LONG |
| close | one `SELL MARKET reduceOnly=true` |
| final ETHUSDT position | `0` |
| final total nonzero positions | `0` |
| final all open orders | `0` |
| final ETHUSDT open orders | `0` |
| process lifecycle | no stop / restart / start |
| leverage / hedge / margin mutation | none |

Important limitation:

- Option C tested signed exchange plumbing and reconciliation.
- It did not test the full production `OrderExecutionEngine.create_order()`
  path because that method calls `set_leverage()`.
- It did not prove live fill quality, live slippage, live liquidity, exchange
  hard-stop reliability, or profitability.

### 5. Capital And Risk

Source evidence: `reports/weekly_profit_2026-06-03_capital_risk_checklist.md`

Runtime defaults reviewed:

| item | value |
| --- | ---: |
| `RISK_PER_TRADE` | 0.017 |
| `MAX_TOTAL_RISK` | 0.0642 |
| `MAX_POSITION_PERCENT` | 0.1459 |
| `MAX_SL_DISTANCE_PCT` | 0.06 |
| `LEVERAGE` | 3 |
| `USE_HARD_STOP_LOSS` | `False` |

Capital feasibility:

| symbol | min notional | floor using code cap | floor using conservative cap |
| --- | ---: | ---: | ---: |
| `BTCUSDT` | 50 | 176.47 USDT | 342.70 USDT |
| `ETHUSDT` | 20 | 70.59 USDT | 137.08 USDT |

PM interpretation:

- `100 USDT` is not a proper BTC/ETH runtime canary capital level.
- `250 USDT` fits the code-implied BTC cap but not the conservative no-leverage
  BTC cap.
- `500 USDT` is the first reviewed scenario that fits both BTC and ETH under
  both cap views.
- Four full-risk concurrent entries would exceed `MAX_TOTAL_RISK`; only three
  full-risk concurrent entries fit the current risk contract.

## Recommended V0 Canary Envelope

If Ruei chooses to approve V0, use this envelope. Anything broader is a new
product decision.

| dimension | recommended constraint |
| --- | --- |
| purpose | controlled live-like evidence collection, not profit claim |
| portfolio | current promoted three-leg BTC/ETH runtime only |
| scanner | diagnostic/shadow only; no runtime feed |
| strategy changes | none |
| threshold changes | none |
| router policy | keep `fail_closed` |
| risk defaults | no increase |
| capital | recommend at least `500 USDT` if running full BTC/ETH scope |
| lower capital alternative | hold; do not silently create an ETH-only runtime |
| evidence window | through 2026-06-08 Week 3 review, then 2026-06-15 participation checkpoint |
| success meaning | clean live-like execution and reconciliation evidence |
| failure meaning | pause or investigate before changing runtime |

V0 canary should not be used to hide the participation problem. If the canary
does not produce enough unique opportunities, the correct next step is a bounded
trigger review, not threshold loosening.

## Kill Criteria

Immediate `pause` or no-canary conditions:

- live endpoint / sandbox endpoint ambiguity
- missing, invalid, leaked, or committed credentials
- `Config.validate()` failure
- runtime config drift from promoted defaults
- scanner universe feeds runtime selection
- router policy not `fail_closed`
- unapproved strategy, symbol, or threshold change
- execution failure that prevents deterministic reconciliation
- nonzero position that cannot be attributed and reconciled
- open orders remain after an expected close
- unprotected-position event
- process restart or service change outside approved runbook
- capital below the min-order / risk floor for the approved scope
- Ruei does not approve canary risk

## Decision Matrix

| possible Ruei decision | product meaning | next action |
| --- | --- | --- |
| `A: Hold` | no real-money transition yet | keep dry-run observer; review Week 3 packet |
| `B: Approve constrained V0 canary request` | accept V0 evidence-collection risk | prepare/run a live-canary activation runbook under explicit scope |
| `C: Reopen research first` | prioritize participation repair before live evidence | create one bounded trigger-reviewed research contract |

PM recommendation: `B`, with the recommended V0 envelope above.

Reason:

- The plumbing gates that blocked V0 have now been materially reduced.
- Remaining weakness is economic participation, and that will not be solved by
  more dry-run plumbing checks.
- A constrained V0 canary can collect live-like evidence without pretending this
  is a V1 weekly-profit system.

## Date Note

The current local environment reports `2026-06-02 09:56:11 +08:00`.
Some prior reports in this evidence chain use `2026-06-03`. This review uses
the current local date in the filename and records that mismatch instead of
silently rewriting prior artifacts.

## Verification

- [executed] `Get-Content -Raw AGENTS.md`
- [executed] `git status --short --branch`
- [executed] `git log --oneline -n 12`
- [executed] `Get-Content -Raw plans/2026-05-28_weekly_profit_v0_to_v1_roadmap.md`
- [executed] `Get-Content -Raw plans/2026-05-28_weekly_profit_deadline_schedule.md`
- [executed] `Get-Content -Raw humanpending.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-01_week2_checkpoint.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-02_execution_path_readiness.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-03_capital_risk_checklist.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-03_phase_b_read_only_auth_pass.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-03_testnet_account_clean_readiness.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-02_option_c_tiny_testnet_lifecycle_rerun.md`
- [executed] `rg -n "STRATEGY_RUNTIME_ENABLED|ENABLED_STRATEGIES|SYMBOLS|USE_SCANNER_SYMBOLS|SCANNER_UNIVERSE_ENABLED|STRATEGY_ROUTER_POLICY|RISK_PER_TRADE|MAX_TOTAL_RISK|MAX_POSITION_PERCENT|MAX_SL_DISTANCE_PCT|LEVERAGE|USE_HARD_STOP_LOSS|SANDBOX_MODE" trader/config.py`
- [executed] `rg -n "def create_order|set_leverage|reduceOnly|stop|close_position|cancel" trader/execution/order_engine.py`
- [executed] `rg -n "risk_amount|MAX_POSITION_PERCENT|MAX_TOTAL_RISK|RISK_PER_TRADE|min_notional|precision|position_value" trader/risk/manager.py`
- [inspected] `AGENTS.md`
- [inspected] `plans/2026-05-28_weekly_profit_v0_to_v1_roadmap.md`
- [inspected] `plans/2026-05-28_weekly_profit_deadline_schedule.md`
- [inspected] `humanpending.md`
- [inspected] `reports/weekly_profit_2026-06-01_week2_checkpoint.md`
- [inspected] `reports/weekly_profit_2026-06-02_execution_path_readiness.md`
- [inspected] `reports/weekly_profit_2026-06-03_capital_risk_checklist.md`
- [inspected] `reports/weekly_profit_2026-06-03_phase_b_read_only_auth_pass.md`
- [inspected] `reports/weekly_profit_2026-06-03_testnet_account_clean_readiness.md`
- [inspected] `reports/weekly_profit_2026-06-02_option_c_tiny_testnet_lifecycle_rerun.md`
- [inspected] `trader/config.py`
- [inspected] `trader/risk/manager.py`
- [inspected] `trader/execution/order_engine.py`
- [assumed] Prior remote reports accurately captured rwUbuntu signed endpoint results and did not print secret values; this review did not reconnect to rwUbuntu or re-run exchange calls.
- [assumed] A future live canary would require a separate approved activation runbook and final preflight before touching live exchange state.

## Contract Impact

- Runtime: no runtime defaults changed; `trader/config.py` untouched.
- Risk: no risk defaults changed; existing caps were interpreted only.
- Scanner: runtime scanner universe remains disabled.
- Research: no strategy, symbol, threshold, or candidate promoted; no research
  lane opened.
- Execution: no order, cancel, close, hedge/margin/leverage mutation, or live
  state action was performed by this review.
- Process: no stop, restart, or start action.
- Credentials: no secrets created, edited, copied, deleted, committed, or
  printed by this review.
- Docs: added this final V0 Go / Hold review and opened HP-004 separately.

## Decision

Decision: `V0 Go Request pending Ruei approval`

Runtime health: `continue`

Participation / economics: `investigate`

Research: `parked`

V1 weekly-profit: `No-Go`

Reason:

- The branch has clean promoted-baseline runtime evidence and Demo/Testnet
  execution-path proof.
- The branch still lacks live PnL, enough weekly participation, rolling
  positive-week evidence, and V1 expectancy confidence.
- The next responsible product move is not more unbounded research. It is a
  human-gated V0 canary decision with strict scope and kill criteria.
