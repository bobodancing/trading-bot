# Weekly Profit Deadline Schedule

Date: 2026-05-28
Branch: `codex/post-promotion-control-20260430`
Status: `ACTIVE_DEADLINE_FILE`
Timezone: `Asia/Taipei`

## Executive Read

These are decision deadlines, not promotion promises.

The branch must move toward controlled earning evidence, but deadline pressure
does not authorize unverifiable live trading, threshold loosening, scanner
runtime activation, or runtime-default drift.

Current deadline posture:

| target | deadline posture |
| --- | --- |
| V0 canary readiness | prepare Go/Hold/No-Go evidence by the Week 2 checkpoint |
| V1 weekly-profit confidence | blocked until rolling weekly evidence is credible |
| research reopen | blocked until a trigger review selects one bounded lane |

## Required Commands For Decision Packets

Run from repo root unless the packet is generated on the Ubuntu observer host.

```powershell
python -c "from trader.config import Config; Config.validate()"
python tools/runtime_weekly_control_packet.py --as-of 2026-06-01 --weeks 2 --completed-only --config-profile promoted_baseline
```

If the Ubuntu observer is the source of truth, the 2026-06-01 packet must record
the exact host/path/command used there. Local Windows evidence is auxiliary
unless it is the active observer source.

## Deadline Table

| date | checkpoint | required deliverable | decision |
| --- | --- | --- | --- |
| 2026-05-28 Thu | Governance cleanup | retired assistant files removed; roadmap/deadline split | accept docs if no runtime contract changed |
| 2026-05-29 Fri | Evidence-source precheck | confirm Ubuntu observer source, packet command, config profile, and artifact paths | repair evidence access or proceed to Week 2 |
| 2026-06-01 Mon | Dry-run Week 2 review | promoted-baseline weekly packet, unique signal-window attribution, scanner boundary check | `pause`, `investigate`, V0 `Hold`, or V0 `Go request` |
| 2026-06-02 Tue | V0 execution-path review | authenticated dry-run/testnet path check plan or evidence; no secrets printed | keep V0 `Hold` unless execution path is verified |
| 2026-06-03 Wed | Capital and risk checklist | min order, precision, leverage, stop behavior, reconciliation, kill criteria | prepare Ruei canary approval request or hold |
| 2026-06-05 Fri | Scanner shadow review | Stage B/C readiness or blocker attribution; no runtime feed | continue shadow, revise diagnostics, or park |
| 2026-06-08 Mon | Dry-run Week 3 review | third weekly packet plus shadow comparison | classify whether silence is market-driven or universe-driven |
| 2026-06-12 Fri | Trigger-review cutoff | if evidence supports it, one pre-registered research contract | open one bounded lane or keep research parked |
| 2026-06-15 Mon | Four-week participation checkpoint | interim participation memo and V0 readiness state | `continue`, `investigate`, `pause`, or `reopen_research` |
| 2026-06-19 Fri | Scanner V3 closeout | scoreboard and next-lane recommendation | park, continue shadow, or draft disabled candidate |
| 2026-07-13 Mon | Rolling 8-week control review | contract-grade 8w runtime evidence packet | formal KPI review; no automatic promotion |

## 2026-06-01 Decision Rules

### `pause`

Choose `pause` if any of these appear:

- config drift
- scanner runtime boundary violation
- execution-integrity breach
- unprotected position event
- evidence contamination that prevents promoted-baseline interpretation

Required action: fix runtime/evidence integrity. Do not interpret economics.

### `investigate`

Choose `investigate` if operations are clean but the Week 2 packet still shows:

- no entry-ready events
- no fills or dry-run handoffs
- no realized exits because no entries opened
- scanner shadow diagnostics show possible external opportunity while BTC/ETH
  remain silent

Required action: produce participation attribution. Do not change runtime
defaults.

### V0 `Hold`

Choose V0 `Hold` if runtime is clean but any canary-readiness item is missing:

- credentials validation without leaks
- authenticated dry-run or testnet execution-path check
- min order and precision review
- leverage and stop behavior review
- persistence and reconciliation review
- Ruei canary risk approval

Required action: finish the readiness checklist.

### V0 `Go Request`

Prepare a V0 `Go` request only if:

- runtime integrity is clean
- config validation passes
- promoted runtime scope is confirmed
- execution path is authenticated and reviewed
- risk/capital checklist is complete
- Ruei is ready to decide the canary risk

V0 `Go` still means controlled evidence collection, not V1 profit confidence.

### V1 `No-Go`

Keep V1 `No-Go` unless rolling weekly evidence shows:

- sufficient weekly participation
- acceptable positive-week rate
- bounded weekly downside
- no hidden dependence on one fragile lane
- promotion-grade candidate evidence where defaults would change

## Research Activation Deadline Rule

No research lane opens before a trigger review answers:

- why this lane
- why now
- what gap it targets
- what evidence would reject it
- what parameter space is allowed
- what untouched or less-touched validation slice will be used

Only one lane may be active. The default candidate, if triggered, is
pre-registered regime-filtered Slot B expansion repair. The lane remains parked
unless the filter is defined before the rerun and uses runtime-available
non-outcome features.

## Human Gate

Create or update `humanpending.md` only when the work is truly blocked by a
Ruei decision. Expected human-gated items:

- V0 canary approval
- runtime strategy-list change
- risk-default change
- scanner runtime consumption
- credential-handling change
- research-lane activation after trigger review
- candidate promotion

Do not create vague open blockers.
