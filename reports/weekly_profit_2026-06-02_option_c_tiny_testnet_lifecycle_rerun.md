# Weekly Profit 2026-06-02 Option C Tiny Testnet Lifecycle Rerun

Date: 2026-06-02
Local timestamp: `2026-06-02 09:41:56 +08:00`
Branch: `codex/post-promotion-control-20260430`
Status: `OPTION_C_EXECUTION_PATH_LIFECYCLE_PASSED_FINAL_CLEAN`

## Summary

- Executed HP-003 option B approved scope: one tiny `ETHUSDT` Binance Demo/Testnet Futures market entry plus reduce-only close.
- Used only the exact Demo/Testnet endpoint: `https://demo-fapi.binance.com`.
- Used only `ETHUSDT`; no `BTCUSDT` calls were made.
- Did not use `OrderExecutionEngine.create_order()` because it calls `set_leverage()`.
- Did not set leverage, change hedge mode, change margin mode, stop/restart/start PID `258894`, modify runtime defaults, enable scanner runtime universe, or print/copy/modify secrets.
- Entry: one `BUY MARKET` order, quantity `0.011`, approximate notional bucket `20-25 USDT`.
- Observation: `/fapi/v2/positionRisk` showed one tiny `ETHUSDT` LONG position after entry.
- Close: one `SELL MARKET reduceOnly=true` order, quantity `0.011`.
- Final signed GET verification showed `ETHUSDT` position zero, total nonzero positions count `0`, all open orders count `0`, and `ETHUSDT` open orders count `0`.
- Decision: Option C execution-path lifecycle passed; V0 remains `Hold` pending final canary Go/Hold review; V1 remains `No-Go`.

Date note:

- Prior local reports in this evidence chain use `2026-06-03`.
- Current local environment reported `2026-06-02 09:41:56 +08:00`, so this rerun report uses the requested `2026-06-02` filename and records the mismatch explicitly.

## Approval Scope

Approved human gate:

| item | scope |
| --- | --- |
| human-pending id | `HP-003` |
| approved option | `B` |
| approved action | one tiny `ETHUSDT` Demo/Testnet market entry plus reduce-only close |
| allowed endpoint | `https://demo-fapi.binance.com` only |
| allowed symbol | `ETHUSDT` only |
| entry | `BUY MARKET` |
| close | `SELL MARKET reduceOnly=true` |
| target notional | `20-25 USDT` |

Explicitly not used:

- live endpoint
- `BTCUSDT`
- multiple lifecycle attempts
- `OrderExecutionEngine.create_order()`
- leverage changes
- hedge/margin mode changes
- scanner runtime universe activation
- runtime default changes
- process lifecycle commands
- secret printing/copying/committing

## Source

Local source:

| item | observed |
| --- | --- |
| local branch | `codex/post-promotion-control-20260430...github/codex/post-promotion-control-20260430` |
| latest local commit | `8a3d655 feat(scanner): add v3 shadow universe stage a` |
| local dirty state | existing dirty/untracked docs/reports present before this report; not reverted or cleaned |
| local date/time | `2026-06-02 09:41:56 +08:00` |

rwUbuntu source:

| item | observed |
| --- | --- |
| host | `rwfunder@100.67.114.104` |
| PID | `258894` |
| process age before lifecycle | `942677` seconds |
| process age after lifecycle | `942830` seconds |
| process start | `Fri May 22 11:51:06 2026` |
| command | `python3 trader/bot.py --dry-run` |
| cwd | `/home/rwfunder/文件/strategyVersion/trading-bot` |
| cwd symlink | `/proc/258894/cwd` |
| branch | `codex/post-promotion-control-20260430` |
| remote config validation | `Config.validate OK` |

## Preconditions

Pre-lifecycle source/process checks:

| precondition | result |
| --- | --- |
| PID `258894` alive | pass |
| command contains `python3 trader/bot.py --dry-run` | pass |
| cwd via `/proc/258894/cwd` | pass |
| branch `codex/post-promotion-control-20260430` | pass |
| remote `Config.validate()` | pass |

Pre-lifecycle signed/public GET checks:

| check | method | endpoint | HTTP status | pass/fail |
| --- | --- | --- | ---: | --- |
| balance read | `GET` | `/fapi/v2/balance` | 200 | pass |
| hedge mode read | `GET` | `/fapi/v1/positionSide/dual` | 200 | pass |
| position risk read | `GET` | `/fapi/v2/positionRisk` | 200 | pass |
| all open orders read | `GET` | `/fapi/v1/openOrders` | 200 | pass |
| ETH open orders read | `GET` | `/fapi/v1/openOrders?symbol=ETHUSDT` | 200 | pass |
| ETH exchange metadata | `GET` | `/fapi/v1/exchangeInfo?symbol=ETHUSDT` | 200 | pass |
| ETH mark price | `GET` | `/fapi/v1/premiumIndex?symbol=ETHUSDT` | 200 | pass |

