# Weekly Profit Phase 4A Trend-Dominant Silent-Week Companion Spec

Date: 2026-05-12
Branch: `codex/post-promotion-control-20260430`
Status: `PHASE_4A_SELECTED_CANDIDATE_CONTRACT`

## Decision

Ruei selected Phase 4A option `1`: `trend_dominant_silent_week_companion`.

This is a research candidate contract, not runtime promotion. It must not change
`Config.ENABLED_STRATEGIES`, promoted plugin params, scanner consumption, risk
sizing, credentials, or execution handoff.

## Evidence Anchor

| metric | value |
| --- | ---: |
| full weeks reviewed | 16 |
| full active-entry weeks | 7 |
| full zero-entry weeks | 9 |
| full silent zero-entry weeks | 9 |
| TRENDING bars in silent zero-entry weeks | 242 |
| RANGING bars in silent zero-entry weeks | 136 |
| trend-dominant silent zero-entry weeks | 6 |
| range-dominant silent zero-entry weeks | 3 |

The important read is that every full zero-entry week also had zero promoted
lane-race activity. The current gap is signal-family silence, not primarily
router blocking or risk rejection. Loosening promoted thresholds would attack
the wrong failure mode.

## Product Objective

Add enough independent trend-side participation to improve weekly active-entry
density without damaging the promoted portfolio's after-fee expectancy.

Primary KPI movement:

- Convert at least 3 full silent zero-entry weeks into active-entry weeks.
- Reduce contract-grade `reopen_research` packets from 7 / 9 to 3 / 9 or fewer.
- Keep rolling 8w net after-fee PnL positive in every contract-grade packet.
- Keep worst week above the independent `-7%` pause line.
- Keep at least 70% of new entries on baseline silent or zero-entry weeks.

## Candidate Family

| field | value |
| --- | --- |
| candidate family | `trend_dominant_silent_week_companion` |
| first mechanism | `supertrend_flip_4h_trending_up_frequency_companion` |
| backup mechanism | `aroon_break_hh_4h_trending_up_frequency_companion` |
| parked mechanism | `donchian_break_retest_up_4h`, only if trend-breadth probes fail and transition attribution justifies it |
| side | LONG only for first pass |
| symbols | fixed `BTC/USDT`, `ETH/USDT`; no scanner universe |
| entry timeframe | `4h` |
| higher-timeframe gate | `1d` trend alignment |
| classification if implemented | `active_research` |

The first mechanism is intentionally simple because `supertrend` is already in
the indicator registry. That does not make it automatically good. The main risk
is that SuperTrend flips may be too sparse to cover already-established trend
weeks. Therefore a coverage probe is mandatory before implementing the plugin.

## Probe Result Update

The first probes are complete. Neither current mechanism is approved for plugin
implementation.

| probe | trend gate mode | candidates | silent zero-entry weeks hit | silent-or-zero candidate ratio | active-week candidate ratio | same-candle promoted overlaps | verdict |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `supertrend_flip_4h_trending_up_frequency_companion` | `strict_1d_ema` | 2 | 0 | 0.0 | 1.0 | 0 | `SUPER_TREND_PROBE_FAIL_PIVOT_OR_REVIEW` |
| `aroon_break_hh_4h_trending_up_frequency_companion` | `strict_1d_ema` | 4 | 0 | 0.0 | 1.0 | 0 | `AROON_PROBE_FAIL_PIVOT_OR_REVIEW` |
| `supertrend_flip_4h_trending_up_frequency_companion` | `diagnostic_no_1d_ema` | 20 | 5 | 0.45 | 0.5 | 0 | `SUPER_TREND_PROBE_FAIL_PIVOT_OR_REVIEW` |
| `aroon_break_hh_4h_trending_up_frequency_companion` | `diagnostic_no_1d_ema` | 46 | 6 | 0.5435 | 0.3913 | 2 | `AROON_PROBE_FAIL_PIVOT_OR_REVIEW` |

Strict `1d EMA` gating is too sparse for the weekly frequency gap. Removing the
gate proves there is trend-side coverage material, but the spillover into
already-active weeks is too high. The next step is precision attribution on the
diagnostic candidates, not strategy implementation.

## Precision Attribution Update

Precision attribution found one implementable pre-plugin filter that passes the
Phase 4A precision contract:

