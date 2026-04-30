# Portfolio A+B Post-Promotion Control

Date: 2026-04-30
Status: `POST_PROMOTION_CONTROL_PASS`

## Scope

- Ruei approval: `APPROVED` on 2026-04-29.
- Promotion commits:
  - `5dee878 chore(runtime): enable frozen portfolio catalog entries`
  - `1933e65 feat(runtime): promote frozen portfolio strategies`
- Recovery scheduling commit: `827b5a7 docs(research): schedule recovery backlog after promotion`
- Slot A: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- Slot B: `donchian_range_fade_4h_range_width_cv_013`

This is control work only. No new alpha research, no Phase 4/5 work, no recovery backlog activation, and no threshold relaxation are included.

## Promotion Artifact Updates

| artifact | post-promotion status |
| --- | --- |
| `reports/portfolio_ab_promotion_gated_freeze.md` | marked `RUEI_APPROVED_RUNTIME_PROMOTED`; catalog/runtime defaults now promoted |
| `reports/portfolio_ab_promotion_review.md` | marked `RUEI_APPROVED_RUNTIME_PROMOTED`; approval and promotion commits recorded |
| `reports/portfolio_a_b_risk_sensitivity.md` | marked `RUEI_APPROVED_PROMOTION_SIZING`; `0.017` recorded as approved runtime sizing |

## Runtime-Default Parity

Parity check used direct `Config` defaults and `StrategyRuntime`; it did not use a backtest strategy override.

| check | expected | result |
| --- | --- | --- |
| `Config.validate()` | pass | PASS |
| `Config.STRATEGY_RUNTIME_ENABLED` | `True` | PASS |
| `Config.ENABLED_STRATEGIES` | Slot A + Slot B | PASS |
| `Config.RISK_PER_TRADE` | `0.017` | PASS |
| `Config.MAX_TOTAL_RISK` | `0.0642` | PASS |
| `Config.STRATEGY_ROUTER_POLICY` | `fail_closed` | PASS |
| catalog promoted entries | both `enabled=True` | PASS |
| `StrategyRuntime.registry.plugins` | exactly Slot A + Slot B | PASS |

Read: Config defaults can load the promoted A+B runtime without `extensions/Backtesting` injecting `ENABLED_STRATEGIES`.

## Promoted-Default Smoke

The smoke command used a control-only `BacktestEngine` wrapper that leaves `STRATEGY_RUNTIME_ENABLED` and `ENABLED_STRATEGIES` untouched. The only per-run config override was `USE_SCANNER_SYMBOLS=False`, so the backtest uses the fixed BTC/ETH smoke universe instead of production scanner JSON.

| smoke cell | window | strategy source | trades | entries | rejects | max_dd_pct | run_errors |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| idle sanity | 2026-01-01..2026-02-28 | `Config.ENABLED_STRATEGIES` | 0 | 0 | 0 | 0.0000 | 0 |
| signal/execution wiring | 2023-10-01..2024-03-31 | `Config.ENABLED_STRATEGIES` | 32 | 32 | 80 | 4.3144 | 0 |

Signal/execution wiring attribution:

| item | value |
| --- | --- |
| Slot A entries | 26 |
| Slot B entries | 6 |
| reject mix | `position_slot_occupied=61`, `cooldown=11`, `strategy_router_blocked=8` |
| entries tier | `CENTRAL=32` |
| BTC 4h regime composition | `TRENDING=82.9%`, `RANGING=17.1%`, `SQUEEZE=0.0%` |

Artifacts:

- `extensions/Backtesting/results/portfolio_ab_post_promotion_control/runtime_default_smoke_summary.json`
- `extensions/Backtesting/results/portfolio_ab_post_promotion_control/runtime_default_smoke_trending_up_summary.json`
- `extensions/Backtesting/results/portfolio_ab_post_promotion_control/runtime_default_smoke_trending_up/`

## Deployment Boundary

- Runtime defaults are promoted, but this pass did not touch real production/testnet service state.
- No credentials handling changed; external files remain secrets-only.
- No scanner defaults changed; smoke backtests used `USE_SCANNER_SYMBOLS=False` only as a backtest isolation control.
- No strategy params, thresholds, gates, risk caps, router policy, or BTC trend-filter settings were changed.
- Smoke results are wiring/regression evidence only, not new live expectancy evidence.
- Current StrategyRuntime still does not enforce `BTC_TREND_FILTER_ENABLED` as a plugin-entry reject or size-zero multiplier; keep that as report-only caveat until runtime code changes.
- Phase 4 RSI2 closeout, Phase 5 BB rescue/park, and recovery backlog activation remain out of scope for this control pass.

## Final Validation

Final repo validation passed:

| command | result |
| --- | --- |
| `python -c "from trader.config import Config; Config.validate()"` | PASS |
| `python -m pytest trader/tests extensions/Backtesting/tests -q` | PASS, `512 passed, 2 skipped in 37.29s` |
