# Backtesting Workspace

This workspace runs local, mocked backtests against the current strategy-plugin runtime.

Legacy V54 / V7 / V6 / V53 strategy tables were removed from this doc because the runtime has been reset. Historical reports may still mention those names, but new research should use `StrategyPlugin` candidates.

## Current Contract

Backtests should exercise the same high-level path as runtime:

```text
StrategyPlugin -> StrategyRuntime -> arbiter/router -> central risk -> execution handoff
```

Runtime defaults live in `trader/config.py`. Backtesting must not introduce a second source of runtime defaults.

## Important Files

- `backtest_engine.py` - `BacktestConfig`, `_backtest_context`, and replay loop.
- `backtest_bot.py` - mocked live-like `TradingBot` factory.
- `config_presets.py` - backtest override whitelist and plugin-runtime presets.
- `plugin_id_filter.py` - backtest-only plugin id allowlist.
- `plugin_candidate_review.py` - promotion-gated candidate report helper.
- `report_generator.py` - per-run CSV / JSON / HTML artifact writer.
- `signal_audit.py` - signal, reject, lane, regime, and BTC trend audit collection.
- `data_loader.py` / `funding_loader.py` / `time_series_engine.py` - replay data plumbing.

## BacktestConfig

Common fields:

```python
BacktestConfig(
    symbols=["BTC/USDT"],
    start="2026-01-01",
    end="2026-03-01",
    initial_balance=10000.0,
    fee_rate=0.0004,
    warmup_bars=100,
    enabled_strategies=["macd_zero_line_btc_1d"],
    allowed_plugin_ids=["macd_zero_line_btc_1d"],
    dry_count_only=False,
    precompute_indicators=True,
    config_overrides={},
)
```

`enabled_strategies` toggles entries from `Config.STRATEGY_CATALOG` for this run only.

`allowed_plugin_ids` is a backtest-only allowlist over emitted strategy plugin ids. It does not change production scanner/runtime defaults.

`dry_count_only=True` keeps candidate/audit flow but blocks order-plan execution so no positions are opened.

## Config Overrides

Per-run overrides must pass `validate_backtest_overrides()` in `config_presets.py`.

Allowed override keys are explicit and must exist on current `Config`.

Forbidden:

- `API_KEY`
- `API_SECRET`
- any `TELEGRAM_*`
- `STRATEGY_ROUTER_POLICY`
- `DB_PATH`
- `POSITIONS_JSON_PATH`

Use helpers:

```python
from config_presets import (
    plugin_runtime_defaults,
    diagnostic_arbiter_off,
    explicit_symbol_universe,
    strategy_id_allowlist,
)
```

## Example

```python
from backtest_engine import BacktestConfig, BacktestEngine
from config_presets import explicit_symbol_universe, plugin_runtime_defaults

cfg = BacktestConfig(
    symbols=["BTC/USDT"],
    start="2026-01-01",
    end="2026-03-01",
    enabled_strategies=["macd_zero_line_btc_1d"],
    allowed_plugin_ids=["macd_zero_line_btc_1d"],
    precompute_indicators=True,
    config_overrides=explicit_symbol_universe(plugin_runtime_defaults()),
)

result = BacktestEngine(cfg).run_single(verbose=False)
```

Generate artifacts:

```python
from pathlib import Path
from report_generator import ReportGenerator

ReportGenerator().generate(result, Path("results/plugin_candidate_review_20260418/macd_zero_line_btc_1d/TRENDING_UP"))
```

## Candidate Review

Use `plugin_candidate_review.py` to aggregate completed run artifacts into:

```text
reports/strategy_plugin_candidate_review.md
```

Verdicts are intentionally narrow:

- `PROMOTE_PLUGIN`
- `KEEP_RESEARCH_ONLY`
- `NEEDS_SECOND_PASS`

Promotion still requires Ruei approval and a runtime config patch in a separate step.

## Test Commands

From repo root:

```bash
python -c "from trader.config import Config; Config.validate()"
python -m pytest trader/tests extensions/Backtesting/tests -q
```

Focused Backtesting tests:

```bash
python -m pytest extensions/Backtesting/tests -q
```
