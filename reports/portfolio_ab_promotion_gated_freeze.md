# Portfolio A+B Promotion-Gated Freeze

Date: 2026-04-29
Status: `RUEI_APPROVED_RUNTIME_PROMOTED`

## Decision

- Freeze decision: `FROZEN_AS_FIRST_2_SLOT_PROMOTION_CANDIDATE`.
- Ruei approved runtime promotion on 2026-04-29.
- Runtime promotion landed in commits `5dee878` and `1933e65`.
- Recovery backlog scheduling landed in commit `827b5a7`; backlog remains scheduled recovery only.
- Credentials, scanner defaults, and live service state were not changed by promotion.
- Approved promotion sizing is `RISK_PER_TRADE=0.017`.

## Frozen Candidate

| slot | strategy_id | spec | plugin | focused_test | catalog_enabled |
| --- | --- | --- | --- | --- | --- |
| Slot A | `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter` | `plans/cartridge_spec_macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter.md` | `trader/strategies/plugins/macd_signal_trending_up_4h_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter.py` | `trader/tests/test_macd_signal_trending_up_4h_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter_strategy.py` | True |
| Slot B | `donchian_range_fade_4h_range_width_cv_013` | `plans/cartridge_spec_donchian_range_fade_4h_range_width_cv_013.md` | `trader/strategies/plugins/donchian_range_fade_4h_range_width_cv_013.py` | `trader/tests/test_donchian_range_fade_4h_range_width_cv_013_strategy.py` | True |

## Frozen Runtime Inputs

| item | value |
| --- | --- |
| symbols | `BTC/USDT`, `ETH/USDT` |
| RISK_PER_TRADE | `0.017` |
| MAX_TOTAL_RISK | `0.0642` from Config default |
| STRATEGY_RUNTIME_ENABLED default | True |
| ENABLED_STRATEGIES default | [`macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`, `donchian_range_fade_4h_range_width_cv_013`] |
| REGIME_ARBITER_ENABLED default | True |
| REGIME_ROUTER_ENABLED default | False |
| STRATEGY_ROUTER_POLICY default | `fail_closed` |

## Hard Gates

| gate | value | threshold | result |
| --- | --- | --- | --- |
| portfolio max_dd_pct | 5.1770 | 8.0000 | PASS |
| max same-symbol same-candle A+B emits | 0 | 5 | PASS |
| Slot A router block rate | 0.1946 | 0.5000 | PASS |
| Slot B router block rate | 0.2222 | 0.5000 | PASS |

## Portfolio Totals

| matrix | trades | net_pnl | max_dd_pct | run_errors | max_overlap |
| --- | --- | --- | --- | --- | --- |
| default | 59 | 2249.7027 | 4.3144 | 0 | 0 |
| supplemental | 156 | 7515.9710 | 5.1770 | 0 | 0 |

## Risk Sensitivity

| risk | total_pack_pnl | max_dd_pct | overlap | central_risk_blocked | entry_stop_violations | gate |
| --- | --- | --- | --- | --- | --- | --- |
| 0.014 | 9426.5046 | 4.7786 | 0 | 8 | 0 | PASS |
| 0.017 | 9765.6737 | 5.1770 | 0 | 8 | 0 | PASS |
| 0.020 | 9970.4821 | 5.1162 | 0 | 8 | 0 | PASS |

## Freeze Checklist

| gate | status | evidence |
| --- | --- | --- |
| StrategyRuntime portfolio matrix | `PASS` | reports/portfolio_a_b_combined_first_pass.md |
| Candidate specs, plugins, and focused tests exist | `PASS` | Frozen Candidate table |
| Catalog entries present and runtime-enabled | `PASS` | trader/strategies/plugins/_catalog.py |
| Same-symbol same-candle overlap | `PASS` | max_overlap=0 |
| Router block rate | `PASS` | both slots <= 0.50 aggregate router block rate |
| Risk sensitivity | `PASS` | reports/portfolio_a_b_risk_sensitivity.md |
| dry_count_only does not open positions | `PASS` | extensions/Backtesting/tests/test_backtest_engine.py::test_dry_count_only_records_candidate_without_opening_trade |
| Central risk and execution handoff | `PASS` | trader/strategy_runtime.py::_process_intent -> _build_risk_plan -> _execute_order_plan |
| Runtime defaults promoted | `PASS` | Config.STRATEGY_RUNTIME_ENABLED / Config.ENABLED_STRATEGIES defaults |

## Runtime Parity Read

- Entry path remains `StrategyPlugin.generate_candidates -> SignalIntent -> StrategyRuntime._process_intent -> arbiter/router -> central RiskPlan -> ExecutableOrderPlan -> TradingBot._execute_order_plan`.
- Plugins do not size orders, place orders, mutate Config defaults, load credentials, or write runtime persistence directly.
- `dry_count_only` is covered as audit-only and must not be used as tradeability proof.
- BTC trend filter is report-only for this freeze because the current plugin entry path does not enforce it as a reject or size-zero multiplier.

## Promotion Closeout

- Ruei approval: `APPROVED`.
- Promotion commit 1: `5dee878 chore(runtime): enable frozen portfolio catalog entries`.
- Promotion commit 2: `1933e65 feat(runtime): promote frozen portfolio strategies`.
- Recovery backlog scheduling commit: `827b5a7 docs(research): schedule recovery backlog after promotion`.
- Post-promotion control is tracked in `reports/portfolio_ab_post_promotion_control.md`.
- Paper-trade, shadow-mode, and service deployment policy remain outside this freeze packet.

## Caveats

- Current StrategyRuntime does not enforce BTC_TREND_FILTER_ENABLED on plugin entries.
- Validation windows overlap; portfolio-pack totals are review evidence, not live expectancy estimates.
- 0.020 risk sensitivity passed but does not automatically justify promotion above 0.017.

## Source Artifacts

- `reports/portfolio_a_b_combined_first_pass.md`
- `reports/portfolio_ab_promotion_review.md`
- `reports/portfolio_a_b_risk_sensitivity.md`
- `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab\slot_a_b\portfolio_ab_promotion_review.json`
- `C:\Users\user\Documents\tradingbot\strategy-runtime-reset\extensions\Backtesting\results\portfolio_ab_risk_sensitivity\portfolio_ab_risk_sensitivity_summary.json`
