# R4 Transition Stress Test

Date: 2026-04-12

Status: diagnostic complete, pending Ruei/Xiaobo review.

This report is diagnostic only. Scenario A is an actual V54 backtest. Scenarios B and C are offline post-trade overlays on top of A, not full runtime backtests. B/C do not model lane occupancy, re-entry effects, order timing, or changed equity path after a blocked entry. Do not treat B/C numbers as production performance claims until the arbiter is implemented and rerun in the backtester.

No runtime code was changed.

## Artifacts

- Backtest root: `tools/Backtesting/results/r4_transition_stress_20260412/`
- Overlay summary: `tools/Backtesting/results/r4_transition_stress_20260412/r4_overlay_summary.csv`
- Trade decisions: `tools/Backtesting/results/r4_transition_stress_20260412/r4_overlay_trade_decisions.csv`
- Transition-zone metrics: `tools/Backtesting/results/r4_transition_stress_20260412/r4_transition_zone_metrics.csv`

## Windows

| Window | Transition thesis | Date range |
|---|---|---|
| `vrev_bull_2023_10_11` | Bear to bull V-reversal | 2023-10-01 to 2023-11-30 |
| `vrev_bear_2024_03_05` | Bull to bear V-reversal | 2024-03-10 to 2024-05-30 |
| `fade_2025_04_06` | Trend to range fade | 2025-04-01 to 2025-06-15 |
| `range_breakout_2024_09_11` | Range to trend breakout | 2024-09-01 to 2024-11-15 |

## Scenario Definitions

| Scenario | Meaning |
|---|---|
| A | V54 alone, actual backtest output |
| B | A plus diagnostic Neutral Zone entry freeze |
| C | B plus diagnostic closed-weekly macro overlay |

Diagnostic Neutral Zone v0 freezes new entries when either condition is true:

- `squeeze_like`: `bbw_pct50 < 5` and `bbw_ratio < 0.35` and `atr_ratio20 <= 1.1`
- `chop_trend`: `entry_regime == TRENDING` and `adx_slope_5 < 0` and (`bbw_ratio < 0.75` or `bbw_pct50 < 25`)

Diagnostic Macro Overlay v0 uses closed weekly BTC EMA20/EMA50. It marks `MACRO_STALLED` when weekly EMA spread is within 1.5%. For TRENDING entries only, it freezes entries when macro state is unknown/stalled or direction is opposite the entry side. RANGING entries are not macro-blocked in this diagnostic.

These thresholds are diagnostic instrumentation, not final R1/R4 production parameters.

## Scenario Summary

`DD est` is closed-trade realized drawdown estimated from the post-filtered trade list. For A-only actual backtest max drawdown, see the next section.

| Window | Scenario | Trades | PnL USDT | Return % | PF | WR % | Sum R | DD est % | Blocked | Blocked PnL | Blocked R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| vrev_bull_2023_10_11 | A | 11 | 44.92 | 0.449 | 1.49 | 54.5 | 1.54 | 0.511 | 0 | 0.00 | 0.00 |
| vrev_bull_2023_10_11 | B | 9 | 39.60 | 0.396 | 1.62 | 55.6 | 1.14 | 0.479 | 2 | 5.32 | 0.40 |
| vrev_bull_2023_10_11 | C | 9 | 39.60 | 0.396 | 1.62 | 55.6 | 1.14 | 0.479 | 2 | 5.32 | 0.40 |
| vrev_bear_2024_03_05 | A | 9 | -50.05 | -0.501 | 0.34 | 33.3 | -4.01 | 0.580 | 0 | 0.00 | 0.00 |
| vrev_bear_2024_03_05 | B | 8 | -41.73 | -0.417 | 0.38 | 37.5 | -2.26 | 0.579 | 1 | -8.32 | -1.75 |
| vrev_bear_2024_03_05 | C | 8 | -41.73 | -0.417 | 0.38 | 37.5 | -2.26 | 0.579 | 1 | -8.32 | -1.75 |
| fade_2025_04_06 | A | 7 | -9.25 | -0.092 | 0.78 | 28.6 | -1.60 | 0.304 | 0 | 0.00 | 0.00 |
| fade_2025_04_06 | B | 2 | 21.93 | 0.219 | 71.47 | 50.0 | 0.70 | 0.000 | 5 | -31.18 | -2.30 |
| fade_2025_04_06 | C | 2 | 21.93 | 0.219 | 71.47 | 50.0 | 0.70 | 0.000 | 5 | -31.18 | -2.30 |
| range_breakout_2024_09_11 | A | 5 | -38.69 | -0.387 | 0.53 | 40.0 | 1.50 | 0.622 | 0 | 0.00 | 0.00 |
| range_breakout_2024_09_11 | B | 4 | -23.63 | -0.236 | 0.65 | 50.0 | 1.87 | 0.471 | 1 | -15.06 | -0.37 |
| range_breakout_2024_09_11 | C | 2 | -13.54 | -0.135 | 0.71 | 50.0 | 1.67 | 0.471 | 3 | -25.15 | -0.17 |

## A Baseline Actual Backtest

| Window | Trades | Return % | PF | WR % | Actual MaxDD % | Trades/week |
|---|---:|---:|---:|---:|---:|---:|
| vrev_bull_2023_10_11 | 11 | 0.4492 | 1.4884 | 54.55 | 0.8585 | 1.28 |
| vrev_bear_2024_03_05 | 9 | -0.5005 | 0.3371 | 33.33 | 1.0346 | 0.78 |
| fade_2025_04_06 | 7 | -0.0925 | 0.7761 | 28.57 | 0.5557 | 0.65 |
| range_breakout_2024_09_11 | 5 | -0.3869 | 0.5281 | 40.00 | 0.9075 | 0.47 |

