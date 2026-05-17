# Weekly Profit Phase 5 / 4E-Repair Holdout Robustness

Date: 2026-05-15
Branch: `codex/post-promotion-control-20260430`
Status: `RESEARCH_ONLY_SLOT_B_SYMBOL_UNIVERSE_EXPANSION_REPAIR_HOLDOUT_REVIEWED`

## Executive Read

Holdout robustness read is `needs_more_research`: 0 / 4 windows pass the same hard-gate packet.

This remains research-only. Runtime defaults are unchanged, Slot A is not expanded, scanner runtime universe is disabled, and Slot B thresholds are unchanged.

## Window Gate Summary

| window | pass | candidate trades | candidate after-fee | active 8w delta | exit-active positive 8w delta | rolling 8w pnl delta | max DD delta | failed gates |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `default/TRENDING_UP` | `False` | 19 | 776.3668 | 0.1250 | -0.1000 | 78.9688 | -0.0775 | `positive_exit_active_8w_ratio_not_down` |
| `default/RANGING` | `False` | 19 | 740.3545 | 0.3750 | 1.0000 | 546.4336 | 1.8280 | `max_dd_not_materially_larger` |
| `default/MIXED` | `False` | 36 | 565.4079 | 0.1250 | -0.0714 | 67.5200 | 5.0332 | `positive_exit_active_8w_ratio_not_down,max_dd_not_materially_larger` |
| `supplemental/range_low_vol` | `False` | 7 | -365.8698 | 0.1250 | -0.1667 | -76.8662 | 2.8156 | `combined_rolling_8w_after_fee_pnl_not_below_baseline,candidate_slot_after_fee_non_negative,positive_exit_active_8w_ratio_not_down,max_dd_not_materially_larger,new_volume_not_mostly_losing_symbols` |

## Aggregate Counts

| metric | value |
| --- | ---: |
| hard-gate pass windows | 0 / 4 |
| candidate after-fee non-negative windows | 3 / 4 |
| active-entry improved windows | 4 / 4 |
| exit-active positive not-down windows | 1 / 4 |
| rolling 8w after-fee not-below windows | 3 / 4 |
| max DD not materially larger windows | 1 / 4 |

## Artifacts

- Summary JSON: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion_repair_holdout\slot_b_symbol_universe_expansion_repair_holdout_summary.json`
- Window CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion_repair_holdout\slot_b_symbol_universe_expansion_repair_holdout_windows.csv`
- Attribution CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion_repair_holdout\slot_b_symbol_universe_expansion_repair_holdout_attribution.csv`
- Weekly rows CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion_repair_holdout\slot_b_symbol_universe_expansion_repair_holdout_weekly_rows.csv`
