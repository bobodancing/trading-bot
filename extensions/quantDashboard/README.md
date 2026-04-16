# quantDashboard

Trading Bot 績效分析儀表板。一鍵從 rwUbuntu 拉取資料庫，生成互動式 HTML 報告。

---

## 快速開始

```bat
:: Windows（推薦）
run.bat           :: 預設 7 天
run.bat --all     :: 全部數據（2026-02-25 之後）
run.bat --days 14 :: 自訂天數
```

```bash
# Linux / bash
./run.sh          # 預設 7 天
./run.sh --all
```

### 依賴安裝

```bash
pip install pandas numpy plotly paramiko
```

---

## 架構

```
tools/quantDashboard/
├── run.bat             # Windows 一鍵入口
├── run.sh              # Linux/bash 入口
├── pull_db.py          # paramiko SFTP 從 rwUbuntu 拉 performance.db
├── build_dashboard.py  # SQLite → metrics → Plotly HTML
├── dashboard.html      # 輸出（gitignore）
└── performance.db      # 拉回的 DB（gitignore）
```

**數據來源**：`rwUbuntu:/home/rwfunder/文件/tradingbot/trading_bot/performance.db`

---

## 指標說明

### Tab 1 — Overview

全局健康度快覽。用 6 個 KPI cards + 3 條時序曲線判斷系統是否在軌道上。

> **前期對比**：使用 `--days N` 時，KPI 自動載入前一期（N 天前 ~ 2N 天前）數據，delta 顯示 period-over-period 變化。使用 `--all` 時無前期對比，delta 改為 vs 固定閾值。

#### KPI Cards

| 指標 | 公式 | 解讀 |
|------|------|------|
| **Trades** | `COUNT(*)` | 期間內完成平倉的交易筆數 |
| **Win Rate** | `COUNT(realized_r > 0) / COUNT(*)` | 獲利交易佔比。> 50% 為正，但需搭配 PF 判斷 |
| **Avg R** | `MEAN(realized_r)` | 平均每筆交易賺多少倍初始風險（R）。> 0 為正期望值 |
| **PF (R-based)** | `SUM(r_wins) / ABS(SUM(r_losses))` | 基於 realized_r 的毛利/毛損比。> 1 才能存活，> 1.5 為健康目標（cap 10.0） |
| **Sharpe (T)** | `MEAN(pnl_pct) / STD(pnl_pct)` | 基於每筆交易的 Sharpe，無年化調整。> 0.5 為可接受，> 1.0 為理想 |
| **Max DD ₮** | `MIN(equity - cummax(equity))` | 權益曲線從高點回落的最大 USDT 金額。負值，絕對值越小越好 |

> **Avg R vs Win Rate**：低 WR + 高 Avg R 的系統（如趨勢追蹤）是健康的；高 WR + 負 Avg R 才是危險訊號。

> **Profit Factor 參考值**：
> - PF < 1.0：系統在虧損
> - 1.0 ~ 1.3：剛好正期望，費用吃掉多數利潤
> - 1.3 ~ 1.8：可接受，需持續監控
> - > 1.8：良好，具有統計優勢

> **Sharpe 計算說明**：此處為**交易級 Sharpe**，用 `pnl_pct` 的均值除以標準差。與傳統年化 Sharpe（乘以 `sqrt(252)`）不同——年化對筆數少的交易系統無意義，因為每筆間隔時間不固定。

---

#### 時序圖表

**Equity Curve（權益曲線）**

```
Y 軸：累積 USDT PnL
計算：pnl_usdt.cumsum()
```

- 每筆平倉的 USDT 損益逐筆累加，反映帳戶實際盈虧軌跡
- 持續向右上角為目標
- 斜率變緩代表系統進入低效期
- X 軸為 `exit_time`（平倉時間），能看出空倉期間的橫盤
- 採用 USDT 累加而非 pnl_pct 複利，因為交易可能時間重疊（concurrent positions）

**Drawdown（回撤）**

