# Runtime Clean Evidence Window Init

Date: 2026-05-18
Branch: `codex/post-promotion-control-20260430`
Status: `CLEAN_OBSERVATION_WINDOW_INITIALIZED`

## Executive Read

Phase 3 runtime evidence has been rotated into an archive so the next weekly
control packet can start from a clean observation window.

This was evidence hygiene only:

- no runtime defaults changed
- no strategy defaults changed
- no scanner runtime-universe activation
- no bot/testnet/live process started
- no `performance.db` or `.log/positions.json` state file was moved

## Archive

| item | value |
| --- | --- |
| archive timestamp | `20260518T052428Z` |
| archive manifest | `.log/evidence_archive/20260518T052428Z/manifest.json` |
| moved evidence files | `8` |
| archived bytes | `334768130` |
| `performance.db` included | `False` |
| `.log/positions.json` included | `False` |

Archived evidence includes:

- `.log/runtime_observability/strategy_runtime_funnel.jsonl`
- `.log/runtime_observability/strategy_runtime_latest.json`
- prior `.log/weekly_control/*` runtime packet outputs

`runtime_scanner.json` was absent and therefore skipped.

## Initial Clean Packet

After rotation, a new baseline-scoped packet was generated with:

```bash
python tools/runtime_weekly_control_packet.py --as-of 2026-05-18 --weeks 1 --config-profile promoted_baseline
```

Initial packet result:

| metric | value |
| --- | ---: |
| runtime events | 0 |
| runtime events after scope | 0 |
| selected config snapshots | 0 |
| malformed runtime events | 0 |
| performance db trades | 0 |
| active positions snapshot | 0 |
| scanner symbols | 0 |
| latest state | `continue` |
| contract grade | `False` |

Interpretation:

- This is a zero-observation initialization packet, not evidence of trading
  health or profitability.
- `continue` only means no pause trigger exists in an empty packet.
- Economic KPIs remain unavailable until `performance.db` contains realized
  exits from the clean observation window.

## Next Required Operating Step

Start collecting promoted-baseline runtime evidence into the clean window:

1. Run only the promoted BTC/ETH three-leg baseline.
2. Keep `USE_SCANNER_SYMBOLS = False`.
3. Keep `SCANNER_UNIVERSE_ENABLED = False`.
4. Generate `runtime_scanner.json` as diagnostic-only evidence.
5. Rebuild packet with:

```bash
python tools/runtime_weekly_control_packet.py --config-profile promoted_baseline
```

Do not interpret weekly economics until the clean window has realized exits in
`performance.db`.
