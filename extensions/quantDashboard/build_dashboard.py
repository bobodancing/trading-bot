"""
quantDashboard — build_dashboard.py
Reads performance.db and outputs a single dark-themed HTML dashboard.

Tasks 2-8 implementation.
"""

import argparse
import re
import sqlite3
import sys
import os
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def hist_as_bar(values, nbins=20, **bar_kwargs):
    """Pre-compute histogram and return a go.Bar trace.

    Workaround: Plotly go.Histogram renders with zero-width bars
    when mixed with go.Bar traces in the same subplot figure.
    """
    counts, edges = np.histogram(values, bins=nbins)
    centers = (edges[:-1] + edges[1:]) / 2
    width = edges[1] - edges[0]
    return go.Bar(x=centers.tolist(), y=counts.tolist(),
                  width=width * 0.9, **bar_kwargs)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "performance.db")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "dashboard.html")
DATA_CUTOFF = "2026-02-25"
R5_START = "2026-04-12"

DARK_BG = "#1a1a2e"
PANEL_BG = "#16213e"
TEXT_COLOR = "#e0e0e0"
ACCENT = "#0f3460"

# --- Design Tokens (global color system) ---
CLR_WIN = "#00C853"       # positive / win
CLR_LOSS = "#F23645"      # negative / loss
CLR_V7 = "#FF8C00"        # V7 strategy (new)
CLR_V54 = "#FFD166"       # V54 no-scale
CLR_V6 = "royalblue"      # V6 strategy (deprecated)
CLR_V53 = "mediumseagreen"   # V53 strategy
CLR_GRID = "#4DD0E1"      # V8 ATR grid
CLR_OTHER = "#90A4AE"     # fallback / unknown
CLR_TIER_A = "#1565C0"    # Tier A — deep blue
CLR_TIER_B = "#7E57C2"    # Tier B — purple
CLR_TIER_C = "#00E676"    # Tier C — bright green
TIER_COLORS = {"A": CLR_TIER_A, "B": CLR_TIER_B, "C": CLR_TIER_C}
STRAT_COLORS = {
    "V54": CLR_V54,
    "V7": CLR_V7,
    "V6": CLR_V6,
    "V53": CLR_V53,
    "GRID": CLR_GRID,
}
STRATEGY_DISPLAY_ORDER = ["V54", "V7", "V53", "V6", "GRID"]
STAGED_STRATEGIES = {"V7", "V6"}
DIRECTIONAL_STRATEGIES = {"V54", "V7", "V53", "V6"}
TRADE_COLUMNS = [
    "id", "trade_id", "symbol", "side", "is_v6_pyramid", "signal_tier",
    "signal_type", "entry_price", "exit_price", "exit_price_source",
    "total_size", "initial_r", "entry_time", "exit_time", "holding_hours",
    "pnl_usdt", "pnl_pct", "realized_r", "mfe_pct", "mae_pct",
    "capture_ratio", "max_r_reached", "stage_reached", "exit_reason",
    "protection_state", "protected_exit", "market_regime", "entry_adx",
    "fakeout_depth_atr", "reverse_2b_depth_atr", "original_size",
    "partial_pnl_usdt", "btc_trend_aligned", "trend_adx", "mtf_aligned",
    "volume_grade", "tier_score", "strategy_name", "grid_level", "grid_round",
    # Forward-compatible optional columns if runtime later persists arbiter fields.
    "arbiter_label", "arbiter_confidence", "arbiter_reason",
]
NUMERIC_COLUMNS = [
    "realized_r", "pnl_usdt", "pnl_pct", "mfe_pct", "mae_pct",
    "capture_ratio", "holding_hours", "entry_adx", "fakeout_depth_atr",
    "reverse_2b_depth_atr", "stage_reached", "entry_price", "exit_price",
    "total_size", "initial_r", "original_size", "partial_pnl_usdt",
    "btc_trend_aligned", "trend_adx", "mtf_aligned", "tier_score",
    "grid_level", "grid_round", "max_r_reached", "arbiter_confidence",
]
LOW_SAMPLE_THRESHOLD = 5  # n < this → dim + warning badge


def apply_typography(fig):
    """Apply consistent typography: larger subplot titles, readable axis labels."""
    fig.update_annotations(font_size=15, font_color=TEXT_COLOR)
    fig.update_xaxes(tickfont=dict(size=12), title_font=dict(size=13))
    fig.update_yaxes(tickfont=dict(size=12), title_font=dict(size=13))


_NAMED_COLORS = {
    "royalblue": (65, 105, 225), "mediumseagreen": (60, 179, 113),
}

def dim_color(color, alpha=0.35):
    """Return rgba() string with reduced opacity for low-sample warning."""
    if color in _NAMED_COLORS:
        r, g, b = _NAMED_COLORS[color]
    else:
        h = color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def low_sample_text(n, base_text):
    """Prepend warning badge if n < threshold."""
    if n < LOW_SAMPLE_THRESHOLD:
        return f"n={n} LOW\u26a0<br>{base_text}" if base_text else f"n={n} LOW\u26a0"
    return f"n={n}<br>{base_text}" if base_text else f"n={n}"


def _is_truthy_flag(value):
    """Normalize legacy integer/bool/string flags from SQLite rows."""
    if pd.isna(value):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def resolve_strategy_label(row):
    """Normalize runtime strategy names into dashboard-friendly labels."""
    strategy_name = row.get("strategy_name")
    if isinstance(strategy_name, str):
        strategy_name = strategy_name.strip()

    explicit = {
        "v54_noscale": "V54",
        "v7_structure": "V7",
        "v6_pyramid": "V6",
        "v53_sop": "V53",
        "v8_atr_grid": "GRID",
    }
    if strategy_name in explicit:
        return explicit[strategy_name]

    if _is_truthy_flag(row.get("is_v6_pyramid")):
        return "V6"

    if not strategy_name:
        return "V53"

    return str(strategy_name).upper()


def empty_trades_frame():
    """Return a dashboard-safe empty trades DataFrame."""
    return pd.DataFrame({col: pd.Series(dtype="object") for col in TRADE_COLUMNS})


def ensure_trade_columns(df):
    """Add missing trade columns so old/new DB schemas render without crashing."""
    for col in TRADE_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df


def map_btc_alignment(value):
    """Map BTC trend alignment flag to display label."""
    if pd.isna(value):
        return "Unknown"
    return "Aligned" if value == 1 or value is True else "Counter"


def prepare_trades_df(df):
    """Normalize runtime trades rows into the shape expected by dashboard tabs."""
    df = ensure_trade_columns(df.copy())
    df["exit_time"] = pd.to_datetime(df["exit_time"], errors="coerce", utc=True).dt.tz_localize(None)
    df["entry_time"] = pd.to_datetime(df["entry_time"], errors="coerce", utc=True)

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if len(df) > 0:
        df["strategy"] = df.apply(resolve_strategy_label, axis=1)
    else:
        df["strategy"] = pd.Series(dtype="object")

    df["exit_date"] = df["exit_time"].dt.date
    df["btc_aligned"] = df["btc_trend_aligned"].apply(map_btc_alignment)
    return df.sort_values("exit_time").reset_index(drop=True)


def ordered_strategies(df, include_grid=True):
    """Return stable strategy ordering for charts and tables."""
    if "strategy" not in df.columns:
        return []

    present = {
        value for value in df["strategy"].dropna().astype(str)
        if value
    }
    if not include_grid:
        present.discard("GRID")

    ordered = [name for name in STRATEGY_DISPLAY_ORDER if name in present]
    extras = sorted(present - set(ordered))
    return ordered + extras


def select_kpi_strategies(df):
    """Choose a compact set of strategies for the KPI strip."""
    present = ordered_strategies(df)
    directional = [name for name in present if name in DIRECTIONAL_STRATEGIES]

    if len(directional) >= 2:
        return directional[:3]
    if len(directional) == 1:
        extras = [name for name in present if name not in directional]
        return directional + extras[:1]
    return present[:2]


def strategy_color(label):
    return STRAT_COLORS.get(label, CLR_OTHER)


def strategy_css_class(label):
    normalized = re.sub(r"[^a-z0-9]+", "-", str(label).lower()).strip("-")
    return f"strat-{normalized}" if normalized else ""

