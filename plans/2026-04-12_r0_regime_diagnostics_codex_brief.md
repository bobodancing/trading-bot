# R0 Regime Diagnostics Codex Brief

Date: 2026-04-12
Target worktree: `projects/trading_bot/.worktrees/feat-grid`
Related spec: `plans/2026-04-12_regime_arbiter_design.md`
Status: execution brief only. Do not implement runtime changes from this brief. Do not edit `plans/2026-04-12_regime_arbiter_design.md` -- spec patches with R0 findings are 小波's responsibility after review.

## Objective

Run R0 diagnostics before any RegimeEngine or arbiter code change.

R0 must answer two questions with evidence:

1. Why did the Apr-May 2025 fade / consolidation area stay usable by V54 as entry-time TRENDING in P0.6?
2. Is SQUEEZE 0 coverage a RegimeEngine issue, a validation-window issue, or still undecidable without chart review?

## Hard Guardrails

1. V54 strategy logic is FROZEN. Do not modify `trader/strategies/v54_noscale/` or V54 lifecycle, lock, stop, sizing, or exit behavior.
2. New range strategy work is blocked until V54-in-RANGING is benchmarked. P0.6 deduped baseline is PF 2.17, n=22, +169 USDT.
3. Diagnose RegimeEngine before changing it. Do not tune thresholds just to make SQUEEZE coverage non-zero.

## Context Bundle

Read these before doing any work:

- `plans/2026-04-12_regime_arbiter_design.md`, especially the R0 section and Hard Guardrails.
- `trader/regime.py`, current `RegimeEngine` implementation.
- `C:/Users/user/Documents/Claude.ai/tools/Backtesting/results/p06_regime_diagnostics_20260412/TRENDING_UP/trades.csv`
- `C:/Users/user/Documents/Claude.ai/tools/Backtesting/results/p06_regime_diagnostics_20260412/TRENDING_UP/signal_audit_summary.json`
- `C:/Users/user/Documents/Claude.ai/tools/Backtesting/results/p06_regime_diagnostics_20260412/TRENDING_DOWN/trades.csv`
- `C:/Users/user/Documents/Claude.ai/tools/Backtesting/results/p06_regime_diagnostics_20260412/TRENDING_DOWN/signal_audit_summary.json`
- `C:/Users/user/Documents/Claude.ai/tools/Backtesting/results/p06_regime_diagnostics_20260412/RANGING/trades.csv`
- `C:/Users/user/Documents/Claude.ai/tools/Backtesting/results/p06_regime_diagnostics_20260412/RANGING/signal_audit_summary.json`
- `C:/Users/user/Documents/Claude.ai/tools/Backtesting/results/p06_regime_diagnostics_20260412/MIXED/trades.csv`
- `C:/Users/user/Documents/Claude.ai/tools/Backtesting/results/p06_regime_diagnostics_20260412/MIXED/signal_audit_summary.json`

The P0.6 output `trades.csv` files include entry-time regime telemetry:

- `entry_regime`
- `entry_regime_trend`
- `entry_regime_direction`
- `entry_regime_reason`
- `entry_regime_candle_time`

## Execution Environment

Run on the local Windows machine. Working directory:

`C:/Users/user/Documents/Claude.ai/tools/Backtesting/`

BTC 4H data source: `tools/Backtesting` cache, already populated by P0.5 / P0.6. Do not run on rwUbuntu; that environment lacks the cache.

Python: same environment used for the P0.6 backtest run, around feat-grid commit `9825bf1`.

## Current RegimeEngine Facts

Current implementation lives in `trader/regime.py`.

Important mechanics to inspect and report against:

- `RegimeEngine.update(df_4h)` advances at most once per new 4H candle.
- `_detect_regime(df)` returns one of `TRENDING`, `RANGING`, `SQUEEZE`, or `None`.
- `None` means ambiguous and keeps previous `current_regime`.
- Hysteresis uses `_pending_regime` and `_confirm_count`; promotion requires `Config.REGIME_CONFIRM_CANDLES`, currently expected to be 3.
- TRENDING can short-circuit before SQUEEZE through `adx >= REGIME_ADX_TRENDING` or ATR expansion.
- SQUEEZE currently requires low BBW percentile, `bbw_ratio < 0.15`, and non-expanding ATR.

## Required Outputs

Write exactly these reports:

