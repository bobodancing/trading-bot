# 🔍 Market Scanner v1.0

**主動掃描加密貨幣市場，找出最符合 2B 策略的交易機會**

## 📋 快速開始

```bash
# 單次掃描
python -m scanner.market_scanner --once

# 循環掃描（每 15 分鐘）
python -m scanner.market_scanner

# 使用自定義配置
python -m scanner.market_scanner --config scanner/scanner_config.json
```

## 🔬 四層過濾邏輯

| 層級 | 名稱 | 功能 |
|-----|------|------|
| Layer 1 | 流動性過濾 | 排除低流動性幣種 |
| Layer 2 | 動能篩選 | 找出有趨勢的標的 |
| Layer 3 | 形態匹配 | 2B 信號 + 預警 |
| Layer 4 | 相關性過濾 | 分散風險 |

## 📊 輸出檔案

- `hot_symbols.json` - 掃描結果（供 Bot 讀取）
- `scanner_results.db` - 歷史記錄
- `scanner.log` - 日誌

## ⚙️ 配置說明

編輯 `scanner_config.json` 調整參數：

```json
{
    "L1_MIN_VOLUME_USD": 50000000,  // 最低 24H 成交量
    "L2_MIN_ADX": 20,               // 最低 ADX 值
    "L3_PRE_2B_THRESHOLD": 0.5,     // Pre-2B 預警距離
    "L4_MAX_PER_SECTOR": 2,         // 同板塊最多標的
    "OUTPUT_TOP_N": 10              // 輸出 Top N
}
```

## 🔗 與 Trading Bot 整合

Scanner 結果會自動保存到 `hot_symbols.json`，Trading Bot 可讀取此檔案使用動態標的。

詳見主專案 README。