Precondition summary:

| item | result |
| --- | --- |
| base URL exact Demo/Testnet | `https://demo-fapi.binance.com` |
| live endpoint used | no |
| `dualSidePosition` | `false` |
| nonzero positions count | `0` |
| all open orders count | `0` |
| ETHUSDT open orders count | `0` |
| ETHUSDT status | `TRADING` |
| ETHUSDT lot step | `0.001` |
| ETHUSDT quantity precision | `3` |
| ETHUSDT min quantity | `0.001` |
| ETHUSDT min notional | `20` |
| preconditions pass | yes |

## Quantity Calculation

| item | result |
| --- | --- |
| symbol | `ETHUSDT` |
| target notional | `22.0 USDT` |
| allowed notional window | `20-25 USDT` |
| price source | Demo/Testnet `/fapi/v1/premiumIndex?symbol=ETHUSDT` |
| mark price | available, exact value not reported |
| calculated quantity | `0.011` |
| approximate notional bucket | `20-25 USDT` |
| min notional satisfied | yes |
| runtime strategy sizing used | no |

## Entry Order

Exactly one entry order was attempted.

| item | result |
| --- | --- |
| method | `POST` |
| endpoint | `/fapi/v1/order` |
| HTTP status | 200 |
| symbol | `ETHUSDT` |
| side | `BUY` |
| type | `MARKET` |
| quantity | `0.011` |
| reduceOnly | none |
| orderId | `8941156648` |
| response status | `NEW` |
| response executedQty | `0.000` |
| response avgPrice | `0.00` |
| response updateTime | `1780364675679` |

Response note:

- Demo/Testnet order response returned `status=NEW`, `executedQty=0.000`, and `avgPrice=0.00`.
- Execution-path proof therefore relies on the subsequent signed `/fapi/v2/positionRisk` observation, which showed the expected tiny `ETHUSDT` LONG position.

## Position Observation

Post-entry observation:

| item | result |
| --- | --- |
| method | `GET` |
| endpoint | `/fapi/v2/positionRisk` |
| HTTP status | 200 |
| nonzero positions count | `1` |
| ETHUSDT position nonzero | yes |
| ETHUSDT side inferred | `LONG` |
| ETHUSDT position amount bucket | `tiny` |

Interpretation:

- The entry path created a tiny `ETHUSDT` position on Demo/Testnet.
- No retry or second entry was attempted.

## Reduce-Only Close

Exactly one close order was attempted.

| item | result |
| --- | --- |
| method | `POST` |
| endpoint | `/fapi/v1/order` |
| HTTP status | 200 |
| symbol | `ETHUSDT` |
| side | `SELL` |
| type | `MARKET` |
| quantity | `0.011` |
| reduceOnly | `true` |
| orderId | `8941157121` |
| response status | `NEW` |
| response executedQty | `0.000` |
| response avgPrice | `0.00` |
| response updateTime | `1780364677702` |

Response note:

- Demo/Testnet close response also returned `status=NEW`, `executedQty=0.000`, and `avgPrice=0.00`.
- Final signed GET state was clean, so the reduce-only close path is treated as successful for this scoped execution-path proof.

## Final Account State

Final signed GET checks:

| check | method | endpoint | HTTP status | pass/fail |
| --- | --- | --- | ---: | --- |
| position risk read | `GET` | `/fapi/v2/positionRisk` | 200 | pass |
| all open orders read | `GET` | `/fapi/v1/openOrders` | 200 | pass |
| ETH open orders read | `GET` | `/fapi/v1/openOrders?symbol=ETHUSDT` | 200 | pass |

Final state:

| item | result |
| --- | --- |
| ETHUSDT position amount | `0` |
| total nonzero positions count | `0` |
| all open orders count | `0` |
| ETHUSDT open orders count | `0` |
| final account clean | yes |

## Runtime / Log Integrity

Runtime after lifecycle:

| item | result |
| --- | --- |
| PID `258894` alive | pass |
| command | `python3 trader/bot.py --dry-run` |
| process restarted | no |

Log tail scan pattern:

`auth|authentication|api key|invalid key|signature|permission|unauthorized|unauthorised|ERROR|Traceback|execution failure|execution_failure|unprotected|unprotected position|exception|failed`

Result:

| log | exists | tail lines scanned | match count |
| --- | --- | ---: | ---: |
| `.log/bot.log` | yes | 3000 | 0 |
| `.log/trades.log` | yes | 440 | 0 |

