# Weekly Profit 2026-06-02 V0 Canary Activation Runbook

Date: 2026-06-02
Branch: `codex/post-promotion-control-20260430`
Status: `V0_ACTIVATION_PATH_REMEDIATED_PENDING_HP006`

## Summary

- Built the constrained V0 canary activation runbook and final preflight package requested after HP-004 option `B`.
- Confirmed HP-004 is recorded as resolved with option `B`.
- HP-005 is now resolved with option `B`: live-mode selection remediation, leverage-scope remediation, tests, and final preflight package only.
- Added HP-006 as an open human gate for actual constrained V0 live activation execution.
- No live activation was performed.
- No exchange state was touched.
- No runtime defaults, risk defaults, scanner settings, strategy list, symbols, thresholds, or credentials were changed.
- HP-005 remediation now provides a default-safe live activation path under the branch contract:
  - `python3 trader/bot.py --dry-run` is dry-run.
  - `python3 trader/bot.py` with current `Config.SANDBOX_MODE=True` is stateful Demo/Testnet, not live.
  - `python3 trader/bot.py --live` sets `Config.SANDBOX_MODE=False` only for the running process and targets Binance live Futures.
  - live startup and live order entry skip implicit `set_leverage()` by default.
- Decision: `V0 activation path remediated; actual live activation still blocked pending HP-006`.

## HP-004 / HP-005 / HP-006

Human gates:

| id | status | read |
| --- | --- | --- |
| HP-004 | resolved | Ruei selected `B`: approve constrained V0 canary request with strict scope; next step is runbook and final preflight, not automatic live execution. |
| HP-005 | resolved | Ruei selected `B`: approve live-mode selection remediation, leverage-scope remediation, tests, and final preflight package only. |
| HP-006 | open | Actual constrained V0 live activation still requires a final human gate after live read-only preflight and process-control confirmation. |

HP-006 remains open because HP-005 remediated the path but did not approve live execution.

## Activation Scope

Recommended V0 envelope:

| dimension | constraint |
| --- | --- |
| purpose | controlled real-market evidence collection only |
| V1 claim | not allowed; V1 remains `No-Go` |
| portfolio | current promoted three-leg BTC/ETH runtime only |
| symbols | `BTC/USDT`, `ETH/USDT` only |
| scanner | diagnostic/shadow only; no runtime feed |
| router | `fail_closed` |
| risk defaults | unchanged |
| strategy defaults | unchanged |
| thresholds | unchanged |
| capital | recommend at least `500 USDT` for full BTC/ETH scope |
| evidence window | through 2026-06-08 Week 3 review, then 2026-06-15 participation checkpoint |

Not allowed in this runbook:

- live activation
- order/cancel/close
- leverage/margin/hedge mutation
- service stop/restart/start
- runtime default edits
- scanner runtime universe activation
- strategy/symbol/threshold promotion
- credential handling changes
- secret printing/copying/committing

## Activation Path Answers

| question | answer |
| --- | --- |
| What exact command would be used for V0 canary? | Candidate command after HP-006 approval and clean final preflight: `python3 trader/bot.py --live` from the activation repo root. |
| What command is current dry-run observer using? | `python3 trader/bot.py --dry-run` |
| What does `python3 trader/bot.py --dry-run` do? | Loads secrets, sets `Config.DRY_RUN=True`, runs StrategyRuntime, records dry-run execution skips, and should not place strategy orders. |
| What does `python3 trader/bot.py` do with current defaults? | It removes dry-run, but because `Config.SANDBOX_MODE=True`, it targets Binance Demo/Testnet Futures, not live. |
| What exact endpoint would current defaults use? | Direct futures client: `https://demo-fapi.binance.com`. ccxt sandbox URLs are also rewritten to Demo Futures in `_init_exchange()`. |
| What endpoint should a real V0 live canary use? | Binance live futures endpoint `https://fapi.binance.com`, only after HP-006 approval and exact preflight confirmation. |
| What makes it live vs dry-run vs Demo/Testnet? | `--dry-run` controls dry-run observer mode. `--live` sets `Config.SANDBOX_MODE=False` for this process only. No flag keeps current Demo/Testnet default. Removing `--dry-run` alone does not make it live. |
| Is changing `Config.SANDBOX_MODE` required? | No runtime-default edit is required after HP-005 remediation. `--live` applies a process-local override and leaves `trader/config.py` unchanged. |
| Is removing `--dry-run` required? | Yes for stateful execution. But removing `--dry-run` while `SANDBOX_MODE=True` produces Demo/Testnet stateful execution, not live canary. |
| What credentials are required? | Live Binance Futures credentials with appropriate read/trade permissions, loaded only from activation host repo-root `secrets.json` via `Config.load_secrets()`. Testnet credentials are not sufficient for live canary. No secret values may be printed. |
| What capital is recommended? | At least `500 USDT` for full BTC/ETH scope. Lower capital should Hold rather than silently narrowing to ETH-only runtime. |