```
Y 軸：從權益高點回落的 USDT 金額（負值）
計算：equity - equity.cummax()
```

- 顯示系統在「虧損修復路上」走多深（以 USDT 絕對值呈現）
- 深且長的回撤比短暫大回撤更危險（資金壓力）
- 注意：此為 USDT 絕對值，非百分比。判斷嚴重度需對照帳戶總資金

**Rolling Win Rate 30T（滾動勝率）**

```
Y 軸：最近 30 筆交易的勝率（%）
視窗：min_periods=1（前期資料不足時縮視窗計算）
```

- 偵測系統是否進入衰退期（滾動 WR 持續下滑）
- 與靜態 WR 的差異：能看出**近期**表現趨勢
- 若滾動 WR 降至 30% 以下需警惕，確認是否有參數失效

---

### Tab 2 — Strategy

比較不同策略的分工與效益。新版 runtime 會依資料中的 `strategy_name` / `is_v6_pyramid` 自動分類，常見標籤為 `V54`、`V7`、`V53`、`V6`，grid 交易則顯示為 `GRID`。

#### KPI Row

頂部 KPI 會依目前資料集中出現的策略動態生成；每個策略顯示 Trades / WR% / Avg R / PnL。

#### Cumulative PnL by Strategy（累積損益曲線）

- X 軸：`exit_time`（平倉時間），Y 軸：累積 USDT PnL
- 各策略會分別繪製一條累積 PnL 曲線
- 判斷哪個策略在拉動整體績效，哪個在拖累
- 若某條策略線長期走平或向下，代表該策略可能正在拖累整體績效

#### Stage Performance（V7 / V6 各階段績效）

只有 staged strategy 會進這張圖，目前包含 `V7` / `V6`。此圖以 **Avg R** 柱狀圖比較各 Stage 的績效：

| Stage | 觸發條件 | 意義 |
|-------|---------|------|
| Stage 1 | 初始入場 | 所有 V6 交易都有 |
| Stage 2 | 價格突破頸線 + 成交量確認 | 趨勢持續，加倉 |
| Stage 3 | 趨勢延伸，第二次加倉 | 大波段獲利核心 |

- Bar 高度 = **Avg R**，Text 標籤包含 `n`、`WR%`、`med`（median R）、`ΣPnL`
- **Avg R vs med**：兩者接近代表分布穩定；差距大代表被 outlier 拉高
- Stage 2/3 的 Avg R 應顯著高於 Stage 1 → 確認滾倉帶來更高報酬
- **小樣本警示**：Stage 2/3 筆數通常很少，需累積足夠數據再下結論

#### Avg R by Tier & Strategy（Tier 平均R）

信號評級系統（A/B/C）的 Avg R 對比，會依目前資料中的非-grid 策略動態分組：

| Tier | 定義 | 預期行為 |
|------|------|---------|
| A | 強勢行情 + 高 ADX + 高成交量 | 最高 Avg R，WR 不一定最高但 EV 最大 |
| B | 中等行情 | 均衡表現 |
| C | 弱勢行情 | 較低 Avg R，考慮降低倉位或過濾 |

- 若 Tier A 的 Avg R 不優於 B/C，代表 Tier 評分系統需要重新校準

#### Win Rate% by Tier & Strategy（Tier 勝率）

獨立圖表，對比各 Tier 的勝率。與 Avg R 圖搭配看，高 WR 不代表高 EV，需兩者兼顧。

---

### Tab 3 — Risk

分析**出場機制品質**與**停損設計效能**。這是最能看出系統缺陷的一頁。

#### KPI Row

頂部 5 個 KPI：Avg MFE% / Avg MAE% / MFE Giveback Med / SL Exits / Avg Loss R

#### Exit Reason Distribution（出場原因分布）

顯示各出場原因的交易筆數：

