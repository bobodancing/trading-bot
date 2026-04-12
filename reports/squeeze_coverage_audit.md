# R0 Report B: SQUEEZE Coverage Audit

Generated: 2026-04-12
Scope: four P0.6 BTCUSDT 4H validation windows.

Guardrail: diagnose first, fix later. This report does not propose threshold, confirm-count, or production-code changes.

Percentile scope: **primary percentiles are per-window**. **Secondary percentiles are pooled, timestamp-deduped cross-window** sanity checks only.

Helper script: `.tmp/r0_generate_reports.py` (diagnostic-only generator, not production code).

## Coverage Summary

| window | bars | raw_SQUEEZE | current_SQUEEZE | low_BBW_primary_lt20 | current_TRENDING | current_RANGING |
| --- | --- | --- | --- | --- | --- | --- |
| TRENDING_UP | 1093 | 0 | 0 | 215 | 906 (82.9%) | 187 (17.1%) |
| TRENDING_DOWN | 1087 | 0 | 0 | 214 | 804 (74.0%) | 283 (26.0%) |
| RANGING | 541 | 0 | 0 | 105 | 355 (65.6%) | 186 (34.4%) |
| MIXED | 1267 | 0 | 0 | 250 | 898 (70.9%) | 369 (29.1%) |

Pooled deduped bars: `3639`. Window-occurrence bars: `3988`. Raw SQUEEZE tags: `0`. Current-regime SQUEEZE bars: `0`.

## Missed-Reason Summary For Low BBW Candidates

Low BBW candidate = primary per-window `BBW_percentile < 20`.

| reason | low_BBW_candidate_bars | pct_of_low_candidates |
| --- | --- | --- |
| bbw_ratio_too_high | 565 | 72.1% |
| promoted_to_TRENDING_via_adx | 219 | 27.9% |

## Top Primary Low-BBW Candidates

Full candidate CSV: `reports/squeeze_coverage_candidates.csv`.

| window | timestamp | close | adx | bbw | primary_bbw_percentile | pooled_bbw_percentile | bbw_ratio_to_history_mean | atr_ratio_20 | raw_detect | current_regime | miss_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TRENDING_UP | 2023-10-15 00:00 | 26880.46 | 21.72 | 0.01076 | 0.00% | 0.11% | 0.326 | 0.776 | None | TRENDING | bbw_ratio_too_high |
| RANGING | 2025-03-23 16:00 | 85011.19 | 16.35 | 0.01821 | 0.00% | 2.93% | 0.411 | 0.736 | RANGING | RANGING | bbw_ratio_too_high |
| MIXED | 2025-06-29 00:00 | 107210.78 | 17.56 | 0.01032 | 0.00% | 0.06% | 0.176 | 0.711 | RANGING | RANGING | bbw_ratio_too_high |
| TRENDING_DOWN | 2026-01-11 16:00 | 90690.80 | 17.17 | 0.00988 | 0.00% | 0.00% | 0.222 | 0.692 | RANGING | RANGING | bbw_ratio_too_high |
| MIXED | 2025-06-29 04:00 | 107402.18 | 14.52 | 0.01035 | 0.08% | 0.08% | 0.179 | 0.688 | RANGING | RANGING | bbw_ratio_too_high |
| TRENDING_UP | 2023-10-15 04:00 | 26882.52 | 20.16 | 0.01080 | 0.09% | 0.14% | 0.331 | 0.739 | None | TRENDING | bbw_ratio_too_high |
| TRENDING_DOWN | 2026-01-11 20:00 | 91013.65 | 16.97 | 0.01022 | 0.09% | 0.03% | 0.234 | 0.721 | RANGING | RANGING | bbw_ratio_too_high |
| MIXED | 2025-06-28 20:00 | 107296.79 | 18.43 | 0.01098 | 0.16% | 0.25% | 0.185 | 0.725 | RANGING | RANGING | bbw_ratio_too_high |
| TRENDING_UP | 2023-10-14 20:00 | 26852.48 | 24.10 | 0.01080 | 0.19% | 0.17% | 0.323 | 0.786 | None | TRENDING | bbw_ratio_too_high |
| TRENDING_DOWN | 2026-01-11 12:00 | 90875.79 | 16.82 | 0.01114 | 0.19% | 0.31% | 0.245 | 0.681 | RANGING | RANGING | bbw_ratio_too_high |
| RANGING | 2025-01-13 04:00 | 93590.24 | 23.96 | 0.01896 | 0.19% | 3.63% | 0.261 | 0.869 | None | TRENDING | bbw_ratio_too_high |
| MIXED | 2025-06-28 16:00 | 107225.74 | 18.81 | 0.01126 | 0.24% | 0.39% | 0.187 | 0.750 | RANGING | RANGING | bbw_ratio_too_high |
| TRENDING_UP | 2023-10-15 08:00 | 26852.47 | 21.50 | 0.01081 | 0.28% | 0.20% | 0.336 | 0.726 | None | TRENDING | bbw_ratio_too_high |
| TRENDING_DOWN | 2026-01-11 08:00 | 90754.99 | 17.61 | 0.01116 | 0.28% | 0.34% | 0.241 | 0.682 | RANGING | RANGING | bbw_ratio_too_high |
| MIXED | 2025-06-28 12:00 | 107449.28 | 18.78 | 0.01128 | 0.32% | 0.42% | 0.186 | 0.771 | RANGING | RANGING | bbw_ratio_too_high |
| TRENDING_UP | 2023-10-14 16:00 | 26864.29 | 23.84 | 0.01084 | 0.37% | 0.22% | 0.321 | 0.801 | None | TRENDING | bbw_ratio_too_high |
| TRENDING_DOWN | 2026-01-11 04:00 | 90710.79 | 19.47 | 0.01120 | 0.37% | 0.36% | 0.238 | 0.709 | RANGING | RANGING | bbw_ratio_too_high |
| RANGING | 2025-02-17 00:00 | 96215.33 | 18.33 | 0.01991 | 0.38% | 4.47% | 0.617 | 0.790 | RANGING | RANGING | bbw_ratio_too_high |
| MIXED | 2025-06-28 08:00 | 107373.39 | 19.42 | 0.01266 | 0.40% | 0.47% | 0.206 | 0.782 | RANGING | RANGING | bbw_ratio_too_high |
| TRENDING_UP | 2023-10-15 12:00 | 26898.87 | 20.31 | 0.01104 | 0.47% | 0.28% | 0.347 | 0.748 | None | TRENDING | bbw_ratio_too_high |