## Blocked Trades

Positive blocked PnL means the diagnostic gate would have missed a winner. Negative blocked PnL means it would have avoided a loser.

| Window | Entry time | Symbol | Side | R | PnL USDT | Block reason | Macro |
|---|---|---|---|---:|---:|---|---|
| vrev_bull_2023_10_11 | 2023-11-01 16:00 UTC | DOGE | LONG | 1.26 | 33.40 | neutral_squeeze_like | MACRO_BULL |
| vrev_bull_2023_10_11 | 2023-11-13 06:00 UTC | DOGE | LONG | -0.86 | -28.08 | neutral_chop_trend_adx_falling | MACRO_BULL |
| vrev_bear_2024_03_05 | 2024-03-14 13:00 UTC | ETH | LONG | -1.75 | -8.32 | neutral_chop_trend_adx_falling | MACRO_BULL |
| fade_2025_04_06 | 2025-04-27 06:00 UTC | BTC | LONG | -1.08 | -10.66 | neutral_chop_trend_adx_falling | MACRO_BULL |
| fade_2025_04_06 | 2025-04-28 04:00 UTC | BTC | LONG | -0.06 | -0.71 | neutral_chop_trend_adx_falling | MACRO_BULL |
| fade_2025_04_06 | 2025-05-12 17:00 UTC | ETH | LONG | -0.61 | -16.49 | neutral_chop_trend_adx_falling | MACRO_BULL |
| fade_2025_04_06 | 2025-05-14 10:00 UTC | BTC | LONG | -1.02 | -13.15 | neutral_chop_trend_adx_falling | MACRO_BULL |
| fade_2025_04_06 | 2025-05-15 14:00 UTC | ETH | LONG | 0.47 | 9.83 | neutral_chop_trend_adx_falling | MACRO_BULL |
| range_breakout_2024_09_11 | 2024-09-07 17:00 UTC | SOL | SHORT | -0.70 | -19.67 | macro_direction_mismatch | MACRO_BULL |
| range_breakout_2024_09_11 | 2024-09-08 10:00 UTC | ETH | SHORT | 0.90 | 9.58 | macro_direction_mismatch | MACRO_BULL |
| range_breakout_2024_09_11 | 2024-11-14 17:00 UTC | BTC | LONG | -0.37 | -15.06 | neutral_chop_trend_adx_falling | MACRO_BULL |

## Transition-Zone Metrics

The zone metric checks entries near RegimeEngine flip timestamps. In this diagnostic, A/B/C have identical zone PnL because the overlay did not block the zone trades themselves.

| Window | +/-5 x 4H trades | +/-5 PnL | +/-5 R | +/-10 x 4H trades | +/-10 PnL | +/-10 R | Read |
|---|---:|---:|---:|---:|---:|---:|---|
| vrev_bull_2023_10_11 | 2 | -2.39 | -0.05 | 3 | -39.83 | -1.01 | Flip-adjacent trades were negative, but B/C did not block them |
| vrev_bear_2024_03_05 | 0 | 0.00 | 0.00 | 1 | -23.20 | -1.11 | One negative trade near the 10-bar zone remained |
| fade_2025_04_06 | 0 | 0.00 | 0.00 | 2 | 21.93 | 0.70 | Main fade losses were not near flip timestamps |
| range_breakout_2024_09_11 | 0 | 0.00 | 0.00 | 0 | 0.00 | 0.00 | No transition-zone trades |

Important read: the Apr-May fade failure is better described as a confidence/chop-trend problem than a simple "entry near a regime flip" problem. R4 acceptance should focus on the P0.6 MIXED entry-time TRENDING loss cluster, not only flip timestamp proximity.

## Acceptance Read

- 4 windows x 3 scenarios: PASS as diagnostic overlay.
- B in fade window: PASS diagnostic. A went from -9.25 USDT / -1.60R to B +21.93 USDT / +0.70R. The gate froze 5 trades: 4 losers and 1 winner, net blocked PnL -31.18 USDT / -2.30R.
- C in V-reversal windows: PASS diagnostic. C did not worsen either V-reversal window versus B, and did not create catastrophic drawdown in the post-filtered trade list.
- Opportunity cost is real. In the bull V-reversal, Neutral blocked a +1.26R DOGE winner and a -0.86R DOGE loser, net missing +0.40R. This is acceptable for a diagnostic but needs threshold review.
- Macro overlay is not yet earned as a default production gate. It added no benefit in the two V-reversal windows or the fade window. It improved the range-breakout window net result, but did so by blocking one loser, one winner, and one later loser. Keep it behind a flag or second-phase validation.

## Recommendation

R4 is good enough to justify implementing the Neutral Zone / scalar confidence path for a real backtest, but not enough to go to R5 testnet.

Suggested next move:

1. Implement Neutral Zone first, with thresholds reviewable and disabled by default until the real rerun passes.
2. Rerun the same 4 windows as a true backtest, not a post-trade overlay.
3. Keep Macro Overlay spec-only or behind an explicit experimental flag until it shows value beyond Neutral.
4. Keep R3 skipped. The range-strategy gap was not proven in R2, and R4 points to arbiter confidence as the more valuable next lever.