- `reports/regime_diagnostic_apr_may_2025.md`
- `reports/squeeze_coverage_audit.md`
- `reports/confidence_score_poc.md`

Optional diagnostic artifacts are allowed only if they help review, for example:

- `reports/regime_diagnostic_apr_may_2025.csv`
- `reports/regime_diagnostic_apr_may_2025.html`
- `reports/squeeze_coverage_candidates.csv`
- `reports/squeeze_coverage_candidates.html`

Do not write production code. If a throwaway helper script is needed, keep it diagnostic-only and mention it in the report. Do not modify `trader/regime.py`, `trader/config.py`, strategy code, router code, or bot runtime code.

## Instrumentation Approach

The diagnostic script may import and instantiate `RegimeEngine` from `trader/regime.py`. Reading instance attributes, including `_pending_regime`, `_confirm_count`, `current_regime`, and any other private attribute needed for diagnostics, is permitted.

Not permitted:

- Subclassing `RegimeEngine` to override behavior
- Monkey-patching its methods at runtime
- Modifying `trader/regime.py` source
- Reimplementing the regime detection logic in the diagnostic script; the point is to observe the runtime engine, not a copy

If a private attribute access is unavoidable, add a one-line comment in the script explaining why.

## Task A: Apr-May 2025 Hysteresis Replay

Replay BTC 4H bars over:

`2025-03-15 -> 2025-06-15`

This range intentionally includes March impulse plus Apr-May consolidation.

Use the same RegimeEngine logic as runtime, but record diagnostic columns per 4H bar. The report must include a table with at least:

Markdown table in `reports/regime_diagnostic_apr_may_2025.md`: keep this narrow and include these 6 core columns:

- `timestamp`
- `close`
- `adx`
- `bbw_ratio_to_history_mean`
- raw `_detect_regime` result
- `current_regime` after hysteresis

CSV artifact at `reports/regime_diagnostic_apr_may_2025.csv`: include the full diagnostic columns:

- `timestamp`
- `close`
- `adx`
- `bbw`
- `atr`
- `atr_avg20`
- `atr_ratio_20`
- `bbw_history_pct`
- `bbw_ratio_to_history_mean`
- raw `_detect_regime` result
- `current_regime` after hysteresis
- `_pending_regime`
- `_confirm_count`
- `trend_direction`
- transition event, if any
- short reason label for the raw decision, such as `adx_trending`, `atr_expansion`, `squeeze_candidate_missed_ratio`, `ranging_candidate`, or `ambiguous_keep_previous`

The report must specifically map the P0.6 MIXED entry-time TRENDING loser cluster against this replay. Include a table of the relevant P0.6 MIXED trades with:

- `entry_time`
- `symbol`
- `side`
- `entry_regime`
- `entry_regime_trend`
- `realized_r`
- `max_r_reached`
- `exit_reason`
- nearest BTC 4H replay row
- raw `_detect_regime` result at the nearest replay row
- `current_regime` at the nearest replay row
- reason label

Minimum questions to answer in the report:

- Did Apr-May stay TRENDING because ADX was still above threshold?
- Did ATR expansion short-circuit TRENDING before BBW/SQUEEZE/RANGING could classify?
- Did `_detect_regime` return `None` often enough to preserve the prior TRENDING state?
- Did `_confirm_count` reset before RANGING could confirm?
- Name at least one concrete hysteresis stuck case with timestamp range and the indicator that appears responsible.

The report can include observations and hypotheses, but must not propose threshold changes as the next action.

## Task B: SQUEEZE Coverage Audit

Use the four P0.6 windows:

- `TRENDING_UP`: `2023-10-01 -> 2024-03-31`
- `TRENDING_DOWN`: `2025-10-07 -> 2026-04-06`
- `RANGING`: `2024-12-31 -> 2025-03-31`
- `MIXED`: `2025-02-01 -> 2025-08-31`

Audit BTC 4H bars from these windows against the current RegimeEngine rules. The expected P0.6 observation was SQUEEZE 0 / 3988 probed BTC 4H window-occurrence bars.

Percentile definitions:

- Primary: compute `BBW_percentile` and `ATR_percentile` per window. This answers whether a given validation window had local compression that the engine missed.
- Secondary: compute a pooled, timestamp-deduped cross-window percentile. This is only a sanity check for absolute low-volatility candidates across the whole P0.6 sample.
- Do not use either percentile to relabel the run or tune thresholds during R0.