| field | value |
| --- | --- |
| filter id | `btc_recovery_band_trend_breadth` |
| mechanisms | `supertrend_flip_4h_trending_up_frequency_companion` OR `aroon_break_hh_4h_trending_up_frequency_companion` |
| symbol | `BTC/USDT` only |
| completed 1d EMA spread band | `-0.08 <= ema_spread_1d <= -0.01` |
| distance cap | `distance_atr <= 3.0` |
| candidates | 11 |
| silent-or-zero candidate ratio | 0.8182 |
| silent zero-entry weeks hit | 5 |
| active-week candidate ratio | 0.1818 |
| same-candle promoted overlaps | 0 |
| projected active full weeks if entries survive combined test | 12 / 16 |

This is a 4h bullish recovery trigger inside a still-negative completed daily
EMA spread. It is not classic daily trend continuation. Implementation remains
research-only until A+B+candidate combined weekly packet evaluation proves that
the added frequency does not damage after-fee expectancy or risk controls.

## Coverage Probe Before Plugin

Before writing a `StrategyPlugin`, run a synthetic signal audit on the same
primary-window replay data used by Phase 3 packets.

The probe must emit a machine-readable artifact with:

- per-candidate timestamp, symbol, side, entry family, and baseline week bucket.
- silent-week hit count.
- zero-entry-week hit count.
- active-week overlap count.
- same-symbol same-candle overlap with promoted entries.
- candidate count by dominant weekly regime.
- candidate count by packet decision state.

Minimum go / no-go gates before plugin implementation:

- At least 3 of the 9 full silent zero-entry weeks receive a candidate.
- At least 70% of candidates land on baseline silent or zero-entry weeks.
- Zero same-symbol same-candle overlap with promoted entries.
- No more than 30% of candidates land in already-active promoted weeks.
- Candidate timestamps must come from replay market candles, not audit generation
  timestamps.

If the SuperTrend probe fails the silent-week hit gate, do not tune it looser.
Move to the Aroon structural-break probe because it can fire inside an ongoing
trend without depending on a fresh trend-direction flip.

## First Mechanism Contract

`supertrend_flip_4h_trending_up_frequency_companion` is a BTC/ETH 4h LONG
candidate with a 1d trend gate.

Entry thesis:

- `supertrend_direction` flips from bearish to bullish on the 4h entry candle.
- 1d trend gate passes: `ema_20 > ema_50` and spread is at least `0.005`.
- The plugin emits once per symbol/candle.
- The plugin does not read baseline weekly labels, packet states, router state,
  or promoted strategy internals.

Stop hint:

- `entry_price - 1.5 * atr_4h`.

Exit thesis:

- close when 4h `supertrend_direction` flips bearish again, or
- close when the 1d trend gate no longer passes.

Risk and execution:

- The plugin only returns `SignalIntent`.
- Central `RiskPlan`, arbiter, router, position manager, and execution handoff
  remain the only sizing and execution path.

## Strict Review Risks

- SuperTrend flip is likely decorrelated from MACD, but it may be too sparse for
  the weekly participation target. The coverage probe must kill it early if it
  cannot cover at least 3 silent weeks.
- Adding ETH can improve participation, but it must not become hidden scanner
  expansion. Scope stays fixed to BTC/ETH.
- A LONG-only trend companion will not solve bear-regime participation. Slot A
  SHORT remains research-only and is not reopened by this contract.
- If candidate entries cluster in already-active weeks, the lane fails even if
  standalone PnL looks positive.
- Positive dry-run or backtest health remains insufficient for live expectancy.

## Implementation Sequence

1. Add `analyze_weekly_profit_trend_companion_probe.py` to generate candidate
   coverage metrics without creating a runtime plugin.
2. Generate the probe JSON and markdown report for the first mechanism.
3. Strict-review the probe. If gates fail, pivot to Aroon without loosening
   SuperTrend.
4. If strict probes fail but no-1d diagnostic probes hit silent weeks, run
   precision attribution before any plugin work.
5. Implement the `btc_recovery_band_trend_breadth` research candidate only as a
   plugin/backtest candidate; do not promote it or change runtime defaults.
6. Only after a passing strict or revised-contract probe, implement the research plugin, catalog it as
   `active_research`, and add focused plugin tests.
7. Run A+B+candidate combined attribution through the Phase 3 weekly control
   packet evaluator.

## Hard Exclusions

- No runtime default changes.
- No threshold loosening in promoted strategies.
- No scanner universe activation.
- No legacy RSI2 / BB / Slot A SHORT revival.
- No direct order sizing or execution in the plugin.
- No use of generated audit timestamps as market timestamps.