## Code Findings

Runtime defaults from `trader/config.py`:

| field | value |
| --- | --- |
| `STRATEGY_RUNTIME_ENABLED` | `True` |
| `ENABLED_STRATEGIES` | promoted three-leg baseline only |
| `SYMBOLS` | `BTC/USDT`, `ETH/USDT` |
| `USE_SCANNER_SYMBOLS` | `False` |
| `SCANNER_UNIVERSE_ENABLED` | `False` |
| `STRATEGY_ROUTER_POLICY` | `fail_closed` |
| `RISK_PER_TRADE` | `0.017` |
| `MAX_TOTAL_RISK` | `0.0642` |
| `MAX_POSITION_PERCENT` | `0.1459` |
| `MAX_SL_DISTANCE_PCT` | `0.06` |
| `LEVERAGE` | `3` |
| `USE_HARD_STOP_LOSS` | `False` |
| `SANDBOX_MODE` | `True` |

Startup and execution findings:

| area | finding | canary impact |
| --- | --- | --- |
| secrets | `trader/bot.py` loads repo-root `secrets.json` through `Config.load_secrets()` | credentials path is clear; values must not be printed |
| dry-run | `--dry-run` sets `Config.DRY_RUN=True` | removing flag is required for stateful execution |
| endpoint | `BinanceFuturesClient(..., Config.SANDBOX_MODE)` selects Demo when sandbox is true and live when false | live requires sandbox false |
| CLI live flag | `--live` sets `Config.SANDBOX_MODE=False` for the current process only | live endpoint selection no longer requires editing runtime defaults |
| startup leverage | `_init_exchange()` skips live `exchange.set_leverage(...)` unless `allow_live_leverage_set=True` | default live startup avoids leverage mutation |
| order leverage | `OrderExecutionEngine.create_order()` skips implicit live `set_leverage()` unless `allow_live_leverage_set=True` | default live entries avoid leverage mutation |
| hard stop | `USE_HARD_STOP_LOSS=False` | exchange-side hard stop lifecycle is not enabled by default |
| ghost adoption | live `_adopt_ghost_positions()` can adopt unmanaged exchange positions when not dry-run | final preflight must require zero exchange positions/open orders |

## Remaining Gates

| gate | state | required resolution |
| --- | --- | --- |
| live endpoint selection | remediated | `--live` provides process-local live endpoint selection without editing `trader/config.py`. |
| startup leverage mutation | remediated | live default skips startup leverage setting unless an explicit approval flag is used. |
| order-path leverage mutation | remediated | live default skips implicit order-path leverage setting unless an explicit approval flag is used. |
| actual live activation | blocked | HP-006 must explicitly approve execution after final read-only live preflight. |
| exact process control command | blocked | Activation package must specify the exact approved start/stop mechanism before execution. |
| live credentials | blocked until final preflight | Live credentials must exist out-of-band in repo-root `secrets.json` on activation host and pass signed read-only checks without leaking secrets. |

The correct next step is HP-006 final human decision plus read-only live
preflight, not automatic live execution.

