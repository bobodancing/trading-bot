# quantDashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** One-click dashboard that pulls perf DB from rwUbuntu and generates interactive Plotly HTML for daily trading bot monitoring.

**Architecture:** `run.sh` pulls SQLite DB via SCP, runs `build_dashboard.py` which reads DB with pandas, computes metrics, generates 4-tab Plotly HTML, then opens browser. No server needed.

**Tech Stack:** Python, pandas, plotly, sqlite3, sshpass (SCP), bash

---

### Task 1: run.sh — One-Click Entry Point

**Files:**
- Create: `tools/quantDashboard/run.sh`
- Create: `tools/quantDashboard/.gitignore`

**Step 1: Create .gitignore**

```
v6_performance.db
dashboard.html
```

**Step 2: Write run.sh**

```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

REMOTE="rwfunder@100.67.114.104"
REMOTE_DB="/home/rwfunder/文件/tradingbot/trading_bot_v6/v6_performance.db"
LOCAL_DB="$SCRIPT_DIR/v6_performance.db"

echo "=== quantDashboard ==="
echo "[1/3] Pulling v6_performance.db from rwUbuntu..."
sshpass -p "0602" scp "$REMOTE:$REMOTE_DB" "$LOCAL_DB"
echo "      Done ($(du -h "$LOCAL_DB" | cut -f1))"

echo "[2/3] Building dashboard..."
python "$SCRIPT_DIR/build_dashboard.py" "$@"

echo "[3/3] Opening dashboard..."
start dashboard.html

echo "=== Done ==="
```

**Step 3: Make executable and test SCP**

Run: `chmod +x tools/quantDashboard/run.sh`
Then: `cd tools/quantDashboard && sshpass -p "0602" scp rwfunder@100.67.114.104:"/home/rwfunder/文件/tradingbot/trading_bot_v6/v6_performance.db" ./v6_performance.db`
Expected: DB file pulled successfully, check with `ls -la v6_performance.db`

**Step 4: Commit**

```bash
git add tools/quantDashboard/run.sh tools/quantDashboard/.gitignore
git commit -m "feat(quantDashboard): add run.sh entry point and gitignore"
```

---

### Task 2: build_dashboard.py — DB Loading + CLI Args

**Files:**
- Create: `tools/quantDashboard/build_dashboard.py`

**Step 1: Write DB loader with CLI args**

```python
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent / "v6_performance.db"
OUTPUT_PATH = Path(__file__).parent / "dashboard.html"
DATA_CUTOFF = "2025-02-25"


def parse_args():
    parser = argparse.ArgumentParser(description="quantDashboard builder")
    parser.add_argument("--days", type=int, default=7, help="Days of data (default: 7)")
    parser.add_argument("--all", action="store_true", help="All data (post 2025-02-25)")
    return parser.parse_args()


def load_trades(days=7, all_data=False):
    conn = sqlite3.connect(DB_PATH)

    if all_data:
        query = "SELECT * FROM trades WHERE exit_time >= ? ORDER BY exit_time"
        df = pd.read_sql_query(query, conn, params=[DATA_CUTOFF])
    else:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        query = "SELECT * FROM trades WHERE exit_time >= ? ORDER BY exit_time"
        df = pd.read_sql_query(query, conn, params=[cutoff])

    conn.close()

    if len(df) == 0:
        raise SystemExit(f"No trades found (filter: {'all' if all_data else f'{days}d'})")

    # Type conversions
    df["exit_time"] = pd.to_datetime(df["exit_time"])
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    df["strategy"] = df["is_v6_pyramid"].map({1: "V6", 0: "V53"})
    df["btc_aligned"] = df["btc_trend_aligned"].map({1: "Aligned", 0: "Counter", None: "Unknown"})
    df["exit_date"] = df["exit_time"].dt.date

    return df


if __name__ == "__main__":
    args = parse_args()
    df = load_trades(days=args.days, all_data=args.all)
    print(f"Loaded {len(df)} trades")
```

**Step 2: Test DB loading**

Run: `cd tools/quantDashboard && python build_dashboard.py --all`
Expected: `Loaded N trades` (N > 0)

Run: `python build_dashboard.py --days 7`
Expected: `Loaded N trades` or exits with "No trades found"

**Step 3: Commit**

