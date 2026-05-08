# Trader Cleanup Phase 1B - Plugin Classification

Date: 2026-05-08

## Scope

Phase 1B classified every `STRATEGY_CATALOG` entry without deleting plugin
files. The classification lives beside the catalog in
`trader/strategies/plugins/_catalog.py` so future agents can distinguish
runtime, fixture, active research, superseded research, and retirement-review
plugins before touching files.

## Classification Rules

- `runtime`: current `Config.ENABLED_STRATEGIES` promotion set.
- `fixture`: plugin contract/tooling fixture or checklist fixture retained for
  validation, not runtime promotion.
- `active_research`: parked research branch with a still-plausible thesis.
- `superseded_research`: historical lineage displaced by a newer/runtime branch.
- `retire_candidate`: no current runtime or research path; deletion still needs
  a separate reference/test review.

## Counts

- `runtime`: 3
- `fixture`: 3
- `active_research`: 3
- `superseded_research`: 24
- `retire_candidate`: 5

## Runtime

- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- `donchian_range_fade_4h_range_width_cv_013`
- `donchian_range_fade_4h_range_width_cv_013_short`

## Fixture

- `fixture_long`
- `fixture_exit`
- `ema_cross_7_19_long_only`

`ema_cross_7_19_long_only` is classified as fixture because the research note
keeps it as a checklist-gate test case, not as a promotion candidate.

## Active Research

- `bb_fade_squeeze_1h`
- `rsi2_pullback_1h_sma5_gap_guard`
- `rsi_mean_reversion_1h`

These remain catalog-visible, default-off, and promotion-gated.

## Superseded Research

- `macd_zero_line_btc_1d`
- `macd_zero_line_btc_1d_trending_up`
- `macd_signal_btc_4h_trending_up`
- `macd_signal_btc_4h_trending_up_confirmed`
- `macd_signal_btc_4h_trending_up_confirmed_failfast`
- `macd_signal_btc_4h_trending_up_underwater_ema_exit`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_late_entry_filter`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_context_gated_late_entry_filter`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_trend_decay_only_late_entry_filter`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_only_late_entry_filter`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_tightened_late_entry_filter`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_late_entry_filter`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_squeeze_release_unconfirmed_late_entry_filter`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_filter`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_local_spread_filter`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_chop_trend_filter`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_remainder_ratchet`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_buffer`
- `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_decay_filter`
- `rsi2_pullback_1h`
- `donchian_range_fade_4h`
- `rsi_mean_reversion_15m`

## Retire Candidates

- `macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter`
- `macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_snapback_guard`
- `macd_signal_btc_4h_trending_down_staged_derisk_giveback_partial67_snapback_followthrough_guard`
- `donchian_range_fade_4h_range_width_cv_013_mid_drift_guard`
- `donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard`

Retirement is not deletion approval. Before deleting any retire candidate, run a
reference review across `trader`, `extensions`, `plans`, and `reports`, then
update or remove focused tests intentionally.

## Code Changes

- Added explicit catalog classification constants and a complete
  `STRATEGY_CATALOG_CLASSIFICATION` map.
- Added import-time validation so catalog entries cannot be added without a
  classification.
- Added optional classification notes for non-obvious fixture and retirement
  decisions.
- Exposed classification in `tools.strategy_plugin_check` output.
- Added focused tests that runtime-enabled plugins are classified as `runtime`.
- Completed the `fixture_exit` fixture plugin contract so all catalog entries
  can be loaded by the plugin check tool.

## Review Notes

- No plugin files were deleted.
- No runtime defaults were changed.
- Classification is stored outside catalog entries to avoid changing the
  `StrategyRegistry.from_config()` entry contract.
- `fixture_exit` now returns no entry candidates and remains exit-only.
- `tools.strategy_plugin_check --all-catalog` loads every plugin. It still
  reports expected documentation/test warnings for some fixture and retire
  candidate entries.
- `retire_candidate` entries still need a later deletion-specific review.
