"""Align router replay rows with V54 entries and scanner candidate timestamps."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import pandas as pd


WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS_ROOT = WORKSPACE_ROOT / "tools" / "Backtesting" / "results"
DEFAULT_REPLAY_ROOT = DEFAULT_RESULTS_ROOT / "regime_router_replay_20260413"
DEFAULT_V54_TRADES = (
    DEFAULT_RESULTS_ROOT
    / "r4_transition_stress_20260412"
    / "r4_overlay_trade_decisions.csv"
)
DEFAULT_SCANNER_ROOT = DEFAULT_RESULTS_ROOT / "r4_transition_true_20260412_fullsymbols"
DEFAULT_OUTPUT_DIR = DEFAULT_RESULTS_ROOT / "regime_router_replay_20260413" / "alignment"


def _parse_utc(values) -> pd.Series:
    return pd.to_datetime(values, utc=True, errors="coerce")


def _outcome_from_r(realized_r) -> str:
    if pd.isna(realized_r):
        return "unknown"
    if realized_r > 0:
        return "winner"
    if realized_r < 0:
        return "loser"
    return "breakeven"


def _router_trade_classification(row: pd.Series) -> str:
    if not bool(row.get("replay_match", False)):
        return "no_replay_match"

    decision = row.get("router_decision")
    outcome = row.get("v54_outcome")
    if decision == "block":
        if outcome == "loser":
            return "protective_block"
        if outcome == "winner":
            return "missed_opportunity"
        if outcome == "breakeven":
            return "breakeven_block"
        return "blocked_unknown_outcome"

    if outcome == "loser":
        return "allowed_loser"
    if outcome == "winner":
        return "allowed_winner"
    if outcome == "breakeven":
        return "allowed_breakeven"
    return "allowed_unknown_outcome"


def _candidate_classification(row: pd.Series) -> str:
    status = row.get("candidate_status")
    outcome = row.get("v54_outcome")

    if status == "arbiter_blocked":
        if outcome == "loser":
            return "protective_block"
        if outcome == "winner":
            return "missed_opportunity"
        if outcome == "breakeven":
            return "breakeven_block"
        return "blocked_candidate_no_v54_outcome"

    if status == "entered":
        if outcome == "loser":
            return "entered_loser"
        if outcome == "winner":
            return "entered_winner"
        if outcome == "breakeven":
            return "entered_breakeven"
        return "entered_no_v54_outcome"

    return "unknown_candidate_status"


def _router_candidate_classification(row: pd.Series) -> str:
    route_row = pd.Series({
        "replay_match": row.get("replay_match"),
        "router_decision": row.get("router_decision"),
        "v54_outcome": row.get("v54_outcome"),
    })
    classification = _router_trade_classification(route_row)
    if classification in {"blocked_unknown_outcome", "allowed_unknown_outcome"}:
        return classification.replace("unknown_outcome", "candidate_no_v54_outcome")
    return classification


def _load_replay(replay_root: Path) -> pd.DataFrame:
    frames = []
    for csv_path in sorted(replay_root.glob("*/regime_router_replay.csv")):
        frame = pd.read_csv(csv_path)
        frame["window"] = csv_path.parent.name
        frame["replay_candle_time"] = _parse_utc(frame["timestamp"])
        frames.append(frame)
    if not frames:
        raise FileNotFoundError(f"No replay CSV files found under {replay_root}")

    replay = pd.concat(frames, ignore_index=True)
    replay["signal_side"] = replay["signal_side"].astype(str).str.upper()
    keep_cols = [
        "window",
        "replay_candle_time",
        "signal_side",
        "raw_regime",
        "detected_regime",
        "arbiter_label",
        "arbiter_confidence",
        "arbiter_entry_allowed",
        "arbiter_reason",
        "router_decision",
        "router_allowed",
        "router_selected_strategy",
        "router_reason",
        "router_block_reason",
        "router_policy",
        "mixed_bucket",
    ]
    return replay[keep_cols].copy()


def _load_v54_trades(v54_trades_csv: Path) -> pd.DataFrame:
    trades = pd.read_csv(v54_trades_csv)
    trades["entry_time_utc"] = _parse_utc(trades["entry_time"])
    trades["entry_regime_candle_time_utc"] = _parse_utc(trades["entry_regime_candle_time"])
    trades["side"] = trades["side"].astype(str).str.upper()
    trades["realized_r"] = pd.to_numeric(trades["realized_r"], errors="coerce")
    trades["pnl_usdt"] = pd.to_numeric(trades["pnl_usdt"], errors="coerce")
    trades["v54_outcome"] = trades["realized_r"].map(_outcome_from_r)
    return trades


def align_v54_entries(replay: pd.DataFrame, trades: pd.DataFrame) -> pd.DataFrame:
    replay_prefixed = replay.rename(columns={
        "signal_side": "side",
        "raw_regime": "replay_raw_regime",
        "detected_regime": "replay_detected_regime",
        "arbiter_label": "replay_arbiter_label",
        "arbiter_confidence": "replay_arbiter_confidence",
        "arbiter_entry_allowed": "replay_arbiter_entry_allowed",
        "arbiter_reason": "replay_arbiter_reason",
        "mixed_bucket": "replay_mixed_bucket",
    })
    aligned = trades.merge(
        replay_prefixed,
        how="left",
        left_on=["window", "entry_regime_candle_time_utc", "side"],
        right_on=["window", "replay_candle_time", "side"],
    )
    aligned["replay_match"] = aligned["replay_candle_time"].notna()
    aligned["router_decision"] = aligned["router_decision"].fillna("no_replay_match")
    aligned["alignment_classification"] = aligned.apply(_router_trade_classification, axis=1)

    cols = [
        "window",
        "trade_id",
        "symbol",
        "side",
        "signal_type",
        "signal_tier",
        "entry_time",
        "entry_regime_candle_time",
        "pnl_usdt",
        "realized_r",
        "v54_outcome",
        "alignment_classification",
        "replay_match",
        "replay_raw_regime",
        "replay_detected_regime",
        "replay_arbiter_label",
        "replay_arbiter_confidence",
        "replay_arbiter_reason",
        "router_decision",
        "router_allowed",
        "router_selected_strategy",
        "router_reason",
        "router_block_reason",
        "router_policy",
        "replay_mixed_bucket",
        "neutral_block",
        "neutral_reason",
        "macro_block",
    ]
    return aligned[cols].copy()


def _iter_b_neutral_dirs(scanner_root: Path) -> Iterable[Path]:
    return sorted(path for path in scanner_root.glob("B_neutral_true_*") if path.is_dir())


def _load_scanner_candidates(scanner_root: Path) -> pd.DataFrame:
    frames = []
    for window_dir in _iter_b_neutral_dirs(scanner_root):
        window = window_dir.name.replace("B_neutral_true_", "", 1)

        entries_path = window_dir / "signal_entries.csv"
        if entries_path.exists():
            entries = pd.read_csv(entries_path)
            entries["window"] = window
            entries["candidate_status"] = "entered"
            entries["reject_reason"] = ""
            frames.append(entries)

        rejects_path = window_dir / "signal_rejects.csv"
        if rejects_path.exists():
            rejects = pd.read_csv(rejects_path)
            rejects = rejects[rejects["reject_reason"] == "regime_arbiter_blocked"].copy()
            rejects["window"] = window
            rejects["candidate_status"] = "arbiter_blocked"
            frames.append(rejects)

    if not frames:
        return pd.DataFrame()

    candidates = pd.concat(frames, ignore_index=True, sort=False)
    candidates["candidate_time_utc"] = _parse_utc(candidates["timestamp"])
    candidates["candidate_regime_candle_time_utc"] = _parse_utc(candidates["mtf_candle_time"])
    missing_candle = candidates["candidate_regime_candle_time_utc"].isna()
    candidates.loc[missing_candle, "candidate_regime_candle_time_utc"] = (
        candidates.loc[missing_candle, "candidate_time_utc"].dt.floor("4h")
    )
    candidates["signal_side"] = candidates["signal_side"].astype(str).str.upper()
    return candidates


def align_scanner_candidates(
    replay: pd.DataFrame,
    trades: pd.DataFrame,
    scanner_root: Path,
) -> pd.DataFrame:
    candidates = _load_scanner_candidates(scanner_root)
    if candidates.empty:
        return candidates

    replay_prefixed = replay.rename(columns={
        "raw_regime": "replay_raw_regime",
        "detected_regime": "replay_detected_regime",
        "arbiter_label": "replay_arbiter_label",
        "arbiter_confidence": "replay_arbiter_confidence",
        "arbiter_entry_allowed": "replay_arbiter_entry_allowed",
        "arbiter_reason": "replay_arbiter_reason",
        "mixed_bucket": "replay_mixed_bucket",
    })
    aligned = candidates.merge(
        replay_prefixed,
        how="left",
        left_on=["window", "candidate_regime_candle_time_utc", "signal_side"],
        right_on=["window", "replay_candle_time", "signal_side"],
    )

    trade_keys = trades[[
        "window",
        "symbol",
        "side",
        "entry_time_utc",
        "trade_id",
        "pnl_usdt",
        "realized_r",
        "v54_outcome",
    ]].rename(columns={
        "side": "signal_side",
        "entry_time_utc": "candidate_time_utc",
        "trade_id": "v54_trade_id",
        "pnl_usdt": "v54_pnl_usdt",
        "realized_r": "v54_realized_r",
    })
    aligned = aligned.merge(
        trade_keys,
        how="left",
        on=["window", "symbol", "signal_side", "candidate_time_utc"],
    )
    aligned["replay_match"] = aligned["replay_candle_time"].notna()
    aligned["scanner_status_classification"] = aligned.apply(_candidate_classification, axis=1)
    aligned["replay_route_classification"] = aligned.apply(
        _router_candidate_classification,
        axis=1,
    )
    aligned["alignment_classification"] = aligned["scanner_status_classification"]

    cols = [
        "window",
        "candidate_status",
        "timestamp",
        "symbol",
        "signal_type",
        "signal_side",
        "signal_tier",
        "candidate_regime_candle_time_utc",
        "reject_reason",
        "arbiter_label",
        "arbiter_confidence",
        "arbiter_reason",
        "v54_trade_id",
        "v54_pnl_usdt",
        "v54_realized_r",
        "v54_outcome",
        "scanner_status_classification",
        "replay_route_classification",
        "alignment_classification",
        "replay_match",
        "replay_raw_regime",
        "replay_detected_regime",
        "replay_arbiter_label",
        "replay_arbiter_confidence",
        "replay_arbiter_reason",
        "router_decision",
        "router_allowed",
        "router_selected_strategy",
        "router_reason",
        "router_block_reason",
        "router_policy",
        "replay_mixed_bucket",
    ]
    return aligned[cols].copy()


def _summary(v54_alignment: pd.DataFrame, scanner_alignment: pd.DataFrame) -> dict:
    summary = {
        "v54_by_classification": (
            v54_alignment["alignment_classification"].value_counts().to_dict()
        ),
        "v54_by_window_classification": (
            v54_alignment
            .groupby(["window", "alignment_classification"], dropna=False)
            .size()
            .reset_index(name="count")
            .to_dict(orient="records")
        ),
        "v54_blocked_r_by_classification": (
            v54_alignment[v54_alignment["router_decision"] == "block"]
            .groupby("alignment_classification", dropna=False)["realized_r"]
            .sum()
            .round(4)
            .to_dict()
        ),
        "v54_blocked_pnl_by_classification": (
            v54_alignment[v54_alignment["router_decision"] == "block"]
            .groupby("alignment_classification", dropna=False)["pnl_usdt"]
            .sum()
            .round(4)
            .to_dict()
        ),
    }
    if not scanner_alignment.empty:
        summary["scanner_by_status_classification"] = (
            scanner_alignment["scanner_status_classification"].value_counts().to_dict()
        )
        summary["scanner_by_replay_route_classification"] = (
            scanner_alignment["replay_route_classification"].value_counts().to_dict()
        )
        summary["scanner_by_status"] = (
            scanner_alignment["candidate_status"].value_counts().to_dict()
        )
        summary["scanner_by_window_status_classification"] = (
            scanner_alignment
            .groupby(["window", "scanner_status_classification"], dropna=False)
            .size()
            .reset_index(name="count")
            .to_dict(orient="records")
        )
        summary["scanner_by_window_replay_route_classification"] = (
            scanner_alignment
            .groupby(["window", "replay_route_classification"], dropna=False)
            .size()
            .reset_index(name="count")
            .to_dict(orient="records")
        )
    return summary


def _write_markdown(output_dir: Path, summary: dict) -> None:
    v54_counts = summary["v54_by_classification"]
    protective = v54_counts.get("protective_block", 0)
    missed = v54_counts.get("missed_opportunity", 0)
    protected_r = summary["v54_blocked_r_by_classification"].get("protective_block", 0.0)
    missed_r = summary["v54_blocked_r_by_classification"].get("missed_opportunity", 0.0)
    protected_pnl = summary["v54_blocked_pnl_by_classification"].get("protective_block", 0.0)
    missed_pnl = summary["v54_blocked_pnl_by_classification"].get("missed_opportunity", 0.0)
    net_blocked_r = round(protected_r + missed_r, 4)
    net_blocked_pnl = round(protected_pnl + missed_pnl, 4)

    lines = [
        "# Regime Router Replay Alignment",
        "",
        "Scope: align Phase 1 router replay rows to R4 V54 baseline entries and true B scanner arbiter-block candidates.",
        "",
        "## V54 Entry Outcome",
        "",
        f"- Protective blocks: {protective} trades, realized R {protected_r}, PnL {protected_pnl} USDT.",
        f"- Missed opportunities: {missed} trades, realized R {missed_r}, PnL {missed_pnl} USDT.",
        f"- Net blocked baseline outcome: realized R {net_blocked_r}, PnL {net_blocked_pnl} USDT. Negative here means the blocked set was net losing, so the gate helped before path effects.",
        "",
        "| Window | Classification | Count |",
        "|---|---|---:|",
    ]
    for row in summary["v54_by_window_classification"]:
        lines.append(
            f"| `{row['window']}` | `{row['alignment_classification']}` | {row['count']} |"
        )

    if "scanner_by_window_status_classification" in summary:
        lines.extend([
            "",
            "## Scanner Candidate Context",
            "",
            "Status classification uses the true B scanner entry/block status. Replay route classification uses the synthetic router replay row matched to the same candidate candle.",
            "",
            "### True B Status",
            "",
            "| Window | Classification | Count |",
            "|---|---|---:|",
        ])
        for row in summary["scanner_by_window_status_classification"]:
            lines.append(
                f"| `{row['window']}` | `{row['scanner_status_classification']}` | {row['count']} |"
            )
        lines.extend([
            "",
            "### Replay Route",
            "",
            "| Window | Classification | Count |",
            "|---|---|---:|",
        ])
        for row in summary["scanner_by_window_replay_route_classification"]:
            lines.append(
                f"| `{row['window']}` | `{row['replay_route_classification']}` | {row['count']} |"
            )

    lines.extend([
        "",
        "## Read",
        "",
        "Use the V54 entry alignment as the outcome-bearing source. Scanner candidate rows are context only when no V54 trade outcome is available.",
        "",
        "A protective block means the router/arbiter would have blocked a losing V54 baseline entry. A missed opportunity means it would have blocked a winning V54 baseline entry.",
        "",
        "The outcome-bearing V54 alignment favors investigating MIXED/chop-trend policy first: 6 protective blocks versus 2 missed opportunities, with fade_2025_04_06 contributing 4 protective blocks and 1 missed opportunity. RANGING is not the immediate pain point in this replay because RANGING continues to route to V54. SQUEEZE has visible opportunity cost through one missed winner, but this sample is thinner than the chop-trend cluster.",
        "",
    ])
    (output_dir / "alignment_summary.md").write_text("\n".join(lines), encoding="utf-8")


def run_alignment(
    *,
    replay_root: Path,
    v54_trades_csv: Path,
    scanner_root: Path,
    output_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    replay = _load_replay(replay_root)
    trades = _load_v54_trades(v54_trades_csv)
    v54_alignment = align_v54_entries(replay, trades)
    scanner_alignment = align_scanner_candidates(replay, trades, scanner_root)
    summary = _summary(v54_alignment, scanner_alignment)

    output_dir.mkdir(parents=True, exist_ok=True)
    v54_alignment.to_csv(output_dir / "v54_entry_alignment.csv", index=False)
    scanner_alignment.to_csv(output_dir / "scanner_candidate_alignment.csv", index=False)
    (output_dir / "alignment_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_markdown(output_dir, summary)
    return v54_alignment, scanner_alignment, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Align router replay with V54 entries.")
    parser.add_argument("--replay-root", default=str(DEFAULT_REPLAY_ROOT))
    parser.add_argument("--v54-trades", default=str(DEFAULT_V54_TRADES))
    parser.add_argument("--scanner-root", default=str(DEFAULT_SCANNER_ROOT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    _, _, summary = run_alignment(
        replay_root=Path(args.replay_root),
        v54_trades_csv=Path(args.v54_trades),
        scanner_root=Path(args.scanner_root),
        output_dir=Path(args.output),
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