| 出場代碼 | 說明 |
|---------|------|
| `sl_hit` | Trailing stop 進入獲利區後被觸發 |
| `hard_stop_hit` | 初始硬止損被觸發（全損） |
| `fast_stop` | 快速止損（進場後快速逆轉） |
| `structure_trail_sl` | 結構追蹤止損（swing point 跌破） |
| `profit_pullback` | 利潤回吐保護（MFE 回落 40%+） |
| `reverse_2b` | 反向 2B 形態出場 |
| `v53_structure_break` | V53 結構跌破（連續 2 根 1H 確認） |
| `stage1_timeout` | V6 Stage 1 超時未進入 Stage 2，主動退出 |
| `early_stop_r` | V6 提前止損——Stage 1 趨勢衰退時提前砍倉，虧損約 -0.8R，比硬止損少虧 |
| `time_exit` | 時間退出（超過最大持倉時間） |

- `hard_stop_hit` 比例高 → 初始 SL 設太緊或信號品質差
- `sl_hit` 比例高 → 好事，代表 trailing stop 運作正常，在獲利中出場
- `time_exit` 比例高 → 行情不如預期，多是 Stage 1 卡住沒機會滾倉

#### Exit Reason EV（各出場原因的期望值）

Y 軸為各出場原因的平均 R（`MEAN(realized_r)`）：

- 綠色 bar = 正期望值出場（好的）
- 紅色 bar = 負期望值出場
- **重點觀察**：任何出場原因若持續呈紅，代表該機制在虧損，需深入分析或修改

> 理想分布：`sl_hit`、`structure_trail_sl` 為正（保護獲利）；`hard_stop_hit` 為最負（損失最大但應控制在 -1R 以內）

#### Capture Ratio Distribution（獲利捕捉率分布）

```
capture_ratio = realized_pnl_pct / mfe_pct
```

代表交易最終實現了多少比例的最大浮動獲利（MFE）：

| 範圍 | 解讀 |
|------|------|
| > 0.8 | 幾乎全抓到波段，出場時機極佳 |
| 0.4 ~ 0.8 | 正常，有些回吐但可接受 |
| < 0.2 | 大量獲利在出場前回吐，trailing 太鬆或出場太晚 |
| 負值 | 曾獲利但最終虧損出場（最糟糕的情境） |

- 分布集中在 0.3 ~ 0.7 為健康
- 有大量負值 → profit_pullback 或 trailing 機制需要調整

#### MFE vs Realized R Scatter（最大浮動獲利 vs 實現R）

- X 軸：`mfe_pct`（交易過程中最大浮動獲利百分比）
- Y 軸：`realized_r`（最終實現的 R 值）
- 綠點 = 獲利交易，紅點 = 虧損交易

**理想模式**：右上角綠點密集（高 MFE → 高實現R）

**問題訊號**：
- 右下角有紅點（MFE 很高但最終虧損）→ 出場機制太差，讓獲利全部吐回
- 左上角空白（沒有低 MFE 但高 R 的交易）→ 正常，R 需要先有浮盈才能實現

#### SL Quality: MAE vs PnL（停損品質）

僅針對停損出場（`sl_hit / hard_stop_hit / fast_stop / structure_trail_sl`）：

- X 軸：`mae_pct`（交易過程中最大浮動虧損百分比）
- Y 軸：`pnl_usdt`（最終損益 USDT）

**目標**：MAE 小（接近 0）且 PnL 大（右上角集中）

**問題訊號**：
- 左下角有點（MAE 深 + PnL 虧損）→ 停損設太鬆，讓虧損擴大才止損
- MAE 普遍很小（靠右）但 PnL 也是負的 → 可能是 fast_stop 過早觸發

#### Realized R Distribution（R 值分布）

所有交易的 `realized_r` 直方圖，綠色 = 獲利（R > 0），紅色 = 虧損（R <= 0）：

- 分布右偏（長尾在右側）→ 系統有抓到大波段，健康
- 虧損集中在 -1R 附近 → SL 設計正確，損失可控
- 虧損散布超過 -1.5R → 可能有滑價或 SL 執行延遲

#### MFE Giveback Distribution（MFE 回吐分布，MFE≥3%）

```
giveback = mfe_pct - pnl_pct
```