The report must include:

- Total BTC 4H bars audited per window and in pooled-deduped form.
- SQUEEZE bar count under current engine rules.
- Count of low BBW candidates per window using primary `BBW_percentile < 20`.
- A top-candidates table with at least the lowest 20 primary-percentile rows, including:
  - `window`
  - `timestamp`
  - `close`
  - `adx`
  - `bbw`
  - `primary_bbw_percentile`
  - `pooled_bbw_percentile`
  - `bbw_ratio_to_history_mean`
  - `atr_ratio_20`
  - raw `_detect_regime`
  - `current_regime`
  - reason the bar did not become SQUEEZE, if missed. Use one of these labels; extend only if a case truly does not fit:
    - `bbw_ratio_too_high`
    - `atr_expanding`
    - `promoted_to_TRENDING_via_adx`
    - `promoted_to_TRENDING_via_atr_expansion`
    - `preserved_previous_state`
    - `ambiguous_keep_previous`
    - `other:<short_descriptor>`
- A short section named `Chart Review Queue` listing the candidate timestamp ranges Ruei should eyeball.

Minimum yes/no answer required:

Does this audit show likely real squeeze candidates that current RegimeEngine failed to tag?

Allowed answers:

- `yes`: include timestamps and evidence.
- `no`: explain why low BBW rows do not look like squeeze candidates under current evidence.
- `undecidable`: explain exactly what chart review or data is still missing.

## Task C: Confidence Score POC

Output:

- `reports/confidence_score_poc.md`

Scope:

- Markdown spec only. Describe how a regime confidence score would be computed if implemented in R1.
- Do not implement it.
- Do not modify `trader/regime.py`.
- The report must explicitly state at the top: `Spec only. Not for R0 execution. R1 implementation will revisit after 小波 + Ruei review.`

Required content:

- Candidate inputs to evaluate, at minimum:
  - ADX absolute level
  - ADX slope: rising / falling / flat
  - BBW percentile: use per-window primary percentile as the R0 diagnostic reference
  - ATR%: `atr / close`
  - Regime persistence: how many bars the current regime has held
- For each candidate input:
  - Proposed normalization, such as z-score, percentile, ratio, bounded linear score, or categorical vote
  - Rationale for why it might help distinguish clean trend, chop-trend, range, squeeze, or transition
- Proposed combination strategy options:
  - Weighted sum
  - Minimum gate
  - Vote / quorum
  - Hybrid gate plus weighted score
  - List options only; do not pick a winner in R0
- Edge cases to handle:
  - Warmup period
  - Missing data
  - Regime just flipped
  - Ambiguous `_detect_regime` returning `None`
  - Conflicting inputs, such as high ADX with collapsing BBW
- Open questions for 小波 + Ruei to decide before R1 implementation.

Hard constraint:

This is a design proposal, not an implementation. Do not write code for confidence scoring in R0.

## Acceptance Checklist

- The brief's "diagnose first, fix later" rule is followed in both reports.
- No production code is changed.
- `trader/regime.py` is not modified.
- No threshold, confirm-count, or config value is changed.
- `reports/regime_diagnostic_apr_may_2025.md` exists and covers `2025-03-15 -> 2025-06-15`.
- `reports/squeeze_coverage_audit.md` exists and states whether percentiles are per-window or pooled.
- `reports/confidence_score_poc.md` exists, lists candidate inputs with normalization proposals, and is explicitly marked as spec-only.
- Report tables are small enough for Ruei to scan, with larger raw tables pushed to optional CSV artifacts if needed.
- Any helper script or artifact is listed in the report.
- After writing the three reports, Codex stops and waits for 小波 + Ruei review. Codex does not begin R1 implementation, does not modify `trader/regime.py`, does not propose threshold patches inline in the reports, and does not edit `plans/2026-04-12_regime_arbiter_design.md`. The spec patch with R0 findings is 小波's job after review.

## Review Notes For Reviewer

When reviewing the R0 output, check:

- Did the agent treat diagnose-before-fix as an acceptance requirement?
- Did it avoid asking to write production code?
- Is the output schema readable at a glance?
- Is the 4H replay range exactly `2025-03-15 -> 2025-06-15`?
- Did it define SQUEEZE percentile scope as primary per-window and secondary pooled-deduped cross-window?
