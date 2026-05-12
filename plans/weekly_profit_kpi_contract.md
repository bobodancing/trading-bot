# Weekly Profit KPI Contract

Date: 2026-05-12
Branch: `codex/post-promotion-control-20260430`
Status: `PHASE_2_KPI_CONTRACT_REVIEWED`

## Purpose

This contract defines how the project will judge progress toward:

> sustainable profitability with meaningful weekly participation,
> without weakening runtime safety or pretending that backtests guarantee
> future weekly returns.

It converts the Phase 1 weekly feasibility review into a shared operating
standard for:

- weekly monitoring
- research trigger reviews
- pause / continue decisions
- later promotion decisions

Primary input:

- `reports/promoted_three_leg_weekly_feasibility_review.md`

## Scope And Contract Stance

This is **not** a promise that every future week will be profitable.

It is a decision contract that says:

1. what the system must show before we call the weekly objective credible
2. what counts as a mild warning
3. what counts as a real research gap
4. what must pause immediately for operational safety

The contract separates:

- **participation**: when the system finds entry opportunities
- **economic outcome**: realized after-fee weekly result
- **operational integrity**: whether runtime behavior is trustworthy enough to
  interpret economic results

## Measurement Rules

### Weekly Basis

- Weekly buckets use UTC ISO weeks anchored on Monday.
- Participation uses **entry week**.
- Economic outcome uses **exit week realized PnL**.
- Reports must flag partial first / last calendar buckets when a review window
  does not start or end on a week boundary.

### Rolling Windows

Use both:

- rolling `4w`: fast warning signal
- rolling `8w`: contract-grade decision basis

The `8w` read decides whether a gap is persistent enough to reopen research.
The `4w` read is allowed to trigger investigation, but not by itself to promote
or reopen work.

A rolling `8w` packet is contract-grade only when all 8 buckets are present and
none of those buckets is a partial review-window boundary week. Partial boundary
weeks are observe-only for reopen / investigate economics, except that
independent pause triggers still win.

### PnL Convention

Where artifact support exists, the contract uses:

- realized weekly PnL
- fee estimate on entry and exit notional
- after-fee weekly net PnL

Phase 1 used:

- fee rate estimate `0.0004` per side

Phase 3 weekly control packets should report:

- `gross_pnl_usdt`
- `fees_est_usdt`
- `net_after_fee_est_usdt`
- the same values normalized as `% of review capital`

## Decision Precedence

Always resolve state in this order:

1. `pause`
2. `reopen_research`
3. `investigate`
4. `continue`

Reason:

- a safety breach must not be hidden by good PnL
- a persistent economic gap should not be downgraded to generic monitoring
- a single weak 4-week patch should not automatically trigger new alpha work

## KPI Registry

| KPI | Meaning | Primary cadence | Required source |
| --- | --- | --- | --- |
| `active_entry_week_ratio_8w` | Weeks with at least one entry divided by completed weeks | rolling 8w | weekly control packet |
| `rolling_8w_entry_trade_count` | Total entries opened in the 8-week window | rolling 8w | weekly control packet |
| `zero_entry_week_streak` | Consecutive weeks with zero entries | weekly | weekly control packet |
| `positive_week_ratio_all_8w_after_fee` | Positive after-fee exit weeks over all completed weeks | rolling 8w | weekly control packet |
| `positive_week_ratio_exit_active_8w_after_fee` | Positive after-fee exit weeks over exit-active weeks | rolling 8w | weekly control packet |
| `rolling_4w_net_after_fee_pnl` | Four-week realized after-fee PnL | rolling 4w | weekly control packet |
| `rolling_8w_net_after_fee_pnl` | Eight-week realized after-fee PnL | rolling 8w | weekly control packet |
| `rolling_8w_realized_exit_count` | Realized exits closed in the 8-week window | rolling 8w | weekly control packet |
| `exit_active_week_count_8w` | Weeks with at least one realized exit | rolling 8w | weekly control packet |
| `worst_week_after_fee_pnl_pct_equity_8w` | Worst single completed week normalized by review capital | rolling 8w | weekly control packet |
| `max_consecutive_losing_weeks_after_fee_8w` | Consecutive negative after-fee exit weeks | rolling 8w | weekly control packet |
| `portfolio_max_drawdown_pct_review_window` | Max portfolio drawdown in the reviewed window | weekly / review window | backtest or weekly packet |
| `execution_attempt_count_weekly` | Execution attempts submitted in the completed week | weekly | runtime observability |
| `execution_failure_count_weekly` | Failed executions in the completed week | weekly | runtime observability |
| `execution_failure_rate_weekly` | Failed executions divided by execution attempts | weekly | runtime observability |
| `config_drift_events_weekly` | Count of config / runtime drift events | weekly | runtime observability |
| `unprotected_position_events_weekly` | Count of positions left without valid protective state | weekly | runtime observability |

