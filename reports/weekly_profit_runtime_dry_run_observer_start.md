# Runtime Dry-Run Observer Start Review

Date: 2026-05-18
Branch: `codex/post-promotion-control-20260430`
Status: `DRY_RUN_OBSERVER_STARTED`

## Executive Read

The Phase 3 clean-window dry-run observer is running against the promoted
BTC/ETH three-leg baseline. This is operational evidence collection only; it is
not live expectancy evidence and it does not authorize runtime-default changes,
scanner runtime-universe activation, or new strategy promotion.

## Runtime Boundary

| item | value |
| --- | --- |
| local process | `python trader/bot.py --dry-run` |
| observed PID at start review | `16560` |
| runtime mode | `dry_run=True` |
| exchange sandbox flag | `True` |
| runtime portfolio | promoted Slot A LONG + Slot B LONG + Slot B SHORT |
| fixed symbols | `BTC/USDT`, `ETH/USDT` |
| scanner symbols consumed by runtime | `False` |
| scanner universe enabled | `False` |
| router policy | `fail_closed` |

The startup log reports:

- fixed universe: `BTC/USDT`, `ETH/USDT`
- runtime enabled: `True`
- side filter: `both`
- regime arbiter: `True`
- regime router: `False`
- BTC trend filter mode: `diagnostic`
- portfolio: Slot A LONG / BTC 4h MACD, Slot B LONG / Donchian range fade,
  Slot B SHORT / Donchian range fade

## Initial Packet Review

Command:

```bash
python tools/runtime_weekly_control_packet.py --as-of 2026-05-18 --weeks 1 --config-profile promoted_baseline
```

Initial packet after observer start:

| metric | value |
| --- | ---: |
| runtime events | 33 |
| runtime events after promoted-baseline scope | 33 |
| runtime events dropped by scope | 0 |
| selected config snapshots | 1 |
| malformed runtime events | 0 |
| performance db trades | 0 |
| active positions snapshot | 0 |
| scanner symbols | 2 |
| execution failures | 0 |
| config drift events | 0 |
| unprotected position events | 0 |
| latest state | `continue` |

Interpretation:

- The observer is writing clean promoted-baseline events.
- No strategy has produced a ready entry yet.
- No dry-run trade has been opened or closed.
- `performance.db` exists, but the `trades` table currently has `0` rows.
- Weekly economics remain observe-only until realized exits exist.

## Known Startup Warning

Because no local `secrets.json` is present, the dry-run process uses placeholder
credentials. Startup therefore logs a Binance private-endpoint `401` while
checking hedge mode. The process continues, and the current evidence does not
show execution attempts, execution failures, positions, or orders.

This warning blocks full live-like credential validation. It does not block
public market-data observation or StrategyRuntime funnel collection.

## Expected Waiting Time

Minimum useful observation:

- `1` completed week for basic operational health:
  config scope, scanner boundary, cycle stability, drift, rejected entries,
  dry-run skips, and unprotected-position checks.

Practical participation read:

- `2-4` completed weeks to see whether promoted BTC/ETH actually produces
  entry-ready weeks under current market conditions.

Contract-grade weekly KPI read:

- `8` completed weeks for the rolling 8w packet gates to be meaningful.

Economic read:

- unknown until the first dry-run entry opens and later exits.
- If the promoted baseline remains silent, the phase can stay blocked even past
  1-2 weeks because `performance.db` will still have no realized exits.

Stop condition for this stage:

- If after `2-4` completed weeks there are still no entry-ready events or
  dry-run exits, treat this as a participation bottleneck and review whether the
  issue is market regime, signal strictness, data readiness, or operational
  credential/sandbox realism.

Promotion condition:

- none. This stage is evidence collection only.
