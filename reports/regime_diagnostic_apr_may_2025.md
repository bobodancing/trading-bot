# R0 Report A: Apr-May 2025 Hysteresis Replay

Generated: 2026-04-12
Scope: BTCUSDT 4H replay, runtime `RegimeEngine`, output range `2025-03-15 -> 2025-06-15`.

Guardrail: diagnose first, fix later. This report does not propose threshold, confirm-count, or production-code changes.

## Method

I replayed the `MIXED` cache from `2025-02-01` to preserve the same pre-April engine state as the P0.6 `MIXED` run, then wrote the requested rows to `reports/regime_diagnostic_apr_may_2025.csv`.

Raw regime classification and final `current_regime` came from the current `RegimeEngine`. Reason labels are post-hoc diagnostics only; they did not decide regime labels.

Helper script: `.tmp/r0_generate_reports.py` (diagnostic-only generator, not production code).

## Replay Composition

### Full requested range: 2025-03-15 -> 2025-06-15

Raw `_detect_regime`:

| label | bars | pct |
| --- | --- | --- |
| None | 177 | 32.0% |
| RANGING | 74 | 13.4% |
| TRENDING | 302 | 54.6% |

Current regime after hysteresis:

| label | bars | pct |
| --- | --- | --- |
| RANGING | 150 | 27.1% |
| TRENDING | 403 | 72.9% |

### Apr-May focus: 2025-04-01 -> 2025-05-31

Raw `_detect_regime`:

| label | bars | pct |
| --- | --- | --- |
| None | 104 | 28.8% |
| RANGING | 38 | 10.5% |
| TRENDING | 219 | 60.7% |

Current regime after hysteresis:

| label | bars | pct |
| --- | --- | --- |
| RANGING | 57 | 15.8% |
| TRENDING | 304 | 84.2% |

Reason labels:

| label | bars | pct |
| --- | --- | --- |
| adx_trending | 215 | 59.6% |
| ambiguous_keep_previous | 81 | 22.4% |
| atr_expansion | 4 | 1.1% |
| ranging_candidate | 38 | 10.5% |
| squeeze_candidate_missed_ratio | 23 | 6.4% |

## Narrow Replay Sample

| timestamp | close | adx | bbw_ratio_to_history_mean | raw_detect | current_regime |
| --- | --- | --- | --- | --- | --- |
| 2025-04-24 00:00 | 92673.95 | 44.74 | 2.392 | TRENDING | TRENDING |
| 2025-04-25 00:00 | 93311.83 | 39.85 | 1.401 | TRENDING | TRENDING |
| 2025-04-26 00:00 | 94739.99 | 47.76 | 0.497 | TRENDING | TRENDING |
| 2025-04-27 00:00 | 94156.21 | 43.98 | 0.485 | TRENDING | TRENDING |
| 2025-04-28 00:00 | 93849.93 | 39.66 | 0.275 | TRENDING | TRENDING |
| 2025-04-29 00:00 | 94658.76 | 34.53 | 0.264 | TRENDING | TRENDING |
| 2025-04-30 00:00 | 95032.84 | 17.54 | 0.390 | RANGING | TRENDING |
| 2025-05-01 00:00 | 94782.60 | 17.41 | 0.545 | None | TRENDING |
| 2025-05-02 00:00 | 97102.32 | 21.86 | 1.344 | None | TRENDING |
| 2025-05-03 00:00 | 96337.50 | 23.37 | 1.697 | None | TRENDING |
| 2025-05-04 00:00 | 95722.23 | 14.77 | 1.136 | None | TRENDING |
| 2025-05-05 00:00 | 94031.47 | 23.24 | 1.199 | None | TRENDING |
| 2025-05-06 00:00 | 94454.01 | 25.54 | 1.210 | TRENDING | TRENDING |
| 2025-05-07 00:00 | 96506.90 | 26.77 | 1.065 | TRENDING | TRENDING |
| 2025-05-08 00:00 | 99152.79 | 27.42 | 1.605 | TRENDING | TRENDING |
| 2025-05-09 00:00 | 102451.04 | 38.28 | 2.412 | TRENDING | TRENDING |
| 2025-05-10 00:00 | 103226.24 | 50.70 | 1.916 | TRENDING | TRENDING |
| 2025-05-11 00:00 | 104007.03 | 61.49 | 1.165 | TRENDING | TRENDING |
| 2025-05-12 00:00 | 104100.13 | 63.26 | 0.350 | TRENDING | TRENDING |
| 2025-05-13 00:00 | 101719.40 | 49.23 | 0.489 | TRENDING | TRENDING |
| 2025-05-14 00:00 | 103587.44 | 35.64 | 0.519 | TRENDING | TRENDING |
| 2025-05-15 00:00 | 102753.63 | 27.92 | 0.486 | TRENDING | TRENDING |
| 2025-05-16 00:00 | 104023.49 | 16.94 | 0.548 | RANGING | TRENDING |
| 2025-05-17 00:00 | 103508.48 | 19.99 | 0.565 | RANGING | TRENDING |
| 2025-05-18 00:00 | 103295.70 | 16.99 | 0.724 | RANGING | RANGING |
| 2025-05-19 00:00 | 103605.88 | 20.23 | 1.108 | None | RANGING |
| 2025-05-20 00:00 | 105761.92 | 24.66 | 1.426 | None | TRENDING |
| 2025-05-21 00:00 | 106843.59 | 28.60 | 1.602 | TRENDING | TRENDING |
| 2025-05-22 00:00 | 111780.84 | 38.16 | 2.281 | TRENDING | TRENDING |

