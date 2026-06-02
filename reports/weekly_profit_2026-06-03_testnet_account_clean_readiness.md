# Weekly Profit 2026-06-03 Testnet Account Clean Readiness

Date: 2026-06-03
Branch: `codex/post-promotion-control-20260430`
Status: `OPTION_B_ACCOUNT_STATE_CLEAN`

## Summary

- Executed read-only account-clean verification after Ruei reset the Binance Demo/Testnet account.
- Confirmed rwUbuntu dry-run source is alive and aligned: PID `258894`, command `python3 trader/bot.py --dry-run`, cwd `/proc/258894/cwd`, branch `codex/post-promotion-control-20260430`.
- `Config.validate()` passed from `/proc/258894/cwd`.
- Loaded credentials only through the normal repo `Config.load_secrets()` path.
- Confirmed the signed client base URL is exactly `https://demo-fapi.binance.com`.
- Performed only signed `GET` calls. No `POST`, `DELETE`, or `PUT` calls were made.
- All requested signed `GET` endpoints returned HTTP `200`.
- USDT balance is present; available balance was recorded only as bucket `5000-10000`.
- Hedge mode read result is `dualSidePosition=false`.
- Total nonzero positions count is `0`.
- Promoted-scope nonzero positions count is `0`.
- All open orders count is `0`; BTC and ETH open orders are both `0`; non-promoted open orders count is `0`.
- `.log/bot.log` and `.log/trades.log` tail scans showed `0` matching integrity signals in the last `3000` lines each.
- Option B account state is clean. V0 remains `Hold`; Option C tiny lifecycle still requires new explicit Ruei approval.

## Source

Runtime source:

| item | observed |
| --- | --- |
| host | `rwfunder@100.67.114.104` |
| PID | `258894` |
| process age at check | `883752` seconds |
| process start | `Fri May 22 11:51:06 2026` |
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

Inspected local files:

- `AGENTS.md`
- `reports/weekly_profit_2026-06-03_phase_b_read_only_auth_pass.md`
- `reports/weekly_profit_2026-06-03_testnet_position_reconciliation.md`
- `humanpending.md`
- `trader/config.py`
- `trader/infrastructure/api_client.py`

## Account-Clean Verification

Endpoint safety:

| item | result |
| --- | --- |
| secrets source | normal repo `Config.load_secrets()` path |
| `secrets.json` present | yes |
| secret values printed/copied | no |
| `Config.SANDBOX_MODE` | `True` |
| client base URL | `https://demo-fapi.binance.com` |
| exact Demo/Testnet URL confirmed | yes |
| live endpoint used | no |
| mutation attempted | no |

Signed read-only endpoint results:

| check | method | endpoint | HTTP status | pass/fail |
| --- | --- | --- | ---: | --- |
| balance read | `GET` | `/fapi/v2/balance` | 200 | pass |
| hedge mode read | `GET` | `/fapi/v1/positionSide/dual` | 200 | pass |
| position risk read | `GET` | `/fapi/v2/positionRisk` | 200 | pass |
| all open orders read | `GET` | `/fapi/v1/openOrders` | 200 | pass |
| BTC open orders read | `GET` | `/fapi/v1/openOrders?symbol=BTCUSDT` | 200 | pass |
| ETH open orders read | `GET` | `/fapi/v1/openOrders?symbol=ETHUSDT` | 200 | pass |

Sanitized account summary:

| item | result |
| --- | --- |
| signed GETs all HTTP `200` | yes |
| USDT balance presence | present |
| available balance bucket | `5000-10000` |
| hedge mode result | `dualSidePosition=false` |
| total nonzero positions count | `0` |
| nonzero promoted-scope positions count | `0` |
| all open orders count | `0` |
| BTC open orders count | `0` |
| ETH open orders count | `0` |
| non-promoted open orders count | `0` |
| clean verification pass | yes |

## Open Positions

| scope | count |
| --- | ---: |
| all symbols | 0 |
| promoted runtime scope: `BTCUSDT`, `ETHUSDT` | 0 |
| non-promoted symbols | 0 |

No close, reduce, or remediation was attempted.

## Open Orders

| scope | count |
| --- | ---: |
| all symbols | 0 |
| `BTCUSDT` | 0 |
| `ETHUSDT` | 0 |
| non-promoted symbols | 0 |

No cancel or order lifecycle action was attempted.

## Log Tail Integrity

Checked `.log/bot.log` and `.log/trades.log`, last `3000` lines each, for:

