# Trader Cleanup Phase 3 - Infrastructure Cleanup

Date: 2026-05-11

## Scope

Phase 3 reviewed and cleaned the infrastructure layer around market data,
Telegram notifications/commands, direct Binance Futures helpers, and
`performance.db` persistence compatibility. The cleanup stayed inside the
current StrategyRuntime baseline:

- `StrategyRuntime` + `StrategyPlugin` contract
- `Config` class defaults only
- secrets-only credential loading
- `PositionManager` / `performance.db` compatibility
- no retired grid/V6/V7/V53 live runtime assumptions

## Preflight

Commands run before edits:

- `git status --short --branch`
- `git log --oneline -8`
- `python -c "from trader.config import Config; Config.validate(); print('Config.validate PASS')"`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\agent_check.ps1 -Scope fast`
- infrastructure inventory with `rg`

Notes:

- Working tree was clean before edits.
- Current checkout reported branch
  `codex/post-promotion-control-20260430...github/codex/post-promotion-control-20260430`.
- `Config.validate PASS`
- fast agent check: `527 passed, 16 deselected`

## Cleaned Files

### `trader/infrastructure/api_client.py`

- Clarified that credentials are injected by the caller after
  `Config.load_secrets()`; the client does not load secrets or mutate
  `Config`.
- Added explicit Binance demo/live Futures base URL constants.
- Extracted signed-param construction, throttling, response dispatch, weight
  update, and timestamp-drift logging helpers.
- `signed_request()` now signs a copy of caller params instead of mutating the
  supplied dict.
- Preserved the existing `sandbox` argument and `signed_request_json()` return
  shape.

### `trader/infrastructure/data_provider.py`

- Reworded stale Demo Trading/scanner implementation comments into current
  runtime/scanner market-data wording.
- Extracted Binance demo futures OHLCV fallback into a helper.
- Extracted DataFrame conversion while preserving the public fetch contract:
  `timestamp` remains both a column and the `DatetimeIndex`.
- Restored retry semantics when ccxt fails and the sandbox fallback cannot
  return usable candles.

### `trader/infrastructure/notifier.py`

- Normalized StrategyRuntime strategy label formatting.
- Kept `legacy_manual` and `manual_protective` labels as compatibility aliases
  for existing `PositionManager` metadata.
- Reworded the old notifier alias comment as backward compatibility, not a
  retired runtime path.
- Preserved Telegram HTML escaping behavior.

### `trader/infrastructure/telegram_handler.py`

- Kept command compatibility for `/positions`, `/status`, `/balance`, and
  `/help`.
- Hardened `/positions` rendering against missing optional `PositionManager`
  fields.
- Escaped strategy label, symbol, side, stage, and tier fields before sending
  Telegram HTML.
- Kept `strategy_name` fallback only as compatibility for historical
  `PositionManager` records.

### `trader/infrastructure/performance_db.py`

- Reworded stale Phase 1-only DB purpose comments toward current
  StrategyRuntime review and dashboard/backtest readers.
- Moved idempotent migration SQL into `IDEMPOTENT_MIGRATIONS`.
- Moved optional insert defaults into `OPTIONAL_TRADE_FIELDS`.
- Added explicit historical compatibility notes for retained fields.
- Preserved `CREATE_TABLE_SQL`, `INSERT_SQL`, required columns, and
  idempotent `ALTER TABLE` behavior.

## Retained Compatibility

- No runtime defaults were changed.
- No credentials handling was changed.
- No `performance.db` columns were deleted or renamed.
- `grid_level` and `grid_round` remain for historical DB/dashboard readers.
- `is_v6_pyramid`, `signal_tier`, `tier_score`, and `strategy_name` remain for
  existing DB rows, backtest artifacts, dashboard code, and `PositionManager`
  compatibility.
- `Notifier = TelegramNotifier` remains for existing imports.
- Market data callers still receive either a populated OHLCV DataFrame or an
  empty DataFrame on failure.

## Removed Or Reworded Residue

- Removed wording that framed Binance demo fallback as an old bot/scanner
  duplication cleanup.
- Replaced "legacy column" wording in market data with reader compatibility
  wording.
- Replaced Phase 1-only `performance.db` wording with current runtime review
  wording.
- Replaced old notifier alias wording with backward-compatible import wording.

## Tests Run

- `python -c "from trader.config import Config; Config.validate(); print('Config.validate PASS')"`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\agent_check.ps1 -Scope fast`
- `python -m pytest trader/tests/infrastructure/test_data_provider.py trader/tests/infrastructure/test_notifier_escape.py trader/tests/infrastructure/test_telegram_handler.py trader/tests/infrastructure/test_perf_db_quality.py -q`
- inline `api_client` smoke for signed-request param immutability and
  non-fatal timestamp-hint parsing

Focused result:

- `30 passed`
- `api_client smoke PASS`

Full validation:

- `python -m pytest trader/tests extensions/Backtesting/tests -q`
  - `543 passed`
- `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\agent_check.ps1 -Scope fast`
  - `527 passed, 16 deselected`

## Known Follow-ups

- Broader repo inventory still contains historical V6/V7/V53/grid wording in
  dashboard/backtest docs and compatibility readers. Those are outside Phase 3
  infrastructure scope.
- `trader/persistence.py` still has retired grid state helpers and old wording;
  it should be handled in a dedicated persistence compatibility phase.
