# Portfolio A+B Monitoring Handoff

Date: 2026-05-05
Status: `OPS_MONITORING_HANDOFF`
Branch: `codex/post-promotion-control-20260430`

## Purpose

This handoff turns the promoted fixed A+B portfolio into the current monitoring
baseline after Phase 4/5 closeout and the `NO_MATERIAL_GAP` trigger review.

It is operational hygiene only:

- no new alpha research
- no runtime promotion
- no scanner universe activation
- no recovery backlog activation
- no production/testnet state change
- no threshold loosening

## Runtime Truth

Current runtime authority is code first, then the reports listed below.

Code truth:

- `trader/config.py`
- `trader/strategy_runtime.py`
- `trader/strategies/plugins/_catalog.py`
- promoted Slot A/B plugin files

Report truth:

- `reports/portfolio_ab_promotion_gated_freeze.md`
- `reports/portfolio_ab_promotion_review.md`
- `reports/portfolio_ab_post_promotion_control.md`
- `reports/phase_4_5_research_closeout.md`
- `reports/portfolio_ab_trigger_review.md`
- `reports/scanner_production_universe_filter_review.md`

Current runtime defaults:

| item | expected value |
| --- | --- |
| `STRATEGY_RUNTIME_ENABLED` | `True` |
| `ENABLED_STRATEGIES` | Slot A + Slot B only |
| `SYMBOLS` | `["BTC/USDT", "ETH/USDT"]` |
| `USE_SCANNER_SYMBOLS` | `False` |
| `SCANNER_UNIVERSE_ENABLED` | `False` |
| `STRATEGY_ROUTER_POLICY` | `"fail_closed"` |
| `REGIME_ARBITER_ENABLED` | `True` |
| `REGIME_ROUTER_ENABLED` | `False` |
| `RISK_PER_TRADE` | `0.017` |
| `MAX_TOTAL_RISK` | `0.0642` |

Promoted scope:

| slot | strategy id | symbol scope | role |
| --- | --- | --- | --- |
| Slot A | `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter` | `BTC/USDT` | 4h trend continuation with transition-aware defense |
| Slot B | `donchian_range_fade_4h_range_width_cv_013` | `BTC/USDT`, `ETH/USDT` | 4h geometric range fade |

Scanner boundary:

- `runtime_scanner.json` is diagnostics-only.
- `scanner_universe.json` is infra-ready and observe-only by default.
- `hot_symbols.json` remains legacy 2B research output, not promoted runtime
  input.
- `StrategyRuntime` reads `scanner_universe.json` only when
  `SCANNER_UNIVERSE_ENABLED=True` and at least one enabled plugin explicitly
  opts into dynamic universe scope.

## Standard Checks

Run before any handoff, release-style branch change, or runtime-adjacent patch:

```bash
python -c "from trader.config import Config; Config.validate(); print('Config.validate PASS')"
python -m pytest trader/tests extensions/Backtesting/tests -q
```

Use this config sanity snapshot when checking for accidental drift:

```bash
python -c "from trader.config import Config; print(Config.STRATEGY_RUNTIME_ENABLED, Config.ENABLED_STRATEGIES, Config.SYMBOLS, Config.USE_SCANNER_SYMBOLS, Config.SCANNER_UNIVERSE_ENABLED, Config.RISK_PER_TRADE, Config.MAX_TOTAL_RISK, Config.STRATEGY_ROUTER_POLICY)"
```

Optional diagnostics:

```bash
python -m scanner.runtime_scanner
python -m scanner.universe_scanner --no-write
```

Read `scanner.runtime_scanner` as advisory context only. Do not treat scanner
diagnostics as runtime symbol selection.

## Watchlist

Configuration drift:

- `SCANNER_UNIVERSE_ENABLED` becomes `True` without an explicit scanner
  activation review.
- `USE_SCANNER_SYMBOLS` becomes `True`.
- `ENABLED_STRATEGIES` contains anything other than promoted Slot A/B.
- `STRATEGY_ROUTER_POLICY` changes away from `fail_closed`.
- `RISK_PER_TRADE` or `MAX_TOTAL_RISK` changes without a sizing review.

Runtime behavior:

- router block rates approach or exceed the promotion hard gate of `0.50`.
- repeated `central_risk_blocked` appears outside expected stress windows.
- Slot A emits outside its fixed BTC scope.
- Slot B emits outside fixed BTC/ETH scope.
- same-symbol same-candle A+B overlap appears; promotion evidence had `0`.
- unexpected candidate generation errors appear in runtime logs or audit rows.

Portfolio behavior:

- drawdown approaches the promotion gate of `8%`.
- Slot A is silent through clear trend-continuation conditions.
- Slot B is silent through multiple credible range-fade conditions.
- Slot B frequency remains low; treat this as a monitoring caveat, not an
  automatic trigger.

Scanner behavior:

- `scanner_universe.json` should not alter promoted A+B symbols.
- stale or malformed scanner universe files should not affect A+B runtime.
- long-running scanner loop mode should not run side by side with cron for the
  same output file.

## Reopen Criteria

Reopen a new trigger review only when new evidence shows a concrete gap.

Good reasons to reopen:

- post-promotion dry-run/live observations show a persistent Slot A trend
  coverage gap
- post-promotion observations show a persistent Slot B ranging or frequency gap
- reject mix drift shows routing, cooldown, central risk, or slot occupancy
  behaving materially differently from promotion evidence
- live/dry-run drawdown behavior approaches the promotion hard gate
- Ruei explicitly requests scanner-universe activation review
- Ruei explicitly requests SHORT or transition-window research despite the
  current `NO_MATERIAL_GAP` classification

Bad reasons to reopen:

- wanting more trades
- wanting to use scanner output because it exists
- trying to rescue RSI2 or BB Fade Squeeze after they were parked
- creating backlog specs without a fresh trigger review
- loosening thresholds to force participation

## Do Not Start Without Ruei Approval

- new backlog `cartridge_spec_<id>.md` files
- new backlog plugin files
- new backlog tests
- new backlog catalog entries
- A+B+candidate combined backtests
- scanner universe runtime activation
- runtime default changes
- production/testnet service changes

## Current Next Work

Monitor the promoted fixed A+B baseline and keep the repo healthy. The next
research move requires a fresh trigger review with concrete new evidence.
