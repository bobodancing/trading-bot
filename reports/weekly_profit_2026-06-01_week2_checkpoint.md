# Weekly Profit 2026-06-01 Week 2 Checkpoint

Date: 2026-06-01
Branch: `codex/post-promotion-control-20260430`
Status: `WEEK_2_CHECKPOINT_PACKET_GENERATED`

## Summary

- Generated the 2026-06-01 Week 2 promoted-baseline runtime packet from rwUbuntu PID `258894` without restarting, stopping, starting, or mutating any process.
- Confirmed the observer process is alive, running `python3 trader/bot.py --dry-run`, from `/home/rwfunder/文件/strategyVersion/trading-bot`, on branch `codex/post-promotion-control-20260430`.
- `Config.validate()` passed on rwUbuntu from `/proc/258894/cwd`.
- Packet integrity is clean: no config drift, no scanner runtime-feed break, no execution failure, no active/unprotected position, and no malformed runtime events.
- Participation evidence remains weak after dedupe: `674` raw ready / dry-run skip events collapse to `3` unique 4h signal windows, all Slot B LONG `BTC/USDT` `LONG`.
- Economic evidence is absent: `performance.db` trade count is `0`, execution attempts are `0`, fills are `0`, exits are `0`, and realized PnL is `0.0000`.
- Legacy side finding recorded only: PID `19413` was supplied as branch `main`, no `--dry-run`, `USE_SCANNER_SYMBOLS=True`, includes `SOL/USDT`. It was not used in this packet and was not acted on.

## Packet Artifacts

Remote rwUbuntu artifacts:

- `/tmp/runtime_weekly_control_packets_20260601.json`
- `/tmp/runtime_weekly_control_packets_20260601.csv`
- `/tmp/runtime_weekly_control_packet_20260601.md`

Local report artifact:

- `reports/weekly_profit_2026-06-01_week2_checkpoint.md`

## Packet Key Values

Review window: `2026-05-18..2026-05-31`, completed UTC ISO weeks, generated as of `2026-06-01`.

| item | value |
| --- | ---: |
| runtime events | 178885 |
| runtime events after scope | 110495 |
| runtime events dropped by scope | 68390 |
| runtime events outside review | 1856 |
| malformed runtime events | 0 |
| selected config snapshots | 1 |
| selected event without run/config hash | 0 |
| scanner feeds runtime | False |
| scanner symbols | 2 |
| performance db trades | 0 |
| active positions | 0 |
| execution attempts weekly | 0 |
| execution failures weekly | 0 |
| config drift events weekly | 0 |
| unprotected position events weekly | 0 |

Selected config snapshot:

| item | value |
| --- | --- |
| ts | `2026-05-22T03:51:12.390671+00:00` |
| run_id | `run-20260522T035112389142Z-43a8bb12` |
| config_hash | `1da7b08c66e6a7c987141a41164f9ca3e773ecc9ab105fa74af5ec702e783d1c` |
| enabled strategies | promoted three-leg baseline only |
| symbols | `BTC/USDT`, `ETH/USDT` |
| scanner runtime universe | `USE_SCANNER_SYMBOLS=False`, `SCANNER_UNIVERSE_ENABLED=False` |
| router/risk | `STRATEGY_ROUTER_POLICY=fail_closed`, `RISK_PER_TRADE=0.017`, `MAX_TOTAL_RISK=0.0642` |

Weekly runtime details:

