# Portfolio A+B Combined First Pass

Date: 2026-04-29
Status: `PHASE_3_PORTFOLIO_FIRST_PASS`

## Scope

- Slot A: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- Slot B: `donchian_range_fade_4h_range_width_cv_013`
- Symbols: `BTC/USDT`, `ETH/USDT`
- `RISK_PER_TRADE`: `0.017`
- `MAX_TOTAL_RISK`: Config default `0.0642`; intentionally not overridden.
- Summary artifact: `extensions\Backtesting\results\portfolio_ab\slot_a_b\portfolio_ab_matrix_summary.json`
- Current StrategyRuntime does not enforce `BTC_TREND_FILTER_ENABLED` on plugin entries; no BTC trend filter reject or size=0 attribution is inferred.

## Decision Gate

| gate | value | threshold | result |
| --- | ---: | ---: | --- |
| portfolio max_dd_pct | 5.1770 | 8.0000 | PASS |
| max window same-symbol same-candle A+B emits | 0 | 5 | PASS |
| Slot A aggregate router block rate | 0.1946 | 0.5000 | PASS |
| Slot B aggregate router block rate | 0.2222 | 0.5000 | PASS |

Verdict: **PASS - A+B portfolio earns first promotion-candidate qualification; no runtime promotion without Ruei approval.**

## Default Windows Portfolio

| window | trades | net_pnl | portfolio_max_dd_pct | run_errors | same_symbol_same_candle_overlaps |
| --- | ---: | ---: | ---: | ---: | ---: |
| `TRENDING_UP` | 32 | 1757.4222 | 4.3144 | 0 | 0 |
| `RANGING` | 3 | 87.4331 | 0.8977 | 0 | 0 |
| `MIXED` | 24 | 404.8474 | 2.3435 | 0 | 0 |

## Default Windows Per-Cartridge

`realized_trade_dd_pct` is closed-trade attribution only; portfolio max drawdown above is the true equity-curve drawdown.

| window | slot | trades | net_pnl | realized_trade_dd_pct | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: |
| `TRENDING_UP` | Slot A | 26 | 1484.5085 | 3.0920 | 0 |
| `TRENDING_UP` | Slot B | 6 | 272.9137 | 0.8119 | 0 |
| `RANGING` | Slot A | 1 | -45.2810 | 0.4528 | 0 |
| `RANGING` | Slot B | 2 | 132.7142 | 0.0000 | 0 |
| `MIXED` | Slot A | 17 | 243.3437 | 2.0565 | 0 |
| `MIXED` | Slot B | 7 | 161.5037 | 0.2716 | 0 |

## Default Windows Reject Mix

| window | slot | entries | rejects | position_slot_occupied | strategy_router_blocked | cooldown | central_risk_blocked | total_risk_limit | router_block_rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `TRENDING_UP` | Slot A | 26 | 70 | 57 | 8 | 5 | 0 | 0 | 0.0833 |
| `TRENDING_UP` | Slot B | 6 | 10 | 4 | 0 | 6 | 0 | 0 | 0.0000 |
| `RANGING` | Slot A | 1 | 3 | 3 | 0 | 0 | 0 | 0 | 0.0000 |
| `RANGING` | Slot B | 2 | 6 | 0 | 4 | 2 | 0 | 0 | 0.5000 |
| `MIXED` | Slot A | 17 | 55 | 36 | 16 | 3 | 0 | 0 | 0.2222 |
| `MIXED` | Slot B | 7 | 9 | 3 | 0 | 6 | 0 | 0 | 0.0000 |

## Supplemental Portfolio

| window | trades | net_pnl | portfolio_max_dd_pct | run_errors | same_symbol_same_candle_overlaps |
| --- | ---: | ---: | ---: | ---: | ---: |
| `bull_strong_up_1` | 11 | 754.3417 | 2.4695 | 0 | 0 |
| `bear_persistent_down` | 24 | 404.8474 | 2.3435 | 0 | 0 |
| `range_low_vol` | 2 | 106.4633 | 0.0000 | 0 | 0 |
| `bull_recovery_2026` | 0 | 0.0000 | 0.0000 | 0 | 0 |
| `ftx_style_crash` | 1 | 30.0738 | 0.6908 | 0 | 0 |
| `sideways_transition` | 3 | 141.2652 | 0.9208 | 0 | 0 |
| `classic_rollercoaster_2021_2022` | 50 | 2797.7194 | 5.1770 | 0 | 0 |
| `recovery_2023_2024` | 65 | 3281.2602 | 4.1090 | 0 | 0 |