衡量每筆交易從最大浮動獲利（MFE）到實際出場之間「放回去」了多少百分比：

| 範圍 | 解讀 |
|------|------|
| < 0.5% | 幾乎在高點出場，出場時機極佳 |
| 0.5% ~ 2% | 正常回吐範圍 |
| > 3% | 出場太晚或 trailing 太鬆，大量浮盈被吃掉 |

> **MFE≥3% 過濾**：僅顯示 MFE 達 3% 以上的交易。MFE 極低（< 3%）的交易若最終虧損，giveback 數字會因 pnl 負值而虛高（假性回吐），不代表出場機制問題，而是進場就錯。過濾後圖表更能反映真正的出場品質。

- 圖表包含 **median 虛線**，追蹤整體回吐中位數
- 配合 Capture Ratio 一起看：Giveback 高 + Capture Ratio 低 → trailing stop 需調緊
- 若 Giveback 中位數持續上升 → 出場機制正在劣化

#### MFE → Exit Scatter（MFE vs 實際出場）

- X 軸：`mfe_pct`（交易過程中最大浮動獲利百分比）
- Y 軸：`pnl_pct`（最終實現損益百分比）
- 白色虛線 = 完美捕捉線（pnl_pct == mfe_pct，在高點出場）
- 綠點 = 獲利交易，紅點 = 虧損交易

**怎麼看**：
- 點越靠近白色虛線 → 出場越接近 MFE 高點，捕捉效率高
- 點遠離虛線（下方）→ 回吐多，出場太晚或 trailing 太鬆
- 紅點在右側（高 MFE 但虧損）→ 最差情境，大浮盈全部吐回還倒虧

---

### Tab 4 — Market

分析**市場環境**對交易結果的影響，找出系統在哪種行情下最有效。

#### KPI Row

頂部 4 個 KPI：BTC Aligned% / Med Duration / Best Day / Worst Day

#### Regime Performance（市場狀態績效）

根據 `market_regime` 欄位（Bot 開倉時記錄的市場狀態）分組比較：

| Regime | 說明 |
|--------|------|
| `STRONG` | MarketFilter 判定為強勢行情（BTC + 板塊同向強漲/跌） |
| `TRENDING` | 一般趨勢行情 |

- Bar 高度 = **Avg R**，Text 標籤包含 `WR%`、`n 筆數`、`med`（median R）、`ΣPnL`
- **Avg R vs med**：兩者接近代表分布穩定；Avg R >> med 代表被少數 outlier 拉高，需謹慎解讀
- 若 `STRONG` 的 Avg R 顯著高於 `TRENDING`，確認行情分類有效
- 若兩者無差異，考慮調整 MarketFilter 參數

#### BTC Alignment（BTC 趨勢同向性）

根據 `btc_trend_aligned` 欄位（開倉時 BTC 1D EMA20/50 方向是否與持倉同向）：

| 分類 | 說明 |
|------|------|
| `Aligned` | 持倉方向與 BTC 大趨勢同向（LONG in bull / SHORT in bear） |
| `Counter` | 逆 BTC 大趨勢做單 |
| `Unknown` | BTC 數據取得失敗（non-fatal fallback） |

- Bar 高度 = **Avg R**，Text 標籤包含 `WR%`、`n 筆數`、`med`（median R）、`ΣPnL`
- **小樣本警示**：Counter 筆數通常遠少於 Aligned，Avg R 容易被 1-2 筆 outlier 扭曲。對比 med 和 ΣPnL 判斷真實表現
- 若 `Aligned` 的 Avg R 顯著高於 `Counter`，可考慮**過濾逆勢信號**
- 若差異不顯著，BTC 趨勢同向性作為過濾器的價值有限

#### Trade Duration Distribution（持倉時間分布，按 Tier 分色）

X 軸：`holding_hours`（持倉小時數），按 `signal_tier` 分色疊加（overlay）：

