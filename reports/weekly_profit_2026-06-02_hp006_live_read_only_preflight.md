# Weekly Profit 2026-06-02 HP-006 Live Read-Only Preflight

Date: 2026-06-02
Local timestamp: `2026-06-02 14:54:44 +08:00`
Branch: `codex/post-promotion-control-20260430`
Status: `HP006_READ_ONLY_PREFLIGHT_FAILED_LIVE_CREDENTIALS_AND_ACTIVATION_HOST_BLOCKERS`

## Summary

- Executed HP-006 option `B`: final read-only live preflight only.
- No actual live activation was performed.
- No order, cancel, close, set-leverage, hedge/margin mutation, or process
  lifecycle action was performed.
- Local HP-005 code path correctly selected live mode process-locally:
  `Config.SANDBOX_MODE=False`, `Config.DRY_RUN=False`, endpoint
  `https://fapi.binance.com`.
- Public live Futures `exchangeInfo` read succeeded for `BTCUSDT` and
  `ETHUSDT`.
- Signed live `GET` checks failed with HTTP `401`, Binance error `-2014`
  (`API-key format invalid`).
- Local repo-root `secrets.json` was not present; live credentials are not
  provisioned/validated in this local activation context.
- rwUbuntu dry-run observer is alive and config-valid, but the remote observer
  checkout did not show HP-005 `--live` / leverage-gate remediation in the
  inspected files.
- Decision: `Hold`; actual V0 live activation remains blocked.

Important interpretation:

- Because signed live account reads failed, live account cleanliness is not
  verified. Do not infer clean positions/orders from empty parsed payloads.
- This preflight proves the local live endpoint selection path, not live account
  readiness.

## Scope

HP-006=B allowed:

- read local repo state and config
- confirm HP-005 remediation behavior
- perform public live Futures metadata `GET`
- perform signed live Futures `GET` only if credentials are available
- inspect rwUbuntu process/code state read-only
- write a report and human blocker

HP-006=B did not allow:

- actual `python3 trader/bot.py --live` activation
- order / cancel / close
- set leverage
- hedge mode or margin mode mutation
- process stop / restart / start
- credential value printing / copying / editing / committing

## Local Repo / Mode Preflight

| item | result |
| --- | --- |
| `Config.validate()` | pass |
| local `--live` mode effect | `DRY_RUN=False`, `SANDBOX_MODE=False` |
| local live endpoint | `https://fapi.binance.com` |
| `trader/config.py` defaults changed | no |
| scanner runtime universe | disabled |
| router policy | `fail_closed` |
| mutation attempted | no |

Runtime contract remained:

- `SYMBOLS=['BTC/USDT', 'ETH/USDT']`
- `USE_SCANNER_SYMBOLS=False`
- `SCANNER_UNIVERSE_ENABLED=False`
- `STRATEGY_ROUTER_POLICY='fail_closed'`
- risk defaults unchanged

## Public Live Metadata

Public endpoint:

- `GET https://fapi.binance.com/fapi/v1/exchangeInfo`
- HTTP status: `200`

Sanitized symbols:

| symbol | status | qty precision | price precision | lot step | market lot step | min notional |
| --- | --- | ---: | ---: | --- | --- | ---: |
| `BTCUSDT` | `TRADING` | 3 | 2 | `0.001` | `0.001` | 50 |
| `ETHUSDT` | `TRADING` | 3 | 2 | `0.001` | `0.001` | 20 |

Public metadata is useful but not sufficient for live activation. Account-level
signed reads still failed.

## Signed Live GET Results

Base URL exact:

```text
https://fapi.binance.com
```

Signed read-only calls attempted:

| check | method | endpoint | HTTP status | result |
| --- | --- | --- | ---: | --- |
| balance | `GET` | `/fapi/v2/balance` | 401 | fail: `-2014 API-key format invalid` |
| position mode | `GET` | `/fapi/v1/positionSide/dual` | 401 | fail: `-2014 API-key format invalid` |
| position risk | `GET` | `/fapi/v2/positionRisk` | 401 | fail: `-2014 API-key format invalid` |
| all open orders | `GET` | `/fapi/v1/openOrders` | 401 | fail: `-2014 API-key format invalid` |
| BTC open orders | `GET` | `/fapi/v1/openOrders?symbol=BTCUSDT` | 401 | fail: `-2014 API-key format invalid` |
| ETH open orders | `GET` | `/fapi/v1/openOrders?symbol=ETHUSDT` | 401 | fail: `-2014 API-key format invalid` |

Credential presence:

| item | result |
| --- | --- |
| local repo-root `secrets.json` | absent |
| canonical API key object present in process | yes, but live signed GET failed |
| canonical API secret object present in process | yes, but live signed GET failed |
| secret values printed | no |

Interpretation:

- The local activation context does not have validated live credentials.
- The process-level placeholders/defaults are not sufficient.
- Live account balance, position mode, positions, and open orders remain
  unverified.

## Activation Host Read-Only Check

rwUbuntu observer:

