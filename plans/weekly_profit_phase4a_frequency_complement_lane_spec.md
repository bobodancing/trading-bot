# Weekly Profit Phase 4A Frequency Complement Lane Spec

Date: 2026-05-12
Branch: `codex/post-promotion-control-20260430`
Status: `PHASE_4A_LANE_SELECTED`

## Executive Read

Selected lane: `frequency_complement_low_overlap` with discussion option `trend_dominant_silent_week_companion`. The target is still not a runtime promotion; it is a bounded research lane aimed at full silent zero-entry weeks.

The strongest evidence is that full zero-entry weeks also have zero promoted lane-race activity. This points to candidate silence, not just post-signal blocking, so the first research question is what independent signal family can cover those weeks without overlapping existing legs.

## Baseline Gap Metrics

| metric | value |
| --- | ---: |
| full weeks | 16 |
| full active-entry weeks | 7 |
| full active-entry ratio | 0.4375 |
| full zero-entry weeks | 9 |
| full silent zero-entry weeks | 9 |
| full silent zero-entry ratio | 0.5625 |
| contract-grade participation-trigger packets | 7 |
| full weeks with promoted lane-race activity | 7 |

## Silent Zero-Entry Regime Mix

| item | value |
| --- | ---: |
| regime bar counts | `{"RANGING": 136, "TRENDING": 242}` |
| regime bar ratio | `{"RANGING": 0.3598, "TRENDING": 0.6402}` |
| dominant-regime week counts | `{"RANGING": 3, "TRENDING": 6}` |

## Silent Full Zero-Entry Weeks

| week_start | entries | lane-race events | dominant regime | regime bars | packet state | packet triggers |
| --- | ---: | ---: | --- | --- | --- | --- |
| `2026-01-05` | 0 | 0 | `TRENDING` | `{"RANGING": 5, "TRENDING": 37}` | `continue` | rolling_8w_not_complete_observe_only |
| `2026-01-19` | 0 | 0 | `TRENDING` | `{"RANGING": 8, "TRENDING": 34}` | `continue` | rolling_8w_not_complete_observe_only |
| `2026-01-26` | 0 | 0 | `TRENDING` | `{"TRENDING": 42}` | `continue` | rolling_8w_not_complete_observe_only |
| `2026-02-02` | 0 | 0 | `TRENDING` | `{"TRENDING": 42}` | `continue` | rolling_8w_not_complete_observe_only |
| `2026-02-16` | 0 | 0 | `RANGING` | `{"RANGING": 42}` | `continue` | rolling_8w_contains_partial_review_week_observe_only |
| `2026-02-23` | 0 | 0 | `TRENDING` | `{"RANGING": 10, "TRENDING": 32}` | `reopen_research` | active_entry_week_ratio_8w, rolling_8w_entry_trade_count |
| `2026-03-02` | 0 | 0 | `RANGING` | `{"RANGING": 42}` | `reopen_research` | active_entry_week_ratio_8w, rolling_8w_entry_trade_count, zero_entry_week_streak |
| `2026-03-09` | 0 | 0 | `RANGING` | `{"RANGING": 23, "TRENDING": 19}` | `reopen_research` | active_entry_week_ratio_8w, rolling_8w_entry_trade_count, zero_entry_week_streak |
| `2026-04-06` | 0 | 0 | `TRENDING` | `{"RANGING": 6, "TRENDING": 36}` | `reopen_research` | active_entry_week_ratio_8w, rolling_8w_entry_trade_count |

## Existing Promoted Activity

| item | value |
| --- | ---: |
| promoted lane-race candidate counts on active weeks | `{"donchian_range_fade_4h_range_width_cv_013": 16, "donchian_range_fade_4h_range_width_cv_013_short": 12, "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter": 16}` |
| promoted slot active-week counts | `{"Slot A LONG": 2, "Slot B LONG": 3, "Slot B SHORT": 2}` |

## Lane Spec

| field | value |
| --- | --- |
| lane id | `frequency_complement_low_overlap` |
| objective | Add participation in full zero-entry weeks where promoted legs emitted no lane-race activity, while preserving the existing after-fee and risk profile. |
| primary target | Silent full zero-entry weeks, not partial boundary weeks and not weeks where promoted Slot A / Slot B candidates already fired. |
| first search bias | Trend-dominant or mixed silent weeks first, because silent zero-entry regime bars are more TRENDING than RANGING in the current evidence. |
| selected discussion option | `trend_dominant_silent_week_companion` |
| selected option reason | Ruei selected option 1 after the Phase 4A lane discussion. It targets the largest silent-week regime bucket before any range or mixed-transition research expansion. |
| candidate contract | `plans/weekly_profit_phase4a_trend_dominant_silent_week_companion_spec.md` |

## Acceptance Gates

- Convert at least 3 full silent zero-entry weeks into active-entry weeks in the primary window.
- Reduce contract-grade reopen_research packets from 7 / 9 to 3 / 9 or fewer.
- Keep latest contract-grade packet state at investigate or better, ideally continue.
- Keep combined primary-window net after-fee estimate at or above the promoted baseline.
- Keep rolling 8w net after-fee PnL positive in every contract-grade packet.
- Keep worst-week loss above the -7% independent pause line and portfolio drawdown at or below 8%.
- Keep at least 70% of new candidate entries on baseline silent or zero-entry weeks.
- Do not create same-symbol same-candle overlap with promoted entries.

## Hard Exclusions

- Do not change promoted runtime defaults.
- Do not loosen thresholds in existing promoted strategies.
- Do not activate scanner runtime consumption.
- Do not reopen legacy RSI2 / BB / Slot A SHORT lanes by default.
- Do not bypass StrategyPlugin, central RiskPlan, arbiter, router, or execution handoff.

## Discussion Options

| rank | option | reason |
| ---: | --- | --- |
| 1 | `trend_dominant_silent_week_companion` | Most silent zero-entry regime bars are TRENDING, yet promoted Slot A did not participate in many of those full weeks. |
| 2 | `range_silent_week_companion` | Several silent weeks are RANGING-dominant, but existing Donchian fade legs did not fire; this is secondary because positive-week density is already a watch item. |
| 3 | `mixed_transition_attribution_probe` | Mixed weeks may reveal transition gaps, but they need attribution before becoming a strategy candidate. |

## Decision Record

`trend_dominant_silent_week_companion` is selected. Implementation must start from the candidate contract path above and must not change runtime defaults.
