# Runtime BTC Trend Filter Mode Review

Date: 2026-05-08
Status: `DIAGNOSTIC_DEFAULT_ENFORCE_SUPPORTED`

## Decision

`BTC_TREND_FILTER_ENABLED` is now explicit in StrategyRuntime:

- default runtime mode: `BTC_TREND_FILTER_RUNTIME_MODE = "diagnostic"`
- diagnostic mode records BTC trend filter decisions but does not block entries
  or change size
- enforce mode can block counter-trend entries when
  `BTC_COUNTER_TREND_MULT = 0.0`
- enforce mode can reduce risk when `0.0 < BTC_COUNTER_TREND_MULT < 1.0`

This avoids silently changing the promoted three-leg portfolio while removing
the prior ambiguity that the filter flag was enabled but unimplemented for
plugin entries.

## Runtime Boundary

No runtime promotion, scanner activation, strategy threshold change, credential
change, or service-state change is included.

Enabling `BTC_TREND_FILTER_RUNTIME_MODE = "enforce"` is a behavior change and
requires fresh review evidence before it should become a default.

## Verification

Focused tests:

```text
python -m pytest trader/tests/test_strategy_runtime_kernel.py trader/tests/test_risk_guard.py trader/tests/test_runtime_observability.py -q
```

Result:

```text
49 passed
```
