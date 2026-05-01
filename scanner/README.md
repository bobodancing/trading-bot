# Scanner

The scanner package now has two separate roles:

- `runtime_scanner.py`: current runtime diagnostics for the promoted StrategyRuntime portfolio.
- `universe_scanner.py`: production eligibility filter that writes `scanner_universe.json`.
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

## Production Universe Scanner

Generate the production eligibility universe:

```bash
python -m scanner.universe_scanner
```

Default output:

```text
scanner_universe.json
```

The universe scanner filters Binance futures USDT markets by liquidity, market
support, excluded-symbol rules, OHLCV depth, and closed-candle freshness. It
does not calculate alpha scores or strategy expectancy.

`StrategyRuntime` can consume this contract through
`Config.SCANNER_UNIVERSE_ENABLED`. If `scanner_universe.json` is missing,
stale, malformed, or not `status=ok`, runtime falls back to the fixed
`Config.SYMBOLS` portfolio. Existing Slot A/B plugins remain bounded by their
own `allowed_symbols`, so the scanner can filter BTC/ETH without widening those
plugins to arbitrary altcoins.

## Legacy 2B Scanner

The old market scanner is still available:

```bash
python -m scanner.market_scanner --once
```

It writes the legacy `hot_symbols.json` contract with `hot_symbols` and
`bot_symbols`. That output is no longer the default live runtime universe for
the promoted A+B portfolio.