```bash
git add tools/quantDashboard/build_dashboard.py
git commit -m "feat(quantDashboard): DB loader with CLI args"
```

---

### Task 3: Metrics Calculation

**Files:**
- Modify: `tools/quantDashboard/build_dashboard.py`

**Step 1: Add metrics function after load_trades**

```python
def compute_metrics(df):
    """Compute all KPI metrics from trade DataFrame."""
    r = df["realized_r"]
    pnl = df["pnl_pct"] / 100

    wins = r[r > 0]
    losses = r[r <= 0]

    wr = (r > 0).mean()
    avg_r = r.mean()

    gross_profit = df.loc[df["pnl_usdt"] > 0, "pnl_usdt"].sum()
    gross_loss = df.loc[df["pnl_usdt"] <= 0, "pnl_usdt"].sum()
    pf = gross_profit / abs(gross_loss) if gross_loss != 0 else float("inf")

    sharpe = pnl.mean() / pnl.std() if pnl.std() != 0 else 0

    expectancy = wr * wins.mean() + (1 - wr) * losses.mean() if len(losses) > 0 else wins.mean()

    equity = (1 + pnl).cumprod()
    drawdown = equity / equity.cummax() - 1
    max_dd = drawdown.min()

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
```

**Step 2: Wire into main**

```python
if __name__ == "__main__":
    args = parse_args()
    df = load_trades(days=args.days, all_data=args.all)
    metrics = compute_metrics(df)
    print(f"Loaded {len(df)} trades | WR={metrics['win_rate']:.1%} | PF={metrics['profit_factor']:.2f} | Sharpe={metrics['sharpe']:.2f}")
```

**Step 3: Test**

Run: `python build_dashboard.py --all`
Expected: prints summary with WR/PF/Sharpe values

**Step 4: Commit**

```bash
git add tools/quantDashboard/build_dashboard.py
git commit -m "feat(quantDashboard): metrics calculation (WR/PF/Sharpe/Expectancy/DD)"
```

---

### Task 4: Tab 1 — Overview

**Files:**
- Modify: `tools/quantDashboard/build_dashboard.py`

**Step 1: Add imports and KPI card helper**

```python
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def make_kpi_card(label, value, fmt=".2f"):
    """Create a single KPI indicator trace."""
    return go.Indicator(
        mode="number",
        title={"text": label},
        value=value,
        number={"valueformat": fmt},
    )
```

**Step 2: Add Tab 1 builder**

```python
def build_overview_tab(df, metrics):
    """Tab 1: Overview — KPIs + Equity + Drawdown + Rolling WR."""

    # KPI row (6 indicators)
    kpi_fig = make_subplots(
        rows=1, cols=6,
        specs=[[{"type": "indicator"}] * 6],
    )
    kpis = [
        ("Trades", metrics["total_trades"], "d"),
        ("Win Rate", metrics["win_rate"] * 100, ".1f"),
        ("Avg R", metrics["avg_r"], ".3f"),
        ("PF", metrics["profit_factor"], ".2f"),
        ("Sharpe", metrics["sharpe"], ".2f"),
        ("Max DD", metrics["max_dd"] * 100, ".1f"),
    ]
    for i, (label, val, fmt) in enumerate(kpis):
        kpi_fig.add_trace(make_kpi_card(label, val, fmt), row=1, col=i + 1)
    kpi_fig.update_layout(height=150, margin=dict(t=40, b=10, l=10, r=10))

    # Charts: Equity + Drawdown + Rolling WR
    chart_fig = make_subplots(rows=3, cols=1, subplot_titles=[
        "Equity Curve", "Drawdown", "Rolling Win Rate (30T)"
    ], vertical_spacing=0.08)

    chart_fig.add_trace(
        go.Scatter(x=df["exit_time"], y=metrics["equity"], name="Equity",
                   line=dict(color="#2196F3")),
        row=1, col=1
    )
    chart_fig.add_trace(
        go.Scatter(x=df["exit_time"], y=metrics["drawdown"], name="Drawdown",
                   fill="tozeroy", line=dict(color="#F44336")),
        row=2, col=1
    )

    rolling_wr = (df["realized_r"] > 0).rolling(30, min_periods=5).mean()
    chart_fig.add_trace(
        go.Scatter(x=df["exit_time"], y=rolling_wr, name="Rolling WR 30T",
                   line=dict(color="#FF9800")),
        row=3, col=1
    )
    chart_fig.update_layout(height=750, showlegend=False)

    return kpi_fig, chart_fig
```

