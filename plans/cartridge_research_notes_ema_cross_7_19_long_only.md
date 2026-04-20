# Cartridge Research Notes: ema_cross_7_19_long_only

## Status

- Plugin id: `ema_cross_7_19_long_only`
- Version: `0.1.0`
- Catalog entry: `enabled: False`
- Promotion status: **research-complete, not promotion-eligible**
- Classification per `plans/cartridge_promotion_checklist.md`: `KEEP_RESEARCH_ONLY` (terminal).

This plugin is kept in the catalog as research fixture and checklist-gate test case. It will not be re-locked or promoted.

## Evidence

- Candidate review: `reports/strategy_plugin_candidate_review.md`
- Full-matrix parameter sweep (5 cells x 3 windows): `reports/strategy_plugin_parameter_sweep_ema_cross_7_19_long_only_20260420T031210Z.md`
- Relevant commits on `codex/strategy-runtime-reset`:
  - `96fe609` cartridge implementation
  - `957c74b` candidate review runner
  - `ffdf9e8` full-matrix sweep
  - `5313e2e` per-window data surfaced in reports
  - `6ea895a` regime-robustness gate added to checklist

## Checklist Result

Final checklist run after `6ea895a`: **13 / 15 pass**.

Failing gates:

- **§3.2**: candidate review `net_pnl` positive in only 1 of 3 DEFAULT_WINDOWS (TRENDING_UP +4220.60, RANGING -2541.37, MIXED -487.71). Gate requires at least 2 of 3.
- **§3.4**: DEFAULT_WINDOW `RANGING` has all 5 sweep cells with `net_pnl < 0` (-2144 to -1712 across `atr_mult` 1.0 to 2.0). Gate requires no window has all cells negative.

## Core Finding

The cartridge is a **regime-dependent single-leg long-only** signal. Aggregate +1191 PnL is carried entirely by the TRENDING_UP window; both RANGING and MIXED are net-negative across the full tested `atr_mult` range.

## Structural Hypothesis

A naked EMA(7) / EMA(19) cross-up is a trend-following signal. In ranging regimes, MA crosses fire frequently on noise and get stopped out against the mean-reverting tape. Without a regime filter or a complementary short leg, the long-only variant cannot diversify across regimes.

## What Was Ruled Out

- Widening the ATR stop. Sweep across `atr_mult` in {1.0, 1.25, 1.5, 1.75, 2.0} cannot rescue RANGING. Losses shrink monotonically but remain negative at every tested cell. Stop-distance tuning refines, it does not restructure.

## Implications for Future Cartridges

1. **Trend-following candidates must address regime explicitly.** Either self-filter entries via a regime gate (for example, a `BTC_TREND_FILTER`-style condition inside `generate_candidates`), or explicitly scope the cartridge to a single regime and document the scoping in its locked spec.
2. **Stop-distance tuning is not a promotion path.** If a base config fails §3.2, a parameter sweep alone will almost never unstick it. Reserve sweeps for second-pass refinement, not structural rescue.
3. **Long-only across all regimes is a high bar.** Without a complementary short leg or a regime filter, expect §3.4 to fail for any naked trend-following signal.

## Non-Commitments

Possible follow-ups, none committed:

- Regime-filtered variant of the EMA cross (enter only when a BTC trend filter agrees).
- Mean-reversion cartridge scoped for RANGING regime, paired with a trend cartridge.
- Short-leg EMA cross-down cartridge.

These are research ideas, not plans. Any of them would start from a fresh locked spec under Phase 4.0, not a re-lock of this plugin.

## Do Not

- Do not re-lock this plugin's spec. The structural finding cannot be fixed by parameter changes.
- Do not flip `enabled: True` in `trader/strategies/plugins/_catalog.py`.
- Do not delete this plugin or its tests. It remains useful as a research fixture and as a checklist-gate regression case.
