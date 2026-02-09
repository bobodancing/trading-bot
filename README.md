# Trading Bot v5.2 — 智能演算法交易系統

基於 2B 突破形態的加密貨幣自動交易系統，整合 Market Scanner 動態選股與多策略信號偵測。

---

## 架構總覽

```
trading-bot-v5.2/
├── trading_bot_gui_v5.2.py      # GUI 控制面板
├── trading_bot_v5.2_optimized.py # 交易核心引擎
├── scanner/
│   ├── market_scanner.py         # 4 層市場掃描器
│   ├── scanner_config.json       # Scanner 配置
│   └── README.md                 # Scanner 文件
├── bot_config.json               # 交易機器人配置
├── requirements.txt              # Python 依賴
└── TRADING_MANUAL.md             # 交易 SOP 手冊
```

---

## 快速開始

### 安裝依賴

```bash
pip install -r requirements.txt
```

### 啟動 GUI

```bash
python trading_bot_gui_v5.2.py
```

### 首次設定流程

1. 在「API 連線」分頁輸入 API 金鑰和密鑰
2. 確認開啟「測試網模式」
3. 在「交易設定」設定交易對和方向
4. 點擊「儲存設定」
5. 點擊「啟動系統」連線交易所
6. 確認帳戶資訊正確後，點擊「開始交易」

---

## 核心功能

### 多策略信號偵測

| 策略 | 說明 | 優先級 |
|------|------|--------|
| 量能突破 | 盤整後放量突破 | 1 (最高) |
| 2B 突破 | 假突破反轉形態 | 2 |
| EMA 回撤 | 趨勢中回撤至均線 | 3 |

### 信號分級入場 (A/B/C)

根據 MTF 確認、市場強度、量能等級綜合評分，分配不同倉位大小：
- A 級 (6+ 分): 100% 倉位
- B 級 (4-5 分): 70% 倉位
- C 級 (<4 分): 50% 倉位

### A+ SOP 出場機制

- 1.5R 獲利：部分減倉 + 止損移至成本
- 3.0R 獲利：再次減倉
- 剩餘倉位：ATR 追蹤止損

---

## Market Scanner 整合

Scanner 作為選股器，自動從全市場 USDT 交易對中篩選潛力標的：

```
Layer 1: 流動性過濾 (24H 成交量)
Layer 2: 動量過濾 (ADX/RSI/ATR/EMA)
Layer 3: 形態匹配 (2B 信號 + Swing Point)
Layer 4: 相關性過濾 (板塊分散)
```

### 啟用 Scanner 聯動

1. 在 GUI「掃描器」分頁執行掃描
2. 勾選「使用掃描結果作為交易標的」
3. 儲存設定 → 啟動系統

Scanner 掃出的標的會自動取代靜態交易對清單，Bot 仍執行完整的獨立信號偵測。

### 獨立執行 Scanner

```bash
# 單次掃描
python -m scanner.market_scanner --once

# 持續掃描 (每 15 分鐘)
python -m scanner.market_scanner

# 自訂配置
python -m scanner.market_scanner --config scanner/scanner_config.json
```

---

## 兩階段操作流程

| 階段 | 操作 | 說明 |
|------|------|------|
| 階段一 | 啟動系統 | 連線交易所，顯示帳戶餘額與持倉，不執行交易 |
| 階段二 | 開始交易 | 確認連線無誤後，啟動自動掃描與交易 |

---

## 風控機制

- **單筆風險控管**: 根據 ATR 計算止損距離，反推倉位大小
- **總風險上限**: 所有持倉加總不超過設定比例
- **硬止損單**: 在交易所端設置實際止損限價單
- **重複開倉防護**: 同一標的不重複建倉
- **市場過濾**: ADX/ATR/EMA 糾纏度三重過濾

---

## 配置說明

所有配置透過 GUI 管理，存於 `bot_config.json`。主要參數：

| 類別 | 參數 | 說明 |
|------|------|------|
| 交易 | `trading_mode` | spot / future |
| 交易 | `trading_direction` | long / short / both |
| 交易 | `leverage` | 槓桿倍數 (1-20) |
| 風控 | `risk_per_trade` | 單筆風險比例 |
| 風控 | `max_total_risk` | 最大總風險比例 |
| 過濾 | `adx_threshold` | ADX 最低門檻 |
| Scanner | `use_scanner_symbols` | 是否使用 Scanner 標的 |
| Scanner | `scanner_max_age_minutes` | Scanner 結果有效期 |

詳細參數說明請參考 [TRADING_MANUAL.md](TRADING_MANUAL.md)。

---

## 技術棧

- Python 3.10+
- ccxt (交易所 API)
- pandas / numpy (技術分析)
- customtkinter (GUI)
- Telegram Bot API (通知)

---

*文檔版本：v5.2*
*最後更新：2026-02-09*
