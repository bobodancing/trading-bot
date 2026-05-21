# Scanner V3 Shadow Universe Packet

Date: 2026-05-21
Branch: `codex/post-promotion-control-20260430`
Status: `STAGE_A_ONE_SHOT_SHADOW_PACKET`

## Executive Read

Scanner V3 Stage A produced a one-shot shadow-universe packet without feeding StrategyRuntime or changing runtime defaults.

This packet is observational only. It does not authorize symbol expansion, scanner runtime consumption, strategy promotion, threshold loosening, order execution, or risk sizing.

## Boundary Check

| item | value |
| --- | --- |
| runtime_selection_feeds_trading | `False` |
| baseline runtime symbols | `BTC/USDT, ETH/USDT` |
| use scanner symbols | `False` |
| scanner universe enabled | `False` |
| Slot A expansion | `False` |
| Slot B shadow diagnostics | `True` |

## Strategy Compatibility

| slot | promoted scope | shadow treatment |
| --- | --- | --- |
| Slot A LONG | `BTC/USDT` only | non-BTC symbols are not evaluated for Slot A |
| Slot B LONG | `BTC/USDT`, `ETH/USDT` runtime only | non-runtime linear USDT perpetuals get diagnostics only |
| Slot B SHORT | `BTC/USDT`, `ETH/USDT` runtime only | non-runtime linear USDT perpetuals get diagnostics only |

## Summary

| metric | value |
| --- | ---: |
| eligible symbols | 20 |
| shadow candidate rows | 36 |
| entry-ready shadow rows | 0 |
| near-setup rows | 1 |
| regime-compatible rows | 13 |
| eligible-only rows | 22 |
| eligible COIN rows | 14 |
| eligible non-COIN rows | 6 |
| excluded symbols | 200 |

## Top Eligible Symbols

| rank | symbol | asset class | contract | quote volume 24h | data ready |
| ---: | --- | --- | --- | ---: | --- |
| 1 | `BTC/USDT` | `COIN` | `PERPETUAL` | 8,520,080,773 | `True` |
| 2 | `ETH/USDT` | `COIN` | `PERPETUAL` | 6,319,922,084 | `True` |
| 3 | `ZEC/USDT` | `COIN` | `PERPETUAL` | 2,167,700,873 | `True` |
| 4 | `HYPE/USDT` | `COIN` | `PERPETUAL` | 1,618,477,480 | `True` |
| 5 | `SOL/USDT` | `COIN` | `PERPETUAL` | 1,520,796,263 | `True` |
| 6 | `CL/USDT` | `COMMODITY` | `TRADIFI_PERPETUAL` | 1,429,913,049 | `True` |
| 7 | `XAG/USDT` | `COMMODITY` | `TRADIFI_PERPETUAL` | 1,379,735,218 | `True` |
| 8 | `XAU/USDT` | `COMMODITY` | `TRADIFI_PERPETUAL` | 1,214,754,017 | `True` |
| 9 | `BSB/USDT` | `COIN` | `PERPETUAL` | 908,528,943 | `True` |
| 10 | `EDEN/USDT` | `COIN` | `PERPETUAL` | 643,609,056 | `True` |
| 11 | `FIDA/USDT` | `COIN` | `PERPETUAL` | 521,496,382 | `True` |
| 12 | `XRP/USDT` | `COIN` | `PERPETUAL` | 458,581,335 | `True` |
| 13 | `BZ/USDT` | `COMMODITY` | `TRADIFI_PERPETUAL` | 374,292,742 | `True` |
| 14 | `PLAY/USDT` | `COIN` | `PERPETUAL` | 363,255,048 | `True` |
| 15 | `DOGE/USDT` | `COIN` | `PERPETUAL` | 358,420,600 | `True` |
| 16 | `SUI/USDT` | `COIN` | `PERPETUAL` | 268,741,751 | `True` |
| 17 | `SNDK/USDT` | `EQUITY` | `TRADIFI_PERPETUAL` | 253,969,482 | `True` |
| 18 | `MU/USDT` | `EQUITY` | `TRADIFI_PERPETUAL` | 242,672,906 | `True` |
| 19 | `BNB/USDT` | `COIN` | `PERPETUAL` | 215,018,103 | `True` |
| 20 | `TON/USDT` | `COIN` | `PERPETUAL` | 214,910,354 | `True` |

