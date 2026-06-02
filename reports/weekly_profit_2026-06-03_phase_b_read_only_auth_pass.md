# Weekly Profit 2026-06-03 Phase B Read-Only Auth Pass

Date: 2026-06-03
Branch: `codex/post-promotion-control-20260430`
Status: `OPTION_B_SIGNED_GET_PASS_INVESTIGATE_OPEN_POSITION`

## Summary

- Re-ran HP-001 option B as read-only authenticated checks only.
- Confirmed rwUbuntu dry-run source is alive and aligned: PID `258894`, command `python3 trader/bot.py --dry-run`, cwd `/home/rwfunder/文件/strategyVersion/trading-bot`, branch `codex/post-promotion-control-20260430`.
- `Config.validate()` passed from `/proc/258894/cwd`.
- `secrets.json` is present in `/proc/258894/cwd`; canonical `API_KEY` and `API_SECRET` keys are present and non-empty under the repo's `Config.load_secrets()` upper-case key normalization behavior.
- Confirmed the signed client is pointed at Binance Demo/Testnet Futures: `https://demo-fapi.binance.com`. No live endpoint was used.
- Signed private `GET` checks passed with HTTP `200` for balance, hedge-mode read, position risk, and BTC/ETH open-order reads.
- USDT balance is present; available balance was recorded only as bucket `1000+`, not as an exact amount.
- Hedge mode read result: `dualSidePosition=false`.
- BTC and ETH open order counts are both `0`.
- Position risk read returned `nonzero_positions_count=1`; per HP-001 rules, no close/cancel/remediation was attempted and readiness decision is `investigate`.
- `.log/bot.log` and `.log/trades.log` tail scans showed no matching auth, signature, permission, traceback, execution failure, unprotected-position, exception, or failed signals in the last `3000` lines each.
- No order, cancel, hedge-mode mutation, margin-mode mutation, leverage change, process lifecycle action, scanner activation, runtime config change, credential edit, credential copy, or secret value print was performed.

## Source

Runtime source:

| item | observed |
| --- | --- |
| host | `rwfunder@100.67.114.104` |
| PID | `258894` |
| process age at check | `873631` seconds |
| command | `python3 trader/bot.py --dry-run` |
| cwd | `/home/rwfunder/文件/strategyVersion/trading-bot` |
| cwd symlink used for commands | `/proc/258894/cwd` |
| branch | `codex/post-promotion-control-20260430` |
| config validation | `Config.validate OK` |

Local preflight:

| item | observed |
| --- | --- |
| local branch | `codex/post-promotion-control-20260430...github/codex/post-promotion-control-20260430` |
| local dirty state | existing dirty/untracked docs/reports present before this report; not reverted or cleaned |
| latest local commit | `8a3d655 feat(scanner): add v3 shadow universe stage a` |

Local evidence inspected:

- `AGENTS.md`
- `humanpending.md`
- `reports/weekly_profit_2026-06-03_phase_b_read_only_auth_rerun.md`
- `reports/weekly_profit_2026-06-03_capital_risk_checklist.md`
- `trader/config.py`
- `trader/infrastructure/api_client.py`
- `trader/execution/order_engine.py`

## Credential Presence

Credential contract from code:

- `trader/config.py` whitelists `API_KEY` and `API_SECRET` as secrets.
- `Config.load_secrets()` loads credentials only from external `secrets.json`.
- `Config.load_secrets()` normalizes input key names with `str(key).upper()` before matching `SECRET_KEYS`.
- `BinanceFuturesClient` receives credentials from `Config` and does not read secrets by itself.

Observed on rwUbuntu `/proc/258894/cwd`:

| item | result |
| --- | --- |
| `secrets.json` | present |
| exact `API_KEY` key | absent |
| exact `API_SECRET` key | absent |
| canonical `API_KEY` after upper-case normalization | present, non-empty |
| canonical `API_SECRET` after upper-case normalization | present, non-empty |
| `Config.load_secrets()` usable for signed GET | yes, confirmed by authenticated HTTP `200` responses |