## Final Preflight Package

Run only after HP-006 authorizes final activation preflight. Do not execute live canary if any item fails.

Local/repo checks:

| check | command | expected |
| --- | --- | --- |
| branch | `git status --short --branch` | `codex/post-promotion-control-20260430`; unrelated dirty evidence identified, no config drift |
| recent commits | `git log --oneline -n 12` | known promoted branch history |
| config contract | `python -c "from trader.config import Config; Config.validate(); print('Config.validate OK')"` | `Config.validate OK` |
| runtime fields | `rg -n "STRATEGY_RUNTIME_ENABLED|ENABLED_STRATEGIES|SYMBOLS|USE_SCANNER_SYMBOLS|SCANNER_UNIVERSE_ENABLED|STRATEGY_ROUTER_POLICY|RISK_PER_TRADE|MAX_TOTAL_RISK|MAX_POSITION_PERCENT|MAX_SL_DISTANCE_PCT|LEVERAGE|USE_HARD_STOP_LOSS|SANDBOX_MODE" trader/config.py` | promoted BTC/ETH scope, scanner disabled, router `fail_closed`, risk unchanged |

Activation-host checks:

| check | expected |
| --- | --- |
| repo root | correct activation host repo path |
| branch | `codex/post-promotion-control-20260430` |
| no existing strategy process conflict | exact approved process-control plan recorded |
| `Config.validate()` | pass |
| credentials | repo-root `secrets.json` exists; `API_KEY` / `API_SECRET` present; no values printed |
| endpoint | signed client confirms intended endpoint before activation; live canary must be `https://fapi.binance.com`, not Demo |
| account mode | read-only `/fapi/v1/positionSide/dual`; no mutation |
| positions | read-only `/fapi/v2/positionRisk`; total nonzero positions count `0` before activation |
| open orders | read-only `/fapi/v1/openOrders`; all open orders count `0` before activation |
| BTC/ETH metadata | exchangeInfo reviewed for min notional, lot step, precision |
| leverage state | read-only/account evidence reviewed; any live leverage setting must be explicitly approved or disabled by code |

Activation command:

```text
Candidate after HP-006 approval and final clean preflight:
cd <activation repo root>
python3 trader/bot.py --live
```

This candidate is valid only if final preflight proves live endpoint mode,
no dry-run flag, no unapproved leverage/mode mutation, correct credentials,
clean account state, and exact process-control plan. Do not add
`--allow-live-leverage-set` unless a human gate explicitly approves live
leverage mutation.

## Evidence Packet Requirements

Daily V0 packet:

- process alive / command / cwd / branch
- `Config.validate()` result
- config snapshot and config hash
- endpoint class: live vs Demo/Testnet
- scanner runtime feed check
- active positions and open orders read-only snapshot
- local `positions.json` reconciliation status
- runtime events: ready, skipped, filled, closed, rejected, execution failures
- unprotected-position and unreconciled-order count
- no secrets printed

Weekly V0 packet:

- weekly control packet from runtime observability
- unique signal-window accounting
- per-slot / per-symbol / per-side contribution
- blocked-gate attribution
- regime/router attribution
- fills, exits, fees, realized and unrealized PnL
- rolling 4w / 8w KPI read
- scanner shadow comparison, diagnostic only
- Go/Hold/Pause/Investigate decision

Do not interpret V0 evidence as V1 weekly-profit proof.

## Scanner Boundary Verification

Required checks:

| source | expected |
| --- | --- |
| `trader/config.py` | `USE_SCANNER_SYMBOLS=False`, `SCANNER_UNIVERSE_ENABLED=False` |
| runtime config snapshot | scanner feed disabled |
| weekly packet | `scanner_feeds_runtime=False` |
| logs | no scanner-selected symbols entering runtime order scope |
| runtime symbols | only `BTC/USDT`, `ETH/USDT` |

If scanner feeds runtime selection, decision is `pause`.

## Config Drift Verification

Required checks:

