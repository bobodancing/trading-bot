# Runtime Evidence Hygiene Review

Date: 2026-05-17
Branch: `codex/post-promotion-control-20260430`
Status: `RUNTIME_EVIDENCE_NOT_CONTRACT_GRADE`

## Executive Read

The current local runtime evidence stream is **not clean enough** to use as a
Phase 3 contract-grade weekly control source.

The unfiltered packet correctly reported `pause`, but that `pause` is an
evidence-hygiene result, not proof that the promoted BTC/ETH runtime baseline is
operationally broken. The local `.log` stream mixes promoted baseline runs,
test fixtures, disabled-runtime checks, candidate research profiles, and pytest
scanner/test artifacts.

No runtime default, strategy default, scanner runtime mode, or promoted symbol
scope was changed by this review.

## Sources Reviewed

| source | observed |
| --- | --- |
| runtime JSONL | `.log/runtime_observability/strategy_runtime_funnel.jsonl` |
| JSONL parsed events | `879276` |
| JSONL malformed lines | `30` |
| JSONL size | `331725550` bytes |
| first runtime event | `2026-05-07T08:33:40.551580+00:00` |
| last runtime event | `2026-05-17T07:02:02.331768+00:00` |
| latest observer summary | `.log/runtime_observability/strategy_runtime_latest.json` |
| `performance.db` | missing |
| `.log/positions.json` | missing |
| `runtime_scanner.json` | missing |

## P0 Findings

### Mixed Config Profiles

The runtime JSONL is append-only and currently contains multiple config
profiles:

| profile | config snapshots |
| --- | ---: |
| `PROMOTED_BASELINE_MATCH` | 1467 |
| `TEST_FIXTURE_LONG` | 397 |
| `RUNTIME_DISABLED_OR_EMPTY` | 282 |
| `RESEARCH_OTHER_CANDIDATE` | 137 |
| `RESEARCH_4E_EXPANSION` | 11 |
| `RESEARCH_4E_REPAIR` | 5 |

This means the current JSONL cannot be read as one runtime stream. Any weekly
control packet built from it must either scope by a known run/profile or be
treated as hygiene-only.

### Execution Failures Are Fixture Failures

All observed execution failures are from `TEST_FIXTURE_LONG`, not the promoted
three-leg baseline:

| item | value |
| --- | ---: |
| execution failures | 64 |
| reason | `post_fill_stop_violation` |
| detail | `long_fill_below_stop` |
| strategy | `fixture_long` |
| symbol | `BTC/USDT` |
| week `2026-05-04` | 28 |
| week `2026-05-11` | 36 |

Therefore the unfiltered packet's `execution_integrity_weekly` pause trigger
should not be interpreted as promoted-baseline live/testnet failure.

### No Economic Evidence Source

`performance.db` is missing in the repo root, and `.log/positions.json` is also
missing. That means:

- realized exits are not available
- after-fee PnL is not available
- active position protection cannot be confirmed from persisted runtime state
- weekly economics are observe-only

The current runtime packet cannot answer weekly profitability. It can only
diagnose evidence plumbing and local runtime event hygiene.

## P1 Findings

### Latest Summary Is Not Baseline

`strategy_runtime_latest.json` reflects only the latest recorder process, not
the entire JSONL history. The current latest summary is from a one-plugin
candidate-style run:

| field | value |
| --- | --- |
| latest plugin entry count | `ema_cross_7_19_long_only: 2` |
| latest cycle plugins | `1` |
| latest cycle status | `completed` |

Do not use `strategy_runtime_latest.json` alone as a promoted-baseline health
source.

### Malformed JSONL Lines Exist

The JSONL parser found `30` malformed lines. Samples are truncated fragments
around `2026-05-08`, consistent with interrupted or concurrent local writes.
The count is low relative to total events, but it confirms the file is not a
strict audit ledger.

### Local Scanner Logs Are Test-Polluted

`.log/scanner.log` includes pytest temp paths such as:

```text
C:\Users\user\AppData\Local\Temp\pytest-of-user\...
```

This confirms local logs are shared by automated tests and local runtime-like
experiments. They should not be mixed into operating evidence without scoping.

## Promoted Baseline Slice

Within the mixed JSONL, events associated with `PROMOTED_BASELINE_MATCH` show:

| item | count |
| --- | ---: |
| config snapshots | 1467 |
| completed scan cycles | 2391 |
| plugin candidate events | 7167 |
| strategy entry ready | 13 |
| execution filled | 14 |
| strategy rejects | 28 |
| execution failures | 0 |

This slice is directionally useful but still not contract-grade because the
current observer has no durable `run_id` / `profile_id` boundary. Attribution by
"last config snapshot" is a hygiene approximation, not a hard audit key.

## Decision

Current evidence status:

```text
RUNTIME_EVIDENCE_NOT_CONTRACT_GRADE
```

Interpretation:

- Do not use the current unfiltered `.log` packet to reopen research.
- Do not use it to judge live expectancy.
- Do not claim promoted runtime failure from the unfiltered `pause`.
- Do use it to justify an evidence-isolation repair before Phase 3 operating
  cadence begins.

## Required Repair Before Weekly Operating Cadence

1. Start Phase 3 with a clean evidence window.
2. Rotate or archive the existing local `.log/runtime_observability` JSONL before
   collecting operating evidence.
3. Require each packet to identify the config profile it is evaluating.
4. Add or use a durable `run_id` / `config_hash` boundary so tests, research
   probes, and live-like runs cannot contaminate one another.
5. Generate `runtime_scanner.json` as diagnostic-only evidence during the same
   window.
6. Ensure `performance.db` exists and receives realized exits before interpreting
   economic KPIs.
7. Keep scanner runtime universe disabled and keep promoted runtime defaults
   unchanged.

## Next Recommended Action

Implement evidence scoping before the first formal operating packet:

```text
runtime weekly packet builder -> require baseline config profile or explicit run_id
```

Then start a fresh dry-run/testnet observation window and rebuild the packet from
that clean stream.
