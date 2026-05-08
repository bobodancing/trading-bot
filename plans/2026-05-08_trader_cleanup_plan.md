# Trader Cleanup Plan

Last updated: 2026-05-08.

This plan tracks the staged cleanup of `trader/` after the StrategyRuntime
reset. Code remains the source of truth. If this plan conflicts with current
runtime code or `Config.validate()`, trust code first and update this plan.

## Goal

Reduce stale runtime residue, research noise, and local clutter under
`trader/` without weakening the promoted StrategyRuntime path.

Current promoted runtime must remain centered on:

- `StrategyRuntime`
- `StrategyPlugin` / `SignalIntent`
- central `RiskPlan`
- `PositionManager` persistence compatibility
- `Config.validate()`
- secrets-only credential loading

## Ground Rules

- Do not promote research plugins while cleaning.
- Do not change runtime defaults unless a phase explicitly includes a reviewed
  default change.
- Do not delete compatibility fields required for existing `positions.json`,
  `performance.db`, dashboards, or backtest artifacts.
- Do not remove a plugin file before its catalog entry, focused tests, plans,
  and reports have been reviewed together.
- Do not remove `v8_grid` wiring until all `ENABLE_GRID_TRADING`, `GRID_*`,
  bot startup, tests, and backtest references are accounted for.
- Keep each phase independently reviewable and commit-sized.

## Baseline Snapshot

Observed during the 2026-05-08 audit:

- `trader/**/__pycache__` exists locally and is ignored.
- `trader/tests/legacy` is ignored and currently contains only stale `.pyc`
  legacy test bytecode.
