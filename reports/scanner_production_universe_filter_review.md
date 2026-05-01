# Scanner Production Universe Filter Review

Date: 2026-05-01
Branch: codex/post-promotion-control-20260430

## Decision

The production scanner filter is implemented as an eligibility universe, not
as alpha scoring.

Runtime now has three separate scanner concepts:

- `runtime_scanner.json`: diagnostics/readiness report.
- `scanner_universe.json`: production symbol eligibility filter.
- `hot_symbols.json`: legacy 2B research output, not the promoted runtime path.

## Filter Conditions

The V1 production universe filter accepts a symbol only when all conditions
pass:

- market is a Binance futures market supported by the exchange object
- symbol uses the `USDT` quote
- symbol is not in the stablecoin exclusion list
- symbol does not match leveraged-token exclusion patterns
- 24h quote volume is at least `20,000,000` USDT
- required OHLCV depth exists for `4h: 200` and `1d: 260`
- latest closed candle is fresh enough for the timeframe
- symbol ranks within the top 20 eligible symbols by 24h quote volume

The filter writes exclusion reason codes such as:

- `excluded_symbol`
- `excluded_pattern`
- `low_volume`
- `market_unsupported`
- `insufficient_data:<timeframe>`
- `stale_data:<timeframe>`

## Slot A/B Fit

Slot A:

- Strategy: MACD BTC 4h continuation under 1d trend gate.
- Current plugin scope: `BTC/USDT` only.
- Scanner effect: BTC must be eligible in `scanner_universe.json`; scanner
  cannot expand Slot A to other symbols.
- Fit: good. The scanner's `4h: 200` and `1d: 260` checks match Slot A's data
  requirements.

Slot B:

- Strategy: Donchian range fade 4h.
- Current plugin scope: `BTC/USDT`, `ETH/USDT`.
- Scanner effect: BTC/ETH are pre-filtered by liquidity and data readiness
  before Slot B sees them.
- Fit: good for current production safety. The `1d: 260` requirement is stricter
  than Slot B needs, but acceptable for the first production universe because
  BTC/ETH have deep daily history and the same universe contract also supports
  Slot A diagnostics.

## Runtime Boundary

`StrategyRuntime` now attempts this order for entry symbols:

1. If `SCANNER_UNIVERSE_ENABLED=True`, load `scanner_universe.json`.
2. If the scanner universe is valid, use its `eligible_symbols` as the base
   universe.
3. If it is missing, stale, malformed, wrong contract, or not `status=ok`, fall
   back to fixed `Config.SYMBOLS`.
4. Apply plugin scope after the base universe.

This means current promoted A+B runtime can be filtered by scanner eligibility
without widening either plugin to arbitrary altcoins.

## Review Notes

The current filter is deliberately conservative:

- It does not score strategy profitability.
- It does not loosen Slot A or Slot B gates.
- It does not bypass router, arbiter, cooldown, risk, or execution handoff.
- It keeps legacy `hot_symbols.json` out of the promoted runtime path.

Future improvement:

- If a future dynamic-universe plugin is promoted, replace the global
  `4h: 200` and `1d: 260` readiness rule with per-plugin timeframe readiness.
  That avoids requiring 1d data for symbols used only by 4h or 1h plugins.
