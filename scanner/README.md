# Scanner

The scanner package now has two separate roles:

- `runtime_scanner.py`: current runtime diagnostics for the promoted StrategyRuntime portfolio.
- `market_scanner.py`: legacy 2B research scanner, retained for historical/research use.

## Runtime Scanner

The promoted A+B runtime does not use scanner output as its tradable universe.
The live universe is fixed by `trader.config.Config.SYMBOLS` and each enabled
plugin's `allowed_symbols`.

Run a one-shot runtime diagnostics report:

```bash
python -m scanner.runtime_scanner
```

Default output:

```text
runtime_scanner.json
```

The runtime report intentionally does not write `bot_symbols` or `hot_symbols`.
It reports:

- enabled strategy ids and plugin scopes
- runtime symbols derived from plugin scope
- OHLCV data depth and freshness by timeframe
- 4h regime feature diagnostics aligned with `RegimeArbiter`
- Slot A MACD trend/readiness telemetry
- Slot B Donchian range/readiness telemetry

This report is advisory only. It does not size orders, place orders, mutate
`Config`, or feed `StrategyRuntime.scan_for_entries()`.

## Legacy 2B Scanner

The old market scanner is still available:

```bash
python -m scanner.market_scanner --once
```

It writes the legacy `hot_symbols.json` contract with `hot_symbols` and
`bot_symbols`. That output is no longer the default live runtime universe for
the promoted A+B portfolio.
