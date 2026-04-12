# SQUEEZE Chart Review Top 3

Generated: 2026-04-12

Scope: D1 blocking review for R1 arbiter spec. This is a data-backed chart review note using BTCUSDT 4H cache and `reports/squeeze_coverage_candidates.csv`. No runtime code was changed.

## Decision

**Recommendation: keep `SQUEEZE` as a first-class R1 state, but give it `NEUTRAL` behavior for now.**

That means:

- `SQUEEZE` exists in the state machine.
- `SQUEEZE` freezes new entries for trend and range strategies.
- Existing positions remain self-managed by their entry strategy.
- No strategy is assigned as `PRIMARY` for `SQUEEZE` in R1.

Reason: 2 of the 3 top candidates look like real compression candidates, but the sample is not strong enough to justify strategy-specific SQUEEZE behavior yet.

## Top 3 Review

| candidate | verdict | evidence | R1 implication |
|---|---|---|---|
| `2023-10-14 12:00 -> 2023-10-15 20:00` | real compression / breakout-prep | Core range 1.87%, after-3d close +4.29%, after-7d close +10.45%, pooled BBW percentile ~0.11% to 0.28%, ATR ratio ~0.73 to 0.80. | SQUEEZE should not be a dead state. This kind of compression can matter before trend expansion. |
| `2025-06-28 08:00 -> 2025-06-29 04:00` | real narrow compression | Core range 0.46%, close change +0.03%, after-3d range 3.40%, ADX < 20, ATR ratio ~0.69 to 0.78, raw/current `RANGING`. | SQUEEZE is distinct enough from ordinary RANGING to justify a freeze-new-entries state. |
| `2025-02-16 16:00 -> 2025-02-17 04:00` | weak / likely ordinary range | Core range 1.53%, close change -1.02%, only 1 candidate row, BBW ratio to history mean 0.617, after-7d close -0.20%. | Do not add SQUEEZE-specific trading logic from this sample. |

## Why Not Placeholder

If `SQUEEZE` is made a placeholder/dead state, R1 loses the ability to pause entries during compression zones like 2025-06-28/29. That would push the same problem back into strategy-level guards, which is exactly what the arbiter is supposed to avoid.

## Why Not Active Strategy State Yet

The 2023 case is breakout-prep and the 2025-06 case is narrow compression, but the 2025-02 case is weak. This is enough for a state-machine guard, not enough for a dedicated SQUEEZE strategy or special handoff rules.

## R1 Spec Patch Target

Use this wording in R1:

`SQUEEZE` is first-class in the arbiter state machine. In R1, it behaves like `NEUTRAL`: freeze new entries for all strategies and let existing positions remain `exit_self_managed`. R1 does not assign any strategy to `SQUEEZE`, and R1 does not tune RegimeEngine thresholds to increase SQUEEZE coverage.