## Participation Contract

| KPI | Continue | Investigate | Reopen Research |
| --- | ---: | ---: | ---: |
| `active_entry_week_ratio_8w` | `>= 0.6250` | `0.5000..0.6249` | `< 0.5000` |
| `rolling_8w_entry_trade_count` | `>= 8` | `6..7` | `<= 5` |
| `zero_entry_week_streak` | `<= 1` | `2` | `>= 3` |

Interpretation:

- `0.6250` means at least `5 / 8` weeks show entry participation.
- `8` entries over `8` weeks is the first floor that resembles a weekly machine,
  even if entries are unevenly clustered.
- A `>= 3` zero-entry-week streak is not acceptable for a system whose product
  direction is weekly participation, provided runtime integrity is clean.

## Economic Outcome Contract

| KPI | Continue | Investigate | Reopen Research |
| --- | ---: | ---: | ---: |
| `positive_week_ratio_all_8w_after_fee` | `>= 0.5000` | `0.3750..0.4999` | `< 0.3750`, only after participation is no longer the dominant gap |
| `positive_week_ratio_exit_active_8w_after_fee` | `>= 0.6000` | `0.5000..0.5999` | `< 0.5000`, when participation is adequate |
| `rolling_4w_net_after_fee_pnl` | `> 0` | `<= 0` for one snapshot | not used alone |
| `rolling_8w_net_after_fee_pnl` | `> 0` | `<= 0` once | `<= 0` with `meets_economic_sample_floor = true` |
| `max_consecutive_losing_weeks_after_fee_8w` | `<= 1` | `2` | `>= 3`, when execution integrity is clean |

Interpretation:

- All-week positive rate is intentionally strict because inactive weeks count
  against the product objective.
- Exit-active positive rate prevents inactivity from being mistaken for poor
  trade quality.
- If participation is weak, a poor all-week positive rate should be diagnosed
  as a **participation gap first**, not automatically as an edge-quality failure.

### Economic Sample Floor

`meets_economic_sample_floor = true` only when all of these are true:

1. operational pause conditions are absent
2. participation is no longer the dominant gap:
   - `active_entry_week_ratio_8w >= 0.5000`
   - `rolling_8w_entry_trade_count >= 6`
3. realized outcome sample is large enough to interpret:
   - `rolling_8w_realized_exit_count >= 8`, or
   - `exit_active_week_count_8w >= 4`

This is an initial operating assumption, not a claim that `8` exits is
statistically sufficient for final strategy promotion. It only decides whether a
negative `8w` economic read is strong enough to reopen research instead of being
treated as a participation-first problem.

## Risk Envelope

| KPI | Continue | Investigate | Pause |
| --- | ---: | ---: | ---: |
| `worst_week_after_fee_pnl_pct_equity_8w` | `> -5.0000%` | `>= -7.0000%` and `<= -5.0000%` | `< -7.0000%` |
| `portfolio_max_drawdown_pct_review_window` | `<= 6.0000%` | `> 6.0000%` and `<= 8.0000%` | `> 8.0000%` |

Interpretation:

- The `8%` portfolio drawdown pause line preserves the existing promotion-era
  risk envelope already used in portfolio review.
- The single-week pause line is intentionally wider than the promotion-era
  baseline because the current mandate accepts high volatility in exchange for
  weekly profit discovery.
- `worst_week_after_fee_pnl_pct_equity_8w < -7.0000%` is an independent pause
  trigger. It does not require another risk breach.

## Operational Integrity Contract

| KPI | Continue | Investigate | Pause |
| --- | ---: | ---: | ---: |
| `execution_integrity_weekly` | `execution_failure_count_weekly = 0` | one isolated failure, or denominator-qualified rate warning | repeated sparse failures, or denominator-qualified rate breach |
| `config_drift_events_weekly` | `0` | not applicable | `>= 1` |
| `unprotected_position_events_weekly` | `0` | not applicable | `>= 1` |

Interpretation:

- Economic conclusions are invalid when runtime integrity is broken.
- `pause` wins over any positive PnL signal.
- Phase 3 must make these metrics routine, not ad hoc.

Execution integrity is a composite rule:

- If `execution_attempt_count_weekly = 0`, report
  `execution_failure_rate_weekly = null`; do not pause on execution rate.
  Participation KPIs handle inactivity.
- `continue`: `execution_failure_count_weekly = 0`.
- `investigate`: any non-zero `execution_failure_count_weekly` that does not
  meet a pause condition.
