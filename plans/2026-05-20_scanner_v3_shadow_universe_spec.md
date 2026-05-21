# Scanner V3 Shadow Universe Spec

Date: 2026-05-20
Branch: `codex/post-promotion-control-20260430`
Status: `SPEC_ONLY`

## Executive Read

Scanner V3 is a new weekly-profit research lane for widening the opportunity
funnel without loosening strategy thresholds.

The current promoted runtime remains fixed:

- Slot A LONG:
  `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- Slot B LONG: `donchian_range_fade_4h_range_width_cv_013`
- Slot B SHORT: `donchian_range_fade_4h_range_width_cv_013_short`
- runtime symbols: `BTC/USDT`, `ETH/USDT`
- scanner runtime consumption: disabled

This spec does not authorize runtime default changes, scanner runtime-universe
activation, promoted symbol expansion, strategy promotion, or threshold
loosening.

## Motivation

The Phase 5 candidate batch closed with no promotion. The strongest
participation repair came from Slot B symbol expansion, but holdout robustness
failed. That result says the project should not use broad static symbol
expansion as a promotion path.

The current clean-window dry-run observer is also showing a participation
warning: the promoted BTC/ETH baseline can run cleanly while still producing no
entry candidates for long periods. That is not a negative expectancy signal by
itself, but it is a weekly-profit participation risk.

Scanner V3 addresses this by asking:

> Which liquid, data-ready symbols would have been worth observing for the
> promoted-style plugins, before any capital or runtime scope is changed?

## Non-Goals

Scanner V3 must not:

- feed `StrategyRuntime` by default
- mutate `trader.config.Config`
- change `Config.SYMBOLS`
- enable `USE_SCANNER_SYMBOLS`
- enable `SCANNER_UNIVERSE_ENABLED`
- promote a dynamic-universe plugin
- loosen Slot A or Slot B thresholds
- use outcome/PnL data inside the scanner ranking
- revive legacy `hot_symbols.json -> bot_symbols` as runtime source
- bypass router, arbiter, cooldown, risk, or execution handoff

## Design Principle

Broaden the funnel by widening observation, not by weakening admission.

Scanner V3 is allowed to say:

> This symbol is liquid, data-ready, regime-compatible, and close enough to a
> promoted-style setup that it deserves shadow tracking.

Scanner V3 is not allowed to say:

> This symbol should trade because we need more trades.

## Existing Scanner Roles

The current scanner split remains intact:

| file | role | runtime effect |
| --- | --- | --- |
| `runtime_scanner.json` | promoted BTC/ETH runtime diagnostics | none |
| `scanner_universe.json` | V1 production eligibility universe | observe-only by default |
| `hot_symbols.json` | legacy 2B scanner output | not promoted runtime source |

Scanner V3 adds a new research-only artifact:

```text
scanner_shadow_universe.json
```

This artifact is not read by `StrategyRuntime`.

## Proposed Contract

`scanner_shadow_universe.json` should use a new contract version:

```json
{
  "scanner_contract_version": "scanner-shadow-universe/v1",
  "scan_time": "2026-05-20T00:00:00+00:00",
  "expires_at": "2026-05-20T00:30:00+00:00",
  "status": "ok",
  "runtime_selection_feeds_trading": false,
  "baseline_runtime_symbols": ["BTC/USDT", "ETH/USDT"],
  "eligible_symbols": [],
  "shadow_candidates": [],
  "excluded_symbols": [],
  "filter_config": {
    "market_type": "future",
    "quote": "USDT",
    "mode": "shadow_observation_only",
    "top_n": 20,
    "candidate_scan_limit": 80,
    "min_quote_volume_usd": 20000000
  }
}
```

`eligible_symbols` entry:

```json
{
  "symbol": "SOL/USDT",
  "rank": 3,
  "quote_volume_24h": 1000000000.0,
  "market_supported": true,
  "data_ready": true,
  "spread_pct": 0.0002,
  "timeframes": {
    "4h": {
      "rows": 260,
      "required_rows": 200,
      "latest_closed_candle": "2026-05-20T00:00:00+00:00",
      "fresh": true
    }
  },
  "reason_codes": []
}
```

`shadow_candidates` entry:

```json
{
  "symbol": "SOL/USDT",
  "strategy_id": "donchian_range_fade_4h_range_width_cv_013",
  "slot_hint": "slot_b",
  "side": "LONG",
  "candidate_class": "near_setup",
  "decision": "observe",
  "runtime_eligible": false,
  "diagnostics": {
    "range_detected": true,
    "width_cv": 0.11,
    "range_width_cv_max": 0.13,
    "lower_touches": 3,
    "upper_touches": 2,
    "near_lower_entry_band": false,
    "distance_to_lower_band_atr": 0.42,
    "rsi_14": 44.0,
    "rsi_entry": 40.0
  },
  "reason_codes": ["near_lower_band", "rsi_not_ready"]
}
```

`excluded_symbols` entry:

```json
{
  "symbol": "LOW/USDT",
  "reason_codes": ["low_volume"],
  "quote_volume_24h": 10000.0
}
```

## Filter Layers

### Layer 0 - Market Eligibility

Purpose: avoid symbols that should not enter any research universe.

Required checks:

- Binance futures market exists and is active/tradable
- quote currency is `USDT`
- stablecoins excluded
- leveraged-token patterns excluded
- quote volume passes configured minimum
- spread proxy passes configured maximum when available
- OHLCV data is deep enough for the evaluated plugin timeframes
- latest closed candle is fresh

Output:

- `eligible_symbols`
- `excluded_symbols`
- reason-code distribution

### Layer 1 - Plugin Compatibility

Purpose: avoid feeding a symbol to a plugin shape it cannot safely evaluate.

Required checks:

- plugin declares dynamic-universe compatibility for research replay, or the
  shadow tool explicitly overrides scope in research-only mode
- symbol quote matches plugin quote requirement
- required timeframes and indicators are available
- plugin-side support is explicit: Slot A, Slot B LONG, Slot B SHORT

Slot A caution:

- promoted Slot A is BTC-specific today.
- Scanner V3 may diagnose non-BTC trend-continuation contexts, but this must be
  treated as separate research and not as promoted Slot A expansion.

Slot B first fit:

- Slot B Donchian LONG/SHORT is the natural first shadow scanner fit because
  prior 4E evidence showed participation repair potential, while also proving
  that static broad expansion is not robust enough.

### Layer 2 - Regime And Predicate Diagnostics

Purpose: explain why a symbol is or is not close to a setup.

Allowed diagnostics:

- regime features available at scan time:
  - ADX
  - ADX slope
  - ATR pct
  - ATR ratio
  - BB width percentile
  - squeeze-like flag
  - chop-trend flag
- Slot A predicate state:
  - MACD cross latest
  - MACD above zero
  - trend gate
  - entry extension ATR
  - transition-aware late-entry veto context
- Slot B predicate state:
  - range detected
  - width CV
  - lower/upper touch counts
  - near lower/upper band
  - distance to entry band in ATR
  - RSI readiness

Disallowed diagnostics:

- future returns
- realized PnL
- post-hoc profitable symbol labels
- hand-picked holdout-window outcome labels

### Layer 3 - Shadow Admission Class

Purpose: rank what deserves observation without authorizing trading.

Candidate classes:

| class | meaning |
| --- | --- |
| `entry_ready_shadow` | promoted-style predicates currently emit an intent in research-only replay |
| `near_setup` | most predicates pass but one or two final timing gates are not ready |
| `regime_compatible` | market regime fits the plugin family but setup predicates are not close |
| `eligible_only` | market/liquidity/data pass, but no plugin setup relevance |
| `excluded` | failed eligibility or safety filters |

No class feeds runtime.

## Evidence Artifacts

Scanner V3 should produce:

- `scanner_shadow_universe.json`
- `scanner_shadow_universe.csv`
- `reports/scanner_v3_shadow_universe_packet.md`

The markdown packet should include:

- top eligible symbols
- top shadow candidates by plugin/side
- exclusion reason-code distribution
- no-entry attribution for current promoted BTC/ETH baseline
- overlap between BTC/ETH baseline and shadow symbols
- explicit statement that runtime selection is unaffected

## Evaluation Plan

### Stage A - One-Shot Shadow Packet

Goal:

- prove the scanner can produce a useful research packet without runtime
  effects.

Required checks:

- `runtime_selection_feeds_trading=false`
- `Config.SYMBOLS` unchanged
- `SCANNER_UNIVERSE_ENABLED=false`
- `USE_SCANNER_SYMBOLS=false`
- no `StrategyRuntime` import side effects that start bot execution

### Stage B - Daily Shadow Observation

Goal:

- collect near-setup and entry-ready shadow counts across changing 4h candles.

Cadence:

- run once daily
- do not run as a competing long-lived scanner loop initially
- keep artifacts local or ignored unless promoted to a report

Daily metrics:

- eligible symbol count
- shadow candidate count by plugin/side
- `entry_ready_shadow` count
- `near_setup` count
- top blocker reason codes
- data freshness failures

### Stage C - Historical Replay

Goal:

- test whether scanner-selected symbols preserve expectancy before any dry-run
  runtime admission.

Minimum replay outputs:

- baseline BTC/ETH packet
- scanner-shadow selected packet
- combined packet
- per-symbol attribution
- per-side attribution
- worst week
- max drawdown delta
- losing-symbol trade-volume share
- overlap with BTC/ETH entries

Hard gates:

- combined rolling 8w after-fee PnL must not be below baseline
- active-entry 8w ratio must improve
- positive all-week ratio must not decline
- positive exit-active week ratio must not decline
- max DD must not materially increase
- added trades must not be dominated by losing symbols
- pass primary and holdout windows

### Stage D - Research-Only Dynamic Plugin Candidate

Only after Stage C passes:

- create research-only dynamic-universe plugin candidate
- `enabled=False`
- no runtime default changes
- no scanner runtime activation
- no threshold changes

### Stage E - Dry-Run Opt-In Review

Only after Ruei approval:

- enable dynamic-universe candidate in a dry-run branch/config override
- keep fixed BTC/ETH promoted baseline as control
- compare runtime evidence side-by-side

This stage is not authorized by this spec.

## Acceptance Criteria For First Implementation

Scanner V3 first implementation is acceptable only if:

- it writes `scanner_shadow_universe.json`
- it never feeds runtime
- it does not alter `scanner_universe.json` semantics
- it does not alter `runtime_scanner.json` semantics
- it does not read or write credentials
- it does not change `trader/config.py`
- it has tests for:
  - contract version
  - no runtime-feed flag
  - eligibility reason codes
  - plugin/side diagnostic fields
  - BTC/ETH baseline kept separate from shadow symbols
  - no legacy `hot_symbols.json` output
- `Config.validate()` passes
- scanner/runtime focused tests pass

Suggested focused test command:

```bash
python -m pytest trader/tests/runtime/test_runtime_scanner.py trader/tests/scanner/test_scanner_universe.py -q
python -c "from trader.config import Config; Config.validate()"
```

## Roadmap Placement

Current roadmap state:

- Phase 5 candidate batch is closed with no promotion.
- 4E static symbol expansion is parked unless a pre-registered regime filter
  exists.
- Phase 3 clean-window dry-run observation is active.

Scanner V3 is therefore appropriate as a new route, but only as a shadow
research lane. It should run alongside the current dry-run observer and should
not replace the promoted BTC/ETH baseline until it produces primary plus
holdout evidence.

## First Work Package

Recommended first work package:

1. Implement `scanner/shadow_universe_scanner.py`.
2. Add `scanner_shadow_universe.json` to `.gitignore`.
3. Add unit tests under `trader/tests/scanner/`.
4. Generate one local packet.
5. Write `reports/scanner_v3_shadow_universe_packet.md`.
6. Review whether shadow candidates would have reduced the current 0-entry
   dry-run silence without using outcome data.

Stop after the packet. Do not promote anything.
