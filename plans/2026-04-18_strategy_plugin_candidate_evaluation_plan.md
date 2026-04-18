# Strategy Plugin Candidate Evaluation Plan

Date: 2026-04-18

Status: active plan. Do not promote any plugin from this plan alone.

Owner: Ruei

Backtest workspace: `extensions/Backtesting/`

## Context

The runtime has been reset to a strategy-plugin kernel. Legacy V54 / 2B / EMA_PULLBACK / VOLUME_BREAKOUT lane work is archived context and is not part of the current research track.

New strategy ideas should be evaluated as `StrategyPlugin` implementations that emit `SignalIntent` objects and then pass through the shared runtime:

```text
StrategyPlugin -> StrategyRuntime -> arbiter/router -> central risk -> execution handoff
```

## Candidate Source

Ruei's research list is the candidate universe. Visible examples include:

- Optimized BTC Mean Reversion
- Volatility Breakout System
- SuperTrend Adaptive
- BB Upper Breakout Short
- SuperTrend Strategy
- Penguin Volatility State
- MACD Zero-Line Long Only
- Hash Momentum
- Moon Phases Long/Short
- 7/19 EMA Crypto
- RSI > 70 Buy / Exit Cross Below 70
- 50 & 200 SMA + RSI Average
- Pivot Point SuperTrend

The list is a research backlog, not a promotion list.

## Plugin Acceptance Shape

Each candidate must define:

- stable plugin id,
- symbol and timeframe scope,
- required indicators,
- params schema,
- entry `SignalIntent` rules,
- required `stop_hint`,
- optional `update_position()` exit logic,
- focused unit tests for signal/no-signal cases,
- backtest run metadata.

Plugins must not:

- size positions,
- place or close orders,
- mutate `Config`,
- load secrets,
- write runtime persistence,
- bypass central risk, arbiter, router, or execution handoff.

## Backtest Guardrails

Backtests must use current StrategyRuntime path.

Config rules:

- Runtime config single source is `trader/config.py`.
- Backtests may use only per-run overrides.
- Overrides must pass `extensions/Backtesting/config_presets.py`.
- No runtime-default JSON mirror.
- No unrestricted `setattr(Config, key, value)` from arbitrary dicts.

Execution rules:

- `dry_count_only` must not open positions.
- Diagnostic arbiter-off runs can explain zero trades, but promotion decisions use the normal plugin-runtime baseline.
- Production scanner defaults are not changed for backtest-only needs.
- No threshold loosening just to get trades.

## Baseline Run Settings

Default research baseline:

```text
STRATEGY_RUNTIME_ENABLED = true for the selected plugin only
REGIME_ARBITER_ENABLED = current Config default
REGIME_ROUTER_ENABLED = current Config default
STRATEGY_ROUTER_POLICY = fail_closed
MACRO_OVERLAY_ENABLED = current Config default
BTC_TREND_FILTER_ENABLED = current Config default
```

Backtest runs should set explicit symbols instead of relying on production scanner JSON unless the test is specifically about scanner-universe robustness.

## First-Pass Windows

Use a small matrix first; expand only after the candidate survives smoke and focused tests.

| Label | Date Range | Purpose |
|---|---|---|
| `TRENDING_UP` | `2023-10-01 -> 2024-03-31` | trend-following and long-only sanity |
| `RANGING` | `2024-12-31 -> 2025-03-31` | chop / mean-reversion stress |
| `MIXED` | `2025-02-01 -> 2025-08-31` | transition / mixed market stress |

Add candidate-specific windows when the strategy thesis requires it.

## Required Outputs

Per candidate/window:

```text
extensions/Backtesting/results/plugin_candidate_review_YYYYMMDD/<PLUGIN_ID>/<WINDOW>/
  summary.json
  trades.csv
  signal_audit_summary.json
  signal_entries.csv
  signal_rejects.csv
  equity_curve.html
```

Review report:

```text
reports/strategy_plugin_candidate_review.md
```

## Report Requirements

The report should include:

- candidate id and thesis,
- symbol/timeframe scope,
- params used,
- total trades / PF / WR / MaxDD / Sharpe / net PnL,
- by-window performance,
- by-regime performance where audit data exists,
- rejection breakdown,
- worst symbol/window/trade,
- whether results are robust enough for a second pass.

Allowed verdicts:

```text
PROMOTE_PLUGIN
KEEP_RESEARCH_ONLY
NEEDS_SECOND_PASS
```

Promotion remains a Ruei decision. A passing report does not automatically change runtime defaults.

## Stop Conditions

Stop and report instead of patching around the result when:

- candidate produces no valid `SignalIntent`,
- candidate cannot provide a valid stop,
- central risk blocks all entries,
- arbiter blocks all entries under normal baseline,
- backtest has run errors,
- data coverage is incomplete,
- result depends on a single symbol or one outlier window.

## Pre-Handoff Checks

Run from repo root:

```bash
python -c "from trader.config import Config; Config.validate()"
python -m pytest trader/tests extensions/Backtesting/tests -q
```

Do not push, promote runtime defaults, or restart services unless Ruei explicitly asks.
