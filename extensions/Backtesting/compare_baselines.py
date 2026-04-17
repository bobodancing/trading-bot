#!/usr/bin/env python3
"""
Baseline Diff — compare two backtest runs (before/after Patch B).

Usage:
    python compare_baselines.py results/baseline_patchA results/baseline_patchB

Outputs a console report + results/diff/comparison_report.txt
"""
import json
import sys
from pathlib import Path

import pandas as pd


def load_dir(d: Path) -> dict:
    out = {}
    for name in [
        "summary.json", "signal_audit_summary.json",
        "trades.csv", "signal_rejects.csv", "signal_entries.csv",
        "regime_transitions.csv", "btc_trend_log.csv",
    ]:
        p = d / name
        if not p.exists():
            continue
        if name.endswith(".json"):
            with open(p, encoding="utf-8") as f:
                out[name] = json.load(f)
        else:
            out[name] = pd.read_csv(p)
    return out


def pct_change(a, b):
    if a == 0:
        return "N/A" if b == 0 else "+inf"
    return f"{(b - a) / abs(a) * 100:+.1f}%"


def compare_summaries(a: dict, b: dict) -> list:
    lines = []
    lines.append("=" * 70)
    lines.append("TRADE-LEVEL SUMMARY COMPARISON")
    lines.append("=" * 70)
    sa = a.get("summary.json", {})
    sb = b.get("summary.json", {})
    keys = [
        "total_trades", "win_rate", "profit_factor",
        "total_return_pct", "max_drawdown_pct", "sharpe", "trades_per_week",
    ]
    lines.append(f"{'metric':<25} {'Before':>12} {'After':>12} {'Change':>10}")
    lines.append("-" * 60)
    for k in keys:
        va = sa.get(k, 0)
        vb = sb.get(k, 0)
        lines.append(f"{k:<25} {va:>12.4f} {vb:>12.4f} {pct_change(va, vb):>10}")
    return lines


