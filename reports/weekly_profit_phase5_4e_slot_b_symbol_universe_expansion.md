# Weekly Profit Phase 5 / 4E Slot B Symbol-Universe Expansion

Date: 2026-05-15
Branch: `codex/post-promotion-control-20260430`
Status: `RESEARCH_ONLY_SLOT_B_SYMBOL_UNIVERSE_EXPANSION_EVALUATED`

## Executive Read

Latest contract-grade packet state is `investigate` for the A+B+Slot-B-expanded-symbols combined run.

The expanded Slot B symbol lane does not pass the hard gates. Failed gate(s): `positive_exit_active_8w_ratio_not_down`.

Runtime defaults remain unchanged. Slot A was not expanded. Scanner runtime universe remains disabled.

Standalone per-symbol attribution keeps `BTC/USDT` as a regime-context sidecar, while candidate plugins remain scoped to the single alt symbol under review.

## Scope

- Baseline symbols: `BTC/USDT`, `ETH/USDT`
- Requested candidate symbols: `SOL/USDT`, `BNB/USDT`, `XRP/USDT`, `ADA/USDT`, `LINK/USDT`
- Included candidate symbols: `SOL/USDT`, `BNB/USDT`, `XRP/USDT`, `ADA/USDT`, `LINK/USDT`
- Excluded candidate symbols: `none`
- Candidate LONG: `donchian_range_fade_4h_range_width_cv_013_symbol_universe_expansion`
- Candidate SHORT: `donchian_range_fade_4h_range_width_cv_013_short_symbol_universe_expansion`
- Candidate plugins are catalog `enabled=False` and research-only.

## Data Availability Gate

| metric | value |
| --- | ---: |
| baseline common 1H rows | 2857 |
| expanded common 1H rows | 2857 |
| shared cursor delta rows | 0 |

## Baseline vs Combined Weekly Packet

| metric | baseline | combined | delta |
| --- | ---: | ---: | ---: |
| `active_entry_week_ratio_8w` | 0.6250 | 0.8750 | 0.2500 |
| `rolling_8w_entry_trade_count` | 9 | 21 | 12.0000 |
| `positive_week_ratio_all_8w_after_fee` | 0.3750 | 0.5000 | 0.1250 |
| `positive_week_ratio_exit_active_8w_after_fee` | 0.6000 | 0.5714 | -0.0286 |
| `rolling_8w_net_after_fee_pnl` | 106.4680 | 368.0052 | 261.5372 |
| `portfolio_max_drawdown_pct_review_window` | 2.1778 | 2.5875 | 0.4097 |

## Primary Window Summary

| metric | baseline | combined |
| --- | ---: | ---: |
| entry trades | 13 | 55 |
| exit trades | 13 | 55 |
| active entry weeks | 7 | 13 |
| after-fee positive week ratio all | 0.3333 | 0.5000 |
| net after fee estimate | 211.4808 | 1546.2225 |
| worst after-fee week | -123.3480 | -98.8164 |
| portfolio max DD pct | 2.1778 | 2.5875 |

## Candidate Symbol Attribution

| symbol | trades | gross pnl | fees est | after-fee pnl | win rate | active entry weeks | worst week | same-time overlap | entry-week overlap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `SOL/USDT` | 12 | 610.2500 | 41.8068 | 568.4432 | 0.7500 | 6 | 24.5316 | 2 | 3 |
| `BNB/USDT` | 8 | 408.3813 | 28.0494 | 380.3319 | 0.8750 | 5 | 0.6187 | 0 | 1 |
| `XRP/USDT` | 5 | 223.8113 | 17.4855 | 206.3258 | 0.8000 | 3 | -35.1332 | 1 | 2 |
| `ADA/USDT` | 6 | 66.7237 | 20.9705 | 45.7532 | 0.6667 | 4 | -19.9129 | 1 | 2 |
| `LINK/USDT` | 11 | 172.5551 | 38.6675 | 133.8876 | 0.5455 | 4 | -68.6102 | 1 | 2 |

## Hard Gate Read

| gate | pass |
| --- | --- |
| `combined_rolling_8w_after_fee_pnl_not_below_baseline` | `True` |
| `candidate_slot_after_fee_non_negative` | `True` |
| `active_entry_8w_ratio_improves` | `True` |
| `positive_all_week_8w_ratio_not_down` | `True` |
| `positive_exit_active_8w_ratio_not_down` | `False` |
| `max_dd_not_materially_larger` | `True` |
| `new_volume_not_mostly_losing_symbols` | `True` |
| `no_threshold_loosening` | `True` |
| `run_errors_clean` | `True` |

## Artifacts

- Summary JSON: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion\slot_b_symbol_universe_expansion_summary.json`
- Weekly packet JSON: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion\weekly_profit_slot_b_symbol_universe_expansion_packets.json`
- Data availability CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion\slot_b_symbol_universe_expansion_data_availability.csv`
- Symbol attribution CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion\slot_b_symbol_universe_expansion_symbol_attribution.csv`
- Weekly rows CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion\slot_b_symbol_universe_expansion_weekly_rows.csv`