## Supplemental Per-Cartridge

| window | slot | trades | net_pnl | realized_trade_dd_pct | entry_stop_violations |
| --- | --- | ---: | ---: | ---: | ---: |
| `bull_strong_up_1` | Slot A | 6 | 595.7043 | 1.0197 | 0 |
| `bull_strong_up_1` | Slot B | 5 | 158.6374 | 0.4409 | 0 |
| `bear_persistent_down` | Slot A | 17 | 243.3437 | 2.0565 | 0 |
| `bear_persistent_down` | Slot B | 7 | 161.5037 | 0.2716 | 0 |
| `range_low_vol` | Slot A | 0 | 0.0000 | 0.0000 | 0 |
| `range_low_vol` | Slot B | 2 | 106.4633 | 0.0000 | 0 |
| `bull_recovery_2026` | Slot A | 0 | 0.0000 | 0.0000 | 0 |
| `bull_recovery_2026` | Slot B | 0 | 0.0000 | 0.0000 | 0 |
| `ftx_style_crash` | Slot A | 0 | 0.0000 | 0.0000 | 0 |
| `ftx_style_crash` | Slot B | 1 | 30.0738 | 0.0000 | 0 |
| `sideways_transition` | Slot A | 2 | 97.3769 | 0.0000 | 0 |
| `sideways_transition` | Slot B | 1 | 43.8883 | 0.0000 | 0 |
| `classic_rollercoaster_2021_2022` | Slot A | 25 | 1612.0356 | 3.4678 | 0 |
| `classic_rollercoaster_2021_2022` | Slot B | 25 | 1185.6837 | 1.7806 | 0 |
| `recovery_2023_2024` | Slot A | 45 | 2245.5016 | 4.4591 | 0 |
| `recovery_2023_2024` | Slot B | 20 | 1035.7585 | 0.7840 | 0 |

## Supplemental Reject Mix

| window | slot | entries | rejects | position_slot_occupied | strategy_router_blocked | cooldown | central_risk_blocked | total_risk_limit | router_block_rate |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `bull_strong_up_1` | Slot A | 6 | 22 | 13 | 8 | 1 | 0 | 0 | 0.2857 |
| `bull_strong_up_1` | Slot B | 5 | 15 | 3 | 8 | 4 | 0 | 0 | 0.4000 |
| `bear_persistent_down` | Slot A | 17 | 55 | 36 | 16 | 3 | 0 | 0 | 0.2222 |
| `bear_persistent_down` | Slot B | 7 | 9 | 3 | 0 | 6 | 0 | 0 | 0.0000 |
| `range_low_vol` | Slot A | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 |
| `range_low_vol` | Slot B | 2 | 6 | 0 | 4 | 2 | 0 | 0 | 0.5000 |
| `bull_recovery_2026` | Slot A | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 |
| `bull_recovery_2026` | Slot B | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 |
| `ftx_style_crash` | Slot A | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0.0000 |
| `ftx_style_crash` | Slot B | 1 | 7 | 3 | 4 | 0 | 0 | 0 | 0.5000 |
| `sideways_transition` | Slot A | 2 | 10 | 6 | 4 | 0 | 0 | 0 | 0.3333 |
| `sideways_transition` | Slot B | 1 | 3 | 3 | 0 | 0 | 0 | 0 | 0.0000 |
| `classic_rollercoaster_2021_2022` | Slot A | 25 | 91 | 65 | 24 | 2 | 0 | 0 | 0.2069 |
| `classic_rollercoaster_2021_2022` | Slot B | 25 | 87 | 47 | 20 | 12 | 8 | 0 | 0.1786 |
| `recovery_2023_2024` | Slot A | 45 | 151 | 104 | 40 | 7 | 0 | 0 | 0.2041 |
| `recovery_2023_2024` | Slot B | 20 | 60 | 22 | 24 | 14 | 0 | 0 | 0.3000 |

## Read

- This is a combined StrategyRuntime portfolio run; both plugins route through central arbiter, central RiskPlan, and shared position slots.
- `central_risk_blocked` and `total_risk_limit` are reported separately so the Config default `MAX_TOTAL_RISK` interaction is visible.
- Same-symbol same-candle overlaps count any candle where both Slot A and Slot B emitted an entry or reject audit row for the same symbol.
- No runtime defaults or catalog promotion flags were changed.