**Step 3: Test by generating temp HTML**

Add to main:
```python
    kpi_fig, chart_fig = build_overview_tab(df, metrics)
    chart_fig.write_html("test_overview.html")
    print("test_overview.html written")
```

Run: `python build_dashboard.py --all`
Expected: `test_overview.html` generated, open manually to verify charts render.

**Step 4: Commit**

```bash
git add tools/quantDashboard/build_dashboard.py
git commit -m "feat(quantDashboard): Tab 1 Overview (KPIs + Equity + DD + Rolling WR)"
```

---

### Task 5: Tab 2 — Strategy

**Files:**
- Modify: `tools/quantDashboard/build_dashboard.py`

**Step 1: Add Tab 2 builder**

```python
def build_strategy_tab(df):
    """Tab 2: Strategy — V6 vs V53 comparison."""

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "Cumulative PnL by Strategy",
            "Stage Reached (V6)",
            "Tier Performance (Avg R)",
            "Tier Performance (Win Rate)",
        ],
        vertical_spacing=0.12,
        horizontal_spacing=0.1,
    )

    # Cumulative PnL by strategy
    for strat in ["V6", "V53"]:
        mask = df["strategy"] == strat
        if mask.any():
            cum_pnl = df.loc[mask, "pnl_usdt"].cumsum()
            fig.add_trace(
                go.Scatter(x=df.loc[mask, "exit_time"], y=cum_pnl, name=strat),
                row=1, col=1
            )

    # Stage reached (V6 only)
    v6 = df[df["strategy"] == "V6"]
    if len(v6) > 0:
        stage_counts = v6["stage_reached"].value_counts().sort_index()
        fig.add_trace(
            go.Bar(x=[f"Stage {s}" for s in stage_counts.index],
                   y=stage_counts.values, name="Stage", showlegend=False,
                   marker_color="#2196F3"),
            row=1, col=2
        )

    # Tier performance
    tier_stats = df.groupby(["signal_tier", "strategy"]).agg(
        avg_r=("realized_r", "mean"),
        wr=("realized_r", lambda x: (x > 0).mean()),
        count=("realized_r", "size"),
    ).reset_index()

    for strat in ["V6", "V53"]:
        mask = tier_stats["strategy"] == strat
        sub = tier_stats[mask]
        if len(sub) > 0:
            fig.add_trace(
                go.Bar(x=sub["signal_tier"], y=sub["avg_r"], name=f"{strat} avgR",
                       text=[f"n={c}" for c in sub["count"]], textposition="auto"),
                row=2, col=1
            )
            fig.add_trace(
                go.Bar(x=sub["signal_tier"], y=sub["wr"] * 100, name=f"{strat} WR%",
                       text=[f"n={c}" for c in sub["count"]], textposition="auto"),
                row=2, col=2
            )

    fig.update_layout(height=700, barmode="group")
    return fig
```

**Step 2: Commit**

```bash
git add tools/quantDashboard/build_dashboard.py
git commit -m "feat(quantDashboard): Tab 2 Strategy (V6/V53 + Tier + Stage)"
```

---

### Task 6: Tab 3 — Risk

**Files:**
- Modify: `tools/quantDashboard/build_dashboard.py`

**Step 1: Add Tab 3 builder**

