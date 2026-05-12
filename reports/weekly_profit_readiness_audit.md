# Weekly Profit Readiness Audit

Date: 2026-05-12
Branch: `codex/post-promotion-control-20260430`
Status: `READINESS_AUDIT_BEFORE_WEEKLY_PROFIT_ROADMAP`

## Executive Verdict

The project is viable enough to move toward the next operating objective:

> build a sustainable automated trading system that keeps meaningful weekly
> participation and improves the probability of positive weekly outcomes
> without sacrificing risk discipline.

But it should **not** begin that roadmap from the current document state
unchanged. The runtime/code path has advanced to a promoted three-leg portfolio,
while several governance, review, scanner, and cleanup documents still describe
the older A+B baseline. That drift is the main preflight risk because it can
misdirect future research, KPI setting, and runtime monitoring.

## Current Code Truth

Current runtime authority remains:

- `trader/config.py`
- `trader/strategy_runtime.py`
- `trader/strategies/plugins/_catalog.py`
- promoted plugin files under `trader/strategies/plugins/`

Current promoted runtime portfolio in code:

| slot | strategy id | role |
| --- | --- | --- |
| Slot A LONG | `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter` | BTC 4h trend continuation |
| Slot B LONG | `donchian_range_fade_4h_range_width_cv_013` | BTC/ETH 4h lower-bound range fade |
| Slot B SHORT | `donchian_range_fade_4h_range_width_cv_013_short` | BTC/ETH 4h upper-bound range fade |

Observed config truth from `trader/config.py`:

- `STRATEGY_RUNTIME_ENABLED = True`
- `ENABLED_STRATEGIES = [Slot A LONG, Slot B LONG, Slot B SHORT]`
- `USE_SCANNER_SYMBOLS = False`
- `SCANNER_UNIVERSE_ENABLED = False`
- `STRATEGY_ROUTER_POLICY = "fail_closed"`
- `RISK_PER_TRADE = 0.017`
- `MAX_TOTAL_RISK = 0.0642`

## Findings

### P0 - Governance Source Drift

`AGENTS.md` is stale and corrupted:

- it still states `STRATEGY_RUNTIME_ENABLED = false`
- it still states `ENABLED_STRATEGIES = []`
- it still states `USE_SCANNER_SYMBOLS = true`
- it still points to the old branch name
- the file has mojibake text in multiple sections

Impact:

- future agents may follow the wrong runtime baseline
- weekly-profit planning can begin from a false source of truth
- approval boundaries become ambiguous because the governance file conflicts
  with current code and handoff docs

Decision:

- **must fix before Phase 1 weekly feasibility work**

### P0 - Post-Promotion Narrative Drift

Several documents still frame the runtime as A+B only, even though Slot B SHORT
is already promoted in code and approval artifacts:

- `reports/phase_4_5_research_closeout.md`
- `reports/portfolio_ab_post_promotion_control.md`
- `reports/portfolio_ab_trigger_review.md`
- `reports/scanner_production_universe_filter_review.md`
- `reports/scanner_runtime_v2_review.md`
- `scanner/README.md`
- `plans/2026-04-30_scanner_production_universe_plan.md`

Examples of stale claims:

- "Promoted A+B remains the only runtime portfolio."
- "Monitor promoted A+B on the fixed runtime baseline."
- scanner docs describing the promoted runtime diagnostics as Slot A/B only.

Impact:

- new weekly cadence analysis could ignore the promoted SHORT leg
- scanner/readiness interpretations may be based on the wrong portfolio shape
- backlog activation decisions can be made against superseded assumptions

Decision:

- **must reconcile or explicitly supersede these docs before roadmap execution**

### P0 - Verification Coverage Drift Around Promoted Scanner Scope

Two scanner-related test files define `PROMOTED_STRATEGIES` without Slot B
SHORT:

- `trader/tests/runtime/test_runtime_scanner.py`
- `trader/tests/scanner/test_scanner_universe.py`

The tooling classification test is current and includes all three promoted
runtime strategies:

- `trader/tests/tooling/test_plugin_tooling.py`

Impact:

- scanner diagnostics can stay green while not fully exercising current
  promoted runtime scope
- future weekly participation studies may trust incomplete advisory scanner
  coverage

