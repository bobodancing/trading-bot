# Weekly Profit Phase 4A Trend Companion Probe Review

Date: 2026-05-12
Branch: `codex/post-promotion-control-20260430`
Decision: `PRECISION_FILTER_FOUND_REQUIRES_PLUGIN_BACKTEST`

## Finding

The selected `trend_dominant_silent_week_companion` lane has coverage material.
Raw strict and diagnostic probes are not clean enough, but precision attribution
found a researchable BTC recovery-band filter.

Strict `1d EMA` versions miss the silent-week target entirely. Diagnostic
no-1d-gate versions hit 5-6 silent zero-entry weeks, but they spill too heavily
into already-active weeks and therefore fail the low-overlap frequency contract.

## Probe Matrix

| mechanism | trend gate mode | candidates | silent weeks hit | silent-or-zero ratio | active-week ratio | same-candle overlaps | verdict |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `supertrend_flip_4h_trending_up_frequency_companion` | `strict_1d_ema` | 2 | 0 | 0.0 | 1.0 | 0 | `SUPER_TREND_PROBE_FAIL_PIVOT_OR_REVIEW` |
| `aroon_break_hh_4h_trending_up_frequency_companion` | `strict_1d_ema` | 4 | 0 | 0.0 | 1.0 | 0 | `AROON_PROBE_FAIL_PIVOT_OR_REVIEW` |
| `supertrend_flip_4h_trending_up_frequency_companion` | `diagnostic_no_1d_ema` | 20 | 5 | 0.45 | 0.5 | 0 | `SUPER_TREND_PROBE_FAIL_PIVOT_OR_REVIEW` |
| `aroon_break_hh_4h_trending_up_frequency_companion` | `diagnostic_no_1d_ema` | 46 | 6 | 0.5435 | 0.3913 | 2 | `AROON_PROBE_FAIL_PIVOT_OR_REVIEW` |

## Precision Filter

`btc_recovery_band_trend_breadth` passes the pre-plugin precision contract:

- mechanisms: `supertrend_flip_4h_trending_up_frequency_companion` OR
  `aroon_break_hh_4h_trending_up_frequency_companion`
- symbol: `BTC/USDT`
- completed 1d EMA spread: `-0.08 <= ema_spread_1d <= -0.01`
- distance cap: `distance_atr <= 3.0`
- result: 11 candidates, 9 on silent-or-zero weeks, ratio 0.8182
- silent zero-entry weeks hit: 5
- active-week spillover: 2 candidates across 2 already-active weeks
- same-symbol same-candle promoted overlaps: 0
- projected active full weeks: 7 / 16 to 12 / 16 if combined backtest allows

## Strict Review

No raw probe passes all go/no-go gates:

- `strict_1d_ema` keeps trend discipline but fails participation coverage.
- `diagnostic_no_1d_ema` finds silent-week candidates but fails the 70% silent-or-zero concentration gate.
- Aroon diagnostic also creates 2 same-symbol same-candle promoted overlaps.
- The precision filter uses only plugin-available candle features. It does not
  use `packet_state`, baseline week labels, or promoted outcomes as runtime
  inputs.
- The thesis changed from daily trend continuation to 4h bullish recovery inside
  a still-negative completed daily EMA spread. That needs combined backtest
  proof before any promotion talk.

## Next Cook

Implement only a research plugin/backtest candidate for the precision filter:

- add focused plugin tests for both mechanism triggers and the shared recovery
  band filter.
- run A+B+candidate combined attribution through the Phase 3 weekly packet
  evaluator.
- keep this as research evidence only; no runtime defaults, promoted thresholds,
  or scanner behavior change.
