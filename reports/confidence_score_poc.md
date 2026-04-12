# R0 Report C: Confidence Score POC

Spec only. Not for R0 execution. R1 implementation will revisit after 小波 + Ruei review.

Guardrail: this is a markdown design proposal only. It does not implement confidence scoring and does not modify `trader/regime.py`.

## Objective

A future arbiter confidence score should express how clean the current regime evidence is, not replace `RegimeEngine` labels during R0. The score should help distinguish clean trend, chop-trend, range, squeeze, and transition/neutral zones.

## Candidate Inputs

| input | proposed normalization | rationale |
|---|---|---|
| ADX absolute level | Bounded linear score against local bands, e.g. map below `REGIME_ADX_RANGING` toward range confidence and above `REGIME_ADX_TRENDING` toward trend confidence. Keep exact bands for R1 review. | Captures trend strength, but should not alone decide trend because Apr-May 2025 shows high-ADX chop-trend risk. |
| ADX slope | Categorical vote from rolling slope over recent 4H bars: rising, falling, flat. Normalize as {-1, 0, +1} or percentile of recent slope magnitude. | Falling ADX can flag trend fade even while ADX remains above the absolute threshold. |
| BBW percentile | Per-window primary percentile for R0 diagnostics; R1 may replace with rolling production percentile over `REGIME_BBW_HISTORY` or a longer BTC-only history. | Low BBW helps identify range/squeeze compression while avoiding absolute volatility assumptions. |
| ATR% (`atr / close`) | Ratio normalized by rolling percentile or z-score of recent ATR%. | Separates genuine volatility expansion from nominal ATR changes caused by BTC price level. |
| Regime persistence | Count consecutive bars in the current confirmed regime; normalize with a cap such as `min(bars / cap, 1.0)`. | High persistence increases confidence in stable regimes; low persistence after a flip should keep confidence muted. |

## Combination Strategy Options

| option | description | risk |
|---|---|---|
| Weighted sum | Convert each input into partial trend/range/squeeze/neutral scores, then compute a weighted average. | Easy to tune into hindsight bias; weights need review. |
| Minimum gate | Require all mandatory signals to clear minimum evidence before confidence rises. | Conservative but may create too much dead zone. |
| Vote / quorum | Let each input vote for TRENDING, RANGING, SQUEEZE, or NEUTRAL; confidence is vote share. | Interpretable, but ties and mixed signals need explicit policy. |
| Hybrid gate plus weighted score | Use hard safety gates for conflict cases, then weighted score inside the allowed bucket. | More robust, but more moving parts to test. |

R0 does not pick a winner.

## Edge Cases

- Warmup period: confidence should be low or unavailable until ADX, BBW, ATR, and persistence windows are populated.
- Missing data: confidence should degrade to neutral / unavailable, not silently pass entries.
- Regime just flipped: persistence should start low; arbiter may hold a neutral zone until confidence rebuilds.
- Ambiguous `_detect_regime` returns `None`: label may preserve previous regime, but confidence should reflect ambiguity instead of inheriting full confidence.
- Conflicting inputs: high ADX with collapsing BBW should probably become low-confidence TRENDING or NEUTRAL until R1 defines the rule.

## Open Questions For 小波 + Ruei

1. Should confidence be one scalar for the active label, or a vector such as `{TRENDING_UP, TRENDING_DOWN, RANGING, SQUEEZE, NEUTRAL}`?
2. Should ADX slope be measured over 3, 5, or 10 BTC 4H bars?
3. Should BBW percentile use `REGIME_BBW_HISTORY=50`, a longer BTC-only rolling window, or the per-window diagnostic percentile only for research reports?
4. Should regime persistence increase confidence symmetrically for TRENDING and RANGING, or should TRENDING fade faster when ADX slope turns down?
5. What confidence threshold creates `REGIME_NEUTRAL` in R1, and should it differ for opening new positions versus managing existing positions?
6. Should macro overlay confidence be merged into the same score or kept as a separate gate above the arbiter?