def compare_signal_audit(a: dict, b: dict) -> list:
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("SIGNAL AUDIT COMPARISON")
    lines.append("=" * 70)
    aa = a.get("signal_audit_summary.json", {})
    ab = b.get("signal_audit_summary.json", {})

    # Top-level counts
    for k in ["total_rejects", "total_entries", "regime_transitions", "btc_trend_snapshots"]:
        va = aa.get(k, 0)
        vb = ab.get(k, 0)
        lines.append(f"  {k:<30} {va:>8} -> {vb:>8}  ({pct_change(va, vb)})")

    # Rejects by reason
    lines.append("")
    lines.append("  Rejects by reason:")
    ra = aa.get("rejects_by_reason", {})
    rb = ab.get("rejects_by_reason", {})
    all_reasons = sorted(set(list(ra.keys()) + list(rb.keys())))
    for r in all_reasons:
        va = ra.get(r, 0)
        vb = rb.get(r, 0)
        flag = " <<<" if abs(vb - va) > max(va, 1) * 0.25 else ""
        lines.append(f"    {r:<35} {va:>6} -> {vb:>6}  ({pct_change(va, vb)}){flag}")

    # Entries by signal type
    lines.append("")
    lines.append("  Entries by signal type:")
    ea = aa.get("entries_by_signal_type", {})
    eb = ab.get("entries_by_signal_type", {})
    all_types = sorted(set(list(ea.keys()) + list(eb.keys())))
    for t in all_types:
        va = ea.get(t, 0)
        vb = eb.get(t, 0)
        flag = " <<<" if va > 0 and abs(vb - va) / va > 0.25 else ""
        lines.append(f"    {t:<35} {va:>6} -> {vb:>6}  ({pct_change(va, vb)}){flag}")

    # Entries by tier
    lines.append("")
    lines.append("  Entries by tier:")
    ta = aa.get("entries_by_tier", {})
    tb = ab.get("entries_by_tier", {})
    for t in sorted(set(list(ta.keys()) + list(tb.keys()))):
        va = ta.get(t, 0)
        vb = tb.get(t, 0)
        lines.append(f"    {t:<35} {va:>6} -> {vb:>6}  ({pct_change(va, vb)})")

    optional_blocks = [
        ("Rejects by MTF status", "rejects_by_mtf_status"),
        ("Entries by MTF status", "entries_by_mtf_status"),
        ("Rejects by MTF reason", "rejects_by_mtf_reason"),
        ("Rejects by MTF gate mode", "rejects_by_mtf_gate_mode"),
        ("Entries by MTF gate mode", "entries_by_mtf_gate_mode"),
        ("Rejects by tier score", "rejects_by_tier_score"),
        ("Entries by tier score", "entries_by_tier_score"),
    ]
    for title, key in optional_blocks:
        da = aa.get(key, {})
        db = ab.get(key, {})
        if not da and not db:
            continue
        lines.append("")
        lines.append(f"  {title}:")
        for item in sorted(set(list(da.keys()) + list(db.keys())), key=str):
            va = da.get(item, 0)
            vb = db.get(item, 0)
            flag = " <<<" if va > 0 and abs(vb - va) / va > 0.25 else ""
            lines.append(f"    {str(item):<35} {va:>6} -> {vb:>6}  ({pct_change(va, vb)}){flag}")

    # Regime transitions
    lines.append("")
    lines.append("  Regime transitions by type:")
    rta = aa.get("regime_transitions_by_type", {})
    rtb = ab.get("regime_transitions_by_type", {})
    for t in sorted(set(list(rta.keys()) + list(rtb.keys()))):
        va = rta.get(t, 0)
        vb = rtb.get(t, 0)
        lines.append(f"    {t:<35} {va:>6} -> {vb:>6}  ({pct_change(va, vb)})")

    # BTC trend distribution
    lines.append("")
    lines.append("  BTC trend distribution:")
    bta = aa.get("btc_trend_distribution", {})
    btb = ab.get("btc_trend_distribution", {})
    for t in sorted(set(list(bta.keys()) + list(btb.keys())), key=str):
        va = bta.get(t, 0)
        vb = btb.get(t, 0)
        lines.append(f"    {str(t):<35} {va:>6} -> {vb:>6}  ({pct_change(va, vb)})")

    lines.append("")
    lines.append("  BTC source distribution:")
    bsa = aa.get("btc_source_distribution", {})
    bsb = ab.get("btc_source_distribution", {})
    for s in sorted(set(list(bsa.keys()) + list(bsb.keys())), key=str):
        va = bsa.get(s, 0)
        vb = bsb.get(s, 0)
        lines.append(f"    {str(s):<35} {va:>6} -> {vb:>6}  ({pct_change(va, vb)})")

    return lines


def compare_exit_reasons(a: dict, b: dict) -> list:
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("EXIT REASON BREAKDOWN")
    lines.append("=" * 70)
    ta = a.get("trades.csv")
    tb = b.get("trades.csv")
    if ta is None or tb is None:
        lines.append("  (trades.csv missing in one or both dirs)")
        return lines

    era = ta["exit_reason"].value_counts().to_dict() if "exit_reason" in ta.columns else {}
    erb = tb["exit_reason"].value_counts().to_dict() if "exit_reason" in tb.columns else {}
    all_reasons = sorted(set(list(era.keys()) + list(erb.keys())), key=str)
    for r in all_reasons:
        va = era.get(r, 0)
        vb = erb.get(r, 0)
        lines.append(f"    {str(r):<35} {va:>6} -> {vb:>6}  ({pct_change(va, vb)})")
    return lines


def diff_entries(a: dict, b: dict) -> list:
    """Find entries that appear in A but not B (removed) and vice versa (added)."""
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("ENTRY DIFF (added/removed signals)")
    lines.append("=" * 70)

    ea = a.get("signal_entries.csv")
    eb = b.get("signal_entries.csv")
    if ea is None or eb is None:
        lines.append("  (signal_entries.csv missing)")
        return lines
    if ea.empty and eb.empty:
        lines.append("  Both empty.")
        return lines

    # Key: (timestamp, symbol, signal_type)
    key_cols = ["timestamp", "symbol", "signal_type"]
    for c in key_cols:
        if c not in ea.columns or c not in eb.columns:
            lines.append(f"  Missing column {c}")
            return lines

    ka = set(ea[key_cols].apply(tuple, axis=1))
    kb = set(eb[key_cols].apply(tuple, axis=1))

    removed = sorted(ka - kb)
    added = sorted(kb - ka)

    lines.append(f"  Entries only in Before (removed by patch): {len(removed)}")
    for ts, sym, sig in removed[:30]:
        lines.append(f"    - {ts}  {sym:<12}  {sig}")
    if len(removed) > 30:
        lines.append(f"    ... and {len(removed) - 30} more")

    lines.append(f"  Entries only in After (added by patch):   {len(added)}")
    for ts, sym, sig in added[:30]:
        lines.append(f"    + {ts}  {sym:<12}  {sig}")
    if len(added) > 30:
        lines.append(f"    ... and {len(added) - 30} more")

    return lines