# ---------------------------------------------------------------------------
# Task 2: CLI args + DB loader
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="quantDashboard")
    parser.add_argument("--days", type=int, default=None,
                        help="Show only the last N days. If omitted, all data is shown.")
    parser.add_argument("--all", action="store_true", dest="all_data",
                        help="Show all data since DATA_CUTOFF (default)")
    parser.add_argument("--db", type=str, default=DB_PATH, help="Path to performance.db")
    parser.add_argument("--out", type=str, default=OUTPUT_PATH, help="Output HTML path")
    parser.add_argument("--r5-start", type=str, default=R5_START,
                        help=f"R5 monitor start date (default {R5_START})")
    args = parser.parse_args()
    if args.days is None:
        args.all_data = True
        args.days = 7
    else:
        args.all_data = False
    return args


def load_trades(days=7, all_data=False, db_path=DB_PATH):
    """Load trades from SQLite, filter by date, add derived columns."""
    if not os.path.exists(db_path):
        print(f"ERROR: DB not found at {db_path}")
        print("Run pull_db.sh to fetch the DB from rwUbuntu, or specify --db <path>.")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    tables = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "trades" not in tables:
        print("WARN: trades table not found. Rendering empty dashboard.")
        conn.close()
        return prepare_trades_df(empty_trades_frame())

    df = pd.read_sql_query("SELECT * FROM trades", conn)
    conn.close()

    if df.empty:
        print("WARN: trades table is empty. Rendering empty dashboard.")
        return prepare_trades_df(empty_trades_frame())

    df = prepare_trades_df(df)

    # Apply date filter
    cutoff = pd.Timestamp(DATA_CUTOFF)
    if all_data:
        df = df[df["exit_time"] >= cutoff]
    else:
        since = pd.Timestamp(datetime.now() - timedelta(days=days))
        effective_cutoff = max(cutoff, since)
        df = df[df["exit_time"] >= effective_cutoff]

    if df.empty:
        period = "all time since cutoff" if all_data else f"last {days} days"
        print(f"WARN: no trades found for {period}. Rendering empty dashboard.")

    return df.sort_values("exit_time").reset_index(drop=True)


def load_prev_period(days=7, all_data=False, db_path=DB_PATH):
    """Load the previous period's trades for comparison.

    For --days N: prev period = [now-2N, now-N).
    For --all: no previous period available → return None.
    """
    if all_data:
        return None

    conn = sqlite3.connect(db_path)
    tables = {
        row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "trades" not in tables:
        conn.close()
        return None

    df = pd.read_sql_query("SELECT * FROM trades", conn)
    conn.close()

    if df.empty:
        return None

    df = prepare_trades_df(df)
    cutoff = pd.Timestamp(DATA_CUTOFF)
    now = pd.Timestamp(datetime.now())
    period_start = max(cutoff, now - timedelta(days=days * 2))
    period_end = now - timedelta(days=days)

    df = df[(df["exit_time"] >= period_start) & (df["exit_time"] < period_end)]

    if df.empty:
        return None

    return df.sort_values("exit_time").reset_index(drop=True)


# ---------------------------------------------------------------------------
# Task 3: compute_metrics()
# ---------------------------------------------------------------------------

def compute_metrics(df):
    """Compute trading performance metrics. df must be pre-sorted by exit_time."""
    r = df["realized_r"].dropna()
    pnl = df["pnl_pct"].dropna()  # position-level % — used for per-trade Sharpe only

    wins = r[r > 0]
    losses = r[r <= 0]

    wr = (r > 0).mean() if len(r) > 0 else 0.0
    avg_r = r.mean() if len(r) > 0 else 0.0

    gross_profit = wins.sum() if len(wins) > 0 else 0.0
    gross_loss = losses.sum() if len(losses) > 0 else 0.0
    if gross_loss != 0:
        pf = gross_profit / abs(gross_loss)
    else:
        pf = float("inf") if gross_profit > 0 else 0.0
    pf = min(pf, 10.0)  # cap for display; inf not meaningful in KPI delta

    if len(pnl) > 1 and pnl.std() != 0:
        sharpe = pnl.mean() / pnl.std()
    else:
        sharpe = 0.0

    avg_win_r = wins.mean() if len(wins) > 0 else 0.0
    avg_loss_r = losses.mean() if len(losses) > 0 else 0.0
    expectancy = wr * avg_win_r + (1 - wr) * avg_loss_r

    # Equity curve: cumulative USDT PnL — correct for concurrent trades
    # (pnl_pct cumprod would be wrong because trades overlap in time)
    usdt = df["pnl_usdt"].fillna(0)
    if len(usdt) > 0:
        equity = usdt.cumsum()
        drawdown = equity - equity.cummax()   # in USDT
        max_dd = drawdown.min()               # in USDT (negative)
    else:
        equity = pd.Series(dtype="float64")
        drawdown = pd.Series(dtype="float64")
        max_dd = 0.0

    return {
        "total_trades": len(df),
        "win_rate": wr,
        "avg_r": avg_r,
        "profit_factor": pf,
        "sharpe": sharpe,
        "expectancy": expectancy,
        "max_dd": max_dd,
        "equity": equity,
        "drawdown": drawdown,
    }


# ---------------------------------------------------------------------------
# Task 4: build_overview_tab(df, metrics)
# ---------------------------------------------------------------------------

def build_overview_tab(df, metrics, prev_metrics=None):
    """Returns (kpi_html, chart_html).

    If prev_metrics is provided, KPI deltas show period-over-period change.
    Otherwise, deltas show vs fixed thresholds (original behavior).
    """

    # KPI figure: 6 Indicator subplots
    kpi_fig = make_subplots(
        rows=1, cols=6,
        specs=[[{"type": "indicator"}] * 6],
    )

    pf_display = round(metrics["profit_factor"], 2)

    # Delta references: use previous period if available, else fixed thresholds
    if prev_metrics:
        refs = {
            "trades": prev_metrics["total_trades"],
            "wr": round(prev_metrics["win_rate"] * 100, 1),
            "avg_r": round(prev_metrics["avg_r"], 3),
            "pf": round(prev_metrics["profit_factor"], 2),
            "sharpe": round(prev_metrics["sharpe"], 2),
            "max_dd": round(prev_metrics["max_dd"], 2),
        }
        delta_suffix = " (vs prev)"
    else:
        refs = {"trades": None, "wr": 50.0, "avg_r": 0.0,
                "pf": 1.0, "sharpe": 0.0, "max_dd": 0.0}
        delta_suffix = ""

    indicators = [
        ("Trades",       metrics["total_trades"],             refs["trades"],  "number" if refs["trades"] is None else "number+delta"),
        ("Win Rate%",    round(metrics["win_rate"] * 100, 1), refs["wr"],      "number+delta"),
        ("Avg R",        round(metrics["avg_r"], 3),          refs["avg_r"],   "number+delta"),
        ("PF (R-based)", pf_display,                          refs["pf"],      "number+delta"),
        ("Sharpe (T)",   round(metrics["sharpe"], 2),         refs["sharpe"],  "number+delta"),
        ("Max DD ₮",     round(metrics["max_dd"], 2),         refs["max_dd"],  "number+delta"),
    ]

    for i, (title, value, ref, mode) in enumerate(indicators, start=1):
        kwargs = dict(
            value=value,
            mode=mode,
            title={"text": title + delta_suffix if ref is not None and prev_metrics else title,
                   "font": {"color": TEXT_COLOR}},
            number={"font": {"color": TEXT_COLOR}},
        )
        if ref is not None:
            kwargs["delta"] = {"reference": ref, "relative": False}
        kpi_fig.add_trace(go.Indicator(**kwargs), row=1, col=i)

    kpi_fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=PANEL_BG,
        plot_bgcolor=PANEL_BG,
        height=180,
        margin=dict(l=10, r=10, t=40, b=10),
        font=dict(color=TEXT_COLOR),
    )

    # Chart figure: 3-row subplot — X axis uses real exit_time timestamps
    # df is pre-sorted by exit_time in load_trades()
    exit_times = df["exit_time"].tolist()
    eq = metrics["equity"].reset_index(drop=True)
    dd = metrics["drawdown"].reset_index(drop=True)

    # Rolling Win Rate (30-trade window) — df already sorted
    rolling_wr = (df["realized_r"] > 0).rolling(30, min_periods=1).mean() * 100

    chart_fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=False,
        subplot_titles=["Cumulative PnL (USDT)", "Drawdown (USDT)", "Rolling Win Rate (30T)"],
        vertical_spacing=0.08,
        row_heights=[0.45, 0.25, 0.30],
    )

    chart_fig.add_trace(
        go.Scatter(x=exit_times, y=eq.tolist(), mode="lines", name="Cum PnL",
                   line=dict(color="#5bc8f5", width=2)),
        row=1, col=1,
    )

    chart_fig.add_trace(
        go.Scatter(x=exit_times, y=dd.tolist(), mode="lines", name="Drawdown",
                   fill="tozeroy", fillcolor="rgba(220,50,50,0.25)",
                   line=dict(color="crimson", width=1.5)),
        row=2, col=1,
    )

    chart_fig.add_trace(
        go.Scatter(x=exit_times, y=rolling_wr.tolist(), mode="lines", name="Rolling WR%",
                   line=dict(color="orange", width=1.5)),
        row=3, col=1,
    )

    chart_fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=PANEL_BG,
        plot_bgcolor=PANEL_BG,
        height=600,
        showlegend=True,
        margin=dict(l=60, r=20, t=60, b=40),
        font=dict(color=TEXT_COLOR),
    )

    kpi_html = kpi_fig.to_html(full_html=False, include_plotlyjs=False)
    chart_html = chart_fig.to_html(full_html=False, include_plotlyjs=False)
    return kpi_html, chart_html


