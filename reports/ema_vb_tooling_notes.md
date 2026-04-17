# EMA/VB Tooling Notes

- Fixed Backtesting bot-root resolution for the isolated `feat-regime-router` folder.
- Added backtest-only `allowed_signal_types` support via `BacktestConfig.allowed_signal_types` and CLI `--allowed-signal-types`.
- Added backtest-only `dry_count_only` support so dry runs can count final candidates without opening positions.
- Added optional precomputed-indicator replay for the review harness to avoid recalculating the same indicator windows on every 1H scan.
- Added `lane_race_audit.csv` with priority and allowlist suppression fields.
- The tooling sets a backtest-only `SIGNAL_STRATEGY_MAP` from `--strategy v54`; runtime `bot_config.json` is not edited.
- Dry count `market_filter_pass_count` is post-market by construction because signal detectors run after market filter in the runtime scanner.
- Review harness: `C:\Users\user\Documents\tradingbot\feat-regime-router\extensions\Backtesting\ema_vb_entry_lane_review.py`.
- Results root: `C:\Users\user\Documents\tradingbot\feat-regime-router\extensions\Backtesting\results\ema_vb_entry_lane_review_20260415`.
