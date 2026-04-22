# Research Note: rsi_mean_reversion (γ + δ)

## Status

- γ `rsi_mean_reversion_15m`: parked. Promotion-ineligible under checklist §5 (backtest engine lacks 15m support).
- δ `rsi_mean_reversion_1h`: parked. Robustness gate §3.2 fails — RANGING window `net_pnl < 0`.
- Both remain in `_catalog.py` with `enabled: False` as research references. Neither is promoted.

## Hypothesis

RSI-14 oversold + close ≤ Bollinger lower band + ADX below `adx_max`, long-only on BTC/USDT and ETH/USDT, during DEFAULT_WINDOWS labeled RANGING, should produce positive expectancy mean-reversion entries. γ tests this on 15m, δ on 1h.

## Findings

### 1. γ (15m): infrastructure boundary, not thesis failure

The backtest engine (`extensions/Backtesting/backtest_engine.py`) hardcodes `{1h, 4h, 1d}` for data loading, indicator precomputation, and iteration tick granularity. 15m cartridges produce empty frames in `_has_entry_columns`, yielding zero candidates and zero trades without raising an error. γ's candidate review returned all-zero metrics with `backtest_run_error_count == 0` across three windows, which motivated promotion checklist §5 (timeframe-support gate, commit `ca4c445`).

γ is a valid cartridge implementation. It cannot be validated until the engine is extended to 15m. Kept as reference for future infra work. γ spec: `plans/cartridge_spec_rsi_mean_reversion_15m.md` (commit `fd5d246`).

### 2. δ (1h): thesis did not survive candidate review

Primary candidate review with baseline runtime filters (`REGIME_ARBITER_ENABLED=True`, `STRATEGY_ROUTER_POLICY="fail_closed"`, `BTC_TREND_FILTER_ENABLED=True`, `BTC_COUNTER_TREND_MULT=0.0`):

| window | trades | net_pnl | max_dd_pct |
|---|---:|---:|---:|
| TRENDING_UP | 4 | -244.7604 | 3.0004 |
| RANGING (declared target) | 5 | -48.2845 | 1.9632 |
| MIXED | 5 | +123.9711 | 1.2669 |

§3.2 requires `net_pnl > 0` in the declared RANGING window when a non-`ANY` `target_regime` is declared. Fails. §2 invariants and §4 risk caps pass.

δ spec: `plans/cartridge_spec_rsi_mean_reversion_1h.md` (commit `6e22462`).

### 3. Mechanism-level learnings

**(a) Local `adx < adx_max` is not a reliable ranging-edge filter.**

The RANGING window's `window_regime_composition_4h` artifact shows the arbiter classified 65.6% of that window's bars as TRENDING, even though the window was labeled "RANGING" by DEFAULT_WINDOWS date bounds. Local 1h `adx < 25` passes easily during short-term consolidation inside a larger trending structure. The entry gate does not distinguish "truly ranging" from "momentarily pausing within a trend".

**(b) Shared arbiter / fail-closed baseline is a net-positive partner for δ, not merely a filter.**

Arbiter-off diagnostic (runner: `extensions/Backtesting/scripts/run_candidate_review_arbiter_off.py`, preset: `diagnostic_arbiter_off()`):

| window | total_trades primary | total_trades arbiter-off | return_pct primary | return_pct arbiter-off |
|---|---:|---:|---:|---:|
| TRENDING_UP | 4 | 10 | — | -1.4180% |
| RANGING | 5 | 7 | -0.4828% | **-1.7838%** |
| MIXED | 5 | 6 | — | +1.1892% |

`strategy_router_blocked` drops from 5 / 6 / 1 (TRENDING_UP / RANGING / MIXED primary) to 0 / 0 / 0 under arbiter-off. Attribution is clean: those rejections were arbiter-side.

The two additional RANGING trades the arbiter had been blocking are net losers — RANGING return degrades from -0.48% to -1.78% (a 1.30pp loss from just 2 additional trades). Win rate drops 40.0% → 28.6%; profit factor drops 0.74 → 0.44. The arbiter is not suppressing δ's edge; it is rescuing δ from its worst entries.

Caveat: arbiter-off is not a pure-δ-edge environment. `position_slot_occupied` and `cooldown` central guards still run. Of the 5 arbiter-blocked RANGING signals in the primary run, arbiter-off only materializes 2 as executed trades; the other 3 are re-blocked downstream (earlier executed trades trigger cooldown and hold open positions, absorbing subsequent signals). Pure δ edge is even weaker than the arbiter-off numbers suggest.

**(c) RSI-mean-reversion 1h standalone lacks sufficient edge in this repo's baseline.**

RANGING fails under both configurations (arbiter-on -0.48%, arbiter-off -1.78%). TRENDING_UP is negative under both. Only MIXED is positive, which is inconsistent with a RANGING-declared thesis — a genuine ranging-edge cartridge should order RANGING > MIXED > TRENDING_UP, not the observed MIXED > RANGING > TRENDING_UP.

## Implication for `dual_regime_strategy_plan.md`

δ is positioned in the dual-regime plan as the RANGING-regime component of a two-cartridge portfolio. These findings constrain that design:

- δ alone does not produce edge in its declared target regime at `locked params`. Routing δ's signals to a regime-appropriate window is necessary but not sufficient; the underlying signals carry net-negative expectancy.
- Any dual-regime design that enables δ must either:
  - add a secondary filter tightening δ's entries to the "truly ranging" subset (addressing learning 3a), or
  - accept δ as an EV-neutral-or-negative volume contributor balanced by a stronger trend-following primary — which requires explicit downstream economics.
- The shared arbiter is a silent partner in any such design. It cannot be removed from the runtime path during planning.

## Out of Scope for this note

- Parameter sweep (checklist §3.4): not run. With 5–7 trades per window, sweep signal is dominated by statistical noise; overfitting risk is high.
- Alternative entry formulations (e.g., `adx < 20`, `bbw_pctrank < 20`, multi-timeframe confirmation): deferred to dual-regime design phase if a revised δ variant is authorized. Would require a new spec and a new cartridge id.
- Re-deriving δ's `locked params` against 1h volatility profile: explicitly listed as Out of Scope in δ spec; not triggered by 1h regime-distribution baseline.

## Artifact references

- γ spec: `plans/cartridge_spec_rsi_mean_reversion_15m.md` (`fd5d246`)
- δ spec: `plans/cartridge_spec_rsi_mean_reversion_1h.md` (`6e22462`)
- Checklist §5 gate: `plans/cartridge_promotion_checklist.md` (`ca4c445`)
- 1h regime distribution baseline: `reports/regime_distribution_baseline_1h.md` (`daa6b76`)
- δ primary candidate review: `reports/strategy_plugin_candidate_review.md` (this commit)
- δ primary artifacts: `extensions/Backtesting/results/rsi_mean_reversion_1h/` (gitignored)
- δ arbiter-off artifacts: `extensions/Backtesting/results/rsi_mean_reversion_1h_arbiter_off/` (gitignored)
- Arbiter-off runner: `extensions/Backtesting/scripts/run_candidate_review_arbiter_off.py` (this commit)
