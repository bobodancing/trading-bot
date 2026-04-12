# R4 True Backtest: Neutral Arbiter

Date: 2026-04-12

Status: complete, pending Ruei/Xiaobo review.

Scope: true backtest rerun after implementing `REGIME_ARBITER_ENABLED` and scalar confidence. This is no longer the R4 offline post-trade overlay.

Decision artifact:

- `tools/Backtesting/results/r4_transition_true_20260412_fullsymbols/`
- Combined summary: `tools/Backtesting/results/r4_transition_true_20260412_fullsymbols/r4_true_summary_with_existing_a.csv`

Symbol universe: `BTC/USDT`, `ETH/USDT`, `SOL/USDT`, `DOGE/USDT`, `BNB/USDT`, `XRP/USDT`.

Earlier smoke/4-symbol outputs under `r4_transition_true_20260412_smoke/` and `r4_transition_true_20260412/` are not decision artifacts.

## Implementation Notes

- Added `RegimeArbiter` with scalar `RegimeSnapshot.confidence`.
- `REGIME_ARBITER_ENABLED = false` by default, so live/default behavior stays off.
- Neutral thresholds are explicit config keys and parity-guarded.
- `MACRO_OVERLAY_ENABLED = false` by default; macro remains experimental.
- V54 strategy logic was not modified.
- `trader/regime.py` thresholds and hysteresis were not modified.

Diagnostic run thresholds:

- `REGIME_ARBITER_ENABLED = true`
- `ARBITER_NEUTRAL_THRESHOLD = 0.5`
- `ARBITER_NEUTRAL_EXIT_THRESHOLD = 0.5`
- `ARBITER_NEUTRAL_MIN_BARS = 1`
- C only: `MACRO_OVERLAY_ENABLED = true`

## Results

A baseline rows are the existing true V54-alone R4 backtests from `tools/Backtesting/results/r4_transition_stress_20260412/`. B/C are true reruns with the implemented arbiter.

| Window | Scenario | Trades | Return % | PF | WR % | MaxDD % | Arbiter blocks |
|---|---|---:|---:|---:|---:|---:|---:|
| vrev_bull_2023_10_11 | A V54 alone | 11 | 0.4492 | 1.4884 | 54.55 | 0.8585 | 0 |
| vrev_bull_2023_10_11 | B Neutral | 8 | 0.4740 | 1.8451 | 62.50 | 0.8760 | 4 |
| vrev_bull_2023_10_11 | C Neutral + Macro | 8 | 0.4740 | 1.8451 | 62.50 | 0.8760 | 4 |
| vrev_bear_2024_03_05 | A V54 alone | 9 | -0.5005 | 0.3371 | 33.33 | 1.0346 | 0 |
| vrev_bear_2024_03_05 | B Neutral | 9 | -0.5005 | 0.3371 | 33.33 | 1.0346 | 0 |
| vrev_bear_2024_03_05 | C Neutral + Macro | 9 | -0.5005 | 0.3371 | 33.33 | 1.0346 | 0 |
| fade_2025_04_06 | A V54 alone | 7 | -0.0925 | 0.7761 | 28.57 | 0.5557 | 0 |
| fade_2025_04_06 | B Neutral | 2 | 0.2193 | 71.4656 | 50.00 | 0.4967 | 5 |
| fade_2025_04_06 | C Neutral + Macro | 2 | 0.2193 | 71.4656 | 50.00 | 0.4967 | 5 |
| range_breakout_2024_09_11 | A V54 alone | 5 | -0.3869 | 0.5281 | 40.00 | 0.9075 | 0 |
| range_breakout_2024_09_11 | B Neutral | 4 | -0.2363 | 0.6469 | 50.00 | 0.6940 | 1 |
| range_breakout_2024_09_11 | C Neutral + Macro | 2 | -0.1354 | 0.7134 | 50.00 | 0.6932 | 3 |

## Arbiter Block Reasons

| Window | B Neutral | C Neutral + Macro |
|---|---|---|
| vrev_bull_2023_10_11 | `low_regime_confidence:chop_trend_adx_falling` x4 | same as B |
| vrev_bear_2024_03_05 | none | none |
| fade_2025_04_06 | `low_regime_confidence:chop_trend_adx_falling` x4; `squeeze_freeze_new_entries` x1 | same as B |
| range_breakout_2024_09_11 | `low_regime_confidence:chop_trend_adx_falling` x1 | `low_regime_confidence:chop_trend_adx_falling` x1; `macro_overlay_blocked:bull_blocks_short` x2 |

## Read

Neutral-only passes the R4 purpose. It avoided the Apr-May fade failure cluster in a true backtest, not just overlay math:

- A: `7 trades`, `-0.0925%`, `PF 0.7761`
- B: `2 trades`, `+0.2193%`, `PF 71.4656`
- Arbiter blocks in fade: `5`

It also did not create catastrophic behavior in either V-reversal window:

- Bull V-reversal improved slightly: `0.4492% -> 0.4740%`
- Bear V-reversal unchanged: `-0.5005% -> -0.5005%`

Macro overlay is still not earned as a default gate:

- It added no value in bull V-reversal, bear V-reversal, or fade.
- It improved the range-breakout sample, but only by adding two extra blocks in one window.
- Keep it behind `MACRO_OVERLAY_ENABLED=false` for R5 unless Ruei explicitly wants an experimental run.

## Recommendation

R5 candidate: V54 + Neutral Arbiter only, with Macro Overlay disabled.

Do not turn on Macro Overlay for the first rwUbuntu testnet pass. The clean next step is to let Neutral prove itself forward before adding macro complexity.