# ---------------------------------------------------------------------------
# Task 5: build_strategy_tab(df)
# ---------------------------------------------------------------------------

def _build_kpi_row(indicators_data, height=140):
    """Build a KPI indicator row. indicators_data: list of (title, value, suffix)."""
    if not indicators_data:
        indicators_data = [("Trades", 0, ""), ("WR%", 0, "%"), ("Avg R", 0, ""), ("PnL", 0, " \u20ae")]
    n = len(indicators_data)
    kpi_fig = make_subplots(rows=1, cols=n,
                            specs=[[{"type": "indicator"}] * n])
    for i, (title, value, suffix) in enumerate(indicators_data, start=1):
        kpi_fig.add_trace(go.Indicator(
            value=value, mode="number",
            title={"text": title, "font": {"color": TEXT_COLOR, "size": 13}},
            number={"font": {"color": TEXT_COLOR, "size": 24},
                    "suffix": suffix if suffix else ""},
        ), row=1, col=i)
    kpi_fig.update_layout(
        template="plotly_dark", paper_bgcolor=PANEL_BG, plot_bgcolor=PANEL_BG,
        height=height, margin=dict(l=10, r=10, t=40, b=10),
        font=dict(color=TEXT_COLOR),
    )
    return kpi_fig.to_html(full_html=False, include_plotlyjs=False)


def build_strategy_tab(df):
    """Returns (kpi_html, chart_html)."""
    # --- KPI row ---
    def _safe(series, fn):
        return fn(series) if len(series) > 0 else 0

    kpi_strategies = select_kpi_strategies(df)
    indicators = []
    for strategy_name in kpi_strategies:
        sub = df[df["strategy"] == strategy_name]
        wr = _safe(sub["realized_r"], lambda s: (s > 0).mean() * 100)
        indicators.extend([
            (f"{strategy_name} Trades", len(sub), ""),
            (f"{strategy_name} WR%", round(wr, 1), "%"),
            (f"{strategy_name} Avg R", round(_safe(sub["realized_r"], lambda s: s.mean()), 3), ""),
            (f"{strategy_name} PnL", round(_safe(sub["pnl_usdt"], lambda s: s.sum()), 1), " \u20ae"),
        ])
    kpi_html = _build_kpi_row(indicators)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "Cumulative PnL by Strategy",
            "Stage Performance (V7/V6 only)",
            "Avg R by Tier & Strategy",
            "Win Rate% by Tier & Strategy",
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.10,
    )

    # (1,1) Cumulative PnL by Strategy
    for strat in ordered_strategies(df):
        sub = df[df["strategy"] == strat]  # df already sorted by exit_time
        if len(sub) > 0:
            cum_pnl = sub["pnl_usdt"].cumsum()
            fig.add_trace(
                go.Scatter(x=sub["exit_time"].tolist(), y=cum_pnl.values.tolist(),
                           mode="lines", name=strat,
                           line=dict(color=strategy_color(strat), width=2)),
                row=1, col=1,
            )

    # (1,2) Stage Reached — Avg R + WR% + n (V7/V6 pyramid strategies)
    staged_df = df[df["strategy"].isin(STAGED_STRATEGIES)]
    if len(staged_df) > 0 and "stage_reached" in staged_df.columns:
        stages = sorted(staged_df["stage_reached"].dropna().astype(int).unique())
        avgs, labels, texts = [], [], []
        for s in stages:
            s_df = staged_df[staged_df["stage_reached"] == s]
            r = s_df["realized_r"].dropna()
            n = len(r)
            avg = r.mean() if n > 0 else 0.0
            med = r.median() if n > 0 else 0.0
            wr = (r > 0).mean() * 100 if n > 0 else 0.0
            pnl = s_df["pnl_usdt"].sum()
            avgs.append(avg)
            labels.append(f"Stage {s}")
            detail = f"WR={wr:.0f}% med={med:.2f} Σ${pnl:.0f}"
            texts.append(low_sample_text(n, detail))
        bar_colors = [
            CLR_V7 if len(staged_df[staged_df["stage_reached"] == s]["realized_r"].dropna()) >= LOW_SAMPLE_THRESHOLD
            else dim_color(CLR_V7)
            for s in stages
        ]
        fig.add_trace(
            go.Bar(x=labels, y=avgs, name="Avg R by Stage",
                   marker_color=bar_colors, text=texts,
                   textposition="outside", showlegend=False),
            row=1, col=2,
        )

    # (2,1) Tier Avg R grouped bar
    tiers = ["A", "B", "C"]
    for strat in ordered_strategies(df, include_grid=False):
        sub = df[df["strategy"] == strat]
        avgs, labels, texts, bar_clrs = [], [], [], []
        for tier in tiers:
            t_df = sub[sub["signal_tier"] == tier]
            n = len(t_df)
            avg = t_df["realized_r"].mean() if n > 0 else 0.0
            avgs.append(avg)
            labels.append(f"Tier {tier}")
            texts.append(low_sample_text(n, ""))
            clr = strategy_color(strat)
            bar_clrs.append(clr if n >= LOW_SAMPLE_THRESHOLD else dim_color(clr))
        fig.add_trace(
            go.Bar(x=labels, y=avgs, name=strat,
                   marker_color=bar_clrs, text=texts, textposition="auto",
                   showlegend=False),
            row=2, col=1,
        )

    # (2,2) Tier WR% grouped bar
    for strat in ordered_strategies(df, include_grid=False):
        sub = df[df["strategy"] == strat]
        wrs, labels, texts, bar_clrs = [], [], [], []
        for tier in tiers:
            t_df = sub[sub["signal_tier"] == tier]
            n = len(t_df)
            wr = (t_df["realized_r"] > 0).mean() * 100 if n > 0 else 0.0
            wrs.append(wr)
            labels.append(f"Tier {tier}")
            texts.append(low_sample_text(n, ""))
            clr = strategy_color(strat)
            bar_clrs.append(clr if n >= LOW_SAMPLE_THRESHOLD else dim_color(clr))
        fig.add_trace(
            go.Bar(x=labels, y=wrs, name=f"{strat} WR%",
                   marker_color=bar_clrs, text=texts, textposition="auto",
                   showlegend=False),
            row=2, col=2,
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=PANEL_BG,
        plot_bgcolor=PANEL_BG,
        height=700,
        barmode="group",
        margin=dict(l=60, r=20, t=80, b=60),
        font=dict(color=TEXT_COLOR),
        showlegend=True,
    )

    apply_typography(fig)
    chart_html = fig.to_html(full_html=False, include_plotlyjs=False)
    return kpi_html, chart_html


