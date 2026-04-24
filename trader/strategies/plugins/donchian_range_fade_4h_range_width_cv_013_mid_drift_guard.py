"""Donchian child candidate that rejects drifting channels."""

from __future__ import annotations

import pandas as pd

from trader.strategies.plugins.donchian_range_fade_4h_range_width_cv_013 import (
    DonchianRangeFade4hRangeWidthCv013Strategy,
)


class DonchianRangeFade4hRangeWidthCv013MidDriftGuardStrategy(
    DonchianRangeFade4hRangeWidthCv013Strategy
):
    id = "donchian_range_fade_4h_range_width_cv_013_mid_drift_guard"
    version = "0.1.0"
    tags = DonchianRangeFade4hRangeWidthCv013Strategy.tags | {
        "mid_drift_guard",
        "structural_probe",
    }
    params_schema = DonchianRangeFade4hRangeWidthCv013Strategy.params_schema | {
        "mid_drift_ratio_max": "float",
    }

    def __init__(self, params=None):
        merged = {
            "range_width_cv_max": 0.13,
            "mid_drift_ratio_max": 0.10,
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
        tail = frame.tail(range_window)
        latest_width = float(tail["donchian_width"].iloc[-1])
        if latest_width <= 0:
            return {
                **state,
                "range_detected": False,
                "mid_drift_ratio": 0.0,
            }

        mid_drift_ratio = abs(
            float(tail["donchian_mid"].iloc[-1]) - float(tail["donchian_mid"].iloc[0])
        ) / latest_width
        mid_drift_ratio_max = float(self.params.get("mid_drift_ratio_max", 0.10))
        return {
            **state,
            "range_detected": bool(state["range_detected"]) and mid_drift_ratio <= mid_drift_ratio_max,
            "mid_drift_ratio": mid_drift_ratio,
            "mid_drift_ratio_max": mid_drift_ratio_max,
        }