`auth|authentication|api key|invalid key|signature|permission|unauthorized|unauthorised|ERROR|Traceback|execution failure|execution_failure|unprotected|unprotected position|exception|failed`

Result:

| log | exists | tail lines scanned | match count |
| --- | --- | ---: | ---: |
| `.log/bot.log` | yes | 3000 | 0 |
| `.log/trades.log` | yes | 3000 | 0 |

## Verification

- [executed] `Get-Content -Raw AGENTS.md`
- [executed] `git status --short --branch`
- [executed] `git log --oneline -n 12`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-03_phase_b_read_only_auth_pass.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-03_testnet_position_reconciliation.md`
- [executed] `Get-Content -Raw humanpending.md`
- [executed] `rg -n "class Config|API_KEY|API_SECRET|load_secrets|SANDBOX_MODE|SYMBOLS|USE_SCANNER_SYMBOLS|SCANNER_UNIVERSE_ENABLED|ENABLED_STRATEGIES|STRATEGY_ROUTER_POLICY|DRY_RUN|RISK_PER_TRADE|MAX_TOTAL_RISK" trader/config.py trader/infrastructure/api_client.py`
- [executed] `Get-Content trader/config.py | Select-Object -First 280`
- [executed] `Get-Content trader/infrastructure/api_client.py | Select-Object -First 180`
- [executed] `ssh -i "$env:USERPROFILE\.ssh\codex_meshnet_ed25519" -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "ps -p 258894 -o pid=,etimes=,lstart=,args="`
- [executed] `ssh -i "$env:USERPROFILE\.ssh\codex_meshnet_ed25519" -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "readlink -f /proc/258894/cwd"`
- [executed] `ssh -i "$env:USERPROFILE\.ssh\codex_meshnet_ed25519" -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "git -C /proc/258894/cwd branch --show-current"`
- [executed] `ssh -i "$env:USERPROFILE\.ssh\codex_meshnet_ed25519" -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "cd /proc/258894/cwd && python3 -c 'from trader.config import Config; Config.validate(); print(chr(67)+chr(111)+chr(110)+chr(102)+chr(105)+chr(103)+chr(46)+chr(118)+chr(97)+chr(108)+chr(105)+chr(100)+chr(97)+chr(116)+chr(101)+chr(32)+chr(79)+chr(75))'"`
- [executed] remote `python3 -` read-only account-clean verification script using `Config.load_secrets()` and signed `GET` only.
- [executed] remote `python3 -` read-only log-tail scanner over `.log/bot.log` and `.log/trades.log`.
- [inspected] `AGENTS.md`
- [inspected] `reports/weekly_profit_2026-06-03_phase_b_read_only_auth_pass.md`
- [inspected] `reports/weekly_profit_2026-06-03_testnet_position_reconciliation.md`
- [inspected] `humanpending.md`
- [inspected] `trader/config.py`
- [inspected] `trader/infrastructure/api_client.py`
- [inspected] rwUbuntu process metadata, branch metadata, and config validation.
- [inspected] sanitized signed read-only account-clean snapshot from Demo/Testnet Futures.
- [inspected] `.log/bot.log` tail, last `3000` lines.
- [inspected] `.log/trades.log` tail, last `3000` lines.
- [assumed] Ruei reset the Demo/Testnet account out-of-band as stated; this task verified the resulting exchange state but did not inspect the reset operation itself.

## Contract Impact

- Runtime: no runtime defaults changed; `trader/config.py` untouched.
- Risk: no risk defaults changed.
- Scanner: no scanner runtime universe activation or symbol-scope change.
- Research: no strategy, symbol, or threshold promotion.
- Execution: no order, cancel, close, reduce, hedge-mode mutation, margin-mode mutation, leverage mutation, or stateful lifecycle action.
- Process: PID `258894` was not stopped, restarted, or started.
- Credentials: no secrets created, edited, copied, deleted, committed, permission-mutated, or printed.
- Docs: added this report only.

## Decision

Decision: `Option B account state clean`

V0 canary: `Hold`

Option C tiny lifecycle: `not approved; requires new explicit Ruei approval`

Reason:

- Signed read-only authentication still passes against Binance Demo/Testnet Futures.
- Account-clean criteria are satisfied: all signed GETs returned HTTP `200`, no nonzero positions exist, and all checked open-order counts are `0`.
- This is readiness evidence only. It does not approve testnet order lifecycle, live canary, order creation, cancel, leverage setting, hedge/margin mutation, scanner runtime universe activation, or runtime default drift.
