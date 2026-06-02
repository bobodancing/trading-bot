# Weekly Profit 2026-06-03 Testnet Position Reconciliation

Date: 2026-06-03
Branch: `codex/post-promotion-control-20260430`
Status: `INVESTIGATE_NON_PROMOTED_TESTNET_POSITION`

## Summary

- Executed read-only reconciliation for the one nonzero Demo/Testnet Futures position found after HP-001 option B signed `GET` passed.
- Confirmed rwUbuntu dry-run source is still alive and aligned: PID `258894`, command `python3 trader/bot.py --dry-run`, cwd `/proc/258894/cwd`, branch `codex/post-promotion-control-20260430`.
- `Config.validate()` passed from `/proc/258894/cwd`.
- Used `Config.load_secrets()` through the normal repo path and confirmed the signed client is pointed at Binance Demo/Testnet Futures, not live.
- Performed only signed `GET` calls. No `POST`, `DELETE`, or `PUT` calls were made.
- The nonzero position is `BASUSDT`, `positionSide=BOTH`, inferred `SHORT`, cross margin, leverage `3`.
- `BASUSDT` is outside promoted runtime scope (`BTCUSDT` / `ETHUSDT`).
- Total open orders count is `0`; no matching open orders exist for `BASUSDT`.
- Runtime evidence did not link the position to this branch: no `BASUSDT` lines, no `execution_filled`, no `TRADE_OPEN`, no active `positions.json` record, and no `performance.db` row for the target symbol.
- Decision is `investigate`; Option C remains blocked until Ruei/ops resolves or explicitly accepts the existing testnet account state.

## Source

Runtime source:

| item | observed |
| --- | --- |
| host | `rwfunder@100.67.114.104` |
| PID | `258894` |
| process age at check | `880838` to `880945` seconds |
| process start | `Fri May 22 11:51:06 2026` local ps output; approx `2026-05-22T03:51:06+00:00` |
| command | `python3 trader/bot.py --dry-run` |
| cwd symlink | `/proc/258894/cwd` |
| resolved cwd | `/home/rwfunder/<non-ascii>/strategyVersion/trading-bot` |
| branch | `codex/post-promotion-control-20260430` |
| config validation | `Config.validate OK` |

Local preflight:

| item | observed |
| --- | --- |
| local branch | `codex/post-promotion-control-20260430...github/codex/post-promotion-control-20260430` |
| latest local commit | `8a3d655 feat(scanner): add v3 shadow universe stage a` |
| local dirty state | existing dirty/untracked docs/reports present before this report; not reverted or cleaned |

Inspected local contract files:

- `AGENTS.md`
- `reports/weekly_profit_2026-06-03_phase_b_read_only_auth_pass.md`
- `reports/weekly_profit_2026-06-03_capital_risk_checklist.md`
- `humanpending.md`
- `trader/config.py`
- `trader/infrastructure/api_client.py`
- `trader/execution/order_engine.py`
- `trader/bot.py`

## Account Snapshot

Endpoint safety:

| item | result |
| --- | --- |
| `Config.SANDBOX_MODE` | `True` |
| client base URL class | `demo_testnet` |
| endpoint safety | `ok_demo_testnet` |
| live endpoint used | no |
| secrets path | normal repo `Config.load_secrets()` path |
| secret values printed/copied | no |

Signed read-only calls:

| check | method | endpoint | HTTP status | pass/fail |
| --- | --- | --- | ---: | --- |
| balance read | `GET` | `/fapi/v2/balance` | 200 | pass |
| position risk read | `GET` | `/fapi/v2/positionRisk` | 200 | pass |
| open orders read | `GET` | `/fapi/v1/openOrders` | 200 | pass |
| hedge mode read | `GET` | `/fapi/v1/positionSide/dual` | 200 | pass |

Sanitized account summary:

| item | result |
| --- | --- |
| authenticated private GETs passed | yes |
| USDT balance presence | present |
| available balance bucket | `5000-10000` |
| hedge mode read result | `dualSidePosition=false` |
| nonzero positions count | `1` |
| total open orders count | `0` |

## Nonzero Position Details

Sanitized nonzero position:

