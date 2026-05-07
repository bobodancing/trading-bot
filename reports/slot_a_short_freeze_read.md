# Slot A SHORT Freeze Read

Date: 2026-05-07
Status: `FROZEN_RESEARCH_READ`

## Decision

- Freeze the Slot A SHORT repair lane.
- Do not promote Slot A SHORT.
- Do not add Slot A SHORT back into the Slot A + Slot B runtime default set.
- Do not run a full `classic_rollercoaster_2021_2022` guard backtest for now.
- Do not spend another V3 classifier pass unless the portfolio later needs a separate trend-continuation SHORT thesis.

## Frozen Read

Slot A SHORT failed as a mirror of Slot A LONG because the bearish-continuation context is asymmetric.

The issue is not runtime routing, order sizing, side handling, or a missing SHORT execution path. The failure concentrates in late bearish breakdown entries where downside continuation is already crowded or exhausted. These entries tend to snap back quickly, producing larger adverse excursion, many stop hits, and several zero-hour stop hits before the staged derisk / giveback lifecycle can help.

This means the Slot A LONG cartridge should not be mirrored into SHORT. A future SHORT trend-continuation lane needs its own thesis and entry context.

## Evidence

| artifact | result |
| --- | --- |
| `reports/slot_a_short_failure_attribution.md` | Slot A SHORT classic stress: 45 trades, net `-2508.9498`, PF `0.1618`, 16 stop hits, 8 zero-hour stop hits |
| `reports/slot_a_short_snapback_guard_experiment.md` | V1/V2 guards remove the targeted failure-month signature, but V2 does not prove profitable continuation preservation |
| `reports/slot_a_short_snapback_classifier.md` | V2 differentiated bucket `v1_block_v2_keep`: 6 trades, net `-39.9238`, PF `0.8824`, 3 stop hits, 2 zero-hour stop hits |

## Resource Read

- The research question has enough answer quality for portfolio decision-making.
- Full classic backtest is low expected value because the dry classifier says V2's extra preserved trades are still negative.
- Another V3 pass is possible, but it is now an optimization problem on a weak thesis, not a high-priority portfolio unlock.
- Slot B SHORT is the stronger SHORT exposure candidate and should stay ahead of Slot A SHORT repair work.

## Reopen Criteria

Only reopen this lane if all are true:

- the portfolio has a clear SHORT-side gap after Slot B SHORT monitoring;
- the new thesis is not a symmetric mirror of Slot A LONG;
- dry classification shows the extra kept bearish-continuation bucket is materially positive and not dominated by zero-hour stop hits;
- Ruei explicitly chooses to spend research budget on a new SHORT trend-continuation lane.

Verdict: `NO_PROMOTION_FREEZE_RESEARCH_DO_NOT_MIRROR_SLOT_A_SHORT`.
