# Weekly Profit V0 To V1 Product Roadmap

Date: 2026-05-28
Branch: `codex/post-promotion-control-20260430`
Status: `ACTIVE_PRODUCT_GOVERNANCE_ROADMAP`

## Executive Verdict

Current state: `investigate`.

This branch is close to a V0 canary-readiness path, but it is not a V1
weekly-profit machine. The runtime contract is cleaner than the economic
evidence. The bottleneck is not "can the bot run"; the bottleneck is whether the
promoted BTC/ETH portfolio can produce enough live-like weekly participation
without weakening edge quality or drawdown discipline.

This roadmap does not authorize runtime-default changes, scanner runtime
universe activation, threshold loosening, strategy promotion, live/testnet state
changes, or credential-handling changes.

## Product Target Split

| target | meaning | current verdict |
| --- | --- | --- |
| V0 canary readiness | controlled small-capital or authenticated execution-path evidence collection | `Hold` until execution-path evidence and Ruei approval exist |
| V1 weekly-profit confidence | credible rolling weekly participation and after-fee outcome evidence | `No-Go` |

V0 is not "stable profit". V0 is permission to collect controlled real-market
evidence with small capital after operational and execution checks pass.

V1 requires enough rolling evidence to claim that the system is becoming a
weekly-profit machine. The branch is not there yet.

## Runtime Contract

Runtime truth remains `trader/config.py -> Config class defaults`.

| contract area | required state |
| --- | --- |
| runtime portfolio | promoted Slot A LONG + Slot B LONG + Slot B SHORT |
| runtime symbols | `BTC/USDT`, `ETH/USDT` |
| scanner runtime universe | disabled |
| scanner output | diagnostic/shadow only |
| router policy | `fail_closed` |
| risk sizing | central `RiskPlan` only |
| credentials | `secrets.json` may load credentials only |
| research candidates | disabled until trigger review and explicit approval |

Any change to these items is a product decision, not implementation cleanup.

## Current Evidence Read

The project has already learned three important things:

1. The promoted baseline is historically net-positive, but not yet a credible
   weekly machine.
2. Participation is the dominant weakness.
3. Adding trades is easy; preserving after-fee weekly quality and drawdown
   stability is the hard part.

Phase 5 is closed with no promotion. The best-looking Slot B symbol expansion
repair passed the primary window but failed all four holdout windows. That
result is useful research evidence, not promotion authority.

Scanner V3 Stage A proves shadow diagnostics can be separated from runtime
selection. It does not prove economic value, and it does not authorize scanner
runtime consumption.

## Work Tracks

### Track A - Promoted Baseline Evidence

Purpose: keep the BTC/ETH three-leg runtime baseline observable and clean.

Required outputs:

- weekly control packet
- unique signal-window accounting
- per-slot, per-symbol, and per-side contribution
- blocked-gate attribution
- regime attribution
- execution failures, config drift, and unprotected-position counts

Track A is the source of truth for runtime health and live-like evidence. It
must not be replaced by scanner shadow results or historical primary-window
success.

### Track B - V0 Canary Readiness

Purpose: determine whether controlled canary evidence collection is safe enough
to request Ruei approval.

Required outputs:

- `Config.validate()` pass
- promoted runtime scope confirmation
- credentials validation without leaking secrets
- authenticated dry-run or testnet order-path check
- min order, precision, leverage, stop, and liquidation-buffer review
- persistence and position reconciliation review
- canary risk proposal and kill criteria
- explicit Ruei approval before any real-money transition

If any of these are missing, V0 remains `Hold`.

### Track C - Scanner Shadow Diagnostics

Purpose: test whether the fixed BTC/ETH universe is too narrow without feeding
the runtime.

Allowed outputs:

- shadow universe packets
- blocker attribution
- baseline-versus-shadow participation comparison
- candidate thesis material for a future trigger review

Forbidden outputs without explicit approval:

- runtime universe activation
- symbol promotion
- threshold loosening
- scanner-ranked live selection
- order execution from scanner output

### Track D - Bounded Research

Purpose: open exactly one research lane only after clean evidence proves a
specific gap.

Default research thesis, if triggered:

> The promoted baseline is operationally clean, but the fixed BTC/ETH universe
> is too narrow for weekly participation under the observed regime.

Preferred lane:

> pre-registered regime-filtered Slot B expansion repair

This lane is parked unless the regime/window filter is registered before the
test, uses runtime-available non-outcome features, and passes the same primary
plus holdout hard gates.

## Decision Gates

### `continue`

Use only when runtime integrity is clean and no material participation or
economic watch condition is active.

Action: keep the observer and weekly packet running. Do not start new alpha
work.

### `investigate`

Use when runtime integrity is clean but participation or evidence quality is
not sufficient to make a Go/No-Go call.

Action: produce a variance note and attribution packet. Do not change runtime
defaults.

### `pause`

Use when operational integrity breaks.

Pause triggers include config drift, scanner boundary violation, repeated
execution failure, unprotected position state, or evidence contamination that
invalidates interpretation.

Action: fix runtime/evidence integrity before interpreting economics.

### `reopen_research`

Use only after clean evidence supports a specific thesis and the trigger review
selects one bounded lane.

Action: create the research contract first. Then run the bounded lane. Do not
promote from primary-window success alone.

### V0 `Go`

Use only when all V0 readiness checks pass and Ruei explicitly approves canary
risk.

Action: controlled evidence collection. Do not call this V1.

### V1 `Go`

Use only after rolling evidence shows sufficient participation, acceptable
positive-week rate, bounded weekly downside, no fragile single-lane dependency,
and promotion-grade candidate evidence where applicable.

Current V1 verdict: `No-Go`.

## 2026-06-01 Checkpoint Interpretation

The 2026-06-01 checkpoint must not become "observe more" by default.

Required decision logic:

| evidence on 2026-06-01 | decision | action |
| --- | --- | --- |
| config drift, scanner boundary break, execution integrity issue, or unprotected position | `pause` | resolve runtime/evidence integrity first |
| runtime clean, no entry-ready windows, no fills, no exits | `investigate` | label participation bottleneck active; produce attribution packet |
| runtime clean, entries exist, but no authenticated execution-path validation | V0 `Hold` | finish canary readiness checks |
| runtime clean, execution path validated, risk checklist complete, Ruei approves | V0 `Go` | controlled canary evidence collection only |
| any state without rolling weekly-profit evidence | V1 `No-Go` | keep V1 claim blocked |

## Definition Of Done For This Roadmap

This branch is not ready to claim weekly-profit readiness until it has:

- stable runtime process evidence
- clean config validation
- clean scanner boundary evidence
- weekly control packet discipline
- unique opportunity accounting
- participation attribution
- authenticated execution-path validation
- capital-efficiency review
- explicit V0 Go/Hold/No-Go decision
- no secrets committed
- no unreviewed runtime-default drift
