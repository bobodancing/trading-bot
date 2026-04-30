# Squeeze-Release Unconfirmed First Pass

Date: `2026-04-29`

Candidate:

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter`

Purpose: test whether a BBW squeeze-release plus prior-bar unconfirmed-breakout
context can localize the partial67 late-entry defense onto the unresolved
default `RANGING` / transition surface without taxing the main bullish trend
window.

## Run

Command:

```bash
python -m extensions.Backtesting.scripts.run_candidate_review --candidate macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter
```

Artifacts:

- `extensions/Backtesting/results/macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter/`
- `reports/strategy_plugin_candidate_review.md`

Result validity:

- `backtest_run_error_count = 0` across all default windows
- `entry_stop_violations = 0` across all default windows
- StrategyRuntime central risk path was used through the candidate-review runner
- Current `StrategyRuntime` does not enforce `BTC_TREND_FILTER_ENABLED`; this
  report does not treat that filter as an active rejection source

## Default Review Matrix

| window | trades | net_pnl | max_dd_pct | run_errors | entry_stop_violations |
| --- | ---: | ---: | ---: | ---: | ---: |
| `TRENDING_UP` | 22 | +987.3493 | 4.5922 | 0 | 0 |
| `RANGING` | 1 | -45.2810 | 0.9090 | 0 | 0 |
| `MIXED` | 17 | +243.3437 | 3.0192 | 0 | 0 |
| aggregate | 40 | +1185.4120 | 4.5922 | 0 | 0 |

Runner verdict in `strategy_plugin_candidate_review.md`: `KEEP_RESEARCH_ONLY`.
That verdict only means the matrix is complete and invariant-clean; it is not a
promotion recommendation.

## Pre-Committed Gate Read

| gate | threshold | result | status |
| --- | ---: | ---: | --- |
| default `TRENDING_UP` retention | >= +1484.5085 | +987.3493 | FAIL |
| default `RANGING` repair | informative | -45.2810 | repaired versus partial67 |
| default `MIXED` retention | informative | +243.3437 | preserved versus partial67 |

The pinned cell fails before supplemental-window gates are needed because the
default `TRENDING_UP` must-pass threshold is missed by `497.1592`.

No parameter sweep should run from this result. The No-Sweep Clause remains in
force because the pinned cell did not preserve the bullish retention gate.

## Head-To-Head

Default aggregate:

| candidate | trades | net_pnl | max_dd_pct | read |
| --- | ---: | ---: | ---: | --- |
| `partial67` working baseline | 46 | +1553.9654 | 4.4059 | reference |
| `chop_trend_tightened` | 42 | +1848.6305 | 2.9860 | best aggregate localized proxy |
| `transition_aware_late_entry_filter` | 37 | +1230.6759 | 4.5977 | repaired transition surface, too selective |
| `transition_aware_tightened` | 44 | +1682.5711 | 4.4059 | leading explicit transition candidate |
| `late_entry_filter` | 16 | +1856.8086 | 1.8572 | raw defense ceiling |
| `squeeze_release_unconfirmed` | 40 | +1185.4120 | 4.5922 | repairs RANGING but overcuts trend |

Per-window:

| candidate | `TRENDING_UP` | `RANGING` | `MIXED` |
| --- | ---: | ---: | ---: |
| `partial67` | `26 / +1484.5085` | `3 / -173.8867` | `17 / +243.3437` |
| `chop_trend_tightened` | `24 / +1670.0429` | `3 / -173.8867` | `15 / +352.4744` |
| `transition_aware_late_entry_filter` | `22 / +992.0771` | `1 / -45.2810` | `14 / +283.8799` |
| `transition_aware_tightened` | `26 / +1484.5085` | `1 / -45.2810` | `17 / +243.3437` |
| `late_entry_filter` | `9 / +1401.7272` | `1 / -45.2810` | `6 / +500.3624` |
| `squeeze_release_unconfirmed` | `22 / +987.3493` | `1 / -45.2810` | `17 / +243.3437` |

## Trade-Set Attribution

Versus `partial67`:

| window | baseline-only trades | baseline-only pnl | squeeze-only trades | squeeze-only pnl | read |
| --- | ---: | ---: | ---: | ---: | --- |
| `TRENDING_UP` | 4 | +497.1592 | 0 | +0.0000 | bullish tax dominates |
| `RANGING` | 2 | -128.6057 | 0 | +0.0000 | removes two losers |
| `MIXED` | 0 | +0.0000 | 0 | +0.0000 | unchanged trade set |

The four removed default `TRENDING_UP` trades were:

| entry_time | exit_reason | pnl_usdt | read |
| --- | --- | ---: | --- |
| `2023-10-20T01:00:00+00:00` | `sl_hit` | -89.3070 | useful loser removal |
| `2023-10-20T03:00:00+00:00` | `unknown` | +107.8995 | missed winner |
| `2023-10-23T01:00:00+00:00` | `sl_hit` | -88.1867 | useful loser removal |
| `2023-10-23T03:00:00+00:00` | `unknown` | +566.7533 | missed major winner |

Net: the gate removes `-177.4937` of losers but also removes `+674.6528` of
winners, for a net bullish tax of `-497.1592`.

Versus `transition_aware_tightened`, the squeeze-release candidate differs only
in default `TRENDING_UP`: it removes the same four trades above and loses the
same `497.1592` of net PnL. `RANGING` and `MIXED` are identical.

Versus the first `transition_aware_late_entry_filter`, the squeeze-release
candidate is not a clean improvement:

- `TRENDING_UP`: +987.3493 versus +992.0771
- `RANGING`: identical at -45.2810
- `MIXED`: restores three trades, but those three add `-40.5362`

## Interpretation

What worked:

- default `RANGING` was repaired from `3 / -173.8867` to `1 / -45.2810`
- default `MIXED` stayed identical to the `partial67` working baseline
- run safety is clean: no run errors and no stop invariant violations

What failed:

- default `TRENDING_UP` fell from `26 / +1484.5085` to `22 / +987.3493`
- aggregate default PnL fell below `partial67`, `transition_aware_tightened`,
  `chop_trend_tightened`, and the raw `late_entry_filter`
- the mechanism behaves closer to the too-selective first
  `transition_aware_late_entry_filter` than to the narrowed
  `transition_aware_tightened` pass

Best read:

- squeeze-release plus unconfirmed breakout is a real defensive signal for the
  default `RANGING` cell
- but at the pinned thresholds it is too broad in clean bullish tape
- because it fails the pre-committed default `TRENDING_UP` retention gate, it
  should not advance to sweep

## Decision

- keep as research evidence only
- do not sweep `squeeze_trough_pctrank_max`
- do not promote or stack with `transition_aware_tightened`
- keep `transition_aware_tightened_late_entry_filter` as the leading explicit
  transition-surface candidate

References:

- [candidate review](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/strategy_plugin_candidate_review.md:1>)
- [squeeze-release spec](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/plans/cartridge_spec_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter.md:1>)
- [transition-aware tightening](</C:/Users/user/Documents/tradingbot/strategy-runtime-reset/reports/macd_signal_btc_4h_trending_up_transition_aware_tightening.md:1>)
