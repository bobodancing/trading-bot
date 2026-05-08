# Trader Cleanup Phase 0 Preflight

Date: 2026-05-08.

## Scope

Phase 0 captured a restartable baseline for staged `trader/` cleanup. No
runtime behavior, source layout, cache cleanup, or plugin classification changes
were performed in this phase.

## Git Baseline

- Branch: `codex/post-promotion-control-20260430`
- Remote tracking: `github/codex/post-promotion-control-20260430`
- Status before report: branch was ahead by 1 commit:
  - `849b2ea docs(trader): record staged cleanup plan`
- Recent commits:
  - `849b2ea docs(trader): record staged cleanup plan`
  - `8f5466b chore(runtime): tighten post-promotion agent workflow`
  - `1ea751d chore(runtime): trim legacy bot residue`
  - `a2086a7 feat(runtime): add testnet observability`
  - `44c5485 feat(research): freeze slot a short mirror lane`

## Validation Baseline

Commands run:

```powershell
python -c "from trader.config import Config; Config.validate(); print('Config.validate PASS')"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\agent_check.ps1 -Scope fast
```

Results:

- `Config.validate PASS`
- fast suite: `556 passed, 16 deselected`

## Trader Tree Inventory

Tracked source count excludes `__pycache__`.

| path | files | python files |
| --- | ---: | ---: |
| `trader` | 141 | 140 |
| `trader/arbiter` | 2 | 2 |
| `trader/execution` | 2 | 2 |
| `trader/indicators` | 3 | 3 |
| `trader/infrastructure` | 6 | 6 |
| `trader/risk` | 2 | 2 |
| `trader/routing` | 2 | 2 |
| `trader/strategies` | 45 | 44 |
| `trader/tests` | 65 | 65 |

Latest folder-touch summary:

| path | latest commit |
| --- | --- |
| `trader/arbiter` | `2026-04-19 40bf6d6` |
| `trader/execution` | `2026-04-04 ef00d7c` |
| `trader/indicators` | `2026-04-23 7c73c6a` |
| `trader/infrastructure` | `2026-05-08 a2086a7` |
| `trader/risk` | `2026-05-08 1ea751d` |
| `trader/routing` | `2026-04-18 8e46ac6` |
| `trader/strategies` | `2026-05-08 8f5466b` |
| `trader/strategies/plugins` | `2026-05-08 8f5466b` |
| `trader/strategies/v8_grid` | `2026-04-04 97cf0ed` |
| `trader/tests` | `2026-05-08 8f5466b` |

## Ignored Local Clutter

Ignored cache directories found:

| path | file count |
| --- | ---: |
| `trader/__pycache__` | 28 |
| `trader/arbiter/__pycache__` | 4 |
| `trader/execution/__pycache__` | 4 |
| `trader/indicators/__pycache__` | 6 |
| `trader/infrastructure/__pycache__` | 12 |
| `trader/risk/__pycache__` | 4 |
| `trader/routing/__pycache__` | 4 |
| `trader/strategies/__pycache__` | 4 |
| `trader/strategies/plugins/__pycache__` | 42 |
| `trader/strategies/v8_grid/__pycache__` | 6 |
| `trader/tests/__pycache__` | 178 |
| `trader/tests/legacy/__pycache__` | 5 |

`trader/tests/legacy` is ignored and currently only contains legacy test
bytecode. It is a Phase 1A local-cleanup candidate.

## Plugin Inventory

- Runtime enabled strategy ids: 3
- Catalog entries: 38
- Plugin files: 37
- Research or fixture plugin files outside runtime modules: 34
- Files missing from catalog: none observed
- Catalog modules missing source files: none observed

Runtime modules:

- `macd_signal_trending_up_4h_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- `donchian_range_fade_4h_range_width_cv_013`
- `donchian_range_fade_4h_range_width_cv_013_short`

Phase 1B should add explicit classification before deleting any plugin files.

## Test Inventory

Rough grouping by filename:

| group | count |
| --- | ---: |
| runtime/core/other | 19 |
| MACD strategy variants | 22 |
| Donchian strategy variants | 5 |
| other research strategy tests | 10 |
| scanner tests inside `trader/tests` | 4 |
| grid/pool tests | 3 |

This supports Phase 2B test reorganization. It does not justify deleting tests
without matching source cleanup.

## Reference Hotspots

Phase 2A grid retirement must account for:

- `trader/bot.py`: `V8AtrGrid`, `PoolManager`, `GridManager`, `ENABLE_GRID_TRADING`
- `trader/grid_manager.py`
- `trader/config.py`: `ENABLE_GRID_TRADING`, `GRID_*`
- `trader/btc_context.py`: grid-enabled BTC trend resolution
- `extensions/Backtesting/grid_adapter.py`
- `trader/tests/test_grid.py`
- `trader/tests/test_grid_integration.py`
- `trader/tests/test_pool_manager.py`

Phase 2C indicator cleanup must account for:

- `TechnicalAnalysis`
- `DynamicThresholdManager`
- `MTFConfirmation`
- `MarketFilter`
- backtesting and scanner imports of `TechnicalAnalysis`, `_adx`, and `_bbw`

Phase 2D risk cleanup must account for:

- live use of `PrecisionHandler`
- live account access through `RiskManager.get_balance()`
- possible retirement or legacy marking for `RiskManager.calculate_position_size()`
- `SignalTierSystem`, `signal_tier`, and `tier_score` as artifact compatibility

Phase 3 infrastructure cleanup must preserve:

- `PerformanceDB` schema compatibility, including legacy columns such as
  `is_v6_pyramid`, `signal_tier`, `tier_score`, `grid_level`, and `grid_round`
- dashboard/backtest readers that still consume historical schema fields
- Telegram and notifier behavior expected by current runtime tests

## Phase Readiness

Phase 0 is ready for review.

Recommended next step after review:

1. Commit this report and the Phase 0 status update.
2. Start Phase 1A local cache cleanup.
3. Then start Phase 1B plugin classification without deleting plugin files in
   the first pass.