```python
def build_risk_tab(df):
    """Tab 3: Risk — Exit analysis + MFE capture + SL quality."""

    fig = make_subplots(
        rows=2, cols=3,
        subplot_titles=[
            "Exit Reason Distribution", "Exit Reason EV (Avg R)", "Capture Ratio",
            "MFE vs Realized PnL", "SL Quality (MAE vs PnL)", "",
        ],
        vertical_spacing=0.12,
    )

    # Exit reason distribution
    exit_dist = df["exit_reason"].value_counts()
    fig.add_trace(
        go.Bar(x=exit_dist.index, y=exit_dist.values, showlegend=False,
               marker_color="#2196F3"),
        row=1, col=1
    )

    # Exit reason EV
    exit_ev = df.groupby("exit_reason")["realized_r"].mean().sort_values()
    colors = ["#4CAF50" if v > 0 else "#F44336" for v in exit_ev.values]
    fig.add_trace(
        go.Bar(x=exit_ev.index, y=exit_ev.values, showlegend=False,
               marker_color=colors),
        row=1, col=2
    )

    # Capture ratio histogram
    cap = df["capture_ratio"].dropna()
    cap = cap[(cap > -5) & (cap < 5)]  # filter outliers
    fig.add_trace(
        go.Histogram(x=cap, nbinsx=40, showlegend=False, marker_color="#FF9800"),
        row=1, col=3
    )

    # MFE vs Realized
    win_mask = df["realized_r"] > 0
    fig.add_trace(
        go.Scatter(x=df.loc[win_mask, "mfe_pct"], y=df.loc[win_mask, "pnl_pct"],
                   mode="markers", name="Win", marker=dict(color="#4CAF50", size=6)),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.loc[~win_mask, "mfe_pct"], y=df.loc[~win_mask, "pnl_pct"],
                   mode="markers", name="Loss", marker=dict(color="#F44336", size=6)),
        row=2, col=1
    )

    # SL Quality
    sl = df[df["exit_reason"].str.contains("sl_hit|stop", case=False, na=False)]
    if len(sl) > 0:
        fig.add_trace(
            go.Scatter(x=sl["mae_pct"], y=sl["pnl_pct"], mode="markers",
                       showlegend=False, marker=dict(color="#9C27B0", size=6)),
            row=2, col=2
        )

    fig.update_layout(height=700)
    return fig
```

**Step 2: Commit**

```bash
git add tools/quantDashboard/build_dashboard.py
git commit -m "feat(quantDashboard): Tab 3 Risk (Exit EV + MFE capture + SL quality)"
```

---

### Task 7: Tab 4 — Market

**Files:**
- Modify: `tools/quantDashboard/build_dashboard.py`

**Step 1: Add Tab 4 builder**

```python
def build_market_tab(df):
    """Tab 4: Market — Regime + BTC alignment + Duration + Daily PnL."""

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "Regime Performance", "BTC Alignment",
            "Trade Duration (hours)", "Daily PnL (USDT)",
        ],
        vertical_spacing=0.12,
    )

    # Regime performance
    regime = df.groupby("market_regime").agg(
        wr=("realized_r", lambda x: (x > 0).mean()),
        avg_r=("realized_r", "mean"),
        count=("realized_r", "size"),
    ).reset_index()
    if len(regime) > 0:
        fig.add_trace(
            go.Bar(x=regime["market_regime"], y=regime["avg_r"],
                   name="Avg R", text=[f"WR={w:.0%} n={c}" for w, c in zip(regime["wr"], regime["count"])],
                   textposition="auto", marker_color="#2196F3"),
            row=1, col=1
        )

    # BTC alignment
    btc = df.groupby("btc_aligned").agg(
        wr=("realized_r", lambda x: (x > 0).mean()),
        avg_r=("realized_r", "mean"),
        count=("realized_r", "size"),
    ).reset_index()
    if len(btc) > 0:
        fig.add_trace(
            go.Bar(x=btc["btc_aligned"], y=btc["avg_r"],
                   name="Avg R", text=[f"WR={w:.0%} n={c}" for w, c in zip(btc["wr"], btc["count"])],
                   textposition="auto", marker_color="#FF9800"),
            row=1, col=2
        )

    # Duration histogram
    fig.add_trace(
        go.Histogram(x=df["holding_hours"], nbinsx=40, showlegend=False,
                     marker_color="#9C27B0"),
        row=2, col=1
    )

    # Daily PnL
    daily = df.groupby("exit_date")["pnl_usdt"].sum().reset_index()
    colors = ["#4CAF50" if v > 0 else "#F44336" for v in daily["pnl_usdt"]]
    fig.add_trace(
        go.Bar(x=daily["exit_date"], y=daily["pnl_usdt"], showlegend=False,
               marker_color=colors),
        row=2, col=2
    )

    fig.update_layout(height=700)
    return fig
```

**Step 2: Commit**

```bash
git add tools/quantDashboard/build_dashboard.py
git commit -m "feat(quantDashboard): Tab 4 Market (Regime + BTC + Duration + Daily PnL)"
```

---

### Task 8: HTML Assembly — Combine All Tabs

**Files:**
- Modify: `tools/quantDashboard/build_dashboard.py`

**Step 1: Add HTML assembly function**

