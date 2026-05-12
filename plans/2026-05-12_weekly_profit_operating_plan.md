# Weekly Profit Operating Plan

Date: 2026-05-12
Branch: `codex/post-promotion-control-20260430`
Status: `PLANNING_BASELINE_FOR_SUSTAINABLE_WEEKLY_PROFIT`

## Mission

Build the project toward:

> a sustainable automated trading system that keeps meaningful weekly trading
> participation and improves the probability of positive weekly outcomes,
> without weakening risk discipline or manufacturing fragile backtest alpha.

This plan treats "every week should make money" as a **business direction**,
not as a dishonest hard guarantee. The operational objective is to improve:

- weekly participation
- weekly positive-rate
- rolling profitability
- drawdown containment
- evidence quality

while preserving the central StrategyRuntime risk contract.

## Non-Negotiables

- no private-key custody or ad hoc live-state manipulation
- no runtime-default changes without review evidence
- no scanner activation simply to create more trades
- no threshold loosening merely to raise participation
- no strategy promotion based on one favorable window
- no confusing dry-run operational health with proven live expectancy

## Current Runtime Baseline

Current promoted portfolio:

| slot | strategy id | role |
| --- | --- | --- |
| Slot A LONG | `macd_signal_btc_4h_trending_up_staged_derisk_giveback_partial67_transition_aware_tightened_late_entry_filter` | BTC 4h trend continuation |
| Slot B LONG | `donchian_range_fade_4h_range_width_cv_013` | BTC/ETH 4h lower-bound range fade |
| Slot B SHORT | `donchian_range_fade_4h_range_width_cv_013_short` | BTC/ETH 4h upper-bound range fade |

Current runtime posture:

- central `RiskPlan`
- fail-closed router policy
- scanner-universe observe-only
- BTC trend filter default mode = `diagnostic`
- no automatic activation of recovery backlog

## Product KPI Ladder

The weekly-profit objective should be governed by four KPI layers.

### 1. Sustainable Profitability

Primary questions:

- Is after-fee expectancy positive?
- Are rolling 4-week and 8-week PnL still positive?
- Is the portfolio reward worth the drawdown consumed?

Core metrics:

- `after_fee_expectancy`
- `rolling_4w_net_pnl`
- `rolling_8w_net_pnl`
- `portfolio_max_drawdown_pct`
- `realized_r_distribution`

### 2. Weekly Participation

Primary questions:

- Does the portfolio trade often enough to avoid long idle spans?
- Are trades concentrated in a few windows, or spread through many weeks?

Core metrics:

- `active_week_ratio`
- `weekly_trade_count_distribution`
- `median_weekly_trade_count`
- `zero_trade_week_count`
- `longest_idle_week_streak`

### 3. Weekly Outcome Stability

Primary questions:

- How often is a week profitable?
- How deep are losing weeks when they occur?
- Are losing weeks clustered?

Core metrics:

- `weekly_positive_rate`
- `weekly_net_pnl_distribution`
- `worst_week_pnl`
- `max_consecutive_losing_weeks`
- `weekly_pnl_by_slot`

### 4. Operational Integrity

Primary questions:

- Does runtime behavior still match the promoted contract?
- Are failures coming from the market, or from the machine?

Core metrics:

- `execution_failure_rate`
- `entry_to_fill_rate`
- `decision_reject_rate`
- `reject_mix_by_reason`
- `scanner_fallback_events`
- `config_drift_events`
- `unprotected_position_events`

Thresholds should **not** be frozen before Phase 1 establishes the current
three-leg portfolio baseline.

## Validation Discipline

The roadmap must distinguish three evidence levels:

1. **Operational evidence**
   - dry-run / testnet / runtime observability
   - proves plumbing, failure modes, and process health

2. **Historical portfolio evidence**
   - backtest and matrix studies
   - proves candidate behavior under known windows