# ---------------------------------------------------------------------------
# Task 6: build_risk_tab(df)
# ---------------------------------------------------------------------------

def build_risk_tab(df):
    """Returns (kpi_html, chart_html)."""
    # --- KPI row ---
    r = df["realized_r"].dropna()
    mfe = df["mfe_pct"].dropna() if "mfe_pct" in df.columns else pd.Series()
    mae = df["mae_pct"].dropna() if "mae_pct" in df.columns else pd.Series()
    gb_df = df[df["mfe_pct"] >= 3] if "mfe_pct" in df.columns and "pnl_pct" in df.columns else pd.DataFrame()
    giveback = (gb_df["mfe_pct"] - gb_df["pnl_pct"]).dropna() if len(gb_df) > 0 else pd.Series()
    giveback = giveback[giveback >= 0] if len(giveback) > 0 else pd.Series()
    sl_count = df["exit_reason"].str.contains(r"(?:stop|sl_hit|hard_stop|trail_sl)",
                  case=False, na=False, regex=True).sum() if "exit_reason" in df.columns else 0

    kpi_html = _build_kpi_row([
        ("Avg MFE%", round(mfe.mean(), 2) if len(mfe) > 0 else 0, "%"),
        ("Avg MAE%", round(mae.mean(), 2) if len(mae) > 0 else 0, "%"),
        ("MFE Giveback Med", round(giveback.median(), 2) if len(giveback) > 0 else 0, "%"),
        ("SL Exits", sl_count, ""),
        ("Avg Loss R", round(r[r <= 0].mean(), 3) if len(r[r <= 0]) > 0 else 0, ""),
    ])

    fig = make_subplots(
        rows=3, cols=3,
        subplot_titles=[
            "Exit Reason Distribution",
            "Exit Reason EV (Avg R)",
            "Capture Ratio Distribution",
            "MFE vs Realized R",
            "SL Quality: MAE vs PnL",
            "Realized R Distribution",
            "MFE Giveback (MFE\u22653%)",
            "MFE \u2192 Exit", "",
        ],
        vertical_spacing=0.10,
        horizontal_spacing=0.10,
        row_heights=[0.33, 0.33, 0.34],
    )

    # (1,1) Exit Reason distribution bar
    if "exit_reason" in df.columns and len(df) > 0:
        er_counts = df["exit_reason"].value_counts()
        fig.add_trace(
            go.Bar(x=er_counts.index.tolist(), y=er_counts.values.tolist(),
                   name="Count", marker_color=CLR_V6, showlegend=False),
            row=1, col=1,
        )

    # (1,2) Exit Reason EV avgR
    if "exit_reason" in df.columns and len(df) > 0:
        ev = df.groupby("exit_reason")["realized_r"].mean().sort_values()
        colors = [CLR_WIN if v >= 0 else CLR_LOSS for v in ev.values]
        fig.add_trace(
            go.Bar(x=ev.index.tolist(), y=ev.values.tolist(),
                   name="Avg R", marker_color=colors, showlegend=False),
            row=1, col=2,
        )

    # (1,3) Capture Ratio histogram — win/loss split, clip to [-2, 1]
    if "capture_ratio" in df.columns and "realized_r" in df.columns:
        cr_df = df[["capture_ratio", "realized_r"]].dropna(subset=["capture_ratio"])
        cr_df = cr_df[(cr_df["capture_ratio"] >= -2) & (cr_df["capture_ratio"] <= 1)]
        if len(cr_df) > 0:
            wins_cr = cr_df[cr_df["realized_r"] > 0]["capture_ratio"]
            losses_cr = cr_df[cr_df["realized_r"] <= 0]["capture_ratio"]
            _, edges = np.histogram(cr_df["capture_ratio"].values, bins=25)
            width = (edges[1] - edges[0]) * 0.9
            centers = ((edges[:-1] + edges[1:]) / 2).tolist()
            if len(wins_cr) > 0:
                w_counts, _ = np.histogram(wins_cr.values, bins=edges)
                fig.add_trace(
                    go.Bar(x=centers, y=w_counts.tolist(), width=width,
                           name="Win", marker_color=CLR_WIN,
                           legendgroup="winloss", showlegend=True, opacity=0.8),
                    row=1, col=3,
                )
            if len(losses_cr) > 0:
                l_counts, _ = np.histogram(losses_cr.values, bins=edges)
                fig.add_trace(
                    go.Bar(x=centers, y=l_counts.tolist(), width=width,
                           name="Loss", marker_color=CLR_LOSS,
                           legendgroup="winloss", showlegend=True, opacity=0.8),
                    row=1, col=3,
                )

    # (2,1) MFE vs Realized scatter
    if "mfe_pct" in df.columns and len(df) > 0:
        mfe_df = df[["mfe_pct", "realized_r", "pnl_usdt", "symbol", "exit_reason"]].dropna(subset=["mfe_pct", "realized_r"])
        wins = mfe_df[mfe_df["realized_r"] > 0]
        losses = mfe_df[mfe_df["realized_r"] <= 0]
        if os.environ.get("QD_DEBUG"):
            print(f"  MFE scatter: {len(wins)} wins, {len(losses)} losses "
                  f"| mfe_pct range [{mfe_df['mfe_pct'].min():.3f}, {mfe_df['mfe_pct'].max():.3f}]")
        for sub, name, color in [(wins, "Win", CLR_WIN), (losses, "Loss", CLR_LOSS)]:
            if len(sub) > 0:
                hover = [f"{s}<br>{e}<br>MFE={m:.2f}% R={r:.2f}"
                         for s, e, m, r in zip(sub["symbol"], sub["exit_reason"], sub["mfe_pct"], sub["realized_r"])]
                fig.add_trace(
                    go.Scatter(x=sub["mfe_pct"].tolist(), y=sub["realized_r"].tolist(),
                               mode="markers", name=name, hovertext=hover, hoverinfo="text",
                               legendgroup="winloss", showlegend=False,
                               marker=dict(color=color, size=7, opacity=0.8)),
                    row=2, col=1,
                )

        # Reference lines for four-quadrant view
        fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.3)",
                      line_width=1, row=2, col=1)

    # (2,2) SL Quality: MAE vs PnL for stop_loss exits
    if "mae_pct" in df.columns and "exit_reason" in df.columns:
        sl_exits_mask = df["exit_reason"].str.contains(
            r"(?:stop|sl_hit|hard_stop|trail_sl)", case=False, na=False, regex=True)
        sl_df = df[sl_exits_mask].dropna(subset=["mae_pct", "pnl_usdt"])
        if os.environ.get("QD_DEBUG"):
            print(f"  SL quality: {len(sl_df)} SL exits "
                  f"| mae_pct range [{sl_df['mae_pct'].min():.3f}, {sl_df['mae_pct'].max():.3f}]"
                  if len(sl_df) > 0 else "  SL quality: 0 SL exits")
        if len(sl_df) > 0:
            hover = [f"{s}<br>{e}<br>MAE={m:.2f}% PnL=${p:.1f}"
                     for s, e, m, p in zip(sl_df["symbol"], sl_df["exit_reason"], sl_df["mae_pct"], sl_df["pnl_usdt"])]
            fig.add_trace(
                go.Scatter(x=sl_df["mae_pct"].tolist(), y=sl_df["pnl_usdt"].tolist(),
                           mode="markers", name="SL Exit", hovertext=hover, hoverinfo="text",
                           marker=dict(color="mediumpurple", size=7, opacity=0.8),
                           showlegend=False),
                row=2, col=2,
            )

        # Reference line: PnL = 0
        fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.3)",
                      line_width=1, row=2, col=2)

    # (2,3) Realized R Distribution histogram
    r_vals = df["realized_r"].dropna()
    if len(r_vals) > 0:
        # Color wins vs losses
        wins_r = r_vals[r_vals > 0]
        losses_r = r_vals[r_vals <= 0]
        # Use shared bin edges so wins/losses align
        all_vals = r_vals.values
        _, edges = np.histogram(all_vals, bins=20)
        if len(wins_r) > 0:
            w_counts, _ = np.histogram(wins_r.values, bins=edges)
            centers = ((edges[:-1] + edges[1:]) / 2).tolist()
            width = (edges[1] - edges[0]) * 0.9
            fig.add_trace(
                go.Bar(x=centers, y=w_counts.tolist(), width=width,
                       name="Win R", marker_color=CLR_WIN,
                       showlegend=False, opacity=0.8),
                row=2, col=3,
            )
        if len(losses_r) > 0:
            l_counts, _ = np.histogram(losses_r.values, bins=edges)
            centers = ((edges[:-1] + edges[1:]) / 2).tolist()
            width = (edges[1] - edges[0]) * 0.9
            fig.add_trace(
                go.Bar(x=centers, y=l_counts.tolist(), width=width,
                       name="Loss R", marker_color=CLR_LOSS,
                       showlegend=False, opacity=0.8),
                row=2, col=3,
            )

        # R = 0 reference line
        fig.add_vline(x=0, line_dash="dot", line_color="rgba(255,255,255,0.3)",
                      line_width=1, row=2, col=3)

    # (3,1) MFE Giveback Distribution — filter MFE >= 3% to exclude false giveback
    if "mfe_pct" in df.columns and "pnl_pct" in df.columns:
        gb_df = df[df["mfe_pct"] >= 3]  # exclude low-MFE false giveback
        giveback = (gb_df["mfe_pct"] - gb_df["pnl_pct"]).dropna()
        giveback = giveback[giveback >= 0]  # filter nonsensical negatives
        if len(giveback) > 0:
            n_bins = max(8, min(30, len(giveback) // 3))
            fig.add_trace(
                hist_as_bar(giveback.values, nbins=n_bins, name="Giveback %",
                            marker_color="goldenrod", showlegend=False),
                row=3, col=1,
            )
            # Add median line
            med = giveback.median()
            fig.add_vline(x=med, line_dash="dash", line_color="white",
                          annotation_text=f"med={med:.2f}%",
                          annotation_font_color="white",
                          row=3, col=1)

    # (3,2) MFE → Exit Scatter: how much of MFE was captured at exit
    if "mfe_pct" in df.columns and "pnl_pct" in df.columns:
        me_df = df[["mfe_pct", "pnl_pct", "realized_r", "symbol", "exit_reason"]].dropna(
            subset=["mfe_pct", "pnl_pct"])
        me_wins = me_df[me_df["realized_r"] > 0]
        me_losses = me_df[me_df["realized_r"] <= 0]
        for sub, name, color in [(me_wins, "Win", CLR_WIN), (me_losses, "Loss", CLR_LOSS)]:
            if len(sub) > 0:
                hover = [f"{s}<br>{e}<br>MFE={m:.2f}% PnL={p:.2f}%"
                         for s, e, m, p in zip(sub["symbol"], sub["exit_reason"], sub["mfe_pct"], sub["pnl_pct"])]
                fig.add_trace(
                    go.Scatter(x=sub["mfe_pct"].tolist(),
                               y=sub["pnl_pct"].tolist(),
                               mode="markers", name=name, hovertext=hover, hoverinfo="text",
                               legendgroup="winloss", showlegend=False,
                               marker=dict(color=color, size=7, opacity=0.8)),
                    row=3, col=2,
                )
        # 45-degree line = perfect capture (pnl_pct == mfe_pct)
        max_mfe = me_df["mfe_pct"].max() if len(me_df) > 0 else 10
        fig.add_trace(
            go.Scatter(x=[0, max_mfe], y=[0, max_mfe],
                       mode="lines", name="Perfect Capture",
                       line=dict(color="white", width=1, dash="dash"),
                       showlegend=False),
            row=3, col=2,
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=PANEL_BG,
        plot_bgcolor=PANEL_BG,
        height=1000,
        barmode="stack",
        margin=dict(l=60, r=20, t=80, b=60),
        font=dict(color=TEXT_COLOR),
        showlegend=True,
    )

    apply_typography(fig)
    chart_html = fig.to_html(full_html=False, include_plotlyjs=False)
    return kpi_html, chart_html


# ---------------------------------------------------------------------------
# Task 7: build_market_tab(df)
# ---------------------------------------------------------------------------

def build_market_tab(df):
    """Returns (kpi_html, chart_html)."""
    # --- KPI row ---
    aligned = df[df.get("btc_aligned", pd.Series()) == "Aligned"] if "btc_aligned" in df.columns else pd.DataFrame()
    aligned_pct = len(aligned) / len(df) * 100 if len(df) > 0 else 0
    hh = df["holding_hours"].dropna() if "holding_hours" in df.columns else pd.Series()
    daily_pnl = df.groupby("exit_date")["pnl_usdt"].sum() if "exit_date" in df.columns else pd.Series()
    best_day = round(daily_pnl.max(), 1) if len(daily_pnl) > 0 else 0
    worst_day = round(daily_pnl.min(), 1) if len(daily_pnl) > 0 else 0

    kpi_html = _build_kpi_row([
        ("BTC Aligned%", round(aligned_pct, 1), "%"),
        ("Med Duration", round(hh.median(), 1) if len(hh) > 0 else 0, "h"),
        ("Best Day", best_day, " \u20ae"),
        ("Worst Day", worst_day, " \u20ae"),
    ])

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "Regime Performance (Avg R)",
            "BTC Alignment (Avg R)",
            "Trade Duration Distribution",
            "Daily PnL",
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.10,
    )

    # (1,1) Regime Performance — Avg R bar + median/n/WR%/PnL annotation
    if "market_regime" in df.columns and len(df) > 0:
        regimes = df.groupby("market_regime")
        labels, avgs, texts = [], [], []
        for regime, grp in regimes:
            r = grp["realized_r"].dropna()
            n = len(r)
            avg = r.mean() if n > 0 else 0.0
            med = r.median() if n > 0 else 0.0
            wr = (r > 0).mean() * 100 if n > 0 else 0.0
            pnl_sum = grp["pnl_usdt"].sum()
            labels.append(str(regime))
            avgs.append(avg)
            detail = f"WR={wr:.0f}% med={med:.2f} \u03a3${pnl_sum:.0f}"
            texts.append(low_sample_text(n, detail))
        fig.add_trace(
            go.Bar(x=labels, y=avgs, name="Regime Avg R",
                   marker_color=CLR_V6, text=texts, textposition="outside",
                   showlegend=False),
            row=1, col=1,
        )

    # (1,2) BTC Alignment — Avg R bar + median/n/WR%/PnL annotation
    if "btc_aligned" in df.columns and len(df) > 0:
        btc_colors_map = {"Aligned": CLR_WIN, "Counter": "orange", "Unknown": "gray"}
        btc_groups = df.groupby("btc_aligned")
        labels, avgs, colors_list, texts = [], [], [], []
        for label, grp in btc_groups:
            r = grp["realized_r"].dropna()
            n = len(r)
            avg = r.mean() if n > 0 else 0.0
            med = r.median() if n > 0 else 0.0
            wr = (r > 0).mean() * 100 if n > 0 else 0.0
            pnl_sum = grp["pnl_usdt"].sum()
            labels.append(str(label))
            avgs.append(avg)
            colors_list.append(btc_colors_map.get(str(label), "orange"))
            detail = f"WR={wr:.0f}% med={med:.2f} \u03a3${pnl_sum:.0f}"
            texts.append(low_sample_text(n, detail))
        fig.add_trace(
            go.Bar(x=labels, y=avgs, name="BTC Align Avg R",
                   marker_color=colors_list, text=texts, textposition="outside",
                   showlegend=False),
            row=1, col=2,
        )

    # (2,1) Trade Duration histogram — by Tier
    if "holding_hours" in df.columns and "signal_tier" in df.columns:
        tier_colors = TIER_COLORS
        hh_all = df["holding_hours"].dropna()
        if len(hh_all) > 0:
            # Shared bin edges across all tiers
            _, edges = np.histogram(hh_all.values, bins=30)
            for tier in ["A", "B", "C"]:
                sub = df[df["signal_tier"] == tier]["holding_hours"].dropna()
                if len(sub) == 0:
                    continue
                counts, _ = np.histogram(sub.values, bins=edges)
                centers = ((edges[:-1] + edges[1:]) / 2).tolist()
                width = float(edges[1] - edges[0])
                med_h = float(sub.median())
                fig.add_trace(
                    go.Bar(x=centers, y=counts.tolist(), width=width * 0.9,
                           name=f"Tier {tier} (med={med_h:.0f}h)",
                           marker_color=tier_colors.get(tier, "mediumpurple"),
                           opacity=0.75),
                    row=2, col=1,
                )
            fig.update_layout(barmode="overlay")
    elif "holding_hours" in df.columns:
        hh = df["holding_hours"].dropna()
        if len(hh) > 0:
            fig.add_trace(
                hist_as_bar(hh.values, nbins=30, name="Holding Hours",
                            marker_color="mediumpurple", showlegend=False),
                row=2, col=1,
            )

    # (2,2) Daily PnL bar
    if "exit_date" in df.columns and "pnl_usdt" in df.columns and len(df) > 0:
        daily = df.groupby("exit_date")["pnl_usdt"].sum().sort_index()
        colors = [CLR_WIN if v >= 0 else CLR_LOSS for v in daily.values]
        fig.add_trace(
            go.Bar(x=[str(d) for d in daily.index], y=daily.values.tolist(),
                   name="Daily PnL", marker_color=colors, showlegend=False),
            row=2, col=2,
        )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=PANEL_BG,
        plot_bgcolor=PANEL_BG,
        height=700,
        margin=dict(l=60, r=20, t=80, b=60),
        font=dict(color=TEXT_COLOR),
        showlegend=True,
    )

    apply_typography(fig)
    chart_html = fig.to_html(full_html=False, include_plotlyjs=False)
    return kpi_html, chart_html