- Run `Config.validate()` before activation and daily.
- Compare runtime config snapshot against promoted baseline:
  - `ENABLED_STRATEGIES`
  - `SYMBOLS`
  - `USE_SCANNER_SYMBOLS`
  - `SCANNER_UNIVERSE_ENABLED`
  - `STRATEGY_ROUTER_POLICY`
  - risk caps
  - `SANDBOX_MODE`
- Verify router policy remains `fail_closed`.
- Verify no strategy, symbol, threshold, scanner, or risk default change appeared.

If config drift appears, decision is `pause`.

## Reconciliation Procedure

Before activation:

1. Signed read-only account snapshot.
2. Confirm no nonzero exchange positions.
3. Confirm no open orders.
4. Confirm `.log/positions.json` has no stale active position.
5. Confirm `performance.db` and logs do not show unresolved lifecycle.

During V0:

1. For every exchange position, match local `positions.json` and runtime log event.
2. For every local active position, match exchange position side/amount.
3. For every open order, identify why it exists and whether it is protective, entry, close, or unexpected.
4. If mismatch exists, stop interpreting economics and classify `investigate` or `pause`.

After any close:

1. Signed read-only `/fapi/v2/positionRisk`.
2. Signed read-only `/fapi/v1/openOrders`.
3. Inspect `.log/positions.json`.
4. Record final clean or residual state.

## Stop / Kill Criteria

Immediate `pause` / no-new-entry conditions:

- live endpoint ambiguity
- Demo/Testnet endpoint used for intended live canary
- `Config.validate()` failure
- scanner runtime feed enabled
- router policy not `fail_closed`
- strategy/symbol/threshold/risk drift
- credentials missing, invalid, leaked, or committed
- nonzero position before activation
- unexpected open orders before activation
- startup or execution path attempts unapproved leverage/mode mutation
- unprotected position appears
- open order cannot be reconciled
- exchange position cannot be matched to local persistence
- execution failure prevents deterministic reconciliation
- capital below approved floor
- process-control command not approved

Safe stop guidance:

- Preserve evidence first: signed read-only position/open-order snapshot, logs, `positions.json`, and config snapshot.
- Do not issue cancel/close orders unless separately approved for remediation.
- If the process is foreground, the approved operator may use a single graceful interrupt only after preserving evidence and confirming no new order is in flight.
- If the process is service-managed, HP-006 must record the exact approved stop command before live activation.
- If an unprotected position or unreconciled order remains, classify `pause`, escalate to Ruei/ops, and do not restart or continue until reconciliation is complete.

## Verification