3. **Promotion evidence**
   - hypothesis-registered, bounded-search, combined-portfolio,
     out-of-sample-aware review packet
   - proves the candidate is strong enough to alter defaults

The project should avoid treating a good total PnL number as sufficient evidence.
The phase gates below are designed to reduce data-snooping pressure and keep new
research candidates bounded.

## Phase 0 - Truth Alignment And Readiness Sync

### Objective

Make the repo say one thing about the current runtime before weekly-profit work
begins.

### Work

- refresh `AGENTS.md`
- reconcile stale A+B-only reports and scanner docs
- update promoted-strategy scanner tests to include Slot B SHORT
- update `plans/2026-05-08_trader_cleanup_plan.md` Phase 3 status
- repair stale/mojibake orientation wording in package-level entry docs
- decide the disposition of aborted untracked draft files from the earlier
  stopped implementation attempt

### Deliverables

- updated governance / scanner / cleanup docs
- corrected scanner test fixtures
- short closeout note for readiness sync

### Exit Gate

- repo no longer presents an A+B-only baseline as "current"
- all source-of-truth docs identify the three-leg runtime correctly
- targeted tests around scanner runtime scope remain green

## Phase 1 - Promoted Portfolio Weekly Feasibility Review

### Objective

Measure whether the existing three-leg portfolio already has a plausible path
toward:

- enough weekly participation
- acceptable positive-week frequency
- bounded weekly downside

### Work

Slice existing promotion / backtest artifacts by calendar week and report:

- active-week ratio
- zero-trade weeks
- weekly trade-count histogram
- weekly positive-rate
- weekly PnL distribution
- worst weekly loss
- longest losing-week streak
- per-slot weekly contribution
- BTC vs ETH weekly contribution
- after-fee weekly read where artifacts support it

### Deliverables

- `reports/promoted_three_leg_weekly_feasibility_review.md`
- machine-readable weekly summary artifact
- KPI calibration memo:
  - which weekly metrics are already viable
  - which are weak
  - whether the weakness is participation, edge quality, or regime coverage

### Exit Gate

The review must answer one of:

1. **Baseline already close enough**  
   Continue into control-system hardening before new alpha work.

2. **Participation gap dominates**  
   Need a carefully bounded frequency-complement lane.

3. **Profit-quality gap dominates**  
   Need regime-specific or entry-quality repair.

4. **Operational ambiguity dominates**  
   Need more runtime evidence before alpha work.

## Phase 2 - Weekly Profit KPI Contract

### Objective

Translate the new business direction into formal acceptance and reopen criteria.

### Work

Define:

- hard gates
- watch metrics
- reopen triggers
- pause triggers
- what qualifies as "enough" weekly trading activity
- what level of negative-week tolerance is acceptable

The KPI contract should include at least:

- `active_week_ratio`
- `weekly_trade_count_floor`
- `weekly_positive_rate`
- `rolling_4w_net_pnl`
- `rolling_8w_net_pnl`
- `max_weekly_loss`
- `max_consecutive_losing_weeks`
- `portfolio_max_drawdown_pct`
- `execution_failure_rate`

### Deliverables

- `plans/weekly_profit_kpi_contract.md`
- decision table:
  - `continue`
  - `investigate`
  - `pause`
  - `reopen_research`

### Exit Gate

- all future research and monitoring work can be evaluated against the same KPI
  contract
- no one can claim "weekly improvement" without showing which KPI moved

## Phase 3 - Operational Evidence Loop

### Objective

Create a recurring weekly control packet that measures live-like runtime health
against the KPI contract.

### Work

Design a repeatable weekly packet sourced from:

- StrategyRuntime observability events
- `performance.db`
- scanner diagnostics
- runtime config snapshot

The packet should answer:

- did the runtime run cleanly?
- were opportunities generated?
- what blocked them?
- what filled?
- what closed?
- how did the week contribute to the weekly KPI ladder?

### Deliverables

- weekly runtime health report format
- machine-readable weekly control summary
- clear distinction between:
  - operational integrity
  - economic performance

