# Weekly Profit Phase 5 / 4E-Repair Holdout Failure Attribution

Date: 2026-05-17
Branch: `codex/post-promotion-control-20260430`
Status: `RESEARCH_ONLY_SLOT_B_SYMBOL_UNIVERSE_EXPANSION_REPAIR_HOLDOUT_FAILURE_ATTRIBUTED_AND_PARKED`

## Executive Read

The Slot B symbol-expansion repair should stay parked. The holdout failure is not a single removable bad trade: it combines weekly-quality instability, drawdown expansion, and one fully negative range-low-vol window.

No runtime defaults, promoted symbols, scanner runtime settings, risk defaults, or thresholds are changed by this attribution.

## Formal Park Decision

| item | decision |
| --- | --- |
| 4E lane status | `PARKED_UNLESS_PRE_REGISTERED_REGIME_FILTER_EXISTS` |
| promotion eligibility | `NO` |
| runtime symbol expansion | `NO` |
| static symbol/side admission repair | `INSUFFICIENT` |
| next allowed research action | `PRE_REGISTERED_REGIME_FILTER_ONLY` |

Reopen condition: a new 4E pass must pre-register a regime/window filter before any rerun, use only runtime-available non-outcome features, and pass the same primary plus holdout hard gates without changing promoted thresholds or runtime defaults.

## Window Verdicts

| window | verdict | failed gates | candidate after-fee | losing symbol/sides | negative candidate weeks | DD proxy | DD worst candidate |
| --- | --- | --- | ---: | --- | ---: | ---: | --- |
| `default/TRENDING_UP` | `PARK_WEEKLY_QUALITY_UNSTABLE` | `positive_exit_active_8w_ratio_not_down` | 776.3668 | `SOL/USDT:LONG, XRP/USDT:SHORT` | 2 | 2.1719% | `XRP/USDT:SHORT` |
| `default/RANGING` | `PARK_DD_UNSTABLE` | `max_dd_not_materially_larger` | 740.3544 | `none` | 1 | 1.4965% | `SOL/USDT:LONG` |
| `default/MIXED` | `PARK_DD_UNSTABLE` | `positive_exit_active_8w_ratio_not_down,max_dd_not_materially_larger` | 565.4079 | `BNB/USDT:SHORT, SOL/USDT:LONG` | 6 | 5.1519% | `SOL/USDT:LONG` |
| `supplemental/range_low_vol` | `PARK_WINDOW_NEGATIVE_EXPECTANCY` | `combined_rolling_8w_after_fee_pnl_not_below_baseline,candidate_slot_after_fee_non_negative,positive_exit_active_8w_ratio_not_down,max_dd_not_materially_larger,new_volume_not_mostly_losing_symbols` | -365.8699 | `ADA/USDT:SHORT, BNB/USDT:SHORT, LINK/USDT:LONG, SOL/USDT:LONG, SOL/USDT:SHORT, XRP/USDT:LONG` | 4 | 2.8900% | `LINK/USDT:LONG` |

## Symbol / Side Failures

| window | symbol | side | trades | after-fee | win rate | worst trade |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `default/TRENDING_UP` | `SOL/USDT` | `LONG` | 1 | -99.8147 | 0.0000 | -99.8147 |
| `default/TRENDING_UP` | `XRP/USDT` | `SHORT` | 2 | -28.4880 | 0.5000 | -42.5322 |
| `default/MIXED` | `BNB/USDT` | `SHORT` | 5 | -50.8026 | 0.2000 | -21.7656 |
| `default/MIXED` | `SOL/USDT` | `LONG` | 7 | -91.3457 | 0.7143 | -199.2055 |
| `supplemental/range_low_vol` | `ADA/USDT` | `SHORT` | 1 | -21.2135 | 0.0000 | -21.2135 |
| `supplemental/range_low_vol` | `BNB/USDT` | `SHORT` | 2 | -2.6526 | 0.5000 | -8.3296 |
| `supplemental/range_low_vol` | `LINK/USDT` | `LONG` | 1 | -151.1745 | 0.0000 | -151.1745 |
| `supplemental/range_low_vol` | `SOL/USDT` | `LONG` | 1 | -53.0001 | 0.0000 | -53.0001 |
| `supplemental/range_low_vol` | `SOL/USDT` | `SHORT` | 1 | -32.2061 | 0.0000 | -32.2061 |
| `supplemental/range_low_vol` | `XRP/USDT` | `LONG` | 1 | -105.6230 | 0.0000 | -105.6230 |

## Worst Weekly Damage

| window | week | candidate after-fee | repair after-fee | worst candidate symbol/side |
| --- | --- | ---: | ---: | --- |
| `supplemental/range_low_vol` | `2025-09-22` | -256.7976 | -256.7976 | `LINK/USDT:LONG` |
| `default/MIXED` | `2025-06-09` | -199.2055 | -184.4393 | `SOL/USDT:LONG` |
| `default/MIXED` | `2025-05-26` | -191.1348 | -182.9663 | `LINK/USDT:LONG` |
| `default/MIXED` | `2025-03-31` | -120.1676 | -120.1676 | `LINK/USDT:LONG` |
| `default/MIXED` | `2025-07-14` | -110.4065 | -170.6960 | `SOL/USDT:SHORT` |
| `default/TRENDING_UP` | `2024-01-15` | -100.7130 | 23.0480 | `SOL/USDT:LONG` |
| `default/RANGING` | `2025-01-27` | -61.7908 | -61.7908 | `SOL/USDT:LONG` |
| `supplemental/range_low_vol` | `2025-11-10` | -53.0001 | -53.0001 | `SOL/USDT:LONG` |

## Closeout Read

- `range_low_vol` is a hard park signal: all added candidate symbol/sides in that holdout are negative in aggregate.
- `MIXED` keeps positive total candidate PnL, but drawdown expansion is too large for promotion.
- `TRENDING_UP` keeps positive total candidate PnL, but added trades reduce exit-active weekly quality.
- The failure is regime/window-sensitive, so a simple static symbol list is not enough evidence for runtime expansion.

## Artifacts

- Summary JSON: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion_repair_holdout\slot_b_symbol_universe_expansion_repair_holdout_failure_attribution_summary.json`
- Symbol/side CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion_repair_holdout\slot_b_symbol_universe_expansion_repair_holdout_failure_symbol_side.csv`
- Weekly CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion_repair_holdout\slot_b_symbol_universe_expansion_repair_holdout_failure_weekly.csv`
- Drawdown CSV: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\slot_b_symbol_universe_expansion_repair_holdout\slot_b_symbol_universe_expansion_repair_holdout_failure_drawdown.csv`