## Chart Review Queue

| range | windows | bars | lowest_primary_bbw_pct | reasons |
| --- | --- | --- | --- | --- |
| 2023-10-09 04:00 -> 2023-10-09 04:00 | TRENDING_UP | 1 | 1.68% | bbw_ratio_too_high |
| 2023-10-14 12:00 -> 2023-10-15 20:00 | TRENDING_UP | 9 | 0.00% | bbw_ratio_too_high, promoted_to_TRENDING_via_adx |
| 2023-11-13 12:00 -> 2023-11-13 16:00 | TRENDING_UP | 2 | 0.74% | bbw_ratio_too_high |
| 2023-12-23 16:00 -> 2023-12-24 16:00 | TRENDING_UP | 7 | 0.56% | bbw_ratio_too_high |
| 2024-02-04 20:00 -> 2024-02-05 04:00 | TRENDING_UP | 3 | 1.58% | bbw_ratio_too_high, promoted_to_TRENDING_via_adx |
| 2025-01-13 04:00 -> 2025-01-13 04:00 | RANGING | 1 | 0.19% | bbw_ratio_too_high |
| 2025-01-26 16:00 -> 2025-01-26 16:00 | RANGING | 1 | 0.77% | bbw_ratio_too_high |
| 2025-02-10 20:00 -> 2025-02-11 00:00 | RANGING | 2 | 0.96% | bbw_ratio_too_high |
| 2025-02-16 16:00 -> 2025-02-17 04:00 | RANGING | 4 | 0.38% | bbw_ratio_too_high |
| 2025-03-23 12:00 -> 2025-03-23 16:00 | RANGING | 2 | 0.00% | bbw_ratio_too_high |

## Minimum Yes/No Answer

Does this audit show likely real squeeze candidates that current RegimeEngine failed to tag?

**Answer: yes.** There are local low-BBW bars below the 5th primary percentile with ADX below the TRENDING threshold, yet no raw/current SQUEEZE tag. Most are blocked by the extreme `bbw_ratio < 0.15` guard rather than by missing data.

This is not a threshold-change recommendation. Ruei should chart-review the queue above before any R1/R2 decision treats these as confirmed SQUEEZE regimes.
