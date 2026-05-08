# Cartridge Spec: donchian_range_fade_4h_range_width_cv_013_short

## Locked Spec

- id: donchian_range_fade_4h_range_width_cv_013_short
- scope: BTC/USDT, ETH/USDT, 4h, SHORT
- indicators: rsi_14, atr, Donchian high/low/mid/width, width_cv
- entry gate: detect a stable Donchian range with `range_width_cv_max = 0.13`,
  require at least one lower and upper boundary touch, require close at or
  above the upper ATR touch band, and require `rsi_14 > 60.0`
- stop hint: `entry_price + 1.5 * atr`
- regime: target_regime = RANGING
- off-regime entry suppression: central arbiter/router path remains in force;
  this plugin itself only validates geometric range structure

## Regime Declaration

- target_regime: RANGING
- rationale: the SHORT overlay fades upper-bound excursions inside the same
  structural Donchian range thesis as promoted Slot B LONG

## Out of Scope

- Slot A SHORT promotion
- changing runtime risk caps
- scanner universe activation
- threshold loosening after promotion
- direct order sizing or execution

## Promotion Evidence

- `reports/portfolio_ab_slot_b_short_promotion_gate.md`
- `reports/portfolio_a_b_short_ablation_research.md`