```python
def build_html(df, metrics, args):
    """Assemble all tabs into single HTML file."""
    kpi_fig, overview_fig = build_overview_tab(df, metrics)
    strategy_fig = build_strategy_tab(df)
    risk_fig = build_risk_tab(df)
    market_fig = build_market_tab(df)

    # Convert all figs to HTML divs
    kpi_html = kpi_fig.to_html(full_html=False, include_plotlyjs=False)
    overview_html = overview_fig.to_html(full_html=False, include_plotlyjs=False)
    strategy_html = strategy_fig.to_html(full_html=False, include_plotlyjs=False)
    risk_html = risk_fig.to_html(full_html=False, include_plotlyjs=False)
    market_html = market_fig.to_html(full_html=False, include_plotlyjs=False)

    period = "All (post 2025-02-25)" if args.all else f"Last {args.days} days"
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>quantDashboard</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #1a1a2e; color: #e0e0e0; }}
  h1 {{ text-align: center; color: #e0e0e0; margin-bottom: 5px; }}
  .subtitle {{ text-align: center; color: #888; margin-bottom: 20px; font-size: 14px; }}
  .tabs {{ display: flex; gap: 0; margin-bottom: 0; border-bottom: 2px solid #333; }}
  .tab {{ padding: 10px 24px; cursor: pointer; background: #16213e; border: 1px solid #333; border-bottom: none; border-radius: 6px 6px 0 0; color: #888; font-weight: 500; }}
  .tab.active {{ background: #0f3460; color: #e0e0e0; border-color: #555; }}
  .tab-content {{ display: none; padding: 20px 0; }}
  .tab-content.active {{ display: block; }}
  .kpi-row {{ margin-bottom: 10px; }}
</style>
</head>
<body>
<h1>quantDashboard</h1>
<p class="subtitle">{period} | {metrics['total_trades']} trades | Generated {now}</p>

<div class="tabs">
  <div class="tab active" onclick="showTab('overview')">Overview</div>
  <div class="tab" onclick="showTab('strategy')">Strategy</div>
  <div class="tab" onclick="showTab('risk')">Risk</div>
  <div class="tab" onclick="showTab('market')">Market</div>
</div>

<div id="overview" class="tab-content active">
  <div class="kpi-row">{kpi_html}</div>
  {overview_html}
</div>
<div id="strategy" class="tab-content">{strategy_html}</div>
<div id="risk" class="tab-content">{risk_html}</div>
<div id="market" class="tab-content">{market_html}</div>

<script>
function showTab(name) {{
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.getElementById(name).classList.add('active');
  event.target.classList.add('active');
  window.dispatchEvent(new Event('resize'));
}}
</script>
</body>
</html>"""

    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {OUTPUT_PATH}")
```

**Step 2: Update main**

```python
if __name__ == "__main__":
    args = parse_args()
    df = load_trades(days=args.days, all_data=args.all)
    metrics = compute_metrics(df)
    build_html(df, metrics, args)
    print(f"Loaded {len(df)} trades | WR={metrics['win_rate']:.1%} | PF={metrics['profit_factor']:.2f} | Sharpe={metrics['sharpe']:.2f}")
```

**Step 3: Full end-to-end test**

Run: `python build_dashboard.py --all`
Expected: `dashboard.html` generated, open manually, verify:
- 4 tabs work (click each)
- KPI cards show numbers
- Charts render with data
- Dark theme applied

**Step 4: Commit**

```bash
git add tools/quantDashboard/build_dashboard.py
git commit -m "feat(quantDashboard): HTML assembly with dark theme tabs"
```

---

### Task 9: End-to-End Test

**Step 1: Run full pipeline**

```bash
cd tools/quantDashboard
./run.sh --all
```

Expected:
1. DB pulled from rwUbuntu
2. Dashboard generated
3. Browser opens `dashboard.html`
4. All 4 tabs render correctly

**Step 2: Test default (7 days)**

```bash
./run.sh
```

Expected: Only recent trades shown, or "No trades found" if none in 7 days.

**Step 3: Test custom range**

```bash
./run.sh --days 30
```

Expected: 30 days of trades.

**Step 4: Fix any issues found during testing**

**Step 5: Final commit**

```bash
git add -A tools/quantDashboard/
git commit -m "feat(quantDashboard): complete v1 — one-click quant dashboard"
```