No secret values were printed, copied, edited, created, deleted, committed, or permission-mutated.

## Endpoint Safety

Code path inspected:

- `Config.SANDBOX_MODE=True`.
- `BinanceFuturesClient(..., sandbox=Config.SANDBOX_MODE)` selected `DEMO_FUTURES_BASE_URL`.
- Observed client base URL: `https://demo-fapi.binance.com`.
- Live URL `https://fapi.binance.com` was not used.

Allowed calls performed:

- Signed `GET` only.
- No `POST`, `DELETE`, or `PUT`.
- No order lifecycle.
- No cancel lifecycle.
- No hedge-mode, margin-mode, or leverage mutation.

## Authenticated Read-Only Checks

| check | method | endpoint | HTTP status | pass/fail | authenticated |
| --- | --- | --- | ---: | --- | --- |
| balance read | `GET` | `/fapi/v2/balance` | 200 | pass | yes |
| hedge mode read | `GET` | `/fapi/v1/positionSide/dual` | 200 | pass | yes |
| position risk read | `GET` | `/fapi/v2/positionRisk` | 200 | pass | yes |
| BTC open orders read | `GET` | `/fapi/v1/openOrders?symbol=BTCUSDT` | 200 | pass | yes |
| ETH open orders read | `GET` | `/fapi/v1/openOrders?symbol=ETHUSDT` | 200 | pass | yes |

Sanitized account summary:

| item | result |
| --- | --- |
| signed private GETs passed | yes |
| USDT balance presence | present |
| available balance bucket | `1000+` |
| hedge mode read result | `dualSidePosition=false` |
| nonzero positions count | `1` |
| BTC open orders count | `0` |
| ETH open orders count | `0` |
| sanitized error category | none |

## Account / Position / Order Readiness

| readiness item | result |
| --- | --- |
| authenticated account read | pass |
| USDT balance presence | pass |
| hedge mode read | pass, `dualSidePosition=false` |
| open positions | investigate: `nonzero_positions_count=1` |
| BTC open orders | pass, count `0` |
| ETH open orders | pass, count `0` |
| surprise positions/orders | position surprise present; no remediation attempted |

Interpretation:

- HP-001 option B signed read-only authentication passed.
- Account readiness is not clean because one nonzero position exists.
- Per task boundary, the position was not closed, reduced, modified, or otherwise handled.
- Option C tiny testnet order lifecycle remains blocked until Ruei separately approves it and the existing position is reconciled.

## Log Tail Integrity

Checked `.log/bot.log` and `.log/trades.log`, last `3000` lines each, for:

`auth|authentication|api key|invalid key|signature|permission|unauthorized|unauthorised|ERROR|Traceback|execution failure|execution_failure|unprotected|unprotected position|exception|failed`

Result:

| log | exists | tail lines scanned | match count | category summary |
| --- | --- | ---: | ---: | --- |
| `.log/bot.log` | yes | 3000 | 0 | no matching tail signals |
| `.log/trades.log` | yes | 3000 | 0 | no matching tail signals |

## Verification

