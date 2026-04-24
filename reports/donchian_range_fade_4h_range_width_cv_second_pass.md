# donchian_range_fade_4h Second Pass: range_width_cv_max

Date: 2026-04-24  
Status: `RESEARCH_SWEEP_ONLY`

## Scope

- Candidate: `donchian_range_fade_4h`
- Sweep target: `range_width_cv_max`
- Grid: `0.08`, `0.10`, `0.13`
- Primary sweep report:
  `reports/strategy_plugin_parameter_sweep_donchian_range_fade_4h_range_width_cv_max_min3.md`

## Result Snapshot

| cell | range_width_cv_max | trades | net_pnl | max_dd_pct | RANGING trades | RANGING net_pnl |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| cell_001 | 0.08 | 6 | 83.8995 | 2.2463 | 0 | 0.0000 |
| cell_002 | 0.10 | 9 | 78.4857 | 2.2463 | 0 | 0.0000 |
| cell_003 | 0.13 | 15 | 567.1316 | 2.1990 | 2 | 132.7142 |

## Read

- `0.08` and `0.10` behave the same where it matters most: both leave the default `RANGING` window completely dark.
- `0.13` is the first cell that actually wakes up the declared thesis surface.
- The improvement is not fake aggregate uplift only:
  - `RANGING` moves from `0 trades / 0.0000` to `2 trades / +132.7142`
  - `TRENDING_UP` also improves from `2 / -83.0180` to `6 / +272.9137`
  - `MIXED` stays unchanged at `7 / +161.5037`
- Risk does not deteriorate in the narrow sweep:
  - `max_dd_pct` improves slightly from `2.2463` to `2.1990`
  - run errors stay `0`
  - entry-stop violations stay `0`

## Interpretation

- The first-pass failure was mainly `range_detected` starvation.
- A narrow relaxation from `0.10` to `0.13` is enough to change regime-window behavior materially.
- This is a meaningful result because attribution stayed clean: no touch logic, RSI gate, cooldown, or exit logic changed.

## Next Step

- Do not mutate the locked baseline spec in place without explicit re-lock.
- The correct next move is to land a child candidate around `range_width_cv_max = 0.13` and review it as a new baseline contender for the Donchian lane.
- If you want to stay maximally conservative, the child can be named as a threshold-specific variant rather than silently replacing `0.10`.
