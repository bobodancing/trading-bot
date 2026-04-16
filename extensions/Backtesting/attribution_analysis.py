#!/usr/bin/env python3
"""
Attribution analysis for baseline changes.

This complements compare_baselines.py by trying to explain *why* entries
shifted between two runs:
    - same-signal retiming
    - filter/context delays
    - signal disappearance
    - same-timestamp retyping to another signal type
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
from pandas.errors import EmptyDataError


ENTRY_KEY_COLS = ["timestamp", "symbol", "signal_type"]
TRADE_KEY_COLS = ["entry_time", "symbol", "signal_type"]
REJECT_REASON_TO_CATEGORY = {
    "trend_filter": "trend_change",
    "tier_filter": "tier_or_mtf_change",
    "market_filter": "market_filter_change",
    "btc_trend_ranging": "btc_context_change",
    "btc_counter_trend_blocked": "btc_context_change",
    "regime_ranging": "regime_change",
    "regime_squeeze": "regime_change",
    "regime_trending_grid_active": "regime_change",
    "no_signal_detected": "signal_disappeared",
    "cooldown": "cooldown",
    "direction_filter": "direction_filter",
}
DELAY_CATEGORY_MAP = {
    "trend_change": "trend_delay",
    "tier_or_mtf_change": "tier_or_mtf_delay",
    "market_filter_change": "market_filter_delay",
    "btc_context_change": "btc_context_delay",
    "regime_change": "regime_delay",
    "signal_disappeared": "signal_delay",
    "cooldown": "cooldown_delay",
    "direction_filter": "direction_delay",
}
REJECT_PRIORITY = {
    "regime_change": 1,
    "btc_context_change": 2,
    "trend_change": 3,
    "tier_or_mtf_change": 4,
    "market_filter_change": 5,
    "signal_disappeared": 6,
    "cooldown": 7,
    "direction_filter": 8,
}


@dataclass
class MatchResult:
    after_idx: Optional[int]
    delta_hours: Optional[float]


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_csv(path: Path, ts_cols: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(path)
    except EmptyDataError:
        return pd.DataFrame()
    for col in ts_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    return df


def load_baseline_dir(path: Path) -> dict:
    return {
        "summary": _load_json(path / "summary.json"),
        "audit": _load_json(path / "signal_audit_summary.json"),
        "entries": _ensure_columns(
            _load_csv(path / "signal_entries.csv", ["timestamp"]),
            [
                "timestamp", "symbol", "signal_type", "signal_tier", "tier_score",
                "mtf_aligned", "mtf_reason", "mtf_status", "tier_component_mtf",
                "tier_component_market", "tier_component_volume", "tier_component_candle",
                "signal_candle_time", "trend_candle_time", "mtf_candle_time",
            ],
        ),
        "rejects": _ensure_columns(
            _load_csv(path / "signal_rejects.csv", ["timestamp"]),
            [
                "timestamp", "symbol", "stage", "reject_reason", "signal_type", "detail",
                "signal_tier", "tier_min", "tier_score", "mtf_aligned", "mtf_reason",
                "mtf_status", "tier_component_mtf", "tier_component_market",
                "tier_component_volume", "tier_component_candle", "signal_candle_time",
                "trend_candle_time", "mtf_candle_time",
            ],
        ),
        "trades": _ensure_columns(
            _load_csv(path / "trades.csv", ["entry_time", "exit_time"]),
            ["entry_time", "exit_time", "symbol", "signal_type", "pnl_usdt"],
        ),
    }


def _ensure_columns(df: pd.DataFrame, required: list[str]) -> pd.DataFrame:
    out = df.copy()
    for col in required:
        if col not in out.columns:
            out[col] = pd.Series(dtype="object")
    return out


def _entry_key(df: pd.DataFrame) -> pd.Series:
    return df[ENTRY_KEY_COLS].apply(tuple, axis=1)


def _trade_key(df: pd.DataFrame) -> pd.Series:
    return df[TRADE_KEY_COLS].apply(tuple, axis=1)


def _trade_lookup(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {}
    keyed = trades.copy()
    keyed["trade_key"] = _trade_key(keyed)
    return keyed.drop_duplicates("trade_key").set_index("trade_key").to_dict("index")


def _pick_best_reject(
    rejects: pd.DataFrame,
    *,
    signal_type: str,
) -> Optional[pd.Series]:
    if rejects.empty:
        return None

    scoped = rejects.copy()
    if "signal_type" in scoped.columns:
        mask = scoped["signal_type"].isna() | (scoped["signal_type"] == signal_type)
        scoped = scoped[mask]
        if scoped.empty:
            scoped = rejects.copy()

    def reject_rank(reason: object) -> int:
        category = REJECT_REASON_TO_CATEGORY.get(str(reason), "other")
        return REJECT_PRIORITY.get(category, 99)

    scoped["_rank"] = scoped["reject_reason"].map(reject_rank)
    return scoped.sort_values(["_rank", "stage"]).iloc[0]


def _find_nearest_after_entry(
    before_row: pd.Series,
    after_candidates: pd.DataFrame,
    *,
    used_after_indices: set[int],
    window_hours: float,
) -> MatchResult:
    if after_candidates.empty:
        return MatchResult(None, None)

    scoped = after_candidates.loc[~after_candidates.index.isin(used_after_indices)].copy()
    if scoped.empty:
        return MatchResult(None, None)

    scoped["delta_hours"] = (
        scoped["timestamp"] - before_row["timestamp"]
    ).dt.total_seconds() / 3600.0
    scoped["abs_delta_hours"] = scoped["delta_hours"].abs()
    scoped = scoped[scoped["abs_delta_hours"] <= window_hours]
    if scoped.empty:
        return MatchResult(None, None)

    scoped = scoped.sort_values(["abs_delta_hours", "delta_hours", "timestamp"])
    best = scoped.iloc[0]
    return MatchResult(int(best.name), float(best["delta_hours"]))


def analyze_baselines(
    before_dir: Path,
    after_dir: Path,
    *,
    window_hours: float = 36.0,
) -> dict:
    before = load_baseline_dir(before_dir)
    after = load_baseline_dir(after_dir)

    entries_before = before["entries"].copy()
    entries_after = after["entries"].copy()
    rejects_after = after["rejects"].copy()
    trades_before_lookup = _trade_lookup(before["trades"])
    trades_after_lookup = _trade_lookup(after["trades"])

    if entries_before.empty:
        return {
            "rows": pd.DataFrame(),
            "summary": {
                "before_dir": str(before_dir),
                "after_dir": str(after_dir),
                "window_hours": window_hours,
                "message": "Missing entries csv in one or both dirs",
            },
        }

    entries_before["entry_key"] = _entry_key(entries_before)
    entries_after["entry_key"] = _entry_key(entries_after)

    before_only = entries_before.loc[~entries_before["entry_key"].isin(entries_after["entry_key"])].copy()
    after_only = entries_after.loc[~entries_after["entry_key"].isin(entries_before["entry_key"])].copy()

    used_after_indices: set[int] = set()
    rows: list[dict] = []

    for _, before_row in before_only.sort_values("timestamp").iterrows():
        symbol = before_row["symbol"]
        signal_type = before_row["signal_type"]
        same_type_after = after_only[
            (after_only["symbol"] == symbol) & (after_only["signal_type"] == signal_type)
        ]
        match = _find_nearest_after_entry(
            before_row,
            same_type_after,
            used_after_indices=used_after_indices,
            window_hours=window_hours,
        )
        if match.after_idx is not None:
            used_after_indices.add(match.after_idx)
            matched_after_row = after_only.loc[match.after_idx]
        else:
            matched_after_row = None

        same_time_rejects = rejects_after[
            (rejects_after["symbol"] == symbol) &
            (rejects_after["timestamp"] == before_row["timestamp"])
        ]
        best_reject = _pick_best_reject(same_time_rejects, signal_type=signal_type)
        reject_reason = None if best_reject is None else str(best_reject["reject_reason"])
        reject_category = None if reject_reason is None else REJECT_REASON_TO_CATEGORY.get(reject_reason, "other")

        same_time_other_type = after_only[
            (after_only["symbol"] == symbol) &
            (after_only["timestamp"] == before_row["timestamp"]) &
            (after_only["signal_type"] != signal_type)
        ]

        if matched_after_row is not None:
            if reject_category in DELAY_CATEGORY_MAP:
                attribution = DELAY_CATEGORY_MAP[reject_category]
            else:
                attribution = "retimed_same_signal"
        elif not same_time_other_type.empty:
            attribution = f"retyped_to_{same_time_other_type.iloc[0]['signal_type'].lower()}"
        elif reject_category is not None:
            attribution = reject_category
        else:
            attribution = "signal_disappeared_unexplained"

        before_trade = trades_before_lookup.get(
            (before_row["timestamp"], symbol, signal_type),
            {},
        )
        after_trade = {}
        if matched_after_row is not None:
            after_trade = trades_after_lookup.get(
                (matched_after_row["timestamp"], symbol, signal_type),
                {},
            )

        row = {
            "symbol": symbol,
            "signal_type": signal_type,
            "before_timestamp": before_row["timestamp"],
            "after_timestamp": None if matched_after_row is None else matched_after_row["timestamp"],
            "delta_hours": match.delta_hours,
            "attribution": attribution,
            "after_same_time_reject_reason": reject_reason,
            "after_same_time_reject_stage": None if best_reject is None else best_reject.get("stage"),
            "after_same_time_reject_detail": None if best_reject is None else best_reject.get("detail"),
            "before_signal_tier": before_row.get("signal_tier"),
            "after_signal_tier": None if matched_after_row is None else matched_after_row.get("signal_tier"),
            "before_tier_score": before_row.get("tier_score"),
            "after_tier_score": None if matched_after_row is None else matched_after_row.get("tier_score"),
            "after_same_time_tier_score": None if best_reject is None else best_reject.get("tier_score"),
            "after_same_time_tier_min": None if best_reject is None else best_reject.get("tier_min"),
            "before_mtf_status": before_row.get("mtf_status"),
            "after_mtf_status": None if matched_after_row is None else matched_after_row.get("mtf_status"),
            "after_same_time_mtf_status": None if best_reject is None else best_reject.get("mtf_status"),
            "before_mtf_reason": before_row.get("mtf_reason"),
            "after_mtf_reason": None if matched_after_row is None else matched_after_row.get("mtf_reason"),
            "after_same_time_mtf_reason": None if best_reject is None else best_reject.get("mtf_reason"),
            "same_time_retyped_to": None if same_time_other_type.empty else same_time_other_type.iloc[0]["signal_type"],
            "before_pnl_usdt": before_trade.get("pnl_usdt"),
            "after_pnl_usdt": after_trade.get("pnl_usdt"),
        }
        rows.append(row)

    result_df = pd.DataFrame(rows)
    summary = {
        "before_dir": str(before_dir),
        "after_dir": str(after_dir),
        "window_hours": window_hours,
        "before_only_entries": int(len(before_only)),
        "after_only_entries": int(len(after_only)),
    }

    if not result_df.empty:
        summary["attribution_counts"] = result_df["attribution"].value_counts().to_dict()
        summary["signal_type_counts"] = result_df["signal_type"].value_counts().to_dict()

        matched = result_df[result_df["after_timestamp"].notna()].copy()
        if not matched.empty:
            summary["matched_entries"] = int(len(matched))
            summary["matched_delta_hours"] = {
                "mean": round(float(matched["delta_hours"].mean()), 3),
                "median": round(float(matched["delta_hours"].median()), 3),
                "within_8h": int((matched["delta_hours"].abs() <= 8).sum()),
                "within_24h": int((matched["delta_hours"].abs() <= 24).sum()),
            }
            if matched["before_pnl_usdt"].notna().any() and matched["after_pnl_usdt"].notna().any():
                pnl_diff = matched["after_pnl_usdt"].fillna(0.0) - matched["before_pnl_usdt"].fillna(0.0)
                summary["matched_trade_pnl_shift"] = {
                    "before_total": round(float(matched["before_pnl_usdt"].fillna(0.0).sum()), 3),
                    "after_total": round(float(matched["after_pnl_usdt"].fillna(0.0).sum()), 3),
                    "delta_total": round(float(pnl_diff.sum()), 3),
                }

        pnl_scoped = result_df.dropna(subset=["before_pnl_usdt"]).copy()
        if not pnl_scoped.empty:
            top_lost = pnl_scoped.sort_values("before_pnl_usdt", ascending=False).head(10)
            summary["top_before_pnl_rows"] = [
                {
                    "symbol": row["symbol"],
                    "signal_type": row["signal_type"],
                    "before_timestamp": row["before_timestamp"].isoformat(),
                    "attribution": row["attribution"],
                    "before_pnl_usdt": round(float(row["before_pnl_usdt"]), 3),
                    "after_pnl_usdt": None if pd.isna(row["after_pnl_usdt"]) else round(float(row["after_pnl_usdt"]), 3),
                }
                for _, row in top_lost.iterrows()
            ]

    return {"rows": result_df, "summary": summary}


def render_report(summary: dict, rows: pd.DataFrame) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("ATTRIBUTION ANALYSIS")
    lines.append("=" * 70)
    lines.append(f"Before: {summary.get('before_dir', '')}")
    lines.append(f"After:  {summary.get('after_dir', '')}")
    lines.append(f"Window: {summary.get('window_hours', 0)} hours")
    lines.append("")
    lines.append(f"Before-only entries: {summary.get('before_only_entries', 0)}")
    lines.append(f"After-only entries:  {summary.get('after_only_entries', 0)}")

    counts = summary.get("attribution_counts", {})
    if counts:
        lines.append("")
        lines.append("Attribution counts:")
        for key, value in counts.items():
            lines.append(f"  {key:<28} {value:>5}")

    deltas = summary.get("matched_delta_hours", {})
    if deltas:
        lines.append("")
        lines.append("Matched retime stats:")
        lines.append(f"  mean delta hours:   {deltas.get('mean', 0)}")
        lines.append(f"  median delta hours: {deltas.get('median', 0)}")
        lines.append(f"  within 8h:          {deltas.get('within_8h', 0)}")
        lines.append(f"  within 24h:         {deltas.get('within_24h', 0)}")

    pnl_shift = summary.get("matched_trade_pnl_shift", {})
    if pnl_shift:
        lines.append("")
        lines.append("Matched trade pnl shift:")
        lines.append(f"  before total: {pnl_shift.get('before_total', 0)}")
        lines.append(f"  after total:  {pnl_shift.get('after_total', 0)}")
        lines.append(f"  delta total:  {pnl_shift.get('delta_total', 0)}")

    top_rows = summary.get("top_before_pnl_rows", [])
    if top_rows:
        lines.append("")
        lines.append("Top before-pnl rows:")
        for row in top_rows[:10]:
            lines.append(
                "  "
                f"{row['before_timestamp']}  {row['symbol']:<10}  {row['signal_type']:<16}  "
                f"{row['before_pnl_usdt']:>8} -> {str(row['after_pnl_usdt']):>8}  "
                f"{row['attribution']}"
            )

    if not rows.empty:
        lines.append("")
        lines.append("Sample attributed rows:")
        sample = rows.sort_values(
            ["attribution", "signal_type", "before_timestamp"]
        ).head(15)
        for _, row in sample.iterrows():
            after_ts = "n/a" if pd.isna(row["after_timestamp"]) else row["after_timestamp"].isoformat()
            delta_h = "n/a" if pd.isna(row["delta_hours"]) else f"{row['delta_hours']:.1f}"
            lines.append(
                "  "
                f"{row['before_timestamp'].isoformat()}  {row['symbol']:<10}  {row['signal_type']:<16}  "
                f"{after_ts:<25}  dh={delta_h:<6}  {row['attribution']}"
            )

    return "\n".join(lines)


def save_analysis(result: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    rows = result["rows"]
    if not rows.empty:
        save_rows = rows.copy()
        for col in ["before_timestamp", "after_timestamp"]:
            if col in save_rows.columns:
                save_rows[col] = save_rows[col].apply(
                    lambda v: "" if pd.isna(v) else pd.Timestamp(v).isoformat()
                )
        save_rows.to_csv(output_dir / "entry_attribution.csv", index=False)
    else:
        pd.DataFrame().to_csv(output_dir / "entry_attribution.csv", index=False)

    with open(output_dir / "attribution_summary.json", "w", encoding="utf-8") as f:
        json.dump(result["summary"], f, indent=2, ensure_ascii=False, default=str)

    report = render_report(result["summary"], rows)
    (output_dir / "attribution_report.txt").write_text(report, encoding="utf-8")


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: python attribution_analysis.py <before_dir> <after_dir> [--output <dir>] [--window-hours <n>]")
        return 1

    before_dir = Path(sys.argv[1])
    after_dir = Path(sys.argv[2])
    output_dir: Optional[Path] = None
    window_hours = 36.0

    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_dir = Path(sys.argv[idx + 1])

    if "--window-hours" in sys.argv:
        idx = sys.argv.index("--window-hours")
        if idx + 1 < len(sys.argv):
            window_hours = float(sys.argv[idx + 1])

    result = analyze_baselines(before_dir, after_dir, window_hours=window_hours)
    report = render_report(result["summary"], result["rows"])
    print(report)

    if output_dir is not None:
        save_analysis(result, output_dir)
        print(f"\n[Saved] {output_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