- [executed] `Get-Content -Raw AGENTS.md`
- [executed] `git status --short --branch`
- [executed] `git log --oneline -n 12`
- [executed] `Get-Content -Raw humanpending.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-03_phase_b_read_only_auth_rerun.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-03_capital_risk_checklist.md`
- [executed] `rg -n "class Config|API_KEY|API_SECRET|load_secrets|TESTNET|testnet|demo|BINANCE|FUTURES|fapi|BASE_URL|Config.validate|USE_SCANNER_SYMBOLS|SCANNER_UNIVERSE_ENABLED|ENABLED_STRATEGIES|SYMBOLS|RISK_PER_TRADE|MAX_TOTAL_RISK" trader/config.py trader/infrastructure/api_client.py trader/execution/order_engine.py`
- [executed] `Get-Content trader/config.py | Select-Object -First 280`
- [executed] `Get-Content trader/infrastructure/api_client.py | Select-Object -First 240`
- [executed] `Get-Content trader/execution/order_engine.py | Select-Object -First 260`
- [executed] `ssh -i "$env:USERPROFILE\.ssh\codex_meshnet_ed25519" -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "ps -p 258894 -o pid=,etimes=,args="`
- [executed] `ssh -i "$env:USERPROFILE\.ssh\codex_meshnet_ed25519" -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "readlink -f /proc/258894/cwd"`
- [executed] `ssh -i "$env:USERPROFILE\.ssh\codex_meshnet_ed25519" -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "git -C /proc/258894/cwd branch --show-current"`
- [executed] `ssh -i "$env:USERPROFILE\.ssh\codex_meshnet_ed25519" -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "cd /proc/258894/cwd && python3 -c 'from trader.config import Config; Config.validate(); print(chr(67)+chr(111)+chr(110)+chr(102)+chr(105)+chr(103)+chr(46)+chr(118)+chr(97)+chr(108)+chr(105)+chr(100)+chr(97)+chr(116)+chr(101)+chr(32)+chr(79)+chr(75))'"`
- [executed] remote `python3 -` read-only script checking `secrets.json`, exact `API_KEY` / `API_SECRET`, and canonical upper-case key presence without printing values.
- [executed] remote `python3 -` read-only script loading secrets through `Config.load_secrets()`, confirming Demo/Testnet Futures base URL, then calling only signed `GET` endpoints listed in this report.
- [executed] remote `python3 -` read-only log-tail scanner over `.log/bot.log` and `.log/trades.log`.
- [inspected] `AGENTS.md`
- [inspected] `humanpending.md`
- [inspected] `reports/weekly_profit_2026-06-03_phase_b_read_only_auth_rerun.md`
- [inspected] `reports/weekly_profit_2026-06-03_capital_risk_checklist.md`
- [inspected] `trader/config.py`
- [inspected] `trader/infrastructure/api_client.py`
- [inspected] `trader/execution/order_engine.py`
- [inspected] rwUbuntu process metadata and git branch metadata.
- [inspected] signed read-only sanitized endpoint results from Demo/Testnet Futures.
- [inspected] `.log/bot.log` tail, last `3000` lines.
- [inspected] `.log/trades.log` tail, last `3000` lines.
- [assumed] Ruei provisioned the `secrets.json` file out-of-band as stated; this report did not inspect secret values or verify the provisioning path.

## Contract Impact

- Runtime: no runtime defaults changed; `trader/config.py` untouched.
- Risk: no risk defaults changed.
- Scanner: no scanner runtime universe activation or symbol-scope change.
- Research: no strategy, symbol, or threshold promotion.
- Execution: no order, cancel, hedge-mode mutation, margin-mode mutation, leverage mutation, or stateful lifecycle action.
- Process: PID `258894` was not stopped, restarted, or started.
- Credentials: no secrets created, edited, copied, deleted, committed, permission-mutated, or printed.
- Docs: added this report only.

## Decision

Decision: `investigate`

Option B endpoint result: `passed`

V0 canary: `Hold`

Option C tiny testnet lifecycle: `not approved; blocked pending separate Ruei approval and position reconciliation`

Reason:

- Signed authenticated `GET` checks succeeded against Binance Demo/Testnet Futures only.
- No BTC or ETH open orders were found.
- One nonzero position exists in position risk. Per HP-001 safety rules, this requires investigation/reconciliation before any option C lifecycle can be considered.
- This remains read-only evidence. It does not approve live canary, testnet order lifecycle, order creation, cancel, leverage setting, hedge/margin mutation, scanner runtime universe activation, or runtime default drift.
