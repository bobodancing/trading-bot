# Weekly Profit Phase 3 Control Packet

Date: 2026-05-12
Branch: `codex/post-promotion-control-20260430`
Status: `PHASE_3_WEEKLY_CONTROL_PACKET_IMPLEMENTED`

## Executive Read

Latest contract-grade packet state is `investigate`. The evaluator is now machine-readable and follows the Phase 2 KPI contract precedence: `pause > reopen_research > investigate > continue`. Latest raw packet `2026-04-27` is partial-window observe-only; the executive read uses the latest contract-grade packet.

This is a control-packet implementation over existing backtest artifacts. It does not alter runtime defaults, scanner activation, strategy thresholds, or credentials.

## Source

- Contract: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\plans\weekly_profit_kpi_contract.md`
- Source summary: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_bidirectional\short_ablation\portfolio_ab_short_ablation_summary.json`
- Primary window: `custom/2026_01_01_2026_04_30`
- Review dates: `2026-01-01..2026-04-30`
- Review capital: `10000.0` USDT
- Fee estimate: `0.0004` per side
- Operational input source: backtest-control defaults. Live/dry-run packets must replace these with runtime observability.

## Latest Contract-Grade Packet KPIs

| KPI | value |
| --- | ---: |
| `rolling_8w_complete` | `True` |
| `rolling_8w_has_partial_review_week` | `False` |
| `active_entry_week_ratio_8w` | 0.6250 |
| `rolling_8w_entry_trade_count` | 9 |
| `zero_entry_week_streak` | 0 |
| `positive_week_ratio_all_8w_after_fee` | 0.3750 |
| `positive_week_ratio_exit_active_8w_after_fee` | 0.6000 |
| `rolling_4w_net_after_fee_pnl` | 9.4722 |
| `rolling_8w_net_after_fee_pnl` | 106.4680 |
| `rolling_8w_realized_exit_count` | 8 |
| `exit_active_week_count_8w` | 5 |
| `meets_economic_sample_floor` | `True` |
| `worst_week_after_fee_pnl_pct_equity_8w` | -1.2335 |
| `max_consecutive_losing_weeks_after_fee_8w` | 1 |
| `portfolio_max_drawdown_pct_review_window` | 2.1778 |
| `execution_attempt_count_weekly` | 0 |
| `execution_failure_count_weekly` | 0 |
| `execution_failure_rate_weekly` | `null` |
| `config_drift_events_weekly` | 0 |
| `unprotected_position_events_weekly` | 0 |

## Latest Contract-Grade Decision

| item | value |
| --- | --- |
| state | `investigate` |
| week_start | `2026-04-20` |
| contract grade | `True` |
| pause triggers | `none` |
| reopen triggers | `none` |
| investigate triggers | `positive_week_ratio_all_8w_after_fee` |
| notes | `none` |

## Weekly Packet States

| week_start | state | contract_grade | active-entry ratio 8w | entries 8w | zero-entry streak | positive all 8w | positive active-exit 8w | net 8w | worst week pct equity 8w | primary trigger/note |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `2025-12-29` | `continue` | False | 0.0000 | 0 | 1 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | rolling_8w_not_complete_observe_only |
| `2026-01-05` | `continue` | False | 0.0000 | 0 | 2 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | rolling_8w_not_complete_observe_only |
| `2026-01-12` | `continue` | False | 0.3333 | 1 | 0 | 0.3333 | 1.0000 | 1.4766 | 0.0000 | rolling_8w_not_complete_observe_only |
| `2026-01-19` | `continue` | False | 0.2500 | 1 | 1 | 0.2500 | 1.0000 | 1.4766 | 0.0000 | rolling_8w_not_complete_observe_only |
| `2026-01-26` | `continue` | False | 0.2000 | 1 | 2 | 0.2000 | 1.0000 | 1.4766 | 0.0000 | rolling_8w_not_complete_observe_only |
| `2026-02-02` | `continue` | False | 0.1667 | 1 | 3 | 0.1667 | 1.0000 | 1.4766 | 0.0000 | rolling_8w_not_complete_observe_only |
| `2026-02-09` | `continue` | False | 0.2857 | 4 | 0 | 0.2857 | 1.0000 | 94.7952 | 0.0000 | rolling_8w_not_complete_observe_only |
| `2026-02-16` | `continue` | False | 0.2500 | 4 | 1 | 0.3750 | 1.0000 | 157.3497 | 0.0000 | rolling_8w_contains_partial_review_week_observe_only |
| `2026-02-23` | `reopen_research` | True | 0.2500 | 4 | 2 | 0.3750 | 1.0000 | 157.3497 | 0.0000 | active_entry_week_ratio_8w, rolling_8w_entry_trade_count |
| `2026-03-02` | `reopen_research` | True | 0.2500 | 4 | 3 | 0.3750 | 1.0000 | 157.3497 | 0.0000 | active_entry_week_ratio_8w, rolling_8w_entry_trade_count, zero_entry_week_streak |
| `2026-03-09` | `reopen_research` | True | 0.1250 | 3 | 4 | 0.2500 | 1.0000 | 155.8731 | 0.0000 | active_entry_week_ratio_8w, rolling_8w_entry_trade_count, zero_entry_week_streak |
| `2026-03-16` | `reopen_research` | True | 0.2500 | 4 | 0 | 0.2500 | 0.6667 | 136.8349 | -0.1904 | active_entry_week_ratio_8w, rolling_8w_entry_trade_count |
| `2026-03-23` | `reopen_research` | True | 0.3750 | 6 | 0 | 0.3750 | 0.7500 | 252.8689 | -0.1904 | active_entry_week_ratio_8w |
| `2026-03-30` | `investigate` | True | 0.5000 | 7 | 0 | 0.5000 | 0.8000 | 297.0647 | -0.1904 | active_entry_week_ratio_8w, rolling_8w_entry_trade_count |
| `2026-04-06` | `reopen_research` | True | 0.3750 | 4 | 1 | 0.3750 | 0.7500 | 203.7461 | -0.1904 | active_entry_week_ratio_8w, rolling_8w_entry_trade_count |
| `2026-04-13` | `reopen_research` | True | 0.5000 | 6 | 0 | 0.2500 | 0.5000 | 17.8436 | -1.2335 | positive_week_ratio_all_8w_after_fee |
| `2026-04-20` | `investigate` | True | 0.6250 | 9 | 0 | 0.3750 | 0.6000 | 106.4680 | -1.2335 | positive_week_ratio_all_8w_after_fee |
| `2026-04-27` | `continue` | False | 0.6250 | 9 | 1 | 0.3750 | 0.5000 | 54.1311 | -1.2335 | rolling_8w_contains_partial_review_week_observe_only |

## Machine-Readable Artifact

- JSON packet series: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_bidirectional\short_ablation\weekly_profit_control_packets.json`

## Phase 4 Readiness

- If live/dry-run packet data confirms the same participation gap, open one bounded frequency-complement trigger review.
- Do not loosen existing strategy thresholds just to create volume.
- Do not promote new runtime defaults from this packet alone.
