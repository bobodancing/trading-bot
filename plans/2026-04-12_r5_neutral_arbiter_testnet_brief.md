# R5 Neutral Arbiter Testnet Brief

Date: 2026-04-12

Status: deployment candidate brief. Do not push or deploy from this brief without Ruei approval.

Candidate: V54 + Neutral Arbiter only. Macro Overlay remains disabled.

## Decision Basis

- R4 true backtest passed for Neutral Arbiter as the next testnet candidate.
- Decision report: `reports/r4_true_backtest_neutral_arbiter.md`
- Decision artifact: `tools/Backtesting/results/r4_transition_true_20260412_fullsymbols/r4_true_summary_with_existing_a.csv`
- Full-symbol universe: BTC, ETH, SOL, DOGE, BNB, XRP.

Key R4 read:

| window | A: V54 alone | B: Neutral Arbiter | read |
|---|---:|---:|---|
| bull V-reversal | +0.4492%, PF 1.4884 | +0.4740%, PF 1.8451 | slight improvement |
| bear V-reversal | -0.5005%, PF 0.3371 | -0.5005%, PF 0.3371 | unchanged |
| trend-to-range fade | -0.0925%, PF 0.7761 | +0.2193%, PF 71.4656 | avoided fade cluster |
| range breakout | -0.3869%, PF 0.5281 | -0.2363%, PF 0.6469 | smaller loss |

Macro Overlay is not part of R5. It did not add value in three of four R4 windows, and its range-breakout benefit came from one small sample.

## R5 Config

Deploy the exact Neutral-only R4 candidate:

```python
REGIME_ARBITER_ENABLED = True
ARBITER_NEUTRAL_THRESHOLD = 0.50
ARBITER_NEUTRAL_EXIT_THRESHOLD = 0.50
ARBITER_NEUTRAL_MIN_BARS = 1
MACRO_OVERLAY_ENABLED = False
MACRO_STALLED_SIZE_MULT = 0.0
MACRO_WEEKLY_EMA_SPREAD_THRESHOLD = 0.015
```

Both `trader/config.py` and `bot_config.json` must carry these values. `REGIME_ARBITER_ENABLED` and the arbiter/macro keys are critical config parity keys, so do not rely on a remote-only JSON override unless the parity plan is explicitly reviewed.

## Guardrails

- V54 strategy logic stays frozen.
- RegimeEngine thresholds and hysteresis stay frozen.
- Arbiter gates new entries only; existing positions remain self-managed by their owning strategy.
- Position handover remains out of scope.
- Macro Overlay remains experimental and off.
- Do not use `BYPASS_CONFIG_PARITY=1` for R5 except for emergency diagnosis.
- Do not push, pull on rwUbuntu, restart services, or change live/testnet capital without Ruei approval.

## Local Acceptance

Before rwUbuntu deploy:

```bash
python scripts/config_parity_check.py --critical-only
python -m pytest trader/tests/test_regime_arbiter.py trader/tests/test_config_parity.py trader/tests/test_btc_trend_routing.py -q
python -m pytest trader/tests -q
```

Expected:

- Config parity critical issue count is 0.
- Focused arbiter/config/routing tests pass.
- Full `trader/tests` pass on Windows before push.

## rwUbuntu Deploy Checklist

Ruei executes after review and push:

```bash
ssh rwfunder@solita7y-andes.nord
cd /home/rwfunder/*/tradingbot/trading_bot
git fetch
git checkout feat/btc-atr-grid
git pull --ff-only
python -m pytest trader/tests/ -q
python scripts/config_parity_check.py --critical-only
```

Confirm runtime config after JSON load:

```bash
python - <<'PY'
from trader.config import Config
Config.load_from_json("bot_config.json")
print("REGIME_ARBITER_ENABLED", Config.REGIME_ARBITER_ENABLED)
print("ARBITER_NEUTRAL_THRESHOLD", Config.ARBITER_NEUTRAL_THRESHOLD)
print("ARBITER_NEUTRAL_EXIT_THRESHOLD", Config.ARBITER_NEUTRAL_EXIT_THRESHOLD)
print("ARBITER_NEUTRAL_MIN_BARS", Config.ARBITER_NEUTRAL_MIN_BARS)
print("MACRO_OVERLAY_ENABLED", Config.MACRO_OVERLAY_ENABLED)
PY
```

Expected output:

```text
REGIME_ARBITER_ENABLED True
ARBITER_NEUTRAL_THRESHOLD 0.5
ARBITER_NEUTRAL_EXIT_THRESHOLD 0.5
ARBITER_NEUTRAL_MIN_BARS 1
MACRO_OVERLAY_ENABLED False
```

Restart testnet services only after tests and config checks pass:

```bash
sudo systemctl restart trader.service
sudo systemctl restart scanner.service
sudo systemctl status trader.service --no-pager
sudo systemctl status scanner.service --no-pager
journalctl -u trader.service -n 200 --no-pager
```

## Post-Deploy Smoke Checks

Review logs for:

- Trader boot has no config parity failure.
- `REGIME_ARBITER_ENABLED=True` and `MACRO_OVERLAY_ENABLED=False` are visible in startup/config diagnostics if logged.
- No repeated `arbiter_snapshot_missing` blocks.
- Neutral blocks, when they occur, are explainable:
  - `low_regime_confidence:chop_trend_adx_falling`
  - `squeeze_freeze_new_entries`
- No position sync or order safety errors.
- Existing positions, if any, continue under their original strategy exits.

## Forward Sample Acceptance

Minimum sample:

- 7 to 14 days testnet observation before any live-capital decision.
- Prefer the R5 spec target of at least 4 weeks.
- Prefer at least 30 candidate signal/entry events if market activity allows. Do not force trades to satisfy the count.

Track:

- Entries opened by V54.
- Entries blocked by arbiter.
- Block reasons and confidence values.
- Winners missed by Neutral gating.
- Whether fade/chop clusters reduce versus V54-alone expectation.
- PF, trade count, realized R, and max drawdown versus contemporaneous backtest.
- Any `arbiter_snapshot_missing`, exchange sync, or order safety issue.

## Rollback

Fast rollback:

```python
REGIME_ARBITER_ENABLED = False
ARBITER_NEUTRAL_EXIT_THRESHOLD = 0.60
MACRO_OVERLAY_ENABLED = False
```

Apply the rollback in both `trader/config.py` and `bot_config.json`, pass config parity, then restart services. Prefer `git revert` of the R5 config commit if already committed and pushed.

Open positions do not require handover on rollback because the arbiter only controls new entries.