Decision:

- **must update before claiming weekly-readiness coverage is current**

### P1 - Cleanup Plan Status Drift

`plans/2026-05-08_trader_cleanup_plan.md` still says:

- `Phase 3 - Infrastructure Cleanup`
- `Status: pending`

But `reports/trader_cleanup_phase3_infrastructure.md` records that Phase 3 was
completed on 2026-05-11 with focused and full-suite validation.

Impact:

- execution ordering is unclear
- future cleanup work can accidentally repeat already-completed work
- roadmap sequencing loses trust

Decision:

- **update the cleanup plan status before adding new Phase work**

### P1 - Residual Legacy / Mojibake Surface Still Pollutes Orientation

The repo intentionally retains historical compatibility fields, but some files
still present old runtime identity as if it were current:

- `trader/__init__.py`
- `extensions/Backtesting/__init__.py`
- historical dashboard planning docs under `extensions/quantDashboard/docs/plans/`
- legacy 2B scanner references in `scanner/market_scanner.py` and related docs

Not all of this should be deleted. Some is compatibility or historical context.
The problem is **presentation drift**, not merely file count.

Impact:

- onboarding tax remains high
- agents may over-index on legacy architecture
- weekly-profit roadmap work spends avoidable time re-discovering historical
  cleanup boundaries

Decision:

- **Phase 0 should separate "fix wording now" from "archive/delete later"**

### P1 - Weekly-Profit Objective Has Not Yet Been Measured Against Current Portfolio

The repo has strong promotion-style evidence, but the new product objective is
different:

> "every week has enough trading activity and weekly PnL should be positive as
> often as the system can responsibly achieve."

The current portfolio reports focus on:

- total trades
- matrix PnL
- max drawdown
- router blocks
- combined promotion gates

They do **not** yet answer:

- active week ratio
- weekly trade-count distribution
- weekly positive-rate
- weekly loss depth
- longest losing-week streak
- after-fee weekly PnL concentration

Impact:

- there is no honest baseline for the new business objective
- research may chase the wrong bottleneck

Decision:

- **the first strategy-facing phase must be a weekly feasibility review, not
  a new alpha build**

### P2 - Slimming Opportunities Exist, But They Are Secondary

Useful future slimming candidates:

- superseded A+B-only narrative reports after the three-leg promotion handoff
  is rewritten
- obsolete or historical-only planning docs that can be moved under an archive
  convention
- presentation cleanup around retained legacy compatibility shims
- retirement review for `retire_candidate` plugin files already cataloged as
  non-current

These are worth doing, but they should not outrank:

1. governance/doc truth sync
2. weekly feasibility measurement
3. KPI contract design

## Immediate Preflight Fix Set

Before beginning the weekly-profit roadmap, do this narrow sync pass:

1. Refresh `AGENTS.md` to current three-leg runtime truth and repair mojibake.
2. Update or explicitly supersede stale A+B-only documents.
3. Update scanner-related promoted strategy tests to include Slot B SHORT.
4. Update `plans/2026-05-08_trader_cleanup_plan.md` to mark Phase 3 complete.
5. Clean orientation wording in `trader/__init__.py` and
   `extensions/Backtesting/__init__.py`.
6. Decide whether the two currently untracked aborted draft files should be
   discarded or parked before the roadmap starts:
   - `tools/runtime_health_report.py`
   - `trader/tests/runtime/test_runtime_health_report.py`

## What Not To Do Yet

Do **not** start any of these before the weekly feasibility baseline exists:

- activate new backlog research
- reopen parked RSI2 or BB Fade Squeeze work
- promote Slot A SHORT repair attempts
- enable scanner-universe runtime consumption
- raise risk-per-trade to force weekly positivity
- loosen thresholds to raise activity

## Recommended Start State For The Roadmap

Begin the roadmap only when:

- governance/docs match current runtime truth
- scanner tests reflect all three promoted legs
- the repo has no misleading "current baseline" documents pointing backward to
  A+B only
- a weekly feasibility analysis is explicitly selected as the first
  strategy-facing phase

That puts the project on firmer ground for the new business goal: sustainable
profitability with weekly participation, rather than a series of disconnected
backtest wins.