- `investigate`: `execution_attempt_count_weekly >= 20`,
  `execution_failure_count_weekly >= 1`, and
  `execution_failure_rate_weekly > 1.0000%` and `<= 3.0000%`.
- `pause`: `execution_failure_count_weekly >= 2` when
  `execution_attempt_count_weekly < 20`.
- `pause`: `execution_attempt_count_weekly >= 20`,
  `execution_failure_count_weekly >= 2`, and
  `execution_failure_rate_weekly > 3.0000%`.

## Decision Table

| State | Trigger | Required Action |
| --- | --- | --- |
| `continue` | No pause trigger, no reopen trigger, no material investigate trigger | Keep weekly control packet running and preserve current runtime scope |
| `investigate` | One or more watch thresholds breached, but no pause / reopen condition | Produce a short variance note and watch the next packet |
| `pause` | Any operational pause trigger, or drawdown exceeds contract pause line | Stop interpreting economics as trustworthy, resolve runtime / risk integrity first |
| `reopen_research` | Persistent participation or economic-quality gap while operations remain clean | Open a formal trigger review and activate exactly one bounded research lane |

## Explicit Reopen Research Triggers

Use these only when operations are clean. Clean operations mean no operational
pause trigger and no execution-integrity investigate condition in the same
decision window.

### Participation Gap

Open a trigger review when any of these are true:

1. `active_entry_week_ratio_8w < 0.5000`
2. `rolling_8w_entry_trade_count <= 5`
3. `zero_entry_week_streak >= 3`

Default research direction:

- frequency-complement lane before broad expectancy repair

### Economic-Quality Gap

Open a trigger review when participation is no longer the dominant gap and any
of these are true:

1. `positive_week_ratio_exit_active_8w_after_fee < 0.5000`
2. `rolling_8w_net_after_fee_pnl <= 0` with
   `meets_economic_sample_floor = true`
3. `max_consecutive_losing_weeks_after_fee_8w >= 3`

Default research direction:

- entry-quality repair
- regime-specific repair
- only then a new candidate if the attribution demands it

## Phase 1 Baseline Mapped Into This Contract

Phase 1 primary contiguous read:

| metric | observed |
| --- | ---: |
| review window | `2026-01-01..2026-04-30` |
| calendar buckets | `18` |
| entry trades | `13` |
| active entry week ratio | `0.3889` |
| zero-entry weeks | `11` |
| positive week ratio, all weeks, after fee | `0.3333` |
| positive week ratio, exit-active weeks, after fee | `0.6667` |
| net after fee estimate | `211.4808` |
| worst after-fee week | `-123.3480 USDT` |
| worst after-fee week on `10,000 USDT` research balance | `-1.2335%` |

Contract read:

- this mapping calibrates Phase 2 threshold selection; it is not yet the formal
  rolling `8w` packet evaluation that Phase 3 must produce
- participation is below the desired `8w` contract posture
- all-week positive rate is weak, but the active-exit positive rate remains
  acceptable enough that inactivity is the first problem to solve
- after-fee net PnL remains positive in the contiguous anchor window
- the first Phase 4 trigger review, once Phase 3 packet plumbing exists, should
  be prepared around **frequency complement / participation repair**

## Current Operating Verdict

Current project verdict after Phase 2:

> `CONTINUE_RUNTIME_MONITORING`
> + `PREPARE_PARTICIPATION_GAP_TRIGGER_REVIEW`

This means:

- do not alter promoted runtime defaults now
- do not loosen thresholds to force activity
- do implement Phase 3 weekly control packets against this contract
- do not claim a formal `reopen_research` state until Phase 3 emits contract-grade
  rolling `8w` packet evidence
- if Phase 3 rolling data confirms the same participation gap, Phase 4 should
  open one bounded frequency-complement research lane

## Phase 3 Handoff Requirements

Phase 3 weekly control packets must emit enough information to calculate:

- every KPI in this contract
- the decision precedence result
- the one-line state:
  - `continue`
  - `investigate`
  - `pause`
  - `reopen_research`

Minimum packet output:

- machine-readable weekly summary
- human-readable review note
- explicit economic sample-floor fields:
  - `rolling_8w_realized_exit_count`
  - `exit_active_week_count_8w`
  - `meets_economic_sample_floor`
- explicit execution integrity fields:
  - `execution_attempt_count_weekly`
  - `execution_failure_count_weekly`
  - `execution_failure_rate_weekly`
- explicit state transition reason
- whether any reopen trigger is now formally satisfied

## Non-Goals

This contract does **not** authorize:

- new runtime defaults
- new enabled strategies
- scanner runtime activation
- threshold loosening for volume optics
- reopening legacy RSI2 / BB / Slot A SHORT work by default

Those require later trigger-review evidence and Ruei approval where existing
project rules demand it.