def go_nogo_assessment(a: dict, b: dict) -> list:
    lines = []
    lines.append("")
    lines.append("=" * 70)
    lines.append("GO / NO-GO ASSESSMENT")
    lines.append("=" * 70)

    flags = []
    sa = a.get("summary.json", {})
    sb = b.get("summary.json", {})

    # Total trades change
    ta = sa.get("total_trades", 0)
    tb = sb.get("total_trades", 0)
    if ta > 0:
        trade_delta = abs(tb - ta) / ta
        if trade_delta > 0.15:
            flags.append(f"YELLOW: total_trades changed {trade_delta:.0%} (>{15}%)")

    # Signal type lane check
    aa = a.get("signal_audit_summary.json", {})
    ab = b.get("signal_audit_summary.json", {})
    ea = aa.get("entries_by_signal_type", {})
    eb = ab.get("entries_by_signal_type", {})
    for sig_type in set(list(ea.keys()) + list(eb.keys())):
        va = ea.get(sig_type, 0)
        vb = eb.get(sig_type, 0)
        if va > 5 and vb == 0:
            flags.append(f"NO-GO: {sig_type} lane went to ZERO (was {va})")
        elif va > 0 and abs(vb - va) / va > 0.25:
            flags.append(f"YELLOW: {sig_type} entries changed {pct_change(va, vb)} (>{25}%)")

    # Regime stuck check
    rta = aa.get("regime_transitions_by_type", {})
    rtb = ab.get("regime_transitions_by_type", {})
    total_trans_a = sum(rta.values())
    total_trans_b = sum(rtb.values())
    if total_trans_a > 3 and total_trans_b == 0:
        flags.append("NO-GO: regime transitions dropped to ZERO (possibly stuck)")
    elif total_trans_a > 0 and total_trans_b > 0:
        delta = abs(total_trans_b - total_trans_a) / total_trans_a
        if delta > 0.5:
            flags.append(f"YELLOW: regime transition count changed {delta:.0%}")

    if not flags:
        lines.append("  GO -- all metrics within acceptable ranges")
    else:
        for f in flags:
            lines.append(f"  {f}")

    return lines


def main():
    if len(sys.argv) < 3:
        print("Usage: python compare_baselines.py <before_dir> <after_dir> [--output <diff_dir>]")
        sys.exit(1)

    dir_a = Path(sys.argv[1])
    dir_b = Path(sys.argv[2])

    output_dir = None
    if "--output" in sys.argv:
        idx = sys.argv.index("--output")
        if idx + 1 < len(sys.argv):
            output_dir = Path(sys.argv[idx + 1])

    if not dir_a.exists():
        print(f"Before dir not found: {dir_a}")
        sys.exit(1)
    if not dir_b.exists():
        print(f"After dir not found: {dir_b}")
        sys.exit(1)

    a = load_dir(dir_a)
    b = load_dir(dir_b)

    all_lines = []
    all_lines.append(f"Baseline Comparison: {dir_a.name} vs {dir_b.name}")
    all_lines.append(f"Before: {dir_a}")
    all_lines.append(f"After:  {dir_b}")

    all_lines += compare_summaries(a, b)
    all_lines += compare_signal_audit(a, b)
    all_lines += compare_exit_reasons(a, b)
    all_lines += diff_entries(a, b)
    all_lines += go_nogo_assessment(a, b)

    report = "\n".join(all_lines)
    print(report)

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "comparison_report.txt").write_text(report, encoding="utf-8")
        print(f"\n[Saved] {output_dir / 'comparison_report.txt'}")


if __name__ == "__main__":
    main()
