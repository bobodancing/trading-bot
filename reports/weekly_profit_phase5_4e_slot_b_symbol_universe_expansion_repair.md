# Weekly Profit Phase 5 / 4E-Repair Slot B Symbol-Universe Expansion

Date: 2026-05-15
Branch: `codex/post-promotion-control-20260430`
Status: `RESEARCH_ONLY_SLOT_B_SYMBOL_UNIVERSE_EXPANSION_REPAIR_EVALUATED`

## Executive Read

Latest contract-grade packet state is `continue` for the A+B+Slot-B-repair-symbols combined run.

The Phase 5/4E-Repair candidate passes this research hard-gate packet. This does not authorize runtime promotion.

Repair admission is side-specific: LONG admits `SOL/USDT`, `BNB/USDT`, `XRP/USDT`, `LINK/USDT`; SHORT admits `SOL/USDT`, `BNB/USDT`, `XRP/USDT`, `ADA/USDT`.

Runtime defaults remain unchanged. Slot A was not expanded. Scanner runtime universe remains disabled. Thresholds are unchanged from promoted Slot B.

## Admission Ablation Read

Ablation is a trade-admission replay over the full-expanded combined artifact, then the selected repair was rerun through `BacktestEngine` as a research-only plugin pair.

| rank | variant | pass | trades | candidate after-fee | active 8w delta | exit-active positive 8w delta | rolling 8w pnl delta |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | `drop_link_short_ada_long` | `True` | 35 | 1476.3888 | 0.1250 | 0.0667 | 382.8464 |
| 2 | `sol_bnb_xrp_ada_short_link_long` | `True` | 35 | 1476.3888 | 0.1250 | 0.0667 | 382.8464 |
| 3 | `drop_link_short` | `True` | 36 | 1456.4759 | 0.1250 | 0.0667 | 382.8464 |
| 4 | `sol_bnb_xrp_link_long` | `True` | 30 | 1410.7227 | 0.1250 | 0.0667 | 382.8464 |
| 5 | `drop_link_all` | `True` | 31 | 1200.8541 | 0.1250 | 0.0667 | 386.3481 |

## Baseline vs Repair Weekly Packet

| metric | baseline | repair | delta |
| --- | ---: | ---: | ---: |
| `active_entry_week_ratio_8w` | 0.6250 | 0.7500 | 0.1250 |
| `rolling_8w_entry_trade_count` | 9 | 19 | 10.0000 |
| `positive_week_ratio_all_8w_after_fee` | 0.3750 | 0.5000 | 0.1250 |
| `positive_week_ratio_exit_active_8w_after_fee` | 0.6000 | 0.6667 | 0.0667 |
| `rolling_8w_net_after_fee_pnl` | 106.4680 | 489.3144 | 382.8464 |
| `portfolio_max_drawdown_pct_review_window` | 2.1778 | 2.5562 | 0.3784 |

## Primary Window Summary

| metric | baseline | repair |
| --- | ---: | ---: |
| entry trades | 13 | 48 |
| exit trades | 13 | 48 |
| active entry weeks | 7 | 12 |
| after-fee positive week ratio all | 0.3333 | 0.5556 |
| net after fee estimate | 211.4808 | 1687.8696 |
| worst after-fee week | -123.3480 | -98.8164 |
| portfolio max DD pct | 2.1778 | 2.5562 |

## Candidate Symbol Attribution

| symbol | trades | gross pnl | fees est | after-fee pnl | win rate | active entry weeks | worst week | same-time overlap | entry-week overlap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `SOL/USDT` | 12 | 610.2500 | 41.8068 | 568.4432 | 0.7500 | 6 | 24.5316 | 2 | 3 |
| `BNB/USDT` | 8 | 408.3813 | 28.0494 | 380.3319 | 0.8750 | 5 | 0.6187 | 0 | 1 |
| `XRP/USDT` | 5 | 223.8113 | 17.4855 | 206.3258 | 0.8000 | 3 | -35.1332 | 1 | 2 |
| `ADA/USDT` | 5 | 83.1414 | 17.4753 | 65.6661 | 0.8000 | 3 | 2.2667 | 1 | 2 |
| `LINK/USDT` | 5 | 273.2392 | 17.6174 | 255.6218 | 0.8000 | 2 | -3.5016 | 0 | 1 |

## Hard Gate Read

| gate | pass |
| --- | --- |
| `combined_rolling_8w_after_fee_pnl_not_below_baseline` | `True` |
| `candidate_slot_after_fee_non_negative` | `True` |
| `active_entry_8w_ratio_improves` | `True` |
| `positive_all_week_8w_ratio_not_down` | `True` |
| `positive_exit_active_8w_ratio_not_down` | `True` |
| `max_dd_not_materially_larger` | `True` |
| `new_volume_not_mostly_losing_symbols` | `True` |
| `no_threshold_loosening` | `True` |
| `run_errors_clean` | `True` |

## Artifacts

- Summary JSON: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion_repair\slot_b_symbol_universe_expansion_repair_summary.json`
- Weekly packet JSON: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion_repair\weekly_profit_slot_b_symbol_universe_expansion_repair_packets.json`
- Admission variants CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion_repair\slot_b_symbol_universe_expansion_repair_variants.csv`
- Symbol attribution CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion_repair\slot_b_symbol_universe_expansion_repair_symbol_attribution.csv`
- Weekly rows CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion_repair\slot_b_symbol_universe_expansion_repair_weekly_rows.csv`
