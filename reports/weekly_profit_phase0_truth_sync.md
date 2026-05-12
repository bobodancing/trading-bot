# Weekly Profit Phase 0 Truth Sync

Date: 2026-05-12
Branch: `codex/post-promotion-control-20260430`
Status: `PHASE_0_TRUTH_SYNC_COMPLETE`

## Purpose

Phase 0 exists to align governance, scanner coverage, and planning documents
with the current three-leg promoted runtime before weekly-profit measurement
begins.

## Completed

- Refreshed ignored local `AGENTS.md` workspace guidance around current code truth:
  - three-leg promoted runtime
  - scanner observe-only defaults
  - current branch and next-work direction
  - weekly-profit roadmap references
  - this file is intentionally local guidance and is not part of the tracked
    repo diff because `AGENTS.md` is ignored in this workspace
- Marked historical A+B-only reports as historical instead of current truth:
  - `reports/phase_4_5_research_closeout.md`
  - `reports/portfolio_ab_post_promotion_control.md`
  - `reports/portfolio_ab_trigger_review.md`
- Updated scanner review/docs to speak in current three-leg terms:
  - `reports/scanner_production_universe_filter_review.md`
  - `reports/scanner_runtime_v2_review.md`
  - `scanner/README.md`
  - `plans/2026-04-30_scanner_production_universe_plan.md`
- Updated cleanup-plan status:
  - `plans/2026-05-08_trader_cleanup_plan.md`
  - Phase 3 now reflects the completed 2026-05-11 infrastructure cleanup.
- Updated promoted scanner fixtures to include Slot B SHORT:
  - `trader/tests/runtime/test_runtime_scanner.py`
  - `trader/tests/scanner/test_scanner_universe.py`
- Replaced stale mojibake package-level orientation strings:
  - `trader/__init__.py`
  - `extensions/Backtesting/__init__.py`
- Removed the two aborted untracked implementation drafts left behind from the
  earlier stopped coding attempt:
  - `tools/runtime_health_report.py`
  - `trader/tests/runtime/test_runtime_health_report.py`

## Intentionally Not Changed

- No runtime defaults changed.
- No scanner runtime-consumption flag changed.
- No strategy thresholds changed.
- No promotion or backlog activation occurred.
- No production/testnet service state was touched.

## Validation

- `python -c "from trader.config import Config; Config.validate(); print('Config.validate PASS')"`
  - PASS
- `python -m pytest trader/tests/runtime/test_runtime_scanner.py trader/tests/scanner/test_scanner_universe.py trader/tests/tooling/test_plugin_tooling.py -q`
  - PASS, `18 passed`
- `python -m pytest trader/tests extensions/Backtesting/tests -q`
  - PASS, `543 passed`

## Next Step

1. Phase 1 promoted three-leg weekly feasibility review.
2. Phase 2 weekly-profit KPI contract.
