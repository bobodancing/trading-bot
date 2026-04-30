# Runtime Scanner V2 Review

Date: 2026-04-30
Branch: codex/post-promotion-control-20260430

## Decision

The scanner is split into two lanes:

- `scanner/runtime_scanner.py` is the current runtime diagnostics lane for the promoted A+B portfolio.
- `scanner/market_scanner.py` remains the legacy 2B research scanner.

The promoted runtime no longer consumes scanner output as its live tradable
universe. `Config.USE_SCANNER_SYMBOLS` is now `False`; `StrategyRuntime` uses
`Config.SYMBOLS` and then narrows that set through enabled plugin
`allowed_symbols`.

## Current Runtime Scope

Enabled strategies:

- Slot A: `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- Slot B: `donchian_range_fade_4h_range_width_cv_013`

Runtime default symbol scope:

- `BTC/USDT`
- `ETH/USDT`

`SOL/USDT` and `DOGE/USDT` are no longer runtime defaults for the promoted A+B
portfolio.

## Runtime Scanner Contract

Default command:

```bash
python -m scanner.runtime_scanner
```

Default output:

```text
runtime_scanner.json
```

The runtime scanner report includes:

- enabled strategy ids and plugin scopes
- runtime symbols derived from plugin `allowed_symbols`
- OHLCV data readiness by required timeframe
- 4h regime feature diagnostics aligned with `RegimeArbiter`
- Slot A MACD/trend telemetry
- Slot B Donchian/range telemetry

The runtime scanner intentionally does not write `bot_symbols` or
`hot_symbols`.

## Deployment Boundary

The runtime scanner is advisory only:

- does not feed `StrategyRuntime.scan_for_entries()`
- does not size orders
- does not place orders
- does not mutate `Config`
- does not widen the promoted runtime symbol universe
- does not loosen strategy gates

The legacy 2B scanner can still produce `hot_symbols.json` for research, but
that JSON is no longer the promoted runtime universe source.

## Follow-Up Backlog

After control is stable, scanner v2 can be expanded with:

- exchange market support checks for each runtime symbol
- data freshness SLA warnings per timeframe
- Telegram-friendly runtime health summary
- optional research-only candidate universe, stored separately from runtime
  diagnostics