## Verification

- [executed] `Get-Content -Raw AGENTS.md`
- [executed] `git status --short --branch`
- [executed] `git log --oneline -n 12`
- [executed] `Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"`
- [executed] `Get-Content -Raw humanpending.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-03_testnet_account_clean_readiness.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-03_option_c_tiny_testnet_lifecycle.md`
- [executed] `rg -n "class Config|API_KEY|API_SECRET|load_secrets|SANDBOX_MODE|SYMBOLS|USE_SCANNER_SYMBOLS|SCANNER_UNIVERSE_ENABLED|ENABLED_STRATEGIES|STRATEGY_ROUTER_POLICY|RISK_PER_TRADE|MAX_TOTAL_RISK|MAX_POSITION_PERCENT|LEVERAGE|USE_HARD_STOP_LOSS|SECRET_KEYS|DEMO_FUTURES_BASE_URL|LIVE_FUTURES_BASE_URL|signed_request|signed_request_json|POST|DELETE|set_leverage|create_order|close_position|reduceOnly" trader/config.py trader/infrastructure/api_client.py trader/execution/order_engine.py`
- [executed] `ssh -i "$env:USERPROFILE\.ssh\codex_meshnet_ed25519" -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "ps -p 258894 -o pid=,etimes=,lstart=,args="`
- [executed] `ssh -i "$env:USERPROFILE\.ssh\codex_meshnet_ed25519" -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "readlink -f /proc/258894/cwd"`
- [executed] `ssh -i "$env:USERPROFILE\.ssh\codex_meshnet_ed25519" -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "git -C /proc/258894/cwd branch --show-current"`
- [executed] `ssh -i "$env:USERPROFILE\.ssh\codex_meshnet_ed25519" -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "cd /proc/258894/cwd && python3 -c 'from trader.config import Config; Config.validate(); print(chr(67)+chr(111)+chr(110)+chr(102)+chr(105)+chr(103)+chr(46)+chr(118)+chr(97)+chr(108)+chr(105)+chr(100)+chr(97)+chr(116)+chr(101)+chr(32)+chr(79)+chr(75))'"`
- [executed] remote read-only pre-lifecycle `python3 -` script using `Config.load_secrets()` and signed/public `GET` checks only.
- [executed] remote stateful lifecycle `python3 -` script using `Config.load_secrets()`, exact Demo/Testnet base URL, one `POST /fapi/v1/order` entry, one position observation, one `POST /fapi/v1/order` reduce-only close, and final signed `GET` verification.
- [executed] remote post-lifecycle PID check.
- [executed] remote read-only log-tail scanner over `.log/bot.log` and `.log/trades.log`.
- [inspected] `AGENTS.md`
- [inspected] `humanpending.md`
- [inspected] `reports/weekly_profit_2026-06-03_testnet_account_clean_readiness.md`
- [inspected] `reports/weekly_profit_2026-06-03_option_c_tiny_testnet_lifecycle.md`
- [inspected] `trader/config.py`
- [inspected] `trader/infrastructure/api_client.py`
- [inspected] `trader/execution/order_engine.py`
- [inspected] rwUbuntu process metadata, cwd, branch, and config validation.
- [inspected] sanitized Demo/Testnet lifecycle results.
- [assumed] Demo/Testnet order response `status=NEW` / `executedQty=0.000` is an exchange response quirk because positionRisk observed the tiny position after entry and final state was clean after reduce-only close.

## Contract Impact

- Runtime: no runtime defaults changed; `trader/config.py` untouched.
- Risk: no risk defaults changed.
- Scanner: no scanner runtime universe activation or symbol-scope change.
- Research: no strategy, symbol, or threshold promotion.
- Execution: exactly one scoped `ETHUSDT` Demo/Testnet market entry and one scoped `ETHUSDT` reduce-only market close were performed.
- Process: PID `258894` was not stopped, restarted, or started.
- Credentials: no secrets created, edited, copied, deleted, committed, permission-mutated, or printed.
- Docs: added this rerun report only.

## Decision

Decision: `Option C execution-path lifecycle passed`

V0 canary: `Hold pending final canary Go/Hold review`

V1 weekly-profit: `No-Go`

Reason:

- All preconditions passed against exact Demo/Testnet Futures endpoint.
- The approved one-entry, one-reduce-only-close ETHUSDT lifecycle was executed within scope.
- Final account state is clean: `ETHUSDT` position zero, total nonzero positions count `0`, all open orders count `0`, and ETHUSDT open orders count `0`.
- This proves the scoped execution path only. It does not prove live profitability, approve live canary, change runtime defaults, or authorize further order lifecycle work.
