# Codex Handoff - strategy-runtime-reset

Last updated: 2026-05-08. Code is the source of truth when this file conflicts
with implementation.

## Working Style

- Language: 繁體中文 + English technical terms.
- Start with code, git log, and local context before asking.
- Keep changes conservative and scoped.
- Comments explain why, not what.
- Timezone: Asia/Taipei.

## Current Runtime Truth

Repo root:

```text
C:\Users\user\Documents\tradingbot\strategy-runtime-reset
```

Current branch:

```text
codex/post-promotion-control-20260430
```

Runtime authority:

- `trader/config.py`
- `trader/strategy_runtime.py`
- `trader/strategies/base.py`
- `trader/strategies/plugins/_catalog.py`
- promoted plugin files under `trader/strategies/plugins/`

Current promoted runtime defaults:

```text
STRATEGY_RUNTIME_ENABLED = true
STRATEGY_RUNTIME_SIDE_FILTER = "both"
ENABLED_STRATEGIES = [
  "macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter",
  "donchian_range_fade_4h_range_width_cv_013",
  "donchian_range_fade_4h_range_width_cv_013_short",
]
USE_SCANNER_SYMBOLS = false
SCANNER_UNIVERSE_ENABLED = false
REGIME_ARBITER_ENABLED = true
REGIME_ROUTER_ENABLED = false
STRATEGY_ROUTER_POLICY = "fail_closed"
MACRO_OVERLAY_ENABLED = false
BTC_TREND_FILTER_ENABLED = true
BTC_TREND_FILTER_RUNTIME_MODE = "diagnostic"
BTC_COUNTER_TREND_MULT = 0.0
RISK_PER_TRADE = 0.017
MAX_TOTAL_RISK = 0.0642
```

Promoted portfolio:

| slot | strategy id | role |
| --- | --- | --- |
| Slot A LONG | `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter` | BTC 4h trend continuation |
| Slot B LONG | `donchian_range_fade_4h_range_width_cv_013` | BTC/ETH 4h lower-bound range fade |
| Slot B SHORT | `donchian_range_fade_4h_range_width_cv_013_short` | BTC/ETH 4h upper-bound range fade |

Slot A SHORT remains research-only and must not be added to runtime defaults
without explicit Ruei approval.

## Frozen Contract

Frozen target is the plugin runtime kernel:

- `StrategyPlugin` / `SignalIntent` boundary.
- `StrategyRuntime` routing and arbiter path.
- central `RiskPlan` sizing and risk caps.
- `PositionManager` / persistence schema compatibility.
- `Config.validate()` fail-fast checks.
- secrets-only credential loading.

Plugins may evolve independently, but plugins must not size orders, place
orders, mutate global `Config`, load credentials, write runtime persistence
directly, or bypass central risk / arbiter / router / execution handoff.

## Safety Boundaries

Do not do these unless Ruei explicitly asks:

- Promote a research plugin into runtime.
- Add a strategy to `ENABLED_STRATEGIES` as a runtime default.
- Change `STRATEGY_ROUTER_POLICY` away from `fail_closed`.
- Enable scanner universe as live runtime input.
- Patch production scanner defaults for a backtest-only need.
- Bypass central risk sizing or execution.
- Touch real production/testnet service state.
- Change credentials handling or commit secrets.
- Break `positions.json` / persistence backward compatibility.
- Reintroduce `bot_config.json` or another runtime-default JSON mirror.
- Recreate legacy V54 / 2B / EMA/VB lane adapters without explicit approval.
- Loosen thresholds just to get trades.

## Standard Checks

Before handoff:

```powershell
python -c "from trader.config import Config; Config.validate(); print('Config.validate PASS')"
python -m pytest trader/tests extensions/Backtesting/tests -q
```

Fast local check while iterating:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\agent_check.ps1 -Scope fast
```

Runtime snapshot:

```powershell
python -c "from trader.config import Config; print(Config.STRATEGY_RUNTIME_ENABLED, Config.STRATEGY_RUNTIME_SIDE_FILTER, Config.ENABLED_STRATEGIES, Config.SYMBOLS, Config.USE_SCANNER_SYMBOLS, Config.SCANNER_UNIVERSE_ENABLED, Config.RISK_PER_TRADE, Config.MAX_TOTAL_RISK, Config.STRATEGY_ROUTER_POLICY)"
```

Optional diagnostics:

```powershell
python -m scanner.runtime_scanner
python -m scanner.universe_scanner --no-write
```

Scanner diagnostics are advisory. They are not runtime symbol selection while
`USE_SCANNER_SYMBOLS=False` and `SCANNER_UNIVERSE_ENABLED=False`.

BTC trend filter note: StrategyRuntime records BTC trend diagnostics by default.
Runtime blocking or size reduction requires `BTC_TREND_FILTER_RUNTIME_MODE =
"enforce"` and fresh review evidence. See
`reports/runtime_btc_trend_filter_mode_review.md`.

## Plugin Work

Use `trader/strategies/plugins/HOWTO.md` for authoring rules.

Normal plugin changes should be limited to:

- `trader/strategies/plugins/<plugin_id>.py`
- focused tests under `trader/tests/`
- one catalog entry in `trader/strategies/plugins/_catalog.py`
- optional backtest smoke when timeframe, side, or exit behavior is new
- reports or backtest artifacts

Candidate reviews must use StrategyRuntime:

```powershell
python -m extensions.Backtesting.scripts.run_candidate_review --candidate <plugin_id>
```

Parameter sweeps are research-only:

```powershell
python -m extensions.Backtesting.scripts.run_parameter_sweep --candidate <plugin_id> --sweep-id <short_id> --param name=value1,value2
```

## Current Work Queue

1. Monitor the promoted three-leg runtime portfolio.
2. Keep scanner universe observe-only unless Ruei approves activation review.
3. Keep Slot A SHORT frozen research-only unless a new non-mirror thesis is
   explicitly selected.
4. Start new recovery backlog work only after a fresh trigger review and Ruei
   approval selects exactly one mechanism pair.
