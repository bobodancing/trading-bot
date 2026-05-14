# Weekly Profit Phase 4A Trend Companion Probe

Date: 2026-05-12
Branch: `codex/post-promotion-control-20260430`
Verdict: `SUPER_TREND_PROBE_FAIL_PIVOT_OR_REVIEW`
Trend gate mode: `diagnostic_no_1d_ema`

## Executive Read

`supertrend_flip_4h_trending_up_frequency_companion` generated 20 synthetic candidates and hit 5 silent zero-entry weeks.

This probe is pre-plugin evidence only. It does not change runtime defaults.

## Gate Results

| gate | pass |
| --- | ---: |
| `silent_week_hit_count_gte_3` | `True` |
| `silent_or_zero_candidate_ratio_gte_0p70` | `False` |
| `same_symbol_same_candle_overlap_eq_0` | `True` |
| `active_week_candidate_ratio_lte_0p30` | `False` |
| `market_timestamp_source_ok` | `True` |

## Metrics

| metric | value |
| --- | ---: |
| candidates | 20 |
| silent zero-entry weeks hit | 5 |
| zero-entry weeks hit | 5 |
| active-entry weeks hit | 6 |
| silent-or-zero candidate ratio | 0.45 |
| active-week candidate ratio | 0.5 |
| same-symbol same-candle promoted overlaps | 0 |
| candidates by dominant regime | `{"RANGING": 5, "TRENDING": 15}` |
| candidates by packet state | `{"continue": 7, "investigate": 4, "reopen_research": 9}` |

## Week Hits

| bucket | weeks |
| --- | --- |
| silent zero-entry | `["2026-01-26", "2026-02-02", "2026-02-23", "2026-03-02", "2026-03-09"]` |
| zero-entry | `["2026-01-26", "2026-02-02", "2026-02-23", "2026-03-02", "2026-03-09"]` |
| active-entry | `["2026-01-12", "2026-02-09", "2026-03-23", "2026-03-30", "2026-04-13", "2026-04-20"]` |

## Next Action

Implement the research plugin only if the strict verdict passes. Diagnostic passes require a contract update and strict review before plugin work.