| item | result |
| --- | --- |
| SSH | pass |
| PID | `258894` alive |
| command | `python3 trader/bot.py --dry-run` |
| cwd | `/home/rwfunder/文件/strategyVersion/trading-bot` |
| branch | `codex/post-promotion-control-20260430` |
| remote `Config.validate()` | pass |
| process mutation | none |

Activation-host remediation check:

- Read-only grep found no `--live`, `allow-live-leverage`, or
  `parse_runtime_args` matches in remote `trader/bot.py` /
  `trader/execution/order_engine.py`.

Interpretation:

- The rwUbuntu observer remains healthy as dry-run evidence source.
- The inspected remote checkout is not yet proven to contain HP-005 remediation.
- Actual activation on rwUbuntu is blocked until the approved remediation code
  is intentionally deployed/verified there.

## Remaining Blockers

| blocker | status | unblock condition |
| --- | --- | --- |
| live credentials | blocked | provision valid live Binance Futures credentials in approved activation host repo-root `secrets.json`, without printing or committing values |
| signed live reads | blocked | rerun HP-006 signed live `GET` checks and receive HTTP `200` |
| live account cleanliness | not verified | signed live reads prove positions `0` and open orders `0` |
| activation host code | blocked | deploy/verify HP-005 remediation on the approved activation host |
| process-control plan | blocked | record exact start/stop/monitoring commands before actual live activation |
| actual live activation | not approved | requires later explicit human gate after clean preflight |

## Verification

- [executed] `Get-Content -Raw AGENTS.md`
- [executed] `git status --short --branch`
- [executed] `git log --oneline -n 12`
- [executed] `Get-Content -Raw humanpending.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-02_hp005_live_mode_leverage_remediation.md`
- [executed] `Get-Content -Raw reports/weekly_profit_2026-06-02_v0_canary_activation_runbook.md`
- [executed] `python -c "from trader.config import Config; Config.validate(); print('Config.validate OK')"`
- [executed] `rg -n -- "STRATEGY_RUNTIME_ENABLED|ENABLED_STRATEGIES|SYMBOLS|USE_SCANNER_SYMBOLS|SCANNER_UNIVERSE_ENABLED|STRATEGY_ROUTER_POLICY|RISK_PER_TRADE|MAX_TOTAL_RISK|MAX_POSITION_PERCENT|MAX_SL_DISTANCE_PCT|LEVERAGE|USE_HARD_STOP_LOSS|SANDBOX_MODE|DRY_RUN" trader/config.py`
- [executed] `rg -n -- "--live|allow-live-leverage|apply_runtime_mode_args|parse_runtime_args|Config.load_secrets|BinanceFuturesClient|set_leverage|scanner_feed" trader/bot.py trader/execution/order_engine.py trader/infrastructure/api_client.py`
- [executed] local read-only Python preflight using `parse_runtime_args(['--live'])`, `Config.load_secrets()`, public live `exchangeInfo`, and signed live `GET` only.
- [executed] SSH read-only rwUbuntu PID/cwd/branch check.
- [executed] remote `Config.validate()` from `/proc/258894/cwd`.
- [executed] remote read-only grep for HP-005 remediation markers.
- [inspected] `AGENTS.md`
- [inspected] `humanpending.md`
- [inspected] `reports/weekly_profit_2026-06-02_hp005_live_mode_leverage_remediation.md`
- [inspected] `reports/weekly_profit_2026-06-02_v0_canary_activation_runbook.md`
- [inspected] `trader/config.py`
- [inspected] `trader/bot.py`
- [inspected] `trader/infrastructure/api_client.py`
- [inspected] rwUbuntu process metadata and remote code-marker scan.
- [assumed] The current local machine is a candidate preflight context, but the actual activation host is not yet finalized.
- [assumed] Ruei selected HP-006 option `B` via this thread; this report records the read-only attempt and blockers.

## Contract Impact

- Runtime: no runtime defaults changed; `trader/config.py` untouched.
- Risk: no risk defaults changed.
- Scanner: scanner runtime universe remains disabled.
- Research: no strategy, symbol, threshold, or candidate changed.
- Execution: no order, cancel, close, set leverage, hedge/margin mutation, or
  live/testnet state mutation.
- Process: no stop, restart, or start action.
- Credentials: no secrets created, edited, copied, printed, or committed.
- Docs: added this HP-006 read-only preflight report and opened HP-007.

## Decision

Decision: `Hold`

HP-006 read-only live preflight: `failed`

Actual V0 live activation: `blocked`

V1 weekly-profit: `No-Go`

Reason:

- Local live endpoint selection is remediated and public live metadata is
  reachable.
- Signed live account reads failed with `-2014 API-key format invalid`.
- Live account cleanliness could not be verified.
- rwUbuntu remains a healthy dry-run observer, but the inspected remote checkout
  does not yet show HP-005 `--live` remediation.
- The next step is to provision valid live credentials on the approved
  activation host, deploy/verify HP-005 remediation there, and rerun HP-006
  read-only preflight. Do not activate live before that.
