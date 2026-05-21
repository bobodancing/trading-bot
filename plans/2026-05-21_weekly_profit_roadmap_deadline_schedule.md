# Weekly Profit Roadmap Deadline Schedule

Date: 2026-05-21
Branch: `codex/post-promotion-control-20260430`
Status: `FINAL_REVIEWED_ROADMAP_SCHEDULE`

## Review Verdict

The schedule is logically consistent with the current roadmap and is approved
as the working plan.

It does not authorize:

- runtime default changes
- promoted symbol expansion
- scanner-universe runtime activation
- threshold loosening
- strategy promotion
- live/testnet state changes

The current promoted BTC/ETH three-leg baseline remains the only approved
runtime portfolio. Scanner V3 is a parallel shadow-research lane only.

## Current State

| area | state | roadmap placement |
| --- | --- | --- |
| Phase 0 truth sync | complete | baseline governance aligned |
| Phase 1 weekly feasibility | complete | participation gap identified |
| Phase 2 KPI contract | complete | weekly decision gates defined |
| Phase 3 operational evidence loop | active | clean dry-run observer started 2026-05-18 |
| Phase 4 trigger review | complete for current batch | reopen only from clean evidence |
| Phase 5 candidate batch | closed, no promotion | 4E parked unless a pre-registered regime filter exists |
| Scanner V3 shadow universe | spec drafted | new shadow lane, not runtime |
| Phase 6 deployment readiness | not started | blocked until evidence quality improves |
| Phase 7 operating rhythm | partially active | weekly packet automation exists |

## Integration Logic

The roadmap should now run on two coordinated tracks.

Track A is the promoted baseline evidence track. It keeps collecting clean
runtime evidence from the fixed BTC/ETH baseline and produces weekly packets.
This is the source of truth for operational health and realized dry-run
economics once exits exist.

Track B is the Scanner V3 shadow track. It explores whether the opportunity
funnel is too narrow without feeding the runtime, changing symbols, loosening
thresholds, or using outcome data in ranking. It can move faster than the
8-week runtime review because it is observational and research-only.

The key constraint is that Track B may explain or prepare the next research
lane, but Track B must not replace Track A as the promoted baseline control.

## Deadline Schedule

| date | checkpoint | deliverable | decision |
| --- | --- | --- | --- |
| 2026-05-21 Thu | Roadmap schedule finalization | this plan plus Scanner V3 spec ready for commit review | lock the two-track operating plan |
| 2026-05-22 Fri | Scanner V3 Stage A implementation | `scanner_shadow_universe.json`, focused tests, no runtime feed | accept or revise the scanner contract |
| 2026-05-23 Sat | Stage A packet review | `reports/scanner_v3_shadow_universe_packet.md` | decide if shadow diagnostics are useful |
| 2026-05-25 Mon | Dry-run Week 1 review | promoted BTC/ETH weekly packet | continue unless operational integrity breaks |
| 2026-05-26..2026-05-29 | Scanner V3 Stage B observation | daily shadow summaries and blocker attribution | decide whether daily shadow cadence is worth keeping |
| 2026-06-01 Mon | Dry-run Week 2 review | second promoted baseline weekly packet | if still no entries, label participation bottleneck as active watch |
| 2026-06-02..2026-06-05 | Scanner V3 Stage C primary replay | historical primary-window replay and attribution | proceed to holdout only if hard gates are plausible |
| 2026-06-08 Mon | Dry-run Week 3 review | third weekly packet plus shadow comparison | confirm whether baseline silence is market or universe driven |
| 2026-06-09..2026-06-12 | Scanner V3 holdout review | holdout robustness packet | park if primary/holdout divergence appears |
| 2026-06-15 Mon | Four-week participation checkpoint | interim Phase 3 participation memo | decide continue, investigate, or prepare bounded research |
| 2026-06-16..2026-06-19 | Scanner V3 closeout | scoreboard and next-lane recommendation | park, continue shadow, or draft enabled=False candidate |
| 2026-07-13 Mon | Rolling 8-week control review | contract-grade 8w runtime evidence packet | formal KPI review; no automatic promotion |

## Decision Gates

### Continue Phase 3

Continue the clean dry-run observer when:

- config drift is zero
- execution failures are zero or denominator-qualified as non-pausing
- scanner runtime universe remains disabled
- runtime scope remains promoted BTC/ETH
- no unprotected position events occur

### Investigate Participation

Open a participation investigation when any of these appear in clean evidence:

- two consecutive completed weeks with no entry-ready events
- no realized exits because no entries were opened
- shadow scanner repeatedly finds near-setup or entry-ready symbols outside
  BTC/ETH while BTC/ETH remains silent

This does not authorize threshold loosening.

### Reopen Research

Reopen bounded research only when clean evidence or Scanner V3 replay supports
a specific thesis. The preferred thesis shape is:

> the promoted baseline is operationally clean, but the fixed BTC/ETH universe
> is too narrow for weekly participation under the observed regime.

Any reopened lane must still pass:

- primary plus holdout review
- combined portfolio attribution
- after-fee comparison against baseline
- active-entry improvement
- positive all-week ratio not down
- positive exit-active ratio not down
- max drawdown not materially worse
- losing-symbol volume not dominant

### Park Scanner V3

Park Scanner V3 if:

- it cannot produce clean data-ready candidates
- shadow candidates are mostly `eligible_only`
- primary replay improves participation but damages after-fee quality
- holdout windows fail like the prior 4E repair lane
- useful candidates depend on outcome-based ranking or threshold loosening

## Deadline Interpretation

The dates are execution deadlines, not promotion promises.

The project should not wait passively until the 8-week review if a 2-4 week
participation bottleneck is already clear. It should also not promote anything
before the 8-week control-grade review plus candidate-specific primary and
holdout evidence.

The correct posture is:

1. keep the promoted baseline running cleanly
2. build Scanner V3 as shadow-only observation
3. use the first 2-4 completed weeks to classify inactivity
4. use the 8-week packet for formal KPI state
5. require separate candidate evidence before any runtime change