# ---------------------------------------------------------------------------
# R5 Monitor tab
# ---------------------------------------------------------------------------

def _r5_start_timestamp(args):
    start = pd.to_datetime(getattr(args, "r5_start", R5_START), errors="coerce")
    if pd.isna(start):
        start = pd.Timestamp(R5_START)
    if getattr(start, "tzinfo", None) is not None:
        start = start.tz_convert("UTC").tz_localize(None)
    return start


def build_r5_monitor_tab(df, args):
    """Returns (kpi_html, chart_html) for the Neutral Arbiter forward sample."""
    r5_start = _r5_start_timestamp(args)
    if len(df) > 0:
        r5_df = df[df["exit_time"] >= r5_start].copy()
    else:
        r5_df = df.copy()

    metrics = compute_metrics(r5_df)
    v54_df = r5_df[r5_df["strategy"] == "V54"] if "strategy" in r5_df.columns else pd.DataFrame()
    r = r5_df["realized_r"].dropna() if "realized_r" in r5_df.columns else pd.Series(dtype="float64")
    wr = (r > 0).mean() * 100 if len(r) > 0 else 0.0
    last_exit = ""
    if len(r5_df) > 0 and r5_df["exit_time"].notna().any():
        last_exit = str(r5_df["exit_time"].max())[:16]

    kpi_html = _build_kpi_row([
        ("R5 Closed Trades", len(r5_df), ""),
        ("V54 Trades", len(v54_df), ""),
        ("WR%", round(wr, 1), "%"),
        ("PF", round(metrics["profit_factor"], 2), ""),
        ("PnL", round(r5_df["pnl_usdt"].fillna(0).sum(), 2) if "pnl_usdt" in r5_df.columns else 0, " \u20ae"),
        ("Max DD", round(metrics["max_dd"], 2), " \u20ae"),
    ], height=150)

    has_arbiter_trade_fields = (
        "arbiter_label" in r5_df.columns
        and r5_df["arbiter_label"].notna().any()
    )
    note_lines = [
        f"R5 start: {r5_start.date()}",
        "Candidate: V54 + Neutral Arbiter only; Macro Overlay off.",
        "This DB view is closed-trades based. Arbiter blocked-entry counts are not available unless runtime later persists arbiter audit fields.",
    ]
    if last_exit:
        note_lines.append(f"Last closed trade in R5 sample: {last_exit}.")
    if has_arbiter_trade_fields:
        note_lines.append("Arbiter trade fields detected in DB; the lower-right chart uses persisted arbiter labels.")
    note_html = "<div class=\"note-panel\">" + "<br>".join(note_lines) + "</div>"

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "R5 Cumulative PnL",
            "Realized R by Symbol",
            "Exit Reasons",
            "Arbiter / Regime Coverage",
        ],
        vertical_spacing=0.13,
        horizontal_spacing=0.10,
    )

    if len(r5_df) == 0:
        fig.add_annotation(
            text="No closed R5 trades yet. This is normal early in testnet.",
            xref="paper", yref="paper", x=0.5, y=0.55, showarrow=False,
            font=dict(color=TEXT_COLOR, size=16),
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=r5_df["exit_time"].tolist(),
                y=r5_df["pnl_usdt"].fillna(0).cumsum().tolist(),
                mode="lines+markers",
                name="R5 Cum PnL",
                line=dict(color="#5bc8f5", width=2),
            ),
            row=1, col=1,
        )

        by_symbol = r5_df.groupby("symbol")["realized_r"].mean().sort_values()
        colors = [CLR_WIN if v >= 0 else CLR_LOSS for v in by_symbol.values]
        fig.add_trace(
            go.Bar(
                x=by_symbol.index.tolist(),
                y=by_symbol.values.tolist(),
                marker_color=colors,
                name="Avg R",
                showlegend=False,
            ),
            row=1, col=2,
        )

        exit_counts = r5_df["exit_reason"].fillna("UNKNOWN").value_counts()
        fig.add_trace(
            go.Bar(
                x=exit_counts.index.tolist(),
                y=exit_counts.values.tolist(),
                marker_color=CLR_V54,
                name="Exit Count",
                showlegend=False,
            ),
            row=2, col=1,
        )

        if has_arbiter_trade_fields:
            labels = r5_df["arbiter_label"].fillna("UNKNOWN").value_counts()
            fig.add_trace(
                go.Bar(
                    x=labels.index.tolist(),
                    y=labels.values.tolist(),
                    marker_color=CLR_GRID,
                    name="Arbiter Label",
                    showlegend=False,
                ),
                row=2, col=2,
            )
        elif "market_regime" in r5_df.columns:
            regimes = r5_df["market_regime"].fillna("UNKNOWN").value_counts()
            fig.add_trace(
                go.Bar(
                    x=regimes.index.tolist(),
                    y=regimes.values.tolist(),
                    marker_color=CLR_OTHER,
                    name="Trade Regime",
                    showlegend=False,
                ),
                row=2, col=2,
            )
            fig.add_annotation(
                text="Blocked-entry audit is not in performance.db",
                xref="x4 domain", yref="y4 domain", x=0.5, y=1.08,
                showarrow=False, font=dict(color="#f6d365", size=12),
            )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=PANEL_BG,
        plot_bgcolor=PANEL_BG,
        height=720,
        margin=dict(l=60, r=20, t=80, b=60),
        font=dict(color=TEXT_COLOR),
        showlegend=True,
    )

    apply_typography(fig)
    chart_html = fig.to_html(full_html=False, include_plotlyjs=False)
    return kpi_html + note_html, chart_html


