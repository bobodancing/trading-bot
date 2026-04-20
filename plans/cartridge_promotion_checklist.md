# Cartridge Promotion Checklist

## 1. Purpose

This checklist defines the minimum gates for moving a plugin from research status in `trader/strategies/plugins/` into runtime `ENABLED_STRATEGIES`. Promotion still requires explicit Ruei approval; it is not automated by reports, sweep output, or tests.

## 2. Invariant Gates

- `entry_stop_violations == 0` across all candidate review windows in the latest `reports/strategy_plugin_candidate_review.md` row.
- `backtest_run_error_count == 0` across all candidate review windows.
- Focused unit tests exist in `trader/tests/test_<plugin_id>*.py` and cover entry intent shape, stop hint math, out-of-scope symbol, no-signal path, and exit signal if the plugin has one.
- Focused tests pass in the latest `python -m pytest trader/tests extensions/Backtesting/tests -q` run.

## 3. Robustness Gates

- Candidate review has completed all 3 DEFAULT_WINDOWS: TRENDING_UP, RANGING, and MIXED.
- Candidate review `net_pnl` is positive in at least 2 of the 3 DEFAULT_WINDOWS, verified from the Per-Window Detail table in `reports/strategy_plugin_candidate_review.md`.
- Phase 5.0 parameter sweep has run at least once with at least 3 cells.
- No DEFAULT_WINDOW has all sweep cells with `net_pnl < 0`, verified from the Per-Window Detail table in `reports/strategy_plugin_parameter_sweep_*.md`.
- Sweep report exists at `reports/strategy_plugin_parameter_sweep_*.md` and has status `RESEARCH_SWEEP_ONLY`.

## 4. Risk Gates

- Candidate review `max_dd_pct` is not above `40.0` in any window.
- The `40.0` drawdown cap is an initial conservative cap and may be adjusted by Ruei later.
- Plugin uses the central `RiskPlan` path and does not size orders, place orders, or bypass runtime execution handoff.

## 5. Process Gates

- `trader/strategies/plugins/HOWTO.md` Locked spec is filled for timeframe, symbol scope, indicators, params, entry rule, and stop rule.
- Plugin is registered in `trader/strategies/plugins/_catalog.py`; `enabled: False` is acceptable before promotion.
- `CLAUDE.md` Current known plugin entries has one entry for the plugin.
- Latest candidate review verdict is `KEEP_RESEARCH_ONLY`, not `NEEDS_SECOND_PASS`.

## 6. Promotion Two Steps

Promotion requires two commits and must only happen after explicit Ruei approval:

1. `trader/strategies/plugins/_catalog.py`: change the target plugin `"enabled"` value to `True`.
2. `trader/config.py`: append the plugin id to `ENABLED_STRATEGIES` and set `STRATEGY_RUNTIME_ENABLED` to `True` if it is still `False`.

After these two commits, the plugin becomes live only after the next release or restart. Paper-trade and shadow-mode gates are separate future phases and are not covered by this checklist.

## 7. Out of Scope

- Live shadow or paper-trade gate.
- Multi-plugin co-trading compatibility tests.
- Dynamic regime routing enablement criteria.
- Automated promotion enforcement tooling.