| week_start | ready | dry-run skips | rejects | fills | failures | config drift | unprotected |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2026-05-18` | 449 | 449 | 0 | 0 | 0 | 0 | 0 |
| `2026-05-25` | 225 | 225 | 0 | 0 | 0 | 0 | 0 |

Latest packet KPI read:

| KPI | value |
| --- | ---: |
| `active_entry_week_ratio_8w` | 0.0000 |
| `rolling_8w_entry_trade_count` | 0 |
| `zero_entry_week_streak` | 2 |
| `positive_week_ratio_all_8w_after_fee` | 0.0000 |
| `positive_week_ratio_exit_active_8w_after_fee` | 0.0000 |
| `rolling_4w_net_after_fee_pnl` | 0.0000 |
| `rolling_8w_net_after_fee_pnl` | 0.0000 |
| `portfolio_max_drawdown_pct_review_window` | 0.0000 |

## Unique Signal-Window Attribution

Dedup key: `candle_ts + strategy_id + symbol + side`.

| metric | raw events | unique windows |
| --- | ---: | ---: |
| `strategy_entry_ready` | 674 | 3 |
| `execution_skipped(reason=dry_run)` | 674 | 3 inferred |

Per-slot / strategy contribution:

| slot | strategy | raw ready | unique windows |
| --- | --- | ---: | ---: |
| Slot B LONG | `donchian_range_fade_4h_range_width_cv_013` | 674 | 3 |
| Slot A LONG | `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter` | 0 | 0 |
| Slot B SHORT | `donchian_range_fade_4h_range_width_cv_013_short` | 0 | 0 |

Per-symbol contribution:

| symbol | raw ready | unique windows |
| --- | ---: | ---: |
| `BTC/USDT` | 674 | 3 |
| `ETH/USDT` | 0 | 0 |

Per-side contribution:

| side | raw ready | unique windows |
| --- | ---: | ---: |
| `LONG` | 674 | 3 |
| `SHORT` | 0 | 0 |

Unique windows:

| candle_ts | first_seen_ts | slot | symbol | side | raw ready | router reason |
| --- | --- | --- | --- | --- | ---: | --- |
| `2026-05-22T16:00:00` | `2026-05-22T20:00:39.903209+00:00` | Slot B LONG | `BTC/USDT` | `LONG` | 225 | `trend_adx_flat_or_falling` |
| `2026-05-22T20:00:00` | `2026-05-23T00:01:09.050992+00:00` | Slot B LONG | `BTC/USDT` | `LONG` | 224 | `clean_trend` |
| `2026-05-27T00:00:00` | `2026-05-27T04:00:19.054409+00:00` | Slot B LONG | `BTC/USDT` | `LONG` | 225 | `clean_trend` |

Dry-run skip attribution:

| attribution | value |
| --- | ---: |
| raw dry-run skips | 674 |
| inferred unique dry-run skip windows | 3 |
| unpaired skip events | 0 |
| week `2026-05-18` | 449 |
| week `2026-05-25` | 225 |
| Slot B LONG | 674 |
| `BTC/USDT` | 674 |
| `LONG` | 674 |

Regime / router attribution from available runtime fields:

| field | raw ready | unique windows |
| --- | ---: | ---: |
| `router_reason=clean_trend` | 449 | 2 |
| `router_reason=trend_adx_flat_or_falling` | 225 | 1 |
| `btc_trend_filter: trend=LONG, mode=diagnostic, reason=daily_ema, source=1d_fallback, counter_trend=False, allowed=True, risk_mult=1.0` | 674 | 3 |

[assumed] Full regime-arbiter labels are not available in the current `strategy_entry_ready` / `execution_skipped` fields. This packet uses `router_reason` plus `btc_trend_filter` as runtime-available attribution proxies only. `execution_skipped` events do not carry `candle_ts` or `cycle_id`; unique skip windows were inferred by matching same strategy/symbol/side to the preceding ready event within 30 seconds.

## Log Tail Integrity Check

Checked `.log/bot.log` and `.log/trades.log` tail, last `3000` lines each, for:

`ERROR|Traceback|execution failure|execution_failure|unprotected|unprotected position|exception|failed`

Result:

- `.log/bot.log`: no matching tail signals
- `.log/trades.log`: no matching tail signals

## Verification

- [executed] `Get-Content -Raw AGENTS.md`
- [executed] `git status --short --branch`
- [executed] `git log --oneline -n 12`
- [executed] `Test-NetConnection 100.67.114.104 -Port 22`
- [executed] `ssh -i $env:USERPROFILE\.ssh\codex_meshnet_ed25519 -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 'ps -p 258894 -o pid=,etimes=,args='`
- [executed] `ssh -i $env:USERPROFILE\.ssh\codex_meshnet_ed25519 -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 'readlink -f /proc/258894/cwd'`
- [executed] `ssh -i $env:USERPROFILE\.ssh\codex_meshnet_ed25519 -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 'git -C /proc/258894/cwd branch --show-current'`
- [executed] `ssh -i $env:USERPROFILE\.ssh\codex_meshnet_ed25519 -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 'git -C /proc/258894/cwd log --oneline -n 5'`
- [executed] `ssh -i $env:USERPROFILE\.ssh\codex_meshnet_ed25519 -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "cd /proc/258894/cwd && python3 -c 'from trader.config import Config; Config.validate(); print(chr(67)+chr(111)+chr(110)+chr(102)+chr(105)+chr(103)+chr(46)+chr(118)+chr(97)+chr(108)+chr(105)+chr(100)+chr(97)+chr(116)+chr(101)+chr(32)+chr(79)+chr(75))'"`
- [executed] `ssh -i $env:USERPROFILE\.ssh\codex_meshnet_ed25519 -o BatchMode=yes -o ConnectTimeout=10 rwfunder@100.67.114.104 "cd /proc/258894/cwd && python3 tools/runtime_weekly_control_packet.py --as-of 2026-06-01 --weeks 2 --completed-only --config-profile promoted_baseline --json-out /tmp/runtime_weekly_control_packets_20260601.json --csv-out /tmp/runtime_weekly_control_packets_20260601.csv --report-out /tmp/runtime_weekly_control_packet_20260601.md"`
- [executed] remote `python3 -` read-only parsers over `/tmp/runtime_weekly_control_packets_20260601.json` and `.log/runtime_observability/strategy_runtime_funnel.jsonl` to extract source quality, config snapshot metadata, unique signal-window attribution, dry-run skip attribution, and router/trend attribution.
- [executed] remote `python3 -` read-only tail scanner over `.log/bot.log` and `.log/trades.log`.
- [inspected] `AGENTS.md`
- [inspected] `tools/runtime_weekly_control_packet.py`
- [inspected] `/tmp/runtime_weekly_control_packet_20260601.md`
- [inspected] `/tmp/runtime_weekly_control_packets_20260601.json`
- [inspected] `.log/runtime_observability/strategy_runtime_funnel.jsonl`
- [inspected] `.log/bot.log` tail, last `3000` lines
- [inspected] `.log/trades.log` tail, last `3000` lines
- [assumed] Legacy PID `19413` details are carried from the task context only; they were not re-inspected and were not included in promoted-baseline packet calculations.
- [assumed] No authenticated execution-path validation was performed in this task because touching live/testnet service state was explicitly out of scope.

## Contract Impact

- Runtime: no runtime defaults changed; `trader/config.py` untouched; PID `258894` not stopped/restarted/started.
- Risk: no risk defaults changed; central risk remains unchanged; active positions `0`; unprotected position events `0`.
- Scanner: runtime scanner universe remains disabled; scanner diagnostics show `runtime_selection_feeds_trading=False`; scanner output remains diagnostic.
- Research: no candidate promoted; no thresholds loosened; no new research lane started. Participation gap remains the active investigation target.
- Docs: added this checkpoint report only.
- Credentials: no `secrets.json` or private key content inspected; no secrets printed in this report.

## Decision

No `pause` trigger fired: config drift `0`, scanner boundary break `False`, execution integrity issue `0`, unprotected position events `0`.

2026-06-01 decision:

- Runtime health: `continue`
- Participation / economic evidence: `investigate`
- V0 canary: `Hold`
- V1 weekly-profit: `No-Go`

Reason: rwUbuntu dry-run plumbing is clean and generated handoff evidence, but the two completed weeks produced only `3` unique 4h signal windows and no authenticated execution-path evidence, fills, exits, or realized PnL. This must not be described as profitability.

`humanpending.md` is not needed for this task. The legacy PID `19413` side finding is not blocking the Week 2 promoted-baseline checkpoint; handling it would be a separate Ruei decision if it becomes operationally relevant.