## Watchlist Availability

| symbol | asset class | contract | quote volume 24h | data ready | in top eligible | reason codes |
| --- | --- | --- | ---: | --- | --- | --- |
| `SOL/USDT` | `COIN` | `PERPETUAL` | 1,520,796,263 | `True` | `True` | `none` |
| `BNB/USDT` | `COIN` | `PERPETUAL` | 215,018,103 | `True` | `True` | `none` |
| `XRP/USDT` | `COIN` | `PERPETUAL` | 458,581,335 | `True` | `True` | `none` |
| `ADA/USDT` | `COIN` | `PERPETUAL` | 122,841,352 | `True` | `False` | `none` |
| `LINK/USDT` | `COIN` | `PERPETUAL` | 99,260,118 | `True` | `False` | `none` |

## Top Shadow Candidates

| symbol | side | asset class | class | reason codes | width CV | RSI |
| --- | --- | --- | --- | --- | ---: | ---: |
| `ZEC/USDT` | `LONG` | `COIN` | `eligible_only` | `range_not_detected, not_near_lower_band, rsi_not_ready` | 0.3179 | 80.2228 |
| `ZEC/USDT` | `SHORT` | `COIN` | `eligible_only` | `range_not_detected, not_near_upper_band` | 0.3179 | 80.2228 |
| `HYPE/USDT` | `LONG` | `COIN` | `eligible_only` | `range_not_detected, not_near_lower_band, rsi_not_ready` | 0.1423 | 80.7148 |
| `HYPE/USDT` | `SHORT` | `COIN` | `eligible_only` | `range_not_detected` | 0.1423 | 80.7148 |
| `SOL/USDT` | `LONG` | `COIN` | `eligible_only` | `range_not_detected, not_near_lower_band, rsi_not_ready` | 0.3045 | 50.9733 |
| `SOL/USDT` | `SHORT` | `COIN` | `eligible_only` | `range_not_detected, not_near_upper_band, rsi_not_ready` | 0.3045 | 50.9733 |
| `CL/USDT` | `LONG` | `COMMODITY` | `near_setup` | `not_near_lower_band` | 0.1030 | 36.4261 |
| `CL/USDT` | `SHORT` | `COMMODITY` | `regime_compatible` | `not_near_upper_band, rsi_not_ready` | 0.1030 | 36.4261 |
| `XAG/USDT` | `LONG` | `COMMODITY` | `regime_compatible` | `not_near_lower_band, rsi_not_ready` | 0.0657 | 47.4377 |
| `XAG/USDT` | `SHORT` | `COMMODITY` | `regime_compatible` | `not_near_upper_band, rsi_not_ready` | 0.0657 | 47.4377 |
| `XAU/USDT` | `LONG` | `COMMODITY` | `regime_compatible` | `not_near_lower_band, rsi_not_ready` | 0.0961 | 52.0178 |
| `XAU/USDT` | `SHORT` | `COMMODITY` | `regime_compatible` | `not_near_upper_band, rsi_not_ready` | 0.0961 | 52.0178 |
| `BSB/USDT` | `LONG` | `COIN` | `eligible_only` | `range_not_detected, not_near_lower_band, rsi_not_ready` | 0.7542 | 56.6095 |
| `BSB/USDT` | `SHORT` | `COIN` | `eligible_only` | `range_not_detected, not_near_upper_band, rsi_not_ready` | 0.7542 | 56.6095 |
| `EDEN/USDT` | `LONG` | `COIN` | `eligible_only` | `range_not_detected, not_near_lower_band, rsi_not_ready` | 0.3219 | 80.2017 |
| `EDEN/USDT` | `SHORT` | `COIN` | `eligible_only` | `range_not_detected, not_near_upper_band` | 0.3219 | 80.2017 |
| `FIDA/USDT` | `LONG` | `COIN` | `eligible_only` | `range_not_detected, not_near_lower_band, rsi_not_ready` | 0.2969 | 75.7412 |
| `FIDA/USDT` | `SHORT` | `COIN` | `eligible_only` | `range_not_detected, not_near_upper_band` | 0.2969 | 75.7412 |
| `XRP/USDT` | `LONG` | `COIN` | `eligible_only` | `range_not_detected, not_near_lower_band` | 0.1469 | 39.8848 |
| `XRP/USDT` | `SHORT` | `COIN` | `eligible_only` | `range_not_detected, not_near_upper_band, rsi_not_ready` | 0.1469 | 39.8848 |
| `BZ/USDT` | `LONG` | `COMMODITY` | `eligible_only` | `range_not_detected, not_near_lower_band` | 0.2230 | 32.6673 |
| `BZ/USDT` | `SHORT` | `COMMODITY` | `eligible_only` | `range_not_detected, not_near_upper_band, rsi_not_ready` | 0.2230 | 32.6673 |
| `PLAY/USDT` | `LONG` | `COIN` | `eligible_only` | `range_not_detected, not_near_lower_band, rsi_not_ready` | 0.4067 | 40.9202 |
| `PLAY/USDT` | `SHORT` | `COIN` | `eligible_only` | `range_not_detected, not_near_upper_band, rsi_not_ready` | 0.4067 | 40.9202 |
| `DOGE/USDT` | `LONG` | `COIN` | `regime_compatible` | `range_not_detected, not_near_lower_band` | 0.0660 | 37.7477 |
| `DOGE/USDT` | `SHORT` | `COIN` | `regime_compatible` | `range_not_detected, not_near_upper_band, rsi_not_ready` | 0.0660 | 37.7477 |
| `SUI/USDT` | `LONG` | `COIN` | `eligible_only` | `range_not_detected, not_near_lower_band, rsi_not_ready` | 0.1411 | 52.3515 |
| `SUI/USDT` | `SHORT` | `COIN` | `eligible_only` | `range_not_detected, not_near_upper_band, rsi_not_ready` | 0.1411 | 52.3515 |
| `SNDK/USDT` | `LONG` | `EQUITY` | `regime_compatible` | `not_near_lower_band, rsi_not_ready` | 0.0391 | 52.2618 |
| `SNDK/USDT` | `SHORT` | `EQUITY` | `regime_compatible` | `not_near_upper_band, rsi_not_ready` | 0.0391 | 52.2618 |

