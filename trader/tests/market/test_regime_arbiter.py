import pandas as pd

from trader.arbiter import RegimeArbiter, RegimeSnapshot
from trader.config import Config


def _df_with_features(*, adx_values, bbw_last=0.7, atr_last=1.0):
    rows = len(adx_values)
    idx = pd.date_range("2025-04-01", periods=rows, freq="4h")
    bbw = [1.0] * (rows - 1) + [bbw_last]
    atr = [1.0] * (rows - 1) + [atr_last]
    return pd.DataFrame(
        {
            "close": [100.0] * rows,
            "adx": adx_values,
            "bbw": bbw,
            "atr": atr,
        },
        index=idx,
    )


def _trend_context(direction="LONG"):
    return {
        "source": "regime",
        "regime": "TRENDING",
        "detected": "TRENDING",
        "direction": direction,
        "reason": "regime_updated",
    }


def test_chop_trend_becomes_neutral_when_threshold_enabled(monkeypatch):
    monkeypatch.setattr(Config, "ARBITER_NEUTRAL_THRESHOLD", 0.5)
    monkeypatch.setattr(Config, "ARBITER_NEUTRAL_EXIT_THRESHOLD", 0.6)
    monkeypatch.setattr(Config, "ARBITER_NEUTRAL_MIN_BARS", 1)
    monkeypatch.setattr(Config, "MACRO_OVERLAY_ENABLED", False)
    df = _df_with_features(adx_values=[35] * 24 + [35, 34, 33, 31, 29, 26], bbw_last=0.7)

    snapshot = RegimeArbiter().evaluate(context=_trend_context(), df_4h=df)

    assert snapshot.label == "NEUTRAL"
    assert snapshot.entry_allowed is False
    assert snapshot.confidence == 0.35
    assert snapshot.reason == "low_regime_confidence:chop_trend_adx_falling"


def test_neutral_threshold_zero_keeps_diagnostic_gate_disabled(monkeypatch):
    monkeypatch.setattr(Config, "ARBITER_NEUTRAL_THRESHOLD", 0.0)
    monkeypatch.setattr(Config, "ARBITER_NEUTRAL_EXIT_THRESHOLD", 0.0)
    monkeypatch.setattr(Config, "MACRO_OVERLAY_ENABLED", False)
    df = _df_with_features(adx_values=[35] * 24 + [35, 34, 33, 31, 29, 26], bbw_last=0.7)

    snapshot = RegimeArbiter().evaluate(context=_trend_context(), df_4h=df)

    assert snapshot.label == "TRENDING_UP"
    assert snapshot.entry_allowed is True
    assert snapshot.confidence == 0.35


def test_squeeze_like_freezes_entries_without_regime_engine_threshold_change(monkeypatch):
    monkeypatch.setattr(Config, "ARBITER_NEUTRAL_THRESHOLD", 0.0)
    monkeypatch.setattr(Config, "MACRO_OVERLAY_ENABLED", False)
    df = _df_with_features(adx_values=[22, 22, 22, 22, 22, 22] * 9, bbw_last=0.2)

    snapshot = RegimeArbiter().evaluate(context=_trend_context(), df_4h=df)

    assert snapshot.label == "SQUEEZE"
    assert snapshot.entry_allowed is False
    assert snapshot.reason == "squeeze_freeze_new_entries"


def test_macro_overlay_blocks_opposite_trend_side_when_flag_enabled(monkeypatch):
    monkeypatch.setattr(Config, "MACRO_OVERLAY_ENABLED", True)
    snapshot = RegimeSnapshot(
        label="TRENDING_UP",
        confidence=0.85,
        direction="LONG",
        source_regime="TRENDING",
        detected="TRENDING",
        macro_state="MACRO_BULL",
        entry_allowed=True,
        reason="clean_trend",
    )

    arbiter = RegimeArbiter()

    assert arbiter.can_enter(snapshot, "LONG") == (True, "clean_trend")
    assert arbiter.can_enter(snapshot, "SHORT") == (
        False,
        "macro_overlay_blocked:bull_blocks_short",
    )
