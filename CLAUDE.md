# CLAUDE.md - strategy-runtime-reset 工作守則

Last updated: 2026-04-18. If this file conflicts with code, trust code first.

## 身份與溝通

- 我是小波（Ruei 家鼠鼠同名）。
- 語言：繁體中文 + English technical terms。
- 風格：直接、簡潔、token-aware、該反對就反對。
- 先讀 code / git log / local context，再問問題。
- Code 優先：讀懂再動手。
- Comments 寫 why，不寫 what。
- 時區：Asia/Taipei。

## 專案定位

- Owner: Ruei。
- Repo root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset`。
- Branch: `codex/strategy-runtime-reset`。
- 主線：strategy-plugin runtime reset。
- 舊 V53/V6/V7/V54 lane runtime 已刪除，不再作為 live 或 research 主線。
- 2B / EMA_PULLBACK / VOLUME_BREAKOUT / V54 lane review 是 legacy context；除非 Ruei 明講，不要復活。

## Runtime Baseline

Runtime baseline is:

```text
StrategyRuntime + StrategyPlugin contract + Config class defaults
```

Runtime config 的唯一來源是 `trader/config.py` 的 `Config` class defaults。外部檔只載 credentials：

```text
secrets.json -> Config.load_secrets()
```

目前 reset runtime 的核心 intent：

```text
STRATEGY_RUNTIME_ENABLED = false
ENABLED_STRATEGIES = []
REGIME_ARBITER_ENABLED = true
REGIME_ROUTER_ENABLED = false
STRATEGY_ROUTER_POLICY = "fail_closed"
MACRO_OVERLAY_ENABLED = false
BTC_TREND_FILTER_ENABLED = true
BTC_COUNTER_TREND_MULT = 0.0
USE_SCANNER_SYMBOLS = true
```

信任 runtime 前從 repo root 跑：

```bash
python -c "from trader.config import Config; Config.validate()"
```

## Frozen Contract

Frozen target is no longer `v54_noscale`.

Frozen target = plugin runtime kernel contract:

- `StrategyPlugin` / `SignalIntent` boundary。
- `StrategyRuntime` routing and arbiter path。
- central `RiskPlan` sizing and risk caps。
- `PositionManager` / persistence schema compatibility。
- `Config.validate()` fail-fast checks。
- secrets-only credential loading。

Plugins may evolve independently, but plugins must not:

- size orders directly,
- place orders directly,
- mutate global `Config` defaults,
- load credentials,
- write runtime persistence directly,
- bypass central risk / arbiter / router / execution handoff.

## Current Strategy Surface

`trader/strategies/plugins/` contains research plugins. The plugin catalog lives in `trader/strategies/plugins/_catalog.py`; catalog presence is not runtime promotion.

Current known plugin entries:

- `fixture_long` / `fixture_exit` - deterministic test fixtures.
- `macd_zero_line_btc_1d` - pilot research plugin, not production-approved by default.
- `macd_zero_line_btc_1d_trending_up` - regime-aware MACD follow-up cartridge, 1d BTC long-only, TRENDING_UP regime-declared.
- `macd_signal_btc_4h_trending_up` - higher-frequency MACD continuation cartridge, BTC 4h entries under a 1d trend gate, TRENDING_UP regime-declared.
- `macd_signal_btc_4h_trending_up_confirmed` - confirmed-entry variant of the 4h MACD continuation cartridge, adds histogram-expansion and price-over-EMA checks under the same 1d trend gate.
- `macd_signal_btc_4h_trending_up_confirmed_failfast` - fail-fast exit variant of the confirmed 4h MACD continuation cartridge, closes stalled continuation attempts after two 4h bars without follow-through.
- `ema_cross_7_19_long_only` - first post-infra research cartridge, 4h BTC/ETH long-only.
- `rsi_mean_reversion_15m` - gamma research cartridge, promotion-ineligible under checklist §5 (backtest engine lacks 15m support); kept as reference for future infra extension.
- `rsi_mean_reversion_1h` - delta research cartridge replacing gamma, 1h BTC/ETH long-only, RANGING regime-declared.

New candidate strategies from Ruei's research list should become strategy plugins before backtest:

- stable plugin id,
- symbol and timeframe scope,
- required indicators,
- params schema,
- entry `SignalIntent` rules,
- required `stop_hint`,
- optional position update / exit logic,
- focused unit tests,
- backtest run metadata.

## Backtest Contract

Backtests must use current StrategyRuntime path unless Ruei explicitly asks for a historical replay.

Rules:

- Per-run `Config` overrides only.
- Overrides must be explicit and whitelisted in `extensions/Backtesting/config_presets.py`.
- No JSON mirror of runtime defaults.
- No "accept any dict key and setattr" behavior.
- Backtest-only controls stay inside `extensions/Backtesting/`; do not change production scanner/runtime defaults.
- `dry_count_only` means candidate/audit collection only; it must not open positions.
- Promotion decisions require real backtest runs through StrategyRuntime and central risk path, not synthetic report tables.

Useful files:

- `extensions/Backtesting/backtest_engine.py` - engine and `_backtest_context`.
- `extensions/Backtesting/backtest_bot.py` - mocked live-like bot factory.
- `extensions/Backtesting/config_presets.py` - override whitelist and plugin-runtime presets.
- `extensions/Backtesting/plugin_id_filter.py` - backtest-only plugin id allowlist.
- `extensions/Backtesting/plugin_candidate_review.py` - plugin candidate report helpers.

## Folder Map

Root:

- `trader/` - runtime bot and strategy-plugin kernel.
- `scanner/` - production scanner tooling; do not change defaults for backtest-only needs.
- `extensions/Backtesting/` - local backtest workspace.
- `extensions/quantDashboard/` - dashboard tooling; may still include legacy labels for historical DB display.
- `plans/` - current planning docs.
- `reports/` - generated or hand-written analysis reports.

Important runtime files:

- `trader/bot.py`
- `trader/config.py`
- `trader/signal_scanner.py`
- `trader/strategy_runtime.py`
- `trader/strategies/base.py`
- `trader/strategies/plugins/`
- `trader/routing/regime_router.py`
- `trader/arbiter/regime_arbiter.py`
- `trader/positions.py`
- `trader/persistence.py`

## Safety Boundaries

Do not do these unless Ruei explicitly asks:

- Promote a research plugin into runtime.
- Turn on `STRATEGY_RUNTIME_ENABLED` by default.
- Add a strategy to `ENABLED_STRATEGIES` as a runtime default.
- Change `STRATEGY_ROUTER_POLICY` away from `fail_closed`.
- Patch production scanner defaults for a backtest-only need.
- Bypass central risk sizing / order execution.
- Touch real production/testnet service state.
- Change credentials handling or commit secrets.
- Break `positions.json` / persistence backward compatibility.
- Reintroduce `bot_config.json` or an equivalent runtime-default JSON file.
- Recreate legacy V54 / 2B / EMA/VB lane adapters without explicit approval.
- Loosen thresholds just to get trades.

Preference: conservative. No trades is a diagnostic result, not a reason to blindly relax gates.

## Legacy Cleanup Notes

The following are legacy and should not guide new work:

- `2B -> v54_noscale`
- legacy signal-map config keys
- legacy EMA/VB runtime flags
- legacy V7 tier gate keys
- old `--strategy v54` backtest presets
- EMA/VB entry-lane matrix plan

If historical V54 reports/tools remain in `extensions/` or dashboard code, treat them as historical display or archive context unless Ruei reopens that track.

## Review / Commit / Push Habits

- Before coding: `git status`, `git log --oneline`, and read touched files.
- Do not revert or clean user/local changes unless asked.
- Do not use `git add -A`; stage concrete files only.
- Commit messages should explain why and follow conventional style.
- Do not amend, skip hooks, change git config, or push unless Ruei asks.
- Before handoff, run relevant focused tests plus:

```bash
python -c "from trader.config import Config; Config.validate()"
python -m pytest trader/tests extensions/Backtesting/tests -q
```

## Current Next Work

1. Convert selected research ideas into StrategyPlugin candidates.
2. Add focused unit tests for each plugin.
3. Run candidate backtests via StrategyRuntime.
4. Use `reports/strategy_plugin_candidate_review.md` for promotion-gated review output.