## P0.6 MIXED Entry-Time TRENDING Cluster

| entry_time | symbol | side | realized_r | max_r | exit_reason | BTC 4H row | raw_detect | current_regime | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2025-04-27 06:00 | BTC | LONG | -1.08 | 0.42 | sl_hit | 2025-04-27 04:00 | TRENDING | TRENDING | adx_trending |
| 2025-04-28 04:00 | BTC | LONG | -0.06 | 1.09 | sl_hit | 2025-04-28 04:00 | TRENDING | TRENDING | adx_trending |
| 2025-05-12 17:00 | ETH | LONG | -0.61 | 0.00 | sl_hit | 2025-05-12 16:00 | TRENDING | TRENDING | adx_trending |
| 2025-05-14 10:00 | BTC | LONG | -1.02 | 0.20 | sl_hit | 2025-05-14 08:00 | TRENDING | TRENDING | adx_trending |
| 2025-05-15 14:00 | ETH | LONG | 0.47 | 1.87 | sl_hit | 2025-05-15 12:00 | TRENDING | TRENDING | adx_trending |
| 2025-05-20 20:00 | ETH | LONG | -0.01 | 0.71 | v54_structure_break | 2025-05-20 20:00 | TRENDING | TRENDING | adx_trending |

## Minimum Questions

- Did Apr-May stay TRENDING because ADX was still above threshold? **Mostly yes.** In Apr-May, `adx_trending` accounts for 215 / 361 bars, and all listed P0.6 cluster entries mapped to BTC 4H rows that were raw/current TRENDING via ADX.
- Did ATR expansion short-circuit TRENDING before BBW/SQUEEZE/RANGING could classify? **No major evidence in this slice.** `atr_expansion` accounts for 4 / 361 Apr-May bars.
- Did `_detect_regime` return `None` often enough to preserve the prior TRENDING state? **Yes, as a secondary effect.** `None` appears in 104 / 361 Apr-May bars, so ambiguity preserved prior state during parts of the fade.
- Did `_confirm_count` reset before RANGING could confirm? **Sometimes, but this was not the dominant Apr-May mechanism.** Short raw-RANGING runs that failed to promote are listed below.
- Concrete stuck case: see the next table. It is diagnostic observation only, not a patch proposal.

## Hysteresis Stuck Cases

| timestamp range | raw RANGING bars | max_confirm_count | promoted_to_RANGING |
| --- | --- | --- | --- |
| 2025-04-05 20:00 -> 2025-04-05 20:00 | 1 | 1 | no |
| 2025-04-16 08:00 -> 2025-04-16 12:00 | 2 | 2 | no |
| 2025-04-19 16:00 -> 2025-04-19 20:00 | 2 | 2 | no |
| 2025-04-30 00:00 -> 2025-04-30 00:00 | 1 | 1 | no |
| 2025-05-16 00:00 -> 2025-05-16 04:00 | 2 | 2 | no |

## Read

The Apr-May failure cluster is better described as **chop-trend still passing the TRENDING detector**, not ATR expansion. ADX stayed high enough on many BTC 4H bars to keep raw detection in TRENDING; when raw detection was ambiguous, hysteresis preserved the prior state. That explains why V54 was allowed to take trend entries inside a visually fading/consolidating area.