### Exit Gate

- a weekly review can be completed without ad hoc log spelunking
- the packet can reveal whether the system is:
  - healthy but inactive
  - active but unprofitable
  - profitable but operationally unsafe

## Phase 4 - Gap Classification And Research Activation

### Objective

Start new research only after the weekly feasibility review proves a concrete
gap.

### Gap Types

1. **Participation gap**
   - too many zero-trade weeks
   - active-week ratio too low

2. **Weekly-quality gap**
   - trades occur, but positive-week rate is inadequate
   - loss weeks are too deep or clustered

3. **Regime gap**
   - specific market states dominate bad weeks
   - transition periods repeatedly damage the weekly profile

4. **Operational gap**
   - execution or data issues distort weekly outcomes

### Candidate Activation Rule

Activate **exactly one** research lane per trigger review:

- a frequency-complement slot
- a transition/regime repair candidate
- Slot A SHORT repair work
- another targeted mechanism justified by the weekly gap

No broad backlog fan-out.

### Deliverables

- trigger review memo
- one selected candidate thesis
- one explicit "why this lane, why now" decision

### Exit Gate

- research begins from a measurable gap, not impatience

## Phase 5 - Candidate Development Under Weekly-Profit Discipline

### Objective

Develop one candidate at a time without overfitting the weekly target.

### Required Research Contract

Every candidate must pre-register:

- hypothesis
- target gap
- expected trade cadence effect
- expected weekly-positive-rate effect
- risk mechanism
- rejection criteria
- bounded parameter sweep plan

### Required Validation

- focused unit tests
- candidate review
- one bounded parameter shelf
- untouched / less-touched validation slice
- combined portfolio attribution
- weekly KPI delta versus the promoted baseline
- fee-drag read where applicable

### Promotion Questions

- does it improve the target weekly KPI?
- does it avoid ruining drawdown?
- does it improve the portfolio, not just standalone PnL?
- does it survive a bounded validation protocol?

### Deliverables

- candidate spec
- candidate review
- sweep memo
- weekly KPI delta memo
- promotion or park decision

### Exit Gate

- no candidate can be promoted solely because aggregate PnL rose

## Phase 6 - Capital Efficiency And Deployment Readiness

### Objective

Make sure the strategy that looks viable on paper also makes sense for small
capital and real execution constraints.

### Work

- min order and precision review
- leverage and liquidation buffer sanity
- realized fee burden
- slippage sensitivity
- fill quality differences between sandbox and real market conditions
- stop-loss reliability review
- runtime reconciliation behavior

### Deliverables

- small-capital deployment checklist
- execution-risk sensitivity note
- explicit go / hold / no-go recommendation for real-money rollout

### Exit Gate

- no live-money transition without capital-efficiency review

## Phase 7 - Operating Rhythm

### Weekly Cadence

Each week should have:

- one control packet
- one KPI status line
- one exception list
- one decision:
  - continue
  - investigate
  - pause
  - reopen research

### Monthly Cadence

Each month should review:

- rolling 4w / 8w PnL
- weekly participation trend
- positive-week trend
- contribution by slot
- whether the portfolio is becoming over-dependent on one lane

## Recommended Execution Order

1. Phase 0 truth sync
2. Phase 1 weekly feasibility review
3. Phase 2 KPI contract
4. Phase 3 operational weekly packet
5. Phase 4 trigger review only if the baseline shows a real gap
6. Phase 5 one-candidate research loop
7. Phase 6 capital-efficiency deployment readiness

## Core Decision Principle

The project should never optimize for "more activity" in isolation.

The only acceptable improvement is:

> more weekly participation or better weekly outcome stability **while**
> preserving central risk discipline, bounded drawdown, and evidence quality.

That principle is the basis for turning the current StrategyRuntime portfolio
into a system that is not merely profitable in research packets, but capable of
earning trust as an ongoing weekly-profit machine.
