# bb_fade_squeeze_1h First Pass

Date: 2026-04-25  
Status: `SUPERSEDED_BY_PHASE_5_CLOSEOUT`

Closeout update (2026-05-05): Phase 5 is parked in
`reports/phase_4_5_research_closeout.md`; do not promote, runtime-enable, or
rescue this candidate without a fresh trigger review.

## Scope

- Candidate: `bb_fade_squeeze_1h`
- Locked spec: `plans/cartridge_spec_bb_fade_squeeze_1h.md`
- Runner:
  `python -m extensions.Backtesting.scripts.run_candidate_review --candidate bb_fade_squeeze_1h`

## Candidate Review Read

| window | trades | net_pnl | max_dd_pct |
| --- | ---: | ---: | ---: |
| TRENDING_UP | 1 | -38.2332 | 0.4172 |
| RANGING | 0 | 0.0000 | 0.0000 |
| MIXED | 0 | 0.0000 | 0.0000 |
| aggregate | 1 | -38.2332 | 0.4172 |

Primary source: `reports/strategy_plugin_candidate_review.md`.

## What Landed Cleanly

- Plugin contract, focused tests, catalog registration, and StrategyRuntime candidate review path all worked without infra changes.
- No backtest run errors.
- The one executed trade had no entry-stop violation.
- Runtime defaults stayed unchanged; the strategy remains disabled in the catalog.

## What Failed

- The declared target regime is `RANGING`, but the locked first pass produced `0` trades in the default `RANGING` window.
- The `MIXED` window also produced `0` trades, so this is broader gate starvation, not only a single-window artifact.
- The only executed trade landed in `TRENDING_UP` and lost `-38.2332`, which means the current gate stack did not express the intended ranging surface.

## Interpretation

- The first-pass implementation is valid as a StrategyRuntime cartridge, but the locked signal shape is not promotion-shaped.
- The likely issue is combined-gate scarcity: `rsi_14 < 30`, lower Bollinger touch, `bbw_pctrank < 20`, and `adx[4h] < 20` rarely align in the review windows.
- Because internal plugin gate failures are not emitted to the runtime audit, the next pass should first add or run a diagnostic gate-attribution count before any threshold re-lock.
- Follow-up diagnostic: `reports/bb_fade_squeeze_1h_gate_attribution.md`.

## Recommended Next Step

Do not promote or runtime-enable this candidate.

If the lane continues, make the next move attribution-first:

1. Use the completed gate-attribution read to decide whether the squeeze definition deserves one narrow rescue child.
2. Only after that, write a child spec for the single bottleneck gate if the thesis still looks alive.
3. Keep `rsi2_pullback_1h` queued next unless Ruei explicitly wants more C1 rescue work first.

## Verdict

`bb_fade_squeeze_1h` is implemented and tested, but baseline v0.1.0 is a research-only miss: target `RANGING` printed no trades, and the only off-target trade lost money.
