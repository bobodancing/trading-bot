# Trader Cleanup Phase 2 - Code-Aware Cleanup

Date: 2026-05-08

## Scope

Phase 2 removed retired grid runtime code, reorganized `trader/tests` by
ownership, and clarified retained legacy indicator/risk helpers. It did not
change promoted StrategyRuntime defaults or delete any StrategyPlugin files.

## 2A - V8 Grid Retirement

Deleted:

- `trader/strategies/v8_grid/`
- `trader/grid_manager.py`
- `extensions/Backtesting/grid_adapter.py`
- `trader/tests/test_grid.py`
- `trader/tests/test_grid_integration.py`
- `trader/tests/test_pool_manager.py`

Removed live wiring from:

- `trader/bot.py`
- `trader/config.py`
- `trader/btc_context.py`
- `extensions/Backtesting/backtest_engine.py`
- `extensions/Backtesting/bot_compat.py`
- `extensions/Backtesting/config_presets.py`
- `trader/infrastructure/notifier.py`
- `trader/infrastructure/telegram_handler.py`

Compatibility intentionally retained:

- `PerformanceDB` keeps `grid_level` and `grid_round` columns.
- quantDashboard keeps historical `v8_atr_grid` display support.
- Backtesting regime probes still run as audit-only sidecars.

## 2B - Test Ownership Tree

`trader/tests` is now grouped by runtime surface:

- `runtime/`
- `plugins/promoted/`
- `plugins/research/`
- `scanner/`
- `market/`
- `infrastructure/`
- `persistence/`
- `tooling/`

`trader/tests/README.md` records the ownership map. `tools.strategy_plugin_check`
now scans tests recursively, and `tools.new_strategy_plugin` scaffolds new
research plugin tests under `trader/tests/plugins/research/`.

## 2C - Indicators

- Removed stale v6 wording from `trader/indicators/technical.py`.
- Kept `DynamicThresholdManager` because risk sizing still imports it.
- Kept `MTFConfirmation` and `MarketFilter` as exported legacy compatibility
  helpers instead of deleting public surface blindly.
- Updated scanner technical-debt wording to point at the current indicator
  adapter.

## 2D - Risk

- Removed stale v6 wording from `trader/risk/manager.py`.
- Documented `RiskManager.calculate_position_size()`,
  `RiskManager.calculate_stop_loss()`, `RiskManager.check_total_risk()`, and
  `SignalTierSystem` as retained legacy helpers.
- Kept `PrecisionHandler` and account/position access live, because `TradingBot`
  and execution still depend on them.

## Review Notes

- No StrategyPlugin files were deleted in Phase 2.
- No runtime strategy defaults were changed.
- Grid config keys and live grid imports now have zero code references under
  `trader`, `extensions`, and `scanner`.
- Historical DB/dashboard grid fields remain compatible.
- Retire-candidate plugin files remain classified but untouched.