# ---------------------------------------------------------------------------
# Task 7b: build_trades_tab(df)
# ---------------------------------------------------------------------------

def build_trades_tab(df):
    """Returns HTML table listing all trades with GMT+8 timestamps."""
    from datetime import timezone as tz

    gmt8 = tz(timedelta(hours=8))

    rows_html = []
    for _, row in df.iterrows():
        symbol = str(row.get("symbol", ""))

        # Timestamps → GMT+8
        entry_t = row.get("entry_time")
        if isinstance(entry_t, str):
            entry_t = pd.to_datetime(entry_t, errors="coerce", utc=True)
        elif isinstance(entry_t, pd.Timestamp) and entry_t.tzinfo is None:
            entry_t = entry_t.tz_localize("UTC")
        exit_t = row.get("exit_time")
        if isinstance(exit_t, pd.Timestamp) and exit_t.tzinfo is None:
            exit_t = exit_t.tz_localize("UTC")

        entry_str = entry_t.astimezone(gmt8).strftime("%m-%d %H:%M") if pd.notna(entry_t) else ""
        exit_str = exit_t.astimezone(gmt8).strftime("%m-%d %H:%M") if pd.notna(exit_t) else ""

        # Notional: use original_size if available (V5.3 partial close), else total_size
        size = row.get("original_size")
        if pd.isna(size) or size is None or size == 0:
            size = row.get("total_size", 0)
        entry_price = row.get("entry_price", 0) or 0
        entry_notional = entry_price * size

        pnl = row.get("pnl_usdt", 0) or 0
        exit_notional = entry_notional + pnl

        # Total change %
        if entry_notional != 0:
            total_chg = (pnl / entry_notional) * 100
        else:
            total_chg = 0.0

        pnl_class = "positive" if pnl >= 0 else "negative"
        chg_class = "positive" if total_chg >= 0 else "negative"
        pnl_sign = "+" if pnl >= 0 else ""
        chg_sign = "+" if total_chg >= 0 else ""

        # Size display (original_size for V5.3, total_size fallback)
        size_str = f"{size:,.0f}" if size == int(size) else f"{size:,.2f}"

        exit_price = row.get("exit_price", 0) or 0

        # data-val for sorting: use raw numeric values
        entry_ts = entry_t.timestamp() if pd.notna(entry_t) else 0
        exit_ts = exit_t.timestamp() if pd.notna(exit_t) else 0

        strategy = row.get("strategy", "")
        strat_class = strategy_css_class(strategy)

        side = str(row.get("side", "")).upper()
        side_class = "side-long" if side == "LONG" else "side-short" if side == "SHORT" else ""
        tier = str(row.get("signal_tier", "") or "")
        tier_class = f"tier-{tier.lower()}" if tier in ("A", "B", "C") else ""
        realized_r = row.get("realized_r", 0) or 0
        r_class = "positive" if realized_r > 0 else "negative" if realized_r < 0 else ""
        r_sign = "+" if realized_r > 0 else ""
        exit_reason = str(row.get("exit_reason", "") or "")

        rows_html.append(
            f'<tr>'
            f'<td data-val="{symbol}">{symbol}</td>'
            f'<td data-val="{strategy}" class="{strat_class}">{strategy}</td>'
            f'<td data-val="{side}" class="{side_class}">{side}</td>'
            f'<td data-val="{tier}" class="{tier_class}">{tier}</td>'
            f'<td data-val="{entry_ts}">{entry_str}</td>'
            f'<td data-val="{exit_ts}">{exit_str}</td>'
            f'<td class="num" data-val="{size}">{size_str}</td>'
            f'<td class="num" data-val="{entry_price}">{entry_price:,.4f}</td>'
            f'<td class="num" data-val="{exit_price}">{exit_price:,.4f}</td>'
            f'<td class="num" data-val="{entry_notional}">{entry_notional:,.2f}</td>'
            f'<td class="num" data-val="{exit_notional}">{exit_notional:,.2f}</td>'
            f'<td class="num {pnl_class}" data-val="{pnl}">{pnl_sign}{pnl:,.2f}</td>'
            f'<td class="num {r_class}" data-val="{realized_r}">{r_sign}{realized_r:.2f}R</td>'
            f'<td class="num {chg_class}" data-val="{total_chg}">{chg_sign}{total_chg:.2f}%</td>'
            f'<td data-val="{exit_reason}">{exit_reason}</td>'
            f'</tr>'
        )

    table_body = "\n".join(rows_html)

    return f"""
<div class="trades-toolbar">
  <input type="text" id="trades-search" placeholder="Search symbol..."
         onkeyup="filterTrades()" />
  <span id="trades-count">{len(rows_html)} trades</span>
</div>
<div class="trades-wrapper">
<table class="trades-table" id="trades-table">
  <thead>
    <tr>
      <th class="sortable" onclick="sortTable(0)">Symbol</th>
      <th class="sortable" onclick="sortTable(1)">Strategy</th>
      <th class="sortable" onclick="sortTable(2)">Side</th>
      <th class="sortable" onclick="sortTable(3)">Tier</th>
      <th class="sortable" onclick="sortTable(4)">Entry Time</th>
      <th class="sortable" onclick="sortTable(5)">Exit Time</th>
      <th class="r sortable" onclick="sortTable(6)">Size</th>
      <th class="r sortable" onclick="sortTable(7)">Entry Price</th>
      <th class="r sortable" onclick="sortTable(8)">Exit Price</th>
      <th class="r sortable" onclick="sortTable(9)">Entry (USDT)</th>
      <th class="r sortable" onclick="sortTable(10)">Exit (USDT)</th>
      <th class="r sortable" onclick="sortTable(11)">PnL (USDT)</th>
      <th class="r sortable" onclick="sortTable(12)">R</th>
      <th class="r sortable" onclick="sortTable(13)">Total Chg</th>
      <th class="sortable" onclick="sortTable(14)">Exit Reason</th>
    </tr>
  </thead>
  <tbody>
    {table_body}
  </tbody>
</table>
</div>
"""


