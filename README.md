# strategy-runtime-reset

StrategyRuntime reset workspace for the promoted strategy-plugin runtime.

Code is the source of truth. For agent handoff and current operating
boundaries, read `docs/codex_handoff.md` first.

## Current Runtime

Promoted runtime defaults live in `trader/config.py`.

Current runtime portfolio:

- Slot A LONG:
  `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- Slot B LONG:
  `donchian_range_fade_4h_range_width_cv_013`
- Slot B SHORT:
  `donchian_range_fade_4h_range_width_cv_013_short`

Scanner universe remains observe-only by default:

```text
USE_SCANNER_SYMBOLS = false
SCANNER_UNIVERSE_ENABLED = false
```

BTC trend filter is diagnostic by default for StrategyRuntime. Enforced blocking
or size reduction requires `BTC_TREND_FILTER_RUNTIME_MODE = "enforce"` and a
fresh review.

## First Commands

From repo root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\agent_check.ps1 -Scope validate
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\runtime_snapshot.ps1
```

Full handoff validation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\agent_check.ps1 -Scope full
```

Fast validation, excluding slower BacktestEngine replay checks:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\agent_check.ps1 -Scope fast
```

Focused validation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\agent_check.ps1 -Scope focused -Tests trader/tests/test_strategy_runtime_kernel.py
```

Equivalent direct commands:

```powershell
python -c "from trader.config import Config; Config.validate(); print('Config.validate PASS')"
python -m pytest trader/tests extensions/Backtesting/tests -q
```

## Repo Map

- `trader/`: live runtime, strategy kernel, risk, routing, persistence.
- `trader/strategies/plugins/`: StrategyPlugin research and promoted plugins.
- `trader/strategies/plugins/_catalog.py`: plugin catalog; catalog presence is
  not promotion by itself.
- `trader/strategies/plugins/HOWTO.md`: plugin authoring contract.
- `scanner/`: scanner diagnostics and universe tooling.
- `extensions/Backtesting/`: mocked StrategyRuntime backtest workspace.
- `extensions/Backtesting/README.md`: backtest commands and artifact contract.
- `plans/`: locked specs and planning notes.
- `reports/`: promotion, closeout, and research reports.
- `docs/codex_handoff.md`: current tracked agent context.

## Runtime Boundaries

Do not change these without explicit Ruei approval:

- promote a research plugin into runtime
- change `STRATEGY_ROUTER_POLICY` away from `fail_closed`
- enable scanner universe as live runtime input
- change credentials handling or commit secrets
- bypass central risk sizing, arbiter/router, or execution handoff
- loosen strategy thresholds just to get trades

## Backtesting

Candidate reviews use the current StrategyRuntime path:

```powershell
python -m extensions.Backtesting.scripts.run_candidate_review --candidate <plugin_id>
```

Parameter sweeps are research-only and not promotion evidence:

```powershell
python -m extensions.Backtesting.scripts.run_parameter_sweep --candidate <plugin_id> --sweep-id <short_id> --param name=value1,value2
```

Sweep result directories use shortened artifact slugs for Windows path safety;
the full candidate id and sweep id remain in `sweep_manifest.json` and the
generated report.

## Plugin Tooling

Check one plugin contract:

```powershell
python -m tools.strategy_plugin_check --strategy-id fixture_long
```

Check current runtime-enabled plugins:

```powershell
python -m tools.strategy_plugin_check --runtime-enabled
```

Preview a new plugin scaffold without writing files:

```powershell
python -m tools.new_strategy_plugin --id sample_breakout_4h --symbols BTC/USDT ETH/USDT --timeframe 4h
```