- [executed] `Get-Content -Raw AGENTS.md`
- [executed] `git status --short --branch`
- [executed] `git log --oneline -n 12`
- [executed] `python -c "from trader.config import Config; Config.validate(); print('Config.validate OK')"`
- [executed] `Get-Content -Raw plans/2026-05-28_weekly_profit_v0_to_v1_roadmap.md`
- [executed] `Get-Content -Raw plans/2026-05-28_weekly_profit_deadline_schedule.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-02_v0_canary_go_hold_review.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-01_week2_checkpoint.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-03_capital_risk_checklist.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-02_option_c_tiny_testnet_lifecycle_rerun.md`
- [executed] `rg -n "STRATEGY_RUNTIME_ENABLED|ENABLED_STRATEGIES|SYMBOLS|USE_SCANNER_SYMBOLS|SCANNER_UNIVERSE_ENABLED|STRATEGY_ROUTER_POLICY|RISK_PER_TRADE|MAX_TOTAL_RISK|MAX_POSITION_PERCENT|MAX_SL_DISTANCE_PCT|LEVERAGE|USE_HARD_STOP_LOSS|SANDBOX_MODE" trader/config.py`
- [executed] `rg -n "argparse|--dry-run|--debug|Config\\.load_secrets|Config\\.DRY_RUN|SANDBOX_MODE|set_sandbox_mode|demo-fapi|fapi\\.binance\\.com|TradingBot\\(|bot\\.run\\(|create_order|_execute_order_plan|execution_engine|_futures_create_order|_futures_close_position|_adopt_ghost_positions|_sync_exchange_positions" trader/bot.py`
- [executed] `rg -n "DEMO_FUTURES_BASE_URL|LIVE_FUTURES_BASE_URL|base_url|sandbox|signed_request|POST|DELETE|positionSide|set_hedge_mode" trader/infrastructure/api_client.py`
- [executed] `rg -n "risk_amount|MAX_POSITION_PERCENT|MAX_TOTAL_RISK|RISK_PER_TRADE|MAX_SL_DISTANCE_PCT|LEVERAGE|min_notional|precision|min_cost|min_qty|position_value|calculate|validate|format_quantity|get_positions|futures_client" trader/risk/manager.py`
- [executed] `Get-Content trader/bot.py | Select-Object -Skip 60 -First 230`
- [executed] `Get-Content trader/bot.py | Select-Object -Skip 780 -First 100`
- [executed] `Get-Content trader/bot.py | Select-Object -Skip 1240 -First 190`
- [executed] `Get-Content trader/risk/manager.py | Select-Object -Skip 240 -First 180`
- [executed] `Get-Content trader/infrastructure/api_client.py | Select-Object -First 180`
- [executed] `Get-Content trader/execution/order_engine.py | Select-Object -First 220`
- [executed] `python -m pytest trader/tests/runtime/test_live_activation_safety.py -q`
- [executed] `python -m pytest trader/tests -q`
- [executed] `python -m pytest extensions/Backtesting/tests -q`
- [inspected] `AGENTS.md`
- [inspected] `humanpending.md`
- [inspected] `plans/2026-05-28_weekly_profit_v0_to_v1_roadmap.md`
- [inspected] `plans/2026-05-28_weekly_profit_deadline_schedule.md`
- [inspected] `reports/weekly_profit_2026-06-02_v0_canary_go_hold_review.md`
- [inspected] `reports/weekly_profit_2026-06-01_week2_checkpoint.md`
- [inspected] `reports/weekly_profit_2026-06-03_capital_risk_checklist.md`
- [inspected] `reports/weekly_profit_2026-06-02_option_c_tiny_testnet_lifecycle_rerun.md`
- [inspected] `trader/config.py`
- [inspected] `trader/bot.py`
- [inspected] `trader/infrastructure/api_client.py`
- [inspected] `trader/execution/order_engine.py`
- [inspected] `trader/risk/manager.py`
- [inspected] `trader/tests/runtime/test_live_activation_safety.py`
- [assumed] HP-004 approval from Ruei is authoritative as stated by the user and recorded in `humanpending.md`.
- [assumed] Actual live credentials, live endpoint read-only checks, and process-control details must be provided out-of-band before HP-006 can approve live activation.

## Contract Impact

- Runtime: no runtime defaults changed; `trader/config.py` untouched.
- Risk: no risk defaults changed.
- Scanner: no scanner runtime universe activation or symbol-scope change.
- Research: no strategy, symbol, threshold, or candidate promoted.
- Execution: no order, cancel, close, set leverage, hedge/margin mutation, or live state action.
- Process: no stop, restart, or start action.
- Credentials: no secrets created, edited, copied, deleted, committed, permission-mutated, or printed.
- Docs: updated this activation runbook and `humanpending.md`; added the HP-005 remediation report.

## Decision

Decision: `V0 activation path remediated; actual live activation still blocked pending HP-006`

V0 canary request: `approved as HP-004=B`

Actual V0 live activation: `blocked pending HP-006`

V1 weekly-profit: `No-Go`

Reason:

- The branch has Demo/Testnet execution-path proof and a constrained V0 request.
- HP-005 remediation now exposes `python3 trader/bot.py --live` as a candidate live activation command without editing `trader/config.py` defaults.
- Live startup and live order entry skip implicit leverage mutation by default.
- Therefore the correct next step is HP-006 final human decision plus read-only live preflight and process-control confirmation, not automatic live execution.
