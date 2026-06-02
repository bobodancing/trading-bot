# Weekly Profit 2026-06-02 HP-005 Live Mode / Leverage Remediation

Date: 2026-06-02
Branch: `codex/post-promotion-control-20260430`
Status: `V0_ACTIVATION_PATH_REMEDIATED_PENDING_HP006`

## Summary

- HP-005 option `B` was treated as approval for implementation only:
  live-mode selection remediation, leverage-scope remediation, tests, and final
  preflight package.
- No live activation was performed.
- No order, cancel, close, set-leverage, margin-mode, or hedge-mode exchange
  mutation was performed.
- Added explicit process-local CLI mode selection:
  - `python3 trader/bot.py --dry-run` remains dry-run and does not imply live.
  - `python3 trader/bot.py` keeps current defaults and therefore remains
    stateful Demo/Testnet if run without `--dry-run`.
  - `python3 trader/bot.py --live` sets `Config.SANDBOX_MODE=False` only for
    the running process and selects Binance live Futures endpoint.
- Added live leverage safety gating:
  - live startup default skips `exchange.set_leverage(...)`.
  - live order path default skips implicit `set_leverage()` before entries.
  - `--allow-live-leverage-set` exists as an explicit gate and requires
    `--live`.
- Added HP-006 as the open human gate for actual V0 live activation execution.

## Approved Scope

HP-005=B allowed:

- live-mode selection remediation
- leverage-scope remediation
- tests
- final preflight package update

HP-005=B did not allow:

- actual live activation
- touching live/testnet exchange state
- creating, cancelling, or closing orders
- changing hedge mode or margin mode
- setting leverage on any exchange account
- changing `trader/config.py` runtime defaults
- changing risk defaults
- enabling scanner runtime universe
- committing secrets or printing secrets

## Code Changes

| file | change |
| --- | --- |
| `trader/bot.py` | added `--live` and `--allow-live-leverage-set`; applied mode selection process-locally after `Config.load_secrets()`; passed leverage gate into `TradingBot` and `OrderExecutionEngine`; added startup safety logging for endpoint class, scanner feed, router policy, and live leverage gate |
| `trader/execution/order_engine.py` | added `allow_live_leverage_set`; live default skips direct leverage mutation and skips implicit leverage before market entry; Demo/Testnet behavior remains deterministic |
| `trader/tests/runtime/test_live_activation_safety.py` | added focused tests for CLI mode selection, endpoint selection, startup leverage gating, order-path leverage gating, and scanner/router defaults |
| `humanpending.md` | recorded HP-006 open gate for actual live activation execution |

`trader/config.py` was not modified.

## Runtime Mode Contract

| command | dry-run | sandbox | endpoint class | allowed meaning |
| --- | --- | --- | --- | --- |
| `python3 trader/bot.py --dry-run` | `True` | unchanged default `True` | Demo/Testnet | observer / dry-run only |
| `python3 trader/bot.py` | `False` | unchanged default `True` | Demo/Testnet | stateful Demo/Testnet only |
| `python3 trader/bot.py --live` | `False` | process-local `False` | live | candidate V0 live canary command after HP-006 and final preflight |
| `python3 trader/bot.py --live --allow-live-leverage-set` | `False` | process-local `False` | live | explicit live leverage mutation path; not recommended for default canary unless separately approved |

Rejected unsafe/ambiguous combinations:

- `--dry-run --live`
- `--allow-live-leverage-set` without `--live`

## Endpoint Safety

`BinanceFuturesClient` endpoint selection remains:

| sandbox | base URL |
| --- | --- |
| `True` | `https://demo-fapi.binance.com` |
| `False` | `https://fapi.binance.com` |

The `--live` flag does not edit `trader/config.py`; it sets
`Config.SANDBOX_MODE=False` only inside the current Python process before
`TradingBot()` is constructed.

## Leverage Safety

Resolved blockers:

| area | previous issue | remediation |
| --- | --- | --- |
| startup | `_init_exchange()` always attempted `exchange.set_leverage(...)` for futures symbols | live default now skips startup leverage setting unless `allow_live_leverage_set=True` |
| order path | `OrderExecutionEngine.create_order()` always called `set_leverage()` before market order | live default now skips implicit leverage setting unless `allow_live_leverage_set=True` |
| direct set leverage helper | direct `set_leverage()` could mutate live account | direct helper now returns `False` and logs a warning in live default |

Demo/Testnet behavior is preserved: sandbox mode still attempts leverage setup
as before, so existing testnet/runtime expectations remain deterministic.