| field | value |
| --- | --- |
| symbol | `BASUSDT` |
| positionSide | `BOTH` |
| side inferred from sign | `SHORT` |
| position amount bucket | `100+` |
| notional bucket | `500-1000` |
| entry price bucket | `0-1` |
| mark price bucket | `0-1` |
| unrealized PnL bucket | `50-100` |
| unrealized PnL sign | `positive` |
| liquidation price bucket | `0-1` |
| leverage | `3` |
| margin type | `cross` |
| isolated margin bucket | `0` |
| update time UTC | `2026-05-29T08:05:28.822000+00:00` |
| age bucket | `1d-7d` |
| promoted runtime scope | no |
| matching open orders exist | no |
| matching open orders count | `0` |

Interpretation:

- The position is not `BTCUSDT` or `ETHUSDT`.
- It is outside the promoted runtime universe and outside the current `Config.SYMBOLS` contract.
- It is not safe to proceed to any option C lifecycle while this unrelated account state is present unless Ruei/ops explicitly resolves or accepts it.

## Open Orders

| item | result |
| --- | --- |
| `/fapi/v1/openOrders` without symbol | HTTP `200` |
| total open orders count | `0` |
| BTC open orders | none returned by all-orders read |
| ETH open orders | none returned by all-orders read |
| BASUSDT matching open orders | `0` |

No order was canceled or modified.

## Runtime Linkage Check

Read-only evidence inspected on rwUbuntu:

| source | exists | read result | BAS target evidence |
| --- | --- | --- | --- |
| `.log/runtime_observability/strategy_runtime_funnel.jsonl` | yes | `180901` JSON lines, `0` parse errors | `0` target symbol events |
| `.log/trades.log` | yes | `23292` lines scanned | `0` `BASUSDT` / `BAS/USDT` lines |
| `.log/bot.log` | yes | `5788` lines scanned | `0` `BASUSDT` / `BAS/USDT` lines |
| `.log/positions.json` | yes | parsed OK, `0` active records | `0` target symbol records |
| `performance.db` | yes | opened read-only; tables: `sqlite_sequence`, `trades` | `0` target symbol rows |

Runtime observability event counts relevant to execution:

| event | count |
| --- | ---: |
| `execution_skipped` | 674 |
| `strategy_entry_ready` | 674 |
| dry-run execution skips | 674 |
| `execution_filled` | 0 |
| target symbol `execution_filled` | 0 |
| target symbol event counts | none |

Text pattern scan:

| source | `DRY_RUN` matches | `execution_filled` / `TRADE_OPEN` / adoption / target matches |
| --- | ---: | --- |
| `.log/runtime_observability/strategy_runtime_funnel.jsonl` | 676 | no target symbol, no fill |
| `.log/trades.log` | 0 | no target symbol, no trade open |
| `.log/bot.log` | 0 | no target symbol |
| `.log/positions.json` | 0 | no active target position |

## Reconciliation Read

The existing `BASUSDT` position appears to be external to this promoted dry-run branch.

Evidence:

- Current runtime command is `python3 trader/bot.py --dry-run`.
- `trader/bot.py` dry-run execution path records `execution_skipped` with reason `dry_run` and returns before order creation.
- `trader/bot.py` ghost adoption and exchange-position sync return early when `Config.DRY_RUN` is true.
- `strategy_runtime_funnel.jsonl` contains dry-run skips, but no `execution_filled`.
- `trades.log` contains no target symbol or `TRADE_OPEN` linkage for `BASUSDT`.
- `positions.json` has no active records.
- `performance.db` has no target symbol rows in read-only query.

This is not enough to prove the exact origin of the testnet position. It is enough to say the position is not linked by local evidence to this branch's dry-run runtime.

## Verification

