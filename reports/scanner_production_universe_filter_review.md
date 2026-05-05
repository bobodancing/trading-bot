# Scanner Production Universe Filter Review

Date: 2026-05-01
Last updated: 2026-05-05
Branch: codex/post-promotion-control-20260430

## Decision

The production scanner filter is implemented as an eligibility universe, not
as alpha scoring. Runtime consumption is parked observe-only by default so the
promoted A+B baseline stays fixed while Phase 4/5 research is closed out.

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

- Strategy: MACD 4h continuation under 1d trend gate.
- Current plugin scope: fixed BTC-only.
- Scanner effect: observe-only unless `SCANNER_UNIVERSE_ENABLED` and a dynamic
  plugin opt-in are explicitly restored.
- Fit: scanner breadth is intentionally not mixed into the current Slot A
  promotion baseline.

Slot B:

- Strategy: Donchian range fade 4h.
- Current plugin scope: fixed BTC/ETH.
- Scanner effect: observe-only unless `SCANNER_UNIVERSE_ENABLED` and a dynamic
  plugin opt-in are explicitly restored.
- Fit: scanner breadth is intentionally not mixed into the current Slot B
  promotion baseline.

## Runtime Boundary

`StrategyRuntime` attempts this scanner-universe order only when
`SCANNER_UNIVERSE_ENABLED=True` and at least one enabled plugin explicitly opts
into dynamic universe scope:

1. If `SCANNER_UNIVERSE_ENABLED=True`, load `scanner_universe.json`.
2. If the scanner universe is valid, use its `eligible_symbols` as the base
   universe.
3. If it is missing, stale, malformed, wrong contract, or not `status=ok`, fall
   back to fixed `Config.SYMBOLS`.
4. Apply plugin scope after the base universe.

The current default is `SCANNER_UNIVERSE_ENABLED=False`; promoted Slot A/B keep
fixed plugin scope, so a valid `scanner_universe.json` does not alter the
default A+B trading universe.

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
