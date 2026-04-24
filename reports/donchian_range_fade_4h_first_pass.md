# donchian_range_fade_4h First Pass

Date: 2026-04-24  
Status: `KEEP_RESEARCH_ONLY`

## Scope

- Candidate: `donchian_range_fade_4h`
- Locked spec: `plans/cartridge_spec_donchian_range_fade_4h.md`
- Runner:
  `python -m extensions.Backtesting.scripts.run_candidate_review --candidate donchian_range_fade_4h`

## Candidate Review Read

| window | trades | net_pnl | max_dd_pct |
| --- | ---: | ---: | ---: |
| TRENDING_UP | 2 | -83.0180 | 2.2463 |
| RANGING | 0 | 0.0000 | 0.0000 |
| MIXED | 7 | 161.5037 | 0.6442 |
| aggregate | 9 | 78.4857 | 2.2463 |

Primary source: `reports/strategy_plugin_candidate_review.md`.

## What landed cleanly

- No backtest run errors.
- No entry-stop violations.
- Plugin contract, focused tests, catalog registration, and StrategyRuntime candidate review path all worked without infra changes.
- The structural range thesis is not obviously dead: MIXED printed `7` trades with positive PnL and low drawdown.

## What failed

- The declared target regime is `RANGING`, but the first-pass review produced `0` trades in the default `RANGING` window.
- That is the main failure, not risk.
- The candidate also lost money in `TRENDING_UP` (`-83.0180`), so the current gate is not simply "too conservative but clean" — it is under-trading the target surface while still leaking some off-thesis exposure elsewhere.

## Interpretation

- The strongest read is `range_detected` starvation, not runtime contamination.
- The gate stack is likely too strict in its current locked baseline:
  - `range_width_cv_max = 0.10`
  - both-side touch requirement
  - lower-boundary entry requirement
  - RSI confirmation
- This matches the brainstorm doc's own known-risk note: if real trade frequency lands below the expected floor, first revisit `range_width_cv_max`.

## Recommended next step

Second pass should start with a narrow structural sweep, not a thesis rewrite:

1. Sweep `range_width_cv_max` first, e.g. `0.10 -> 0.15 -> 0.20`.
2. Keep touch logic unchanged on the first sweep so attribution stays clean.
3. Re-check whether default `RANGING` starts printing real trades before touching `touch_atr_band` or touch-count requirements.

## Verdict

`donchian_range_fade_4h` is now a valid ranging-lane research cartridge in the pipeline, but baseline v0.1.0 is not promotion-shaped. The correct next move is a focused structural second pass, not runtime consideration.