| 顏色 | Tier | 預期 |
|------|------|------|
| 深藍 (#1565C0) | A | 高品質信號，預期持倉較長（走完波段） |
| 紫色 (#7E57C2) | B | 中品質，持倉分布居中 |
| 亮綠 (#00E676) | C | 低品質，預期快速出場居多 |

- 每個 Tier 的 legend 標示 **median 持倉時長**（med=Xh）
- 分布右偏（少數交易持倉很久）→ 正常，大波段交易持倉長
- 大量交易集中在 0-4h → 多是 fast_stop 或 hard_stop 快速出場
- **觀察重點**：Tier A 是否比 B/C 更常出現在長持倉區間（右側）
- 配合 Stage Reached 一起看：Stage 3 的交易平均持倉應顯著更長

#### Daily PnL（每日損益）

按 `exit_date` 彙總當日所有平倉 PnL（USDT）：

- 綠色 = 當日獲利，紅色 = 當日虧損
- 看是否有連續虧損日（需警惕市場環境是否改變）
- 單日極端虧損 → 確認是否有 Black Swan 或系統異常

### Tab 5 — Trades

逐筆交易明細表，可排序、可搜尋。

#### 欄位說明

| 欄位 | 說明 |
|------|------|
| **Symbol** | 交易對 |
| **Strategy** | 依 `strategy_name` 顯示，如 `V54` / `V7` / `V53` / `V6` / `GRID` |
| **Side** | `LONG`（綠）/ `SHORT`（紅） |
| **Tier** | 信號評級 `A`（深藍）/ `B`（紫）/ `C`（亮綠） |
| **Entry Time** | 開倉時間（GMT+8） |
| **Exit Time** | 平倉時間（GMT+8） |
| **Size** | 持倉量，優先取 `original_size`，沒有才 fallback `total_size` |
| **Entry / Exit Price** | 開平倉價格 |
| **Entry / Exit (USDT)** | 開平倉名義價值 |
| **PnL (USDT)** | 實現損益 |
| **R** | `realized_r`（實現 R 值） |
| **Total Chg** | `PnL / Entry Notional`（百分比） |
| **Exit Reason** | 出場原因代碼 |

- 點擊表頭可排序（升/降序切換）
- 搜尋框支援 Symbol 過濾

---

## 互動功能

- **Scatter hover**：所有散佈圖（MFE vs R、SL Quality、MFE → Exit）hover 顯示 `Symbol`、`Exit Reason`、關鍵數值，方便追蹤個別交易
- **Trades 排序**：點擊表頭可升/降序排序
- **Trades 搜尋**：輸入 Symbol 即時過濾

---

## 數據截點

`DATA_CUTOFF = "2026-02-25"`

2026-02-25 之前的 `capture_ratio` 欄位數值錯誤（舊公式 `realized_r/mfe_pct` 混合單位），已修正。Dashboard 預設過濾此截點前的數據以確保分析正確性。

---

## CLI 完整選項

```
python build_dashboard.py [OPTIONS]

Options:
  --days N      顯示最近 N 天（預設 7）
  --all         顯示 DATA_CUTOFF 之後所有數據
  --db PATH     指定 DB 路徑（預設 ./performance.db）
  --out PATH    指定輸出 HTML 路徑（預設 ./dashboard.html）
```

---

## 常見問題

**Q: Dashboard 某個 Tab 的圖表是空白的？**
點擊其他 Tab 再點回來，或重新整理瀏覽器。Tab 切換時 Plotly 會自動 resize。

**Q: MFE / Capture Ratio 圖表沒資料？**
Terminal 會印出 `MFE scatter: X wins, Y losses` 的診斷訊息，確認是否資料庫中有這些欄位數據。早期交易（2026-02-27 前）這些欄位可能為 NULL。

**Q: DB pull 失敗？**
確認 rwUbuntu (100.67.114.104) Meshnet 連線正常，或手動執行：
```bash
python pull_db.py
```

**Q: 只想看本機的 DB 不想 pull？**
```bat
python build_dashboard.py --db C:\path\to\performance.db --all
```
