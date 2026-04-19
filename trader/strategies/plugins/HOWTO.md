# Strategy Plugin Authoring HOWTO

This guide is for research cartridges that plug into the current
`StrategyRuntime` kernel. A plugin may describe trade intent and position
management, but sizing, risk caps, routing, persistence, and execution stay in
the shared runtime.

## Cartridge Checklist

A normal new plugin should only need:

- `trader/strategies/plugins/<plugin_id>.py`
- focused tests under `trader/tests/`
- one catalog entry
- optional backtest smoke test when the plugin uses a new timeframe, side, or
  exit pattern
- candidate review artifacts under `reports/` or
  `extensions/Backtesting/results/`

If a normal plugin requires edits to `trader/bot.py`,
`trader/strategy_runtime.py`, `extensions/Backtesting/backtest_engine.py`, or
runtime `Config` defaults, treat that as infrastructure debt and stop for review.

Catalog note: add catalog entries to `trader/strategies/plugins/_catalog.py`.
Catalog presence is not promotion; runtime activation still requires
`STRATEGY_RUNTIME_ENABLED=True` and an explicit `ENABLED_STRATEGIES` list.

## Plugin Contract

Subclass `StrategyPlugin` and set these class attributes:

```python
class ExampleStrategy(StrategyPlugin):
    id = "example_plugin_id"
    version = "0.1.0"
    tags = {"research", "long_only"}
    required_timeframes = {"1h": 100}
    required_indicators = {"ema", "atr"}
    params_schema = {
        "symbol": "str",
        "timeframe": "str",
        "risk_pct": "float",
        "emit_once": "bool",
    }
    allowed_symbols = {"BTC/USDT"}
    max_concurrent_positions = 1
    risk_profile = StrategyRiskProfile.fixed_risk_pct()
```

Plugins must not:

- size orders directly
- place or close orders directly
- mutate `Config`
- load credentials
- write runtime persistence directly
- bypass central risk, arbiter, router, or execution handoff

## Params Schema

`params_schema` is validated when `StrategyRegistry.from_config()` loads an
enabled plugin.

Supported scalar types:

- `"str"` or `str`
- `"bool"` or `bool`
- `"int"` or `int`
- `"float"` or `float`

Unknown param keys fail fast. Wrong types fail fast. Missing params are allowed
so plugins can keep local code defaults.

`bool` is not accepted as `int`. `int` is accepted as `float`.

Add a new validator only when a real plugin needs it. Do not encode complex
schemas ad hoc inside individual plugins.

## Indicators

Declare every indicator the plugin needs in `required_indicators`.

Supported names currently come from `IndicatorRegistry.supported_indicators()`:

- `ema`
- `sma`
- `atr`
- `adx`
- `bbw`
- `rsi`
- `macd`
- `bollinger`
- `supertrend`

Unsupported indicator names fail fast at registry load. This is intentional:
missing indicators must not look like a normal zero-signal run.

Plugins should still guard required columns before reading a frame, because data
can be empty, too short, or NaN-filled even when the indicator name is valid.

## Entry Intent

`generate_candidates(context)` returns a list of `SignalIntent`.

Each entry intent must include:

- `strategy_id`: exactly the plugin `id`
- `symbol`
- `side`: `LONG` or `SHORT`
- `timeframe`
- `candle_ts`
- `entry_type`
- `stop_hint`
- optional `confidence`
- optional `metadata`
- optional `entry_price`

Always provide a valid `StopHint`. Central risk rejects entries without a stop.

```python
SignalIntent(
    strategy_id=self.id,
    symbol=symbol,
    side="LONG",
    timeframe=timeframe,
    candle_ts=candle_ts,
    entry_type="ema_cross_up",
    stop_hint=StopHint(
        price=stop_price,
        reason="atr_stop",
        metadata={"atr": atr, "atr_mult": atr_mult},
    ),
    metadata={"fast_ema": fast, "slow_ema": slow},
    entry_price=entry_price,
)
```

## Exit Logic

Use `update_position(context, position)` for plugin-owned exit decisions.

Return a `PositionDecision`:

- `Action.HOLD`
- `Action.CLOSE`
- `Action.PARTIAL_CLOSE`
- `Action.UPDATE_SL`

The plugin describes the decision only. The shared monitor performs close,
partial close, or stop updates.

## Position Plugin State

`PositionManager.plugin_state` is the per-position state channel available to
plugins.

Rules:

- Store only JSON-serializable values.
- Keep backward compatibility when changing state shape.
- Prefer namespacing multi-field state under the plugin id.
- Do not store secrets or large market data snapshots.
- Do not depend on process-local plugin instance state for open positions.

Example:

```python
state = dict(getattr(position, "plugin_state", {}) or {})
mine = dict(state.get(self.id, {}) or {})
mine["updates"] = int(mine.get("updates", 0)) + 1
state[self.id] = mine
position.plugin_state = state
```

## Backtest Rules

Candidate backtests should use explicit symbols instead of scanner JSON unless
the test is specifically about scanner-universe robustness.

Use:

```python
from extensions.Backtesting.config_presets import (
    explicit_symbol_universe,
    plugin_runtime_defaults,
    strategy_id_allowlist,
)
```

Backtest config:

```python
cfg = BacktestConfig(
    symbols=["BTC/USDT"],
    start="2026-01-01",
    end="2026-03-01",
    enabled_strategies=["example_plugin_id"],
    allowed_plugin_ids=["example_plugin_id"],
    config_overrides=explicit_symbol_universe(plugin_runtime_defaults()),
)
```

`dry_count_only=True` records candidates and audit data without opening
positions. It must not be used as proof that a candidate can trade.

Do not loosen thresholds just to get trades. Report zero-trade results and the
reject breakdown.

## Tests

Add focused tests for:

- registry load
- no-signal cases
- entry intent shape
- invalid stop or missing data behavior
- exit decision, if implemented
- any plugin-specific params

Run before handoff:

```bash
python -c "from trader.config import Config; Config.validate()"
python -m pytest trader/tests extensions/Backtesting/tests -q
```

## First New Cartridge

The first new research plugin after the infrastructure pass is expected to be:

```text
ema_cross_7_19_long_only
```

Before coding it, lock:

- timeframe
- symbol scope
- stop rule
- params

Do not improvise those choices in code.
