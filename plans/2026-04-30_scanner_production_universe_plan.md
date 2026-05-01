# Scanner Production Universe Plan

Date: 2026-04-30
Last updated: 2026-05-01
Status: V1 implemented for runtime universe filtering; keep alpha research separate
Owner: Ruei
Branch: codex/post-promotion-control-20260430

## Summary

This plan defines how the scanner can later become a production trading-pair
filter again without disturbing the current promoted A+B runtime.

The current scanner v2 remains diagnostics-only for testnet runtime. During
Phase 4/5, scanner output must stay observe-only so RSI2 and BB Fade Squeeze
closeout reports are not mixed with a new symbol-selection variable.

Production scanner integration is a runtime-universe project, not an alpha
research task.

Implementation note (2026-05-01):

- `scanner/universe_scanner.py` writes `scanner_universe.json`.
- `StrategyRuntime` can consume `scanner_universe.json` before applying plugin
  scope.
- Missing/stale/malformed universe files fall back to fixed `Config.SYMBOLS`.
- Promoted Slot A/B remain bounded by their own `allowed_symbols`.

## Locked Decisions

- Phase 4/5: scanner observe-only.
- Production universe file: `scanner_universe.json`.
- Legacy live path to avoid: `hot_symbols.json -> bot_symbols`.
- First production universe scope: Binance futures USDT top liquid symbols.
- First cap: top 20 eligible symbols.
- First filter depth: eligibility only, no alpha scoring.
- Runtime failure mode: fallback to fixed portfolio.
- Dynamic universe contract: plugin opt-in only.
- Promoted A+B portfolio remains fixed BTC/ETH unless explicitly changed later.

## Intended Data Flow

Future production flow:

```text
Binance futures USDT markets
  -> scanner eligibility filter
  -> scanner_universe.json
  -> runtime scanner-universe loader
  -> StrategyRuntime
  -> plugin opt-in scope check
  -> central router / risk / execution
```

Current Phase 4/5 flow remains unchanged:

```text
Config.SYMBOLS + plugin.allowed_symbols
  -> StrategyRuntime
  -> central router / risk / execution
```

## Scanner Universe Contract

`scanner_universe.json` should be a new contract, separate from
`runtime_scanner.json` and legacy `hot_symbols.json`.

Minimum fields:

```json
{
  "scanner_contract_version": "scanner-universe/v1",
  "scan_time": "2026-04-30T00:00:00+00:00",
  "expires_at": "2026-04-30T00:30:00+00:00",
  "status": "ok",
  "eligible_symbols": [],
  "excluded_symbols": [],
  "filter_config": {
    "market_type": "future",
    "quote": "USDT",
    "top_n": 20,
    "mode": "eligibility_only"
  }
}
```

`eligible_symbols` entries should include:

- `symbol`
- `rank`
- `quote_volume_24h`
- `data_ready`
- `market_supported`
- `reason_codes`

`excluded_symbols` entries should include:

- `symbol`
- `reason_codes`
- optional evidence fields such as `quote_volume_24h`, `rows`, or
  `latest_closed_candle`.

## Eligibility Filter V1

The first production filter should only answer:

> Is this symbol eligible to be considered by an opt-in runtime plugin?

It must not answer:

> Is this symbol expected to be profitable for a strategy?

V1 checks:

- Binance futures market exists and is tradable.
- Quote currency is USDT.
- Symbol is not in the excluded stablecoin list.
- Symbol does not match leveraged-token patterns.
- 24h quote volume passes the configured minimum.
- OHLCV data depth passes the required timeframe warmup.
- Latest closed candle is fresh enough for the scan interval.
- Result rank is within top 20 after eligibility filtering.

V1 explicitly does not include:

- strategy alpha score
- win-rate or expectancy ranking
- live threshold loosening
- order sizing
- execution hints
- credential loading
- runtime config mutation

## Runtime Integration Plan

Runtime integration must be disabled by default until Phase 4/5 closeout is
complete and Ruei approves the next runtime-universe step.

Future config shape:

```python
SCANNER_UNIVERSE_ENABLED = False
SCANNER_UNIVERSE_JSON_PATH = "scanner_universe.json"
SCANNER_UNIVERSE_MAX_AGE_MINUTES = 30
```

Runtime symbol behavior:

- If `SCANNER_UNIVERSE_ENABLED` is false, use current fixed behavior.
- If scanner JSON is missing, stale, malformed, or has `status != "ok"`,
  fallback to fixed portfolio.
- Non-opt-in plugins receive only their current `allowed_symbols` scope.
- Opt-in plugins may receive scanner eligible symbols, but still must define
  their own support boundary.
- Scanner symbols must never bypass central risk, router, arbiter, cooldown, or
  execution handoff.

Suggested plugin opt-in shape:

```python
supports_dynamic_universe = False
dynamic_universe_quote = "USDT"
dynamic_universe_max_symbols = 20
```

Existing promoted A+B plugins should remain non-opt-in unless a later research
and promotion report explicitly changes them.

## Phase Schedule

### Phase 4/5 Runtime Use With Fixed Plugin Scope

- Keep `runtime_scanner.json` as diagnostics-only.
- Generate `scanner_universe.json` with `scanner/universe_scanner.py`.
- Runtime may use `scanner_universe.json` as a pre-filter before Slot A/B
  `allowed_symbols`.
- Do not use scanner universe to alter RSI2 or BB closeout backtest symbols
  unless the specific run is testing scanner-universe behavior.
- Reports should separate scanner filtering effects from alpha gate effects.

### Post Phase 4/5 Integration

- Add scanner-universe loader and schema validation.
- Add plugin opt-in contract.
- Add tests for fixed fallback and opt-in isolation.
- Run testnet dry-run before any live production use.

### Production Enablement

- Enable only after Ruei approval.
- Start with one dynamic-universe-capable plugin.
- Keep A+B fixed BTC/ETH as fallback baseline.
- Monitor eligible/excluded reason-code distribution before relying on it for
  capital deployment.

## Acceptance Criteria

The future implementation is acceptable only if:

- Missing or bad scanner JSON falls back to fixed BTC/ETH behavior.
- Existing A+B runtime behavior is unchanged while plugins are non-opt-in.
- Dynamic scanner symbols cannot reach non-opt-in plugins.
- `hot_symbols.json` is not used as the production runtime universe source.
- Tests cover stale JSON, malformed JSON, empty eligible list, non-opt-in
  plugins, and opt-in plugin scoping.
- Full runtime validation still passes:

```bash
python -c "from trader.config import Config; Config.validate()"
python -m pytest trader/tests extensions/Backtesting/tests -q
```

## Out of Scope

- No code changes in this plan commit.
- No scanner-driven runtime trading during Phase 4/5.
- No new alpha research from scanner ranking.
- No revival of legacy 2B scanner as the live symbol source.
- No expansion of promoted A+B beyond BTC/ETH.
- No push from this commit unless Ruei explicitly requests it.
