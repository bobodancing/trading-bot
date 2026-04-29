# CLAUDE.md - strategy-runtime-reset 撌乩?摰?

Last updated: 2026-04-29. If this file conflicts with code, trust code first.

## 頨思遢????
- ?撠郭嚗uei 摰園?曌?????- 隤?嚗?擃葉??+ English technical terms??- 憸冽嚗?乓陛瞏oken-aware?府??撠勗?撠?- ?? code / git log / local context嚗???憿?- Code ?芸?嚗???????- Comments 撖?why嚗?撖?what??- ??嚗sia/Taipei??
## 撠?摰?

- Owner: Ruei??- Repo root: `C:\Users\user\Documents\tradingbot\strategy-runtime-reset`??- Branch: `codex/strategy-runtime-reset`??- 銝餌?嚗trategy-plugin runtime reset??- ??V53/V6/V7/V54 lane runtime 撌脣?歹?銝?雿 live ??research 銝餌???- 2B / EMA_PULLBACK / VOLUME_BREAKOUT / V54 lane review ??legacy context嚗??Ruei ??嚗?閬儔瘣颯?
## Runtime Baseline

Runtime baseline is:

```text
StrategyRuntime + StrategyPlugin contract + Config class defaults
```

Runtime config ?銝靘???`trader/config.py` ??`Config` class defaults???冽??芾? credentials嚗?
```text
secrets.json -> Config.load_secrets()
```

?桀? reset runtime ?敹?intent嚗?
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

靽∩遙 runtime ?? repo root 頝?

```bash
python -c "from trader.config import Config; Config.validate()"
```

## Frozen Contract

Frozen target is no longer `v54_noscale`.

Frozen target = plugin runtime kernel contract:

- `StrategyPlugin` / `SignalIntent` boundary??- `StrategyRuntime` routing and arbiter path??- central `RiskPlan` sizing and risk caps??- `PositionManager` / persistence schema compatibility??- `Config.validate()` fail-fast checks??- secrets-only credential loading??
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

Locked spec lane adopted into the current pipeline:

- `plans/ranging_strategy_brainstorm_design.md` is brainstorming / handoff context only. Do not implement directly from that file when a locked cartridge spec exists.
- `plans/cartridge_spec_donchian_range_fade_4h.md` - first implementation priority; structural range thesis, no ADX dependency.
- `plans/cartridge_spec_bb_fade_squeeze_1h.md` - second implementation priority; HTF ADX + BBW squeeze ranging thesis.
- `plans/cartridge_spec_rsi2_pullback_1h.md` - third implementation priority; ANY-regime pullback thesis, kept separate from declared-RANGING validation.
- Catalog entries follow implementation. Do not add remaining locked-spec ids to `trader/strategies/plugins/_catalog.py` until the concrete plugin files and focused tests land.

- `fixture_long` / `fixture_exit` - deterministic test fixtures.
- `macd_zero_line_btc_1d` - pilot research plugin, not production-approved by default.
- `macd_zero_line_btc_1d_trending_up` - regime-aware MACD follow-up cartridge, 1d BTC long-only, TRENDING_UP regime-declared.
- `macd_signal_btc_4h_trending_up` - higher-frequency MACD continuation cartridge, BTC 4h entries under a 1d trend gate, TRENDING_UP regime-declared.
- `macd_signal_btc_4h_trending_up_confirmed` - confirmed-entry variant of the 4h MACD continuation cartridge, adds histogram-expansion and price-over-EMA checks under the same 1d trend gate.
- `macd_signal_btc_4h_trending_up_confirmed_failfast` - fail-fast exit variant of the confirmed 4h MACD continuation cartridge, closes stalled continuation attempts after two 4h bars without follow-through.
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter` - promoted Slot A runtime candidate, BTC 4h continuation under a 1d trend gate with tightened transition-aware late-entry defense.
- `ema_cross_7_19_long_only` - first post-infra research cartridge, 4h BTC/ETH long-only.
- `donchian_range_fade_4h` - first ranging-lane implementation candidate, 4h BTC/ETH long-only, structural Donchian range geometry, RANGING regime-declared.
- `donchian_range_fade_4h_range_width_cv_013` - threshold-relaxed Donchian child candidate, keeps the same range-geometry thesis and only widens `range_width_cv_max` to 0.13 after the narrow second-pass sweep woke the default RANGING window.
- `donchian_range_fade_4h_range_width_cv_013_mid_drift_guard` - structural-validation child on top of the `0.13` Donchian candidate; keeps the relaxed width gate but rejects channels whose Donchian midpoint drifts too far during the detection window.
- `donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard` - softer structural-validation child on top of the `0.13` Donchian candidate; keeps the relaxed width gate but rejects only the most one-sided boundary-touch structures.
- `rsi_mean_reversion_15m` - gamma research cartridge, promotion-ineligible under checklist 禮5 (backtest engine lacks 15m support); kept as reference for future infra extension.
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

1. Portfolio A+B has been promoted into runtime defaults by Ruei approval:
   commit `5dee878` enabled the catalog entries and commit `1933e65` set
   `STRATEGY_RUNTIME_ENABLED=True` with the frozen pair in `ENABLED_STRATEGIES`.
2. Promoted candidate pair:
   Slot A `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`;
   Slot B `donchian_range_fade_4h_range_width_cv_013`.
3. Next immediate work is post-promotion control: update promotion artifacts,
   verify runtime-default parity, run a small promoted-default smoke backtest,
   and define deployment boundary. Do not start new alpha research during this
   control pass.
4. After post-promotion control, close Phase 4 RSI2 attribution and Phase 5 BB
   rescue/park decision from `plans/2026-04-25_portfolio_research_reorder_plan.md`.
5. `plans/2026-04-25_strategy_research_backlog_design.md` is now scheduled as
   the recovery pool after Phase 4/5 closeout plus trigger review. Do not
   implement backlog plugins until a trigger review memo and explicit Ruei
   approval select exactly one mechanism pair.
