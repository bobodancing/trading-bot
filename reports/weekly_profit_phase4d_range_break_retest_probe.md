# Weekly Profit Phase 4D Range-Break Retest Probe

Date: 2026-05-14
Branch: `codex/post-promotion-control-20260430`
Verdict: `RANGE_BREAK_RETEST_PROBE_PASS_RESEARCH_PLUGIN_CANDIDATE`

## Executive Read

Selected variant `range_break_retest_conservative_30` hit 4 silent zero-entry weeks with silent-or-zero ratio `0.8333`.

This is a research-plugin candidate, not a runtime promotion. The next proof point is A+B+candidate combined weekly packet evaluation.

## Gate Results

| gate | pass |
| --- | ---: |
| `candidate_count_between_3_and_20` | `True` |
| `silent_week_hit_count_gte_3` | `True` |
| `silent_or_zero_candidate_ratio_gte_0p70` | `True` |
| `same_symbol_same_candle_overlap_eq_0` | `True` |
| `active_week_candidate_ratio_lte_0p30` | `True` |
| `market_timestamp_source_ok` | `True` |

## Selected Metrics

| metric | value |
| --- | ---: |
| candidates | 6 |
| silent zero-entry weeks hit | 4 |
| zero-entry weeks hit | 4 |
| active-entry weeks hit | 1 |
| silent-or-zero candidate ratio | 0.8333 |
| active-week candidate ratio | 0.1667 |
| same-symbol same-candle promoted overlaps | 0 |
| candidates by side | `{"LONG": 4, "SHORT": 2}` |
| candidates by symbol | `{"BTC/USDT": 3, "ETH/USDT": 3}` |

## Variant Comparison

| variant | candidates | silent weeks | silent/zero ratio | active ratio | overlaps | pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `range_break_retest_conservative_30` | 6 | 4 | 0.8333 | 0.1667 | 0 | `True` |
| `range_break_hold_conservative_30` | 6 | 4 | 0.8333 | 0.1667 | 0 | `True` |
| `range_break_retest_conservative_20` | 11 | 3 | 0.4545 | 0.5455 | 0 | `False` |
| `range_break_retest_broad_30` | 44 | 9 | 0.5455 | 0.3636 | 0 | `False` |

## Week Hits

| bucket | weeks |
| --- | --- |
| silent zero-entry | `["2026-02-16", "2026-03-02", "2026-03-09", "2026-04-06"]` |
| zero-entry | `["2026-02-16", "2026-03-02", "2026-03-09", "2026-04-06"]` |
| active-entry | `["2026-03-23"]` |

## Selected Candidates

| timestamp | symbol | side | breakout | lag | width_cv | bbw_pct | adx | break_atr | silent/zero | active |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `2026-02-18T20:00:00Z` | `BTC/USDT` | `SHORT` | `2026-02-18T16:00:00Z` | 1 | 0.1030 | 2.0 | 14.34 | 0.3754 | `True` | `False` |
| `2026-03-04T12:00:00Z` | `BTC/USDT` | `LONG` | `2026-03-04T08:00:00Z` | 1 | 0.0072 | 38.0 | 14.79 | 0.6346 | `True` | `False` |
| `2026-03-23T00:00:00Z` | `BTC/USDT` | `SHORT` | `2026-03-22T20:00:00Z` | 1 | 0.0365 | 40.0 | 33.02 | 0.2648 | `False` | `True` |
| `2026-03-05T00:00:00Z` | `ETH/USDT` | `LONG` | `2026-03-04T12:00:00Z` | 3 | 0.0999 | 18.0 | 14.38 | 0.9091 | `True` | `False` |
| `2026-03-13T04:00:00Z` | `ETH/USDT` | `LONG` | `2026-03-13T00:00:00Z` | 1 | 0.0239 | 20.0 | 16.36 | 0.5385 | `True` | `False` |
| `2026-04-11T20:00:00Z` | `ETH/USDT` | `LONG` | `2026-04-11T16:00:00Z` | 1 | 0.0767 | 30.0 | 36.27 | 1.1237 | `True` | `False` |

## Guardrails

- This is pre-plugin diagnostic evidence only.
- Runtime defaults, promoted strategies, scanner settings, credentials, and risk caps remain unchanged.
- Baseline week labels are used only for offline attribution; the proposed plugin inputs are candle-derived.

## Next Action

Implement a research-only StrategyPlugin candidate and run A+B+candidate combined weekly packet evaluation.
