# Weekly Profit Phase 4A Trend Companion Probe

Date: 2026-05-14
Branch: `codex/post-promotion-control-20260430`
Verdict: `SUPER_TREND_PROBE_FAIL_PIVOT_OR_REVIEW`
Trend gate mode: `strict_1d_ema`

## Executive Read

`supertrend_flip_4h_trending_up_frequency_companion` generated 2 synthetic candidates and hit 0 silent zero-entry weeks.

This probe is pre-plugin evidence only. It does not change runtime defaults.

## Gate Results

| gate | pass |
| --- | ---: |
| `silent_week_hit_count_gte_3` | `False` |
| `silent_or_zero_candidate_ratio_gte_0p70` | `False` |
| `same_symbol_same_candle_overlap_eq_0` | `True` |
| `active_week_candidate_ratio_lte_0p30` | `False` |
| `market_timestamp_source_ok` | `True` |

## Metrics

| metric | value |
| --- | ---: |
| candidates | 2 |
| silent zero-entry weeks hit | 0 |
| zero-entry weeks hit | 0 |
| active-entry weeks hit | 1 |
| silent-or-zero candidate ratio | 0.0 |
| active-week candidate ratio | 1.0 |
| same-symbol same-candle promoted overlaps | 0 |
| candidates by dominant regime | `{"RANGING": 2}` |
| candidates by packet state | `{"investigate": 2}` |

## Week Hits

| bucket | weeks |
| --- | --- |
| silent zero-entry | `[]` |
| zero-entry | `[]` |
| active-entry | `["2026-04-20"]` |

## Next Action

Implement the research plugin only if the strict verdict passes. Diagnostic passes require a contract update and strict review before plugin work.
