# quantDashboard Design

Date: 2026-03-08

## Purpose

Daily monitoring dashboard for trading bot performance. One-click script: pull DB from rwUbuntu → generate interactive HTML → open browser.

## Architecture

```
tools/quantDashboard/
├── run.sh              # SCP pull DB → python build → open browser
├── build_dashboard.py  # SQLite → metrics → Plotly HTML
├── dashboard.html      # output (gitignore)
└── v6_performance.db   # pulled DB (gitignore)
```

## Data Source

- `v6_performance.db` (SQLite, 27 columns) via SCP from rwUbuntu
- NOT log files — DB is structured, complete, and has all Phase 1 fields
- Default: last 7 days (`--all` for everything, cutoff 2025-02-25 to exclude dirty data)

## CLI

```bash
./run.sh              # default: 7 days
./run.sh --all        # all data (post 2025-02-25)
./run.sh --days 14    # custom range
```

## Dependencies

```
pip install pandas plotly
```

No sklearn, no numpy (pandas covers it).

## Dashboard Tabs

### Tab 1: Overview
- KPI cards: Total Trades / Win Rate / Avg R / PF / Sharpe / Max DD
- Equity Curve (line)
- Drawdown Curve (area, red)
- Rolling Win Rate 30T (line)

### Tab 2: Strategy (V6 vs V53)
- Strategy KPI table (WR / avgR / PF / count per strategy)
- Cumulative PnL by Strategy (grouped bar)
- Tier Performance: avgR + WR per A/B/C, colored by strategy (grouped bar)
- Stage Reached distribution (stacked bar, V6 only)

### Tab 3: Risk
- Exit Reason distribution (bar)
- Exit Reason EV: avgR per reason, red/green (bar)
- MFE vs Realized scatter (x=mfe_pct, y=pnl_pct)
- Capture Ratio histogram
- SL Quality scatter (MAE vs PnL for stop_loss exits)

### Tab 4: Market
- Regime Performance: WR + avgR per STRONG/TRENDING (grouped bar)
- BTC Alignment: WR + avgR for aligned vs not (grouped bar)
- Trade Duration histogram (holding_hours)
- Daily PnL (bar, grouped by date)

## Metrics Formulas

```python
# Win Rate
wr = (realized_r > 0).mean()

# Profit Factor
pf = gross_profit / abs(gross_loss)

# Sharpe (trade-based, no annualization)
sharpe = returns.mean() / returns.std()

# Expectancy
expectancy = wr * avg_win_r + (1 - wr) * avg_loss_r

# Max Drawdown
equity = (1 + pnl_pct/100).cumprod()
drawdown = equity / equity.cummax() - 1
max_dd = drawdown.min()
```

## NOT doing

- KMeans clustering (no causal meaning; use market_regime instead)
- Health Score (no theoretical basis)
- Sortino (trade-based annualization meaningless)
- Log parsing (DB is superior)
- sklearn dependency (unnecessary)

## SSH Details

- Host: `rwfunder@100.67.114.104` (Meshnet)
- Password: `0602`
- DB path: `/home/rwfunder/文件/tradingbot/trading_bot_v6/v6_performance.db`
- Tool: `sshpass -p 0602 scp ...`
