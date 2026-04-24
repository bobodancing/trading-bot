"""Donchian child candidate with a soft touch-balance guard."""

from __future__ import annotations

import math
import pandas as pd

from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013 import (
    DonchianRangeFade4hRangeWidthCv013Strategy,
)


class DonchianRangeFade4hRangeWidthCv013TouchImbalanceGuardStrategy(
    DonchianRangeFade4hRangeWidthCv013Strategy
):
    id = "donchian_range_fade_4h_range_width_cv_013_touch_imbalance_guard"
    version = "0.1.0"
    tags = DonchianRangeFade4hRangeWidthCv013Strategy.tags | {
        "touch_imbalance_guard",
        "structural_probe",
    }
    params_schema = DonchianRangeFade4hRangeWidthCv013Strategy.params_schema | {
        "touch_imbalance_ratio_max": "float",
    }

    def __init__(self, params=None):
        merged = {
            "range_width_cv_max": 0.13,
            "touch_imbalance_ratio_max": 2.5,
        }
        if params:
            merged.update(dict(params))
        super().__init__(merged)

    def _range_state(
        self,
        frame: pd.DataFrame,
        *,
        range_window: int,
        range_width_cv_max: float,
        touch_atr_band: float,
        min_lower_touches: int,
        min_upper_touches: int,
    ) -> dict[str, int | float | bool]:
        state = super()._range_state(
            frame,
            range_window=range_window,
            range_width_cv_max=range_width_cv_max,
            touch_atr_band=touch_atr_band,
            min_lower_touches=min_lower_touches,
            min_upper_touches=min_upper_touches,
        )
        lower_touches = int(state["lower_touches"])
        upper_touches = int(state["upper_touches"])
        min_touches = min(lower_touches, upper_touches)
        touch_imbalance_ratio = (
            math.inf
            if min_touches <= 0
            else max(lower_touches, upper_touches) / min_touches
        )
        touch_imbalance_ratio_max = float(self.params.get("touch_imbalance_ratio_max", 2.5))
        return {
            **state,
            "range_detected": bool(state["range_detected"])
            and touch_imbalance_ratio <= touch_imbalance_ratio_max,
            "touch_imbalance_ratio": touch_imbalance_ratio,
            "touch_imbalance_ratio_max": touch_imbalance_ratio_max,
        }
