# Scanner

The scanner package now has two separate roles:

- `runtime_scanner.py`: current runtime diagnostics for the promoted StrategyRuntime portfolio.
- `universe_scanner.py`: production eligibility filter that writes `scanner_universe.json`.
- `market_scanner.py`: legacy 2B research scanner, retained for historical/research use.

## Runtime Scanner

The runtime diagnostics scanner is advisory only. Promoted A+B live symbol
selection remains fixed by `trader.config.Config.SYMBOLS` plus plugin scope;
`scanner_universe.json` is infra-ready but observe-only by default.

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

The command above runs once and exits, which is still the safest mode for cron.
For a long-running scanner process, use loop mode:

```bash
python -m scanner.universe_scanner --loop --interval-minutes 15
```

Use either cron one-shot execution or loop mode, not both, so two scanner
processes do not compete to update the same file.

Loop mode only rewrites `scanner_universe.json`; it does not import or run
`bot.py`. Runtime remains decoupled and will keep falling back to
`Config.SYMBOLS` if the universe file is missing, stale, or malformed. Universe
writes use an atomic temp-file replace so `bot.py` should not read a half-written
JSON file.

The universe scanner filters Binance futures USDT markets by liquidity, market
support, excluded-symbol rules, OHLCV depth, and closed-candle freshness. It
does not calculate alpha scores or strategy expectancy.

`StrategyRuntime` can consume this contract only when
`Config.SCANNER_UNIVERSE_ENABLED` is explicitly enabled and a plugin opts into
dynamic universe scope. The current promoted Slot A/B plugins keep fixed scope,
so Phase 4/5 research remains on the BTC/ETH fixed-symbol baseline.

## Legacy 2B Scanner

The old market scanner is still available:

```bash
python -m scanner.market_scanner --once
```

It writes the legacy `hot_symbols.json` contract with `hot_symbols` and
`bot_symbols`. That output is no longer the default live runtime universe for
the promoted A+B portfolio.