## Baseline Slot B Diagnostics

| symbol | side | class | reason codes | rows 4h |
| --- | --- | --- | --- | ---: |
| `BTC/USDT` | `LONG` | `eligible_only` | `range_not_detected, not_near_lower_band, rsi_not_ready` | 200 |
| `BTC/USDT` | `SHORT` | `eligible_only` | `range_not_detected, not_near_upper_band, rsi_not_ready` | 200 |
| `ETH/USDT` | `LONG` | `eligible_only` | `range_not_detected, not_near_lower_band, rsi_not_ready` | 200 |
| `ETH/USDT` | `SHORT` | `eligible_only` | `range_not_detected, not_near_upper_band, rsi_not_ready` | 200 |

## Reason-Code Distribution

| source | reason | count |
| --- | --- | ---: |
| shadow candidate | `not_near_lower_band` | 18 |
| shadow candidate | `not_near_upper_band` | 17 |
| shadow candidate | `range_not_detected` | 26 |
| shadow candidate | `rsi_not_ready` | 28 |
| exclusion | `excluded_symbol` | 1 |
| exclusion | `low_volume` | 192 |
| exclusion | `not_linear_usdt_contract` | 23 |
| exclusion | `quote_not_usdt` | 23 |

## Interpretation

- Stage A proves the shadow scanner can separate baseline BTC/ETH diagnostics from non-runtime shadow symbols.
- Economic value is not evaluated here; that requires Stage C historical replay and holdout review.
- Runtime selection remains fixed on the promoted BTC/ETH baseline.