# ---------------------------------------------------------------------------
# Task 8: build_html()
# ---------------------------------------------------------------------------

def build_html(df, metrics, args, prev_metrics=None, r5_df=None):
    """Assembles all tabs into a single dark-themed HTML file."""

    kpi_html, overview_chart_html = build_overview_tab(df, metrics, prev_metrics)
    r5_kpi_html, r5_chart_html = build_r5_monitor_tab(r5_df if r5_df is not None else df, args)
    strat_kpi_html, strategy_chart_html = build_strategy_tab(df)
    risk_kpi_html, risk_chart_html = build_risk_tab(df)
    market_kpi_html, market_chart_html = build_market_tab(df)
    trades_html = build_trades_tab(df)

    # Period label
    if getattr(args, "all_data", False):
        period_label = f"All trades since {DATA_CUTOFF}"
    else:
        period_label = f"Last {args.days} days"
        if prev_metrics:
            period_label += f" (delta vs prev {args.days}d: {prev_metrics['total_trades']} trades)"

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    subtitle = f"{period_label} | {metrics['total_trades']} trades | {timestamp}"

    css = f"""
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background-color: {DARK_BG};
    color: {TEXT_COLOR};
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    padding: 0;
    overflow-x: hidden;
  }}
  .header {{
    background-color: {ACCENT};
    padding: 20px 30px 16px;
    border-bottom: 2px solid #0a2742;
  }}
  .header h1 {{
    font-size: 2rem;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 2px;
  }}
  .header p {{
    font-size: 0.9rem;
    color: #a0b4c8;
    margin-top: 4px;
  }}
  .tab-bar {{
    display: flex;
    background-color: {PANEL_BG};
    padding: 0 20px;
    border-bottom: 1px solid #0a2742;
  }}
  .tab-btn {{
    padding: 14px 28px;
    cursor: pointer;
    font-size: 0.95rem;
    color: #a0b4c8;
    border: none;
    background: none;
    border-bottom: 3px solid transparent;
    transition: all 0.2s;
    font-weight: 500;
  }}
  .tab-btn:hover {{
    color: #ffffff;
    background-color: rgba(255,255,255,0.05);
  }}
  .tab-btn.active {{
    color: #5bc8f5;
    border-bottom: 3px solid #5bc8f5;
  }}
  .tab-content {{
    display: none;
    padding: 20px 24px;
  }}
  .tab-content.active {{
    display: block;
  }}
  .kpi-section {{
    margin-bottom: 16px;
    background-color: {PANEL_BG};
    border-radius: 8px;
    padding: 8px;
  }}
  .chart-section {{
    background-color: {PANEL_BG};
    border-radius: 8px;
    padding: 8px;
  }}
  .chart-section-full {{
    background-color: {PANEL_BG};
    border-radius: 8px;
    padding: 8px;
    margin-top: 0;
  }}
  .note-panel {{
    background: rgba(15, 52, 96, 0.65);
    border: 1px solid rgba(91, 200, 245, 0.25);
    border-radius: 8px;
    color: #d8e9f8;
    font-size: 0.9rem;
    line-height: 1.55;
    margin: 0 0 12px;
    padding: 12px 16px;
  }}
  .trades-toolbar {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 10px;
  }}
  .trades-toolbar input {{
    background: {PANEL_BG};
    border: 1px solid #0a2742;
    color: {TEXT_COLOR};
    padding: 8px 14px;
    border-radius: 6px;
    font-size: 0.85rem;
    width: 220px;
    outline: none;
  }}
  .trades-toolbar input:focus {{
    border-color: #5bc8f5;
  }}
  .trades-toolbar span {{
    color: #a0b4c8;
    font-size: 0.8rem;
  }}
  .trades-wrapper {{
    overflow-x: auto;
    max-height: 600px;
    overflow-y: auto;
  }}
  .trades-table {{
    border-collapse: collapse;
    font-size: 0.85rem;
    white-space: nowrap;
    width: 100%;
  }}
  .sortable {{
    cursor: pointer;
    user-select: none;
  }}
  .sortable:hover {{
    background-color: rgba(255,255,255,0.1) !important;
  }}
  .sortable::after {{
    content: " \u2195";
    opacity: 0.4;
    font-size: 0.7rem;
  }}
  .sort-asc::after {{
    content: " \u2191";
    opacity: 1;
  }}
  .sort-desc::after {{
    content: " \u2193";
    opacity: 1;
  }}
  .trades-table th, .trades-table td {{
    padding: 8px 16px;
  }}
  .trades-table th {{
    background-color: {ACCENT};
    color: #ffffff;
    text-align: left;
    position: sticky;
    top: 0;
    z-index: 1;
  }}
  .trades-table th.r {{ text-align: right; }}
  .trades-table td {{
    border-bottom: 1px solid #0a2742;
  }}
  .trades-table tr:hover {{
    background-color: rgba(255,255,255,0.04);
  }}
  .trades-table .num {{
    text-align: right;
    font-variant-numeric: tabular-nums;
  }}
  .trades-table .positive {{
    color: {CLR_WIN};
  }}
  .trades-table .negative {{
    color: {CLR_LOSS};
  }}
  .trades-table .strat-v7 {{
    color: #ff8c42;
    font-weight: 600;
  }}
  .trades-table .strat-v54 {{
    color: {CLR_V54};
    font-weight: 600;
  }}
  .trades-table .strat-v6 {{
    color: #5b8cf5;
    font-weight: 600;
  }}
  .trades-table .strat-v53 {{
    color: #66bb6a;
    font-weight: 600;
  }}
  .trades-table .strat-grid {{
    color: {CLR_GRID};
    font-weight: 600;
  }}
  .trades-table .side-long {{
    color: {CLR_WIN};
  }}
  .trades-table .side-short {{
    color: {CLR_LOSS};
  }}
  .trades-table .tier-a {{
    color: {CLR_TIER_A};
    font-weight: 700;
  }}
  .trades-table .tier-b {{
    color: {CLR_TIER_B};
  }}
  .trades-table .tier-c {{
    color: {CLR_TIER_C};
  }}
</style>
"""

    js = """
<script>
  function showTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(function(el) {
      el.classList.remove('active');
    });
    document.querySelectorAll('.tab-btn').forEach(function(el) {
      el.classList.remove('active');
    });
    document.getElementById(tabId).classList.add('active');
    event.currentTarget.classList.add('active');
    setTimeout(function() {
      var tabEl = document.getElementById(tabId);
      if (tabEl) {
        tabEl.querySelectorAll('.js-plotly-plot').forEach(function(plot) {
          Plotly.Plots.resize(plot);
        });
      }
    }, 100);
  }

  // --- Trades Tab: Sort & Filter ---
  var _sortCol = -1, _sortAsc = true;
  function sortTable(colIdx) {
    var table = document.getElementById('trades-table');
    var tbody = table.tBodies[0];
    var rows = Array.from(tbody.rows);
    var th = table.tHead.rows[0].cells[colIdx];
    // Toggle direction
    if (_sortCol === colIdx) { _sortAsc = !_sortAsc; }
    else { _sortCol = colIdx; _sortAsc = true; }
    // Clear sort indicators
    Array.from(table.tHead.rows[0].cells).forEach(function(c) {
      c.classList.remove('sort-asc', 'sort-desc');
    });
    th.classList.add(_sortAsc ? 'sort-asc' : 'sort-desc');
    // Sort
    var isNum = (colIdx >= 6 && colIdx <= 13); // columns 6-13 are numeric
    rows.sort(function(a, b) {
      var av = a.cells[colIdx].getAttribute('data-val');
      var bv = b.cells[colIdx].getAttribute('data-val');
      if (isNum) { av = parseFloat(av) || 0; bv = parseFloat(bv) || 0; }
      else { av = av.toLowerCase(); bv = bv.toLowerCase(); }
      if (av < bv) return _sortAsc ? -1 : 1;
      if (av > bv) return _sortAsc ? 1 : -1;
      return 0;
    });
    rows.forEach(function(r) { tbody.appendChild(r); });
  }

  function filterTrades() {
    var q = document.getElementById('trades-search').value.toLowerCase();
    var table = document.getElementById('trades-table');
    var rows = table.tBodies[0].rows;
    var visible = 0;
    for (var i = 0; i < rows.length; i++) {
      var text = rows[i].cells[0].textContent.toLowerCase();
      var show = text.indexOf(q) !== -1;
      rows[i].style.display = show ? '' : 'none';
      if (show) visible++;
    }
    document.getElementById('trades-count').textContent = visible + ' trades';
  }
</script>
"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>quantDashboard</title>
  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
  {css}
</head>
<body>

<div class="header">
  <h1>quantDashboard</h1>
  <p>{subtitle}</p>
</div>

<div class="tab-bar">
  <button class="tab-btn active" onclick="showTab('tab-overview')">Overview</button>
  <button class="tab-btn" onclick="showTab('tab-r5')">R5 Monitor</button>
  <button class="tab-btn" onclick="showTab('tab-strategy')">Strategy</button>
  <button class="tab-btn" onclick="showTab('tab-risk')">Risk</button>
  <button class="tab-btn" onclick="showTab('tab-market')">Market</button>
  <button class="tab-btn" onclick="showTab('tab-trades')">Trades</button>
</div>

<div id="tab-overview" class="tab-content active">
  <div class="kpi-section">
    {kpi_html}
  </div>
  <div class="chart-section">
    {overview_chart_html}
  </div>
</div>

<div id="tab-r5" class="tab-content">
  <div class="kpi-section">
    {r5_kpi_html}
  </div>
  <div class="chart-section">
    {r5_chart_html}
  </div>
</div>

<div id="tab-strategy" class="tab-content">
  <div class="kpi-section">
    {strat_kpi_html}
  </div>
  <div class="chart-section">
    {strategy_chart_html}
  </div>
</div>

<div id="tab-risk" class="tab-content">
  <div class="kpi-section">
    {risk_kpi_html}
  </div>
  <div class="chart-section">
    {risk_chart_html}
  </div>
</div>

<div id="tab-market" class="tab-content">
  <div class="kpi-section">
    {market_kpi_html}
  </div>
  <div class="chart-section">
    {market_chart_html}
  </div>
</div>

<div id="tab-trades" class="tab-content">
  <div class="chart-section-full">
    {trades_html}
  </div>
</div>

{js}
</body>
</html>
"""

    out_path = getattr(args, "out", OUTPUT_PATH)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Dashboard written to: {out_path}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = parse_args()
    df = load_trades(days=args.days, all_data=getattr(args, "all_data", False),
                     db_path=args.db)
    metrics = compute_metrics(df)

    # Load previous period for comparison
    prev_df = load_prev_period(days=args.days,
                               all_data=getattr(args, "all_data", False),
                               db_path=args.db)
    prev_metrics = compute_metrics(prev_df) if prev_df is not None else None

    r5_source_df = df if getattr(args, "all_data", False) else load_trades(
        all_data=True,
        db_path=args.db,
    )

    build_html(df, metrics, args, prev_metrics, r5_df=r5_source_df)
    print(
        f"Done: {len(df)} trades | "
        f"WR={metrics['win_rate']:.1%} | "
        f"PF={metrics['profit_factor']:.2f} | "
        f"Sharpe={metrics['sharpe']:.2f}"
    )
    if prev_metrics:
        print(
            f"Prev: {prev_metrics['total_trades']} trades | "
            f"WR={prev_metrics['win_rate']:.1%} | "
            f"PF={prev_metrics['profit_factor']:.2f}"
        )
