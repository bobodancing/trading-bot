# Weekly Profit Phase 4A Trend Companion Precision Attribution

Date: 2026-05-14
Branch: `codex/post-promotion-control-20260430`
Verdict: `PRECISION_FILTER_FOUND_REQUIRES_PLUGIN_BACKTEST`

## Executive Read

Recommended filter: `btc_recovery_band_trend_breadth`. It keeps 9 / 11 candidates on baseline silent-or-zero weeks and hits 5 silent zero-entry weeks.

Projected active full weeks move from 7 / 16 to 12 / 16 if candidate entries survive combined backtest routing and position constraints.

## Evaluated Filters

| filter | candidates | silent/zero ratio | silent weeks hit | active ratio | overlaps | pass |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `btc_recovery_band_trend_breadth` | 11 | 0.8182 | 5 | 0.1818 | 0 | `True` |
| `supertrend_deep_recovery_precision` | 5 | 1.0000 | 4 | 0.0000 | 0 | `True` |
| `supertrend_deep_recovery_first_week` | 4 | 1.0000 | 4 | 0.0000 | 0 | `True` |
| `btc_recovery_band_first_week` | 7 | 0.7143 | 5 | 0.2857 | 0 | `True` |

## Recommended Filter

| field | value |
| --- | --- |
| filter id | `btc_recovery_band_trend_breadth` |
| mechanisms | `["supertrend_flip_4h_trending_up_frequency_companion", "aroon_break_hh_4h_trending_up_frequency_companion"]` |
| symbols | `["BTC/USDT"]` |
| ema spread band | `-0.08 <= ema_spread_1d <= -0.01` |
| distance cap | `distance_atr <= 3.0` |
| rank policy | `none` |
| rationale | BTC-only trend recovery band: daily EMA spread is still negative but no longer panic-deep, and entry is not more than 3 ATR away from the mechanism anchor. |

## Selected Candidate Weeks

| bucket | weeks |
| --- | --- |
| silent zero-entry | `["2026-01-05", "2026-01-26", "2026-02-02", "2026-03-09", "2026-04-06"]` |
| active spillover | `["2026-03-16", "2026-03-30"]` |

## Selected Candidates

| timestamp | symbol | mechanism | silent/zero | active | ema_spread_1d | distance_atr |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `2026-01-05T00:00:00Z` | `BTC/USDT` | `aroon_break_hh_4h_trending_up_frequency_companion` | `True` | `False` | -0.0282 | 1.350 |
| `2026-01-05T12:00:00Z` | `BTC/USDT` | `aroon_break_hh_4h_trending_up_frequency_companion` | `True` | `False` | -0.0282 | 0.669 |
| `2026-01-05T16:00:00Z` | `BTC/USDT` | `aroon_break_hh_4h_trending_up_frequency_companion` | `True` | `False` | -0.0282 | 0.345 |
| `2026-01-28T08:00:00Z` | `BTC/USDT` | `aroon_break_hh_4h_trending_up_frequency_companion` | `True` | `False` | -0.0101 | 0.585 |
| `2026-02-08T12:00:00Z` | `BTC/USDT` | `supertrend_flip_4h_trending_up_frequency_companion` | `True` | `False` | -0.0690 | 2.860 |
| `2026-03-10T12:00:00Z` | `BTC/USDT` | `aroon_break_hh_4h_trending_up_frequency_companion` | `True` | `False` | -0.0652 | 0.035 |
| `2026-03-13T08:00:00Z` | `BTC/USDT` | `aroon_break_hh_4h_trending_up_frequency_companion` | `True` | `False` | -0.0546 | 0.203 |
| `2026-03-16T20:00:00Z` | `BTC/USDT` | `aroon_break_hh_4h_trending_up_frequency_companion` | `False` | `True` | -0.0430 | 0.357 |
| `2026-04-01T04:00:00Z` | `BTC/USDT` | `aroon_break_hh_4h_trending_up_frequency_companion` | `False` | `True` | -0.0310 | 0.097 |
| `2026-04-07T20:00:00Z` | `BTC/USDT` | `aroon_break_hh_4h_trending_up_frequency_companion` | `True` | `False` | -0.0276 | 1.479 |
| `2026-04-11T16:00:00Z` | `BTC/USDT` | `aroon_break_hh_4h_trending_up_frequency_companion` | `True` | `False` | -0.0143 | 0.297 |

## Attribution Read

The useful candidates cluster in a recovery band where completed 1d EMA spread is negative, but not panic-deep. This is not a classic daily trend-continuation entry; it is a 4h bullish recovery trigger inside a still-negative daily spread.

| group | count | ema_spread median | distance_atr median |
| --- | ---: | ---: | ---: |
| `silent_or_zero` | 34 | -0.0599 | 0.6149 |
| `active_spillover` | 28 | -0.0307 | 0.5612 |

## Guardrails

- This is a pre-plugin precision filter, not runtime promotion.
- The filter uses only candle-derived fields available to a plugin: symbol, mechanism trigger, completed 1d EMA spread, and ATR-normalized distance.
- Completed 1d EMA spread is computed with the same rolling 1d snapshot semantics used by StrategyRuntime backtests.
- It does not use packet_state, baseline week labels, or promoted strategy outcomes as runtime inputs.
- Next step is a StrategyPlugin candidate plus A+B+candidate combined weekly packet evaluation.