- `trader/strategies/plugins` has 37 plugin files and 38 catalog entries.
- Runtime enabled plugins are only:
  - `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
  - `donchian_range_fade_4h_range_width_cv_013`
  - `donchian_range_fade_4h_range_width_cv_013_short`
- `trader/strategies/v8_grid` is default-off but still wired through `bot.py`,
  `GridManager`, config, and tests.
- `trader/indicators`, `trader/risk`, `trader/infrastructure`, and some test
  metadata still contain old V6/V7/V53 wording or mojibake comments.

## Phase 0 - Preflight

Status: completed on 2026-05-08.

Phase 0 output:

- `reports/trader_cleanup_phase0_preflight.md`

Before each cleanup phase:

```powershell
git status --short --branch
git log --oneline -5
python -c "from trader.config import Config; Config.validate(); print('Config.validate PASS')"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\agent_check.ps1 -Scope fast
```

Produce or refresh an inventory for the phase:

- files touched
- runtime import references
- test references
- config references
- persistence or artifact compatibility concerns

## Phase 1 - Low-Risk Cleanup

Status: pending.

### 1A. Local Cache Cleanup

Scope:

- `trader/**/__pycache__`
- ignored `trader/tests/legacy`

Plan:

- Remove ignored local bytecode/cache directories only.
- Do not commit cache deletion unless tracked files unexpectedly appear.
- Confirm `.gitignore` covers `__pycache__/`.

Review gate:

- `git status --ignored --short trader`
- confirm no tracked source files were removed.

### 1B. Plugin Classification

Scope:

- `trader/strategies/plugins`
- `trader/strategies/plugins/_catalog.py`
- focused plugin tests only if needed

Plan:

- Classify catalog entries into:
  - `runtime`
  - `fixture`
  - `active_research`
  - `superseded_research`
  - `retire_candidate`
- Make runtime vs research status easier for future agents to see.
- Prefer catalog metadata, comments, or a small report before deleting files.
- Do not delete strategy variants in this phase unless a follow-up review
  explicitly proves they are superseded and unused.

Review gate:

```powershell
python -m tools.strategy_plugin_check --runtime-enabled --strict
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\agent_check.ps1 -Scope fast
```

Phase 1 handoff output:

- plugin classification summary
- retire-candidate list
- files safe to remove in a later phase

## Phase 2 - Code-Aware Cleanup

Status: pending.

### 2A. Retire `trader/strategies/v8_grid`

Reason:

The promoted portfolio now has a dedicated RANGING lane via Donchian range fade,
so the default-off V8 grid path may no longer justify live runtime wiring.

Required review before deletion:

- `trader/bot.py` imports and initialization:
  - `V8AtrGrid`
  - `PoolManager`
  - `GridManager`
- `trader/grid_manager.py`
- `trader/config.py`:
  - `ENABLE_GRID_TRADING`
  - `GRID_*`
- `trader/btc_context.py` fallback behavior when grid is disabled.
- `trader/infrastructure/notifier.py` and Telegram grid messages.
- `trader/infrastructure/performance_db.py` grid columns.
- `trader/tests/test_grid.py`, `test_grid_integration.py`,
  `test_pool_manager.py`, and related backtesting references.

Expected approach:

- First remove live wiring and tests that only exercise retired behavior.
- Keep DB/report compatibility fields unless a separate migration plan exists.
- Keep historical artifact readers compatible.

Review gate:

```powershell
rg -n "ENABLE_GRID_TRADING|GRID_|V8AtrGrid|PoolManager|GridManager" trader extensions scanner
python -c "from trader.config import Config; Config.validate(); print('Config.validate PASS')"
python -m pytest trader/tests extensions/Backtesting/tests -q
```

### 2B. Reorganize `trader/tests`

Goal:

Make tests reflect current ownership instead of old strategy generations.

Suggested grouping:

- runtime kernel and persistence compatibility
- promoted plugin tests
- research plugin tests
- scanner advisory tests
- infrastructure tests
- retired/legacy compatibility tests

Do not reduce coverage just to make the tree smaller.

Review gate:

```powershell
python -m pytest trader/tests -q
```

### 2C. Clean `trader/indicators`

Scope:

- `trader/indicators/technical.py`
- `trader/indicators/registry.py`

Plan:

- Replace stale V6 wording and mojibake comments.
- Review whether `MTFConfirmation`, `MarketFilter`, and
  `DynamicThresholdManager` are still live, research-only, or unused.
- Prefer moving research-only helpers behind clear names over deleting them
  blindly.

Review gate:

```powershell
rg -n "TechnicalAnalysis|MTFConfirmation|MarketFilter|DynamicThresholdManager" trader extensions scanner
python -m pytest trader/tests/test_indicator_registry.py trader/tests/test_bbw.py -q
```

### 2D. Clean `trader/risk`

Scope:

- `trader/risk/manager.py`
- risk-related bot/runtime call sites

Plan:

- Keep `PrecisionHandler` and account/balance access.
- Review `RiskManager.calculate_position_size()` because central runtime sizing
  now lives in `StrategyRuntime`.
- Mark or split `SignalTierSystem` if it is only legacy/research artifact
  compatibility.
- Do not remove fields still written to `PerformanceDB`, signal audit, or
  dashboard artifacts.

Review gate:

```powershell
rg -n "RiskManager|PrecisionHandler|SignalTierSystem|calculate_position_size|signal_tier|tier_score" trader extensions scanner
python -m pytest trader/tests/test_risk_guard.py trader/tests/test_strategy_runtime_kernel.py -q
```

## Phase 3 - Infrastructure Cleanup

Status: pending.

Scope:

- `trader/infrastructure/api_client.py`
- `trader/infrastructure/data_provider.py`
- `trader/infrastructure/notifier.py`
- `trader/infrastructure/telegram_handler.py`
- `trader/infrastructure/performance_db.py`

Plan:

- Read each file before changing it.
- Separate live runtime needs from dashboard/backtest compatibility.
- Remove or rewrite stale version wording and mojibake comments.
- Keep schema compatibility for `performance.db`; no destructive migrations
  without a dedicated migration plan.
- Align Telegram/notifier labels with current StrategyRuntime names.

Review gate:

```powershell
python -m pytest trader/tests/test_data_provider.py trader/tests/test_notifier_escape.py trader/tests/test_telegram_handler.py trader/tests/test_perf_db_quality.py -q
python -m pytest trader/tests extensions/Backtesting/tests -q
```

## Final Handoff Checklist

At the end of every phase, record:

- completed items
- intentionally retained legacy compatibility
- deleted files
- moved files
- tests run
- known follow-ups

Do not start the next phase until the current phase has been reviewed and
committed.