- [executed] `Get-Content -Raw AGENTS.md`
- [executed] `git status --short --branch`
- [executed] `git log --oneline -n 12`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-03_phase_b_read_only_auth_pass.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-03_capital_risk_checklist.md`
- [executed] `Get-Content -Raw humanpending.md`
- [executed] `rg -n "class Config|API_KEY|API_SECRET|load_secrets|SANDBOX_MODE|SYMBOLS|USE_SCANNER_SYMBOLS|SCANNER_UNIVERSE_ENABLED|ENABLED_STRATEGIES|STRATEGY_ROUTER_POLICY|DRY_RUN|RISK_PER_TRADE|MAX_TOTAL_RISK" trader/config.py`
- [executed] `Get-Content trader/config.py | Select-Object -First 280`
- [executed] `Get-Content trader/infrastructure/api_client.py | Select-Object -First 240`
- [executed] `Get-Content trader/execution/order_engine.py | Select-Object -First 260`
- [executed] `rg -n "DRY_RUN|dry-run|Config\\.load_secrets|create_order|close_position|cancel|set_leverage|execution_filled|TRADE_OPEN|positions\\.json|PositionManager|performance\\.db|strategy_runtime_funnel|signed_request|OrderExecutionEngine|Futures" trader/bot.py`
- [executed] `Get-Content trader/bot.py | Select-Object -Skip 60 -First 180`
- [executed] `Get-Content trader/bot.py | Select-Object -Skip 470 -First 80`
- [executed] `Get-Content trader/bot.py | Select-Object -Skip 800 -First 150`
- [executed] `Get-Content trader/bot.py | Select-Object -Skip 960 -First 200`
- [executed] `Get-Content trader/bot.py | Select-Object -Skip 1320 -First 120`
- [executed] `ssh -i "$env:USERPROFILE\.ssh\codex_meshnet_ed25519" -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "ps -p 258894 -o pid=,etimes=,lstart=,args="`
- [executed] `ssh -i "$env:USERPROFILE\.ssh\codex_meshnet_ed25519" -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "readlink -f /proc/258894/cwd"`
- [executed] `ssh -i "$env:USERPROFILE\.ssh\codex_meshnet_ed25519" -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "git -C /proc/258894/cwd branch --show-current"`
- [executed] `ssh -i "$env:USERPROFILE\.ssh\codex_meshnet_ed25519" -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "cd /proc/258894/cwd && python3 -c 'from trader.config import Config; Config.validate(); print(chr(67)+chr(111)+chr(110)+chr(102)+chr(105)+chr(103)+chr(46)+chr(118)+chr(97)+chr(108)+chr(105)+chr(100)+chr(97)+chr(116)+chr(101)+chr(32)+chr(79)+chr(75))'"`
- [executed] remote `python3 -` read-only account snapshot script using `Config.load_secrets()` and signed `GET` only.
- [executed] remote `python3 -` read-only linkage scanner over `.log/runtime_observability/strategy_runtime_funnel.jsonl`, `.log/trades.log`, `.log/bot.log`, `.log/positions.json`, and read-only `performance.db`.
- [inspected] `AGENTS.md`
- [inspected] `reports/weekly_profit_2026-06-03_phase_b_read_only_auth_pass.md`
- [inspected] `reports/weekly_profit_2026-06-03_capital_risk_checklist.md`
- [inspected] `humanpending.md`
- [inspected] `trader/config.py`
- [inspected] `trader/infrastructure/api_client.py`
- [inspected] `trader/execution/order_engine.py`
- [inspected] `trader/bot.py`
- [inspected] rwUbuntu process metadata, branch metadata, and config validation.
- [inspected] sanitized signed read-only account snapshot from Demo/Testnet Futures.
- [inspected] remote runtime observability, bot log, trade log, positions persistence, and performance database linkage signals.
- [assumed] The Demo/Testnet position existed before this read-only reconciliation and was not caused by the checks in this task; this task did not inspect account activity outside the repo evidence files.

## Contract Impact

- Runtime: no runtime defaults changed; `trader/config.py` untouched.
- Risk: no risk defaults changed.
- Scanner: no scanner runtime universe activation or symbol-scope change.
- Research: no strategy, symbol, or threshold promotion.
- Execution: no order, cancel, close, reduce, hedge-mode mutation, margin-mode mutation, leverage mutation, or stateful lifecycle action.
- Process: PID `258894` was not stopped, restarted, or started.
- Credentials: no secrets created, edited, copied, deleted, committed, permission-mutated, or printed.
- Persistence: `.log/positions.json` and `performance.db` were read only; no files were altered on rwUbuntu.
- Docs: added this report only.

## Decision

Decision: `investigate`

Option B account state: `not clean`

V0 canary: `Hold`

Option C tiny testnet lifecycle: `not approved; blocked pending separate Ruei approval and account-state resolution`

Reason:

- The nonzero position is `BASUSDT`, a non-promoted symbol outside BTC/ETH runtime scope.
- There are no open orders, but the account still has an unrelated active testnet position.
- Local branch evidence does not link the position to this dry-run runtime.
- Before any option C lifecycle, Ruei/ops must resolve or explicitly accept the existing account state. No remediation was performed here.
