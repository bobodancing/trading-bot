# Portfolio A+B Trigger Review

Date: 2026-05-05
Status: `TRIGGER_REVIEW_NO_MATERIAL_GAP`
Branch: `codex/post-promotion-control-20260430`

## Scope

This memo classifies whether the completed A+B promotion, Phase 4 RSI2
closeout, and Phase 5 BB Fade Squeeze closeout justify activating any recovery
backlog mechanism pair.

Decision boundary:

- This is a research trigger review only.
- It does not promote a strategy.
- It does not start a Wave 1 candidate.
- It does not modify runtime defaults, scanner defaults, catalog enablement,
  production/testnet state, or thresholds.

## Inputs

- A+B promotion review: `reports/portfolio_ab_promotion_review.md`
- A+B gated freeze: `reports/portfolio_ab_promotion_gated_freeze.md`
- A+B post-promotion control: `reports/portfolio_ab_post_promotion_control.md`
- Phase 4/5 closeout: `reports/phase_4_5_research_closeout.md`
- Scanner scope repair:
  `e5dae15 fix(runtime): restore promoted slot fixed universe`
- Backlog routing table:
  `plans/2026-04-25_strategy_research_backlog_design.md`

## Decision

Trigger classification: `NO_MATERIAL_GAP`.

Action: no recovery backlog activation. Monitor promoted A+B on the fixed
runtime baseline.

This does not mean the portfolio is complete forever. It means the current
evidence does not justify starting a new mechanism pair now.

## Trigger Table

| trigger class | decision | evidence read | action |
| --- | --- | --- | --- |
| Slot A trend/SHORT gap | not fired | Slot A passed promotion gates and remains the stronger validated trend leg. SHORT remains structurally unvalidated because `TRENDING_DOWN` promotion windows and BTC trend-filter silent-block attribution are not ready. | do not start A1/A2/A3 |
| Slot B ranging/frequency gap | not fired | Slot B passed as part of A+B. Donchian range-fade remains the validated ranging leg; BB Fade Squeeze failed target participation and was parked. Low ranging trade count is a monitoring caveat, not enough to force a new Slot B pair. | do not start B1/B2/B3 |
| Transition-window coverage gap | not fired | The promoted Slot A already uses transition-aware tightened defense. The squeeze-release side branch repaired some ranging surface but failed trend retention, and Phase 4/5 did not expose a clean transition hole. | do not start T1/T2/T3 |
| No material gap | fired | A+B passed hard gates, post-promotion control passed, RSI2 and BB closeouts did not justify new slots, and scanner universe was returned to observe-only default. | keep backlog parked |

## Evidence Snapshot

A+B promotion evidence:

- Portfolio max drawdown gate passed: `5.1770%` versus `8.0000%`.
- Same-symbol same-candle A+B overlap passed: `0`.
- Slot A aggregate router block rate passed: `0.1946`.
- Slot B aggregate router block rate passed: `0.2222`.
- Default matrix: `59` trades, `+2249.7027` PnL, `4.3144%` max drawdown.
- Supplemental matrix: `156` trades, `+7515.9710` PnL, `5.1770%` max drawdown.
- Risk sensitivity kept the approved runtime sizing at `RISK_PER_TRADE=0.017`.
- Post-promotion runtime-default smoke passed with no run errors.

Phase 4/5 closeout evidence:

- RSI2 `sma5_gap_guard` improved its parent, but residual stop-outs remained
  broad and did not yield a clean second guard.
- Phase 4 therefore parked RSI2 and closed the 3-slot A+B+RSI2 path.
- BB Fade Squeeze produced only `1` first-pass trade and `0` target `RANGING`
  trades.
- BB gate attribution showed the squeeze definition is a redesign problem, not
  a narrow rescue.
- Phase 5 therefore parked BB Fade Squeeze.

Scanner evidence:

- Scanner universe infrastructure remains available, but runtime consumption is
  observe-only by default.
- Promoted A+B remains fixed-scope after
  `e5dae15 fix(runtime): restore promoted slot fixed universe`.
- Scanner output must not be used as a hidden new selection variable for this
  trigger decision.

## Residual Caveats

- Current `StrategyRuntime` does not enforce `BTC_TREND_FILTER_ENABLED` as a
  plugin-entry reject or size-zero multiplier; this remains a report-only caveat
  until runtime code changes.
- `TRENDING_DOWN` is not yet a fully supported promotion validation lane. SHORT
  research can be planned later, but it should not be activated from this memo.
- Validation windows overlap; these results are promotion and regression
  evidence, not live expectancy guarantees.
- A live or dry-run monitoring period may reveal an actual gap later. That
  should create a new trigger review, not retroactively activate this backlog.

## Backlog State

Recovery backlog remains `DO-NOT-START`.

Do not create:

- new `cartridge_spec_<id>.md` files from the backlog
- new backlog plugin implementations
- new backlog catalog entries
- A+B+backlog combined backtests
- runtime or scanner promotion changes

## Next Work

Recommended next work is monitoring and operational hygiene for promoted A+B:

- use `reports/portfolio_ab_monitoring_handoff.md` as the current monitoring
  handoff
- keep `Config.validate()` and full test suite green
- keep scanner universe observe-only unless Ruei explicitly requests a new
  scanner-universe activation review
- review post-promotion dry-run/live observations when available
- revisit trigger classification only when new evidence shows a concrete gap