## Final Preflight Package

Required before HP-006 can approve actual activation:

1. Confirm branch `codex/post-promotion-control-20260430`.
2. Confirm no unreviewed code/config/risk/scanner drift.
3. Run `Config.validate()`.
4. Confirm `trader/config.py` defaults:
   - `SYMBOLS=["BTC/USDT", "ETH/USDT"]`
   - `USE_SCANNER_SYMBOLS=False`
   - `SCANNER_UNIVERSE_ENABLED=False`
   - `STRATEGY_ROUTER_POLICY="fail_closed"`
   - risk defaults unchanged
5. Confirm live credentials exist out-of-band in repo-root `secrets.json`.
6. Perform signed read-only live endpoint checks without printing secrets:
   - `/fapi/v2/balance`
   - `/fapi/v1/positionSide/dual`
   - `/fapi/v2/positionRisk`
   - `/fapi/v1/openOrders`
   - BTC/ETH symbol-specific open-order checks
7. Confirm endpoint base URL is exactly `https://fapi.binance.com`.
8. Confirm pre-activation account state is clean:
   - total nonzero positions count `0`
   - all open orders count `0`
   - BTC open orders count `0`
   - ETH open orders count `0`
9. Confirm no scanner runtime feed.
10. Confirm process-control plan and kill criteria are explicitly approved.

Candidate activation command after HP-006 and clean final preflight:

```bash
python3 trader/bot.py --live
```

Do not add `--allow-live-leverage-set` unless HP-006 or a later gate explicitly
approves live leverage mutation.

## Verification

- [executed] `Get-Content -Raw AGENTS.md`
- [executed] `git status --short --branch`
- [executed] `git log --oneline -n 12`
- [executed] `python -c "from trader.config import Config; Config.validate(); print('Config.validate OK')"`
- [executed] `rg -n "SANDBOX_MODE|DRY_RUN|--dry-run|set_leverage|create_order|set_sandbox_mode|DEMO_FUTURES_BASE_URL|LIVE_FUTURES_BASE_URL|Config\\.load_secrets|USE_SCANNER_SYMBOLS|SCANNER_UNIVERSE_ENABLED|STRATEGY_ROUTER_POLICY"`
- [executed] `python -m pytest trader/tests/runtime/test_live_activation_safety.py -q`
- [executed] `python -m pytest trader/tests -q`
- [executed] `python -m pytest extensions/Backtesting/tests -q`
- [executed] `git diff --check`
- [executed] `git diff -- trader/config.py`
- [inspected] `AGENTS.md`
- [inspected] `humanpending.md`
- [inspected] `reports/weekly_profit_2026-06-02_v0_canary_activation_runbook.md`
- [inspected] `reports/weekly_profit_2026-06-02_v0_canary_go_hold_review.md`
- [inspected] `reports/weekly_profit_2026-06-02_option_c_tiny_testnet_lifecycle_rerun.md`
- [inspected] `reports/weekly_profit_2026-06-03_capital_risk_checklist.md`
- [inspected] `trader/config.py`
- [inspected] `trader/bot.py`
- [inspected] `trader/infrastructure/api_client.py`
- [inspected] `trader/execution/order_engine.py`
- [inspected] `trader/risk/manager.py`
- [inspected] `trader/tests/runtime/test_live_activation_safety.py`
- [assumed] HP-005=B approval is authoritative as stated by Ruei/user and recorded in `humanpending.md`.
- [assumed] Final live credentials and live account clean state remain out-of-band and were not checked in this remediation task.

## Contract Impact

- Runtime: added explicit process-local live mode; did not change
  `trader/config.py` defaults.
- Risk: no risk defaults changed.
- Scanner: scanner runtime universe remains disabled.
- Research: no strategy, symbol, threshold, or candidate changed.
- Execution: no exchange order lifecycle executed; live default now avoids
  implicit leverage mutation.
- Credentials: no secrets created, edited, copied, printed, or committed.
- Docs: updated human gate state and activation/preflight evidence.

## Decision

Decision: `V0 activation path remediated; actual live activation still blocked pending HP-006`

V0 canary activation command candidate: `python3 trader/bot.py --live`

V1 weekly-profit: `No-Go`

Rationale:

- The live endpoint selection blocker is resolved without runtime-default drift.
- The implicit live leverage mutation blocker is resolved by default-safe gating.
- Tests pass for focused runtime safety, full `trader/tests`, and Backtesting
  regression.
- Actual live activation still requires HP-006, live read-only preflight, clean
  account state, approved process-control plan, and operator confirmation.
