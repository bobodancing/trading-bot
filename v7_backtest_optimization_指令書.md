# V7 Backtest Optimization 指令書

## 背景與根因

V7 回測分析發現三大問題：
1. **Tier C 穩定虧損** -- 三段回測 WR = 0%/12%/10%，穩定拖累績效
2. **Stage 2 加倉在浮虧中放大虧損** -- 浮虧時加倉等於攤平，違反趨勢跟隨原則
3. **Stage 3 trailing SL 反應太慢** -- 滿倉後只看 1H K 線，大波段回撤吃掉利潤

改善方案：砍 Tier C 進場 + 加倉浮盈門檻 + breakeven SL + **Stage 3 多時間框架 trailing（15m）**

所有改動已在本機驗證完畢（356 tests passed）。

---

## 安全紅線

1. **不影響既有持倉**（只影響新進場和新加倉判斷）
2. **不改核心信號邏輯**（2B/EMA_PULLBACK/VOLUME_BREAKOUT 不變）
3. **每步完成後**：`pytest` 全過

---

## 修改清單

### 1. `trader/config.py` -- 新增三個 V7 參數

**位置**: `V7_STAGE_VOLUME_MULT` 之後、`EARLY_EXIT_COOLDOWN_HOURS` 之前

**Before**:
```python
    V7_STAGE_VOLUME_MULT = 1.0    # 加倉量能門檻（volume / vol_ma）

    # 快速止損/時間退出後的冷卻時間
```

**After**:
```python
    V7_STAGE_VOLUME_MULT = 1.0    # 加倉量能門檻（volume / vol_ma）
    V7_MIN_SIGNAL_TIER = 'B'      # 最低可進場 tier（'A'=只做A, 'B'=A+B, 'C'=全做）
    V7_MIN_PNL_PCT_FOR_ADD = 0.0  # 加倉最低浮盈門檻（%），0=breakeven
    V7_STAGE3_TRAIL_TIMEFRAME = '15m'  # Stage 3 trailing 用的低時間框架

    # 快速止損/時間退出後的冷卻時間
```

---

### 2. `trader/bot.py` -- Tier 過濾 + Stage 3 低時間框架 fetch

#### 2a. Tier 過濾

**位置**: `signal_details['trend_adx']` 設定之後、`# === Risk Guard: BTC Trend Filter ===` 之前

**Before**:
```python
                )

                # === Risk Guard: BTC Trend Filter ===
```

**After**:
```python
                )

                # === Risk Guard: Tier 過濾 ===
                _tier_rank = {'A': 3, 'B': 2, 'C': 1}
                _min_tier = getattr(Config, 'V7_MIN_SIGNAL_TIER', 'C')
                if _tier_rank.get(signal_tier, 0) < _tier_rank.get(_min_tier, 0):
                    logger.info(
                        f"{symbol}: 跳過（Tier {signal_tier} < 最低要求 {_min_tier}，score={tier_score}）"
                    )
                    continue

                # === Risk Guard: BTC Trend Filter ===
```

#### 2b. Monitor loop: Stage 2+ fetch 15m + 傳遞 df_trail

**位置**: monitor loop 中，`df_4h` 取得之後、`pm.monitor(...)` 呼叫之前

**Before**:
```python
                # V6 / V7: 額外取得 4H 數據
                df_4h = None
                if pm.strategy_name in ("v6_pyramid", "v7_structure"):
                    df_4h = self.fetch_ohlcv(symbol, '4h', limit=50)
                    if df_4h is not None and not df_4h.empty:
                        df_4h = TechnicalAnalysis.calculate_indicators(df_4h)

                # Monitor（V7 P2 起回傳 Dict）
                decision = pm.monitor(current_price, df_1h, df_4h)
```

**After**:
```python
                # V6 / V7: 額外取得 4H 數據
                df_4h = None
                if pm.strategy_name in ("v6_pyramid", "v7_structure"):
                    df_4h = self.fetch_ohlcv(symbol, '4h', limit=50)
                    if df_4h is not None and not df_4h.empty:
                        df_4h = TechnicalAnalysis.calculate_indicators(df_4h)

                # V7 Stage 2+: 額外取得低時間框架數據（更靈敏的 trailing）
                df_trail = None
                if pm.strategy_name == "v7_structure" and pm.stage >= 2:
                    trail_tf = getattr(Config, 'V7_STAGE3_TRAIL_TIMEFRAME', None)
                    if trail_tf:
                        df_trail = self.fetch_ohlcv(symbol, trail_tf, limit=50)
                        if df_trail is not None and not df_trail.empty:
                            df_trail = TechnicalAnalysis.calculate_indicators(df_trail)

                # Monitor（V7 P2 起回傳 Dict）
                decision = pm.monitor(current_price, df_1h, df_4h, df_trail=df_trail)
```

---

### 3. `trader/positions.py` -- monitor 傳遞 df_trail

**Before**:
```python
    def monitor(self, current_price: float, df_1h=None, df_4h=None) -> Dict[str, Any]:
        """
        統一監控入口（V7 P2 起回傳 Dict）。

        委託 self.strategy.get_decision() 計算出場/加倉決策。

        Returns:
            dict: {
                "action"   : str,            # "ACTIVE"|"CLOSE"|"STAGE2_TRIGGER"|
                                             #   "STAGE3_TRIGGER"|"V53_REDUCE_15R"|"V53_REDUCE_25R"
                "reason"   : str,
                "new_sl"   : Optional[float],
                "close_pct": Optional[float],
            }
        """
        if self.is_closed:
            return {"action": "ACTIVE", "reason": "ALREADY_CLOSED", "new_sl": None, "close_pct": None}
        return self.strategy.get_decision(self, current_price, df_1h, df_4h)
```

**After**:
```python
    def monitor(self, current_price: float, df_1h=None, df_4h=None, df_trail=None) -> Dict[str, Any]:
        """
        統一監控入口（V7 P2 起回傳 Dict）。

        委託 self.strategy.get_decision() 計算出場/加倉決策。

        Args:
            df_trail: 低時間框架數據（15m），Stage 3 trailing 用。

        Returns:
            dict: {
                "action"   : str,            # "ACTIVE"|"CLOSE"|"STAGE2_TRIGGER"|
                                             #   "STAGE3_TRIGGER"|"V53_REDUCE_15R"|"V53_REDUCE_25R"
                "reason"   : str,
                "new_sl"   : Optional[float],
                "close_pct": Optional[float],
            }
        """
        if self.is_closed:
            return {"action": "ACTIVE", "reason": "ALREADY_CLOSED", "new_sl": None, "close_pct": None}
        return self.strategy.get_decision(self, current_price, df_1h, df_4h, df_trail=df_trail)
```

---

### 4. `trader/strategies/base.py` -- 基底類加 **kwargs

**Before**:
```python
    @abstractmethod
    def get_decision(
        self,
        pm: 'PositionManager',
        current_price: float,
        df_1h: pd.DataFrame,
        df_4h: pd.DataFrame = None,
    ) -> DecisionDict:
```

**After**:
```python
    @abstractmethod
    def get_decision(
        self,
        pm: 'PositionManager',
        current_price: float,
        df_1h: pd.DataFrame,
        df_4h: pd.DataFrame = None,
        **kwargs,
    ) -> DecisionDict:
```

---

### 5. `trader/strategies/v53_sop.py` + `trader/strategies/v6_pyramid.py` -- 加 **kwargs

兩個檔案同樣改法：

**Before**（各自的 `get_decision`）:
```python
    def get_decision(
        self,
        pm: 'PositionManager',
        current_price: float,
        df_1h,
        df_4h=None,
    ) -> DecisionDict:
```

**After**:
```python
    def get_decision(
        self,
        pm: 'PositionManager',
        current_price: float,
        df_1h,
        df_4h=None,
        **kwargs,
    ) -> DecisionDict:
```

---

### 6. `trader/strategies/v7_structure.py` -- 四處修改

#### 6a. `get_decision` 加 **kwargs

**Before**:
```python
    def get_decision(
        self,
        pm: 'PositionManager',
        current_price: float,
        df_1h,
        df_4h=None,
    ) -> DecisionDict:
```

**After**:
```python
    def get_decision(
        self,
        pm: 'PositionManager',
        current_price: float,
        df_1h,
        df_4h=None,
        **kwargs,
    ) -> DecisionDict:
```

#### 6b. 加倉呼叫處傳 current_price

**Before**:
```python
            add_result = self._check_add_trigger(pm, df_1h, Cfg)
```

**After**:
```python
            add_result = self._check_add_trigger(pm, current_price, df_1h, Cfg)
```

#### 6c. Trailing SL 使用 df_trail

**Before**:
```python
        # 5. 結構 Trailing SL（Stage 2/3）
        if pm.stage >= 2 and df_1h is not None and len(df_1h) > 0:
            trailing = self._structure_trailing_sl(pm, df_1h, Cfg)
            if trailing is not None:
                return {**result, "action": Action.UPDATE_SL, "reason": "V7_STRUCTURE_TRAIL_SL", "new_sl": trailing}
```

**After**:
```python
        # 5. 結構 Trailing SL（Stage 2/3）
        #    Stage 2+ 優先用低時間框架（15m）做更靈敏的 trailing；加倉判斷仍用 1H
        if pm.stage >= 2 and df_1h is not None and len(df_1h) > 0:
            df_trail = kwargs.get('df_trail')
            trail_df = df_trail if (df_trail is not None and len(df_trail) > 0) else df_1h
            trailing = self._structure_trailing_sl(pm, trail_df, Cfg)
            if trailing is not None:
                return {**result, "action": Action.UPDATE_SL, "reason": "V7_STRUCTURE_TRAIL_SL", "new_sl": trailing}
```

#### 6d. `_check_add_trigger` 方法簽名 + 浮盈門檻

**Before**:
```python
    def _check_add_trigger(self, pm, df_1h, Cfg) -> Optional[DecisionDict]:
        """三條件 AND 加倉觸發"""
        from trader.structure import StructureAnalysis

        swings = StructureAnalysis.find_swing_points(
```

**After**:
```python
    def _check_add_trigger(self, pm, current_price, df_1h, Cfg) -> Optional[DecisionDict]:
        """三條件 AND 加倉觸發（需浮盈 >= 門檻才允許加倉）"""
        from trader.structure import StructureAnalysis

        # 浮盈門檻：浮虧中不加倉
        min_pnl = getattr(Cfg, 'V7_MIN_PNL_PCT_FOR_ADD', 0.0)
        if pm.avg_entry and pm.avg_entry > 0:
            unrealized_pnl_pct = (current_price - pm.avg_entry) / pm.avg_entry * 100
            if pm.side == 'SHORT':
                unrealized_pnl_pct = -unrealized_pnl_pct
            if unrealized_pnl_pct < min_pnl:
                return None

        swings = StructureAnalysis.find_swing_points(
```

#### 6e. 計算新 SL 加入 breakeven 保護

**Before**:
```python
        if pm.side == 'LONG':
            new_sl = swing_price - atr_buffer
        else:
            new_sl = swing_price + atr_buffer
```

**After**:
```python
        if pm.side == 'LONG':
            new_sl = swing_price - atr_buffer
            # 加倉時 SL 至少在 breakeven
            if pm.avg_entry and new_sl < pm.avg_entry:
                new_sl = pm.avg_entry
        else:
            new_sl = swing_price + atr_buffer
            # 加倉時 SL 至少在 breakeven
            if pm.avg_entry and new_sl > pm.avg_entry:
                new_sl = pm.avg_entry
```

#### 6f. `_structure_trailing_sl` 參數名改為 df（語意明確）

**Before**:
```python
    def _structure_trailing_sl(self, pm, df_1h, Cfg) -> Optional[float]:
        """結構 Trailing SL：追蹤新形成的順勢 swing point（棘輪只往有利方向移動）"""
        from trader.structure import StructureAnalysis

        swings = StructureAnalysis.find_swing_points(
            df_1h, Cfg.SWING_LEFT_BARS, Cfg.SWING_RIGHT_BARS
        )
```

**After**:
```python
    def _structure_trailing_sl(self, pm, df, Cfg) -> Optional[float]:
        """結構 Trailing SL：追蹤新形成的順勢 swing point（棘輪只往有利方向移動）

        df 可以是 1H 或低時間框架（如 15m），由呼叫端根據 stage 決定。
        """
        from trader.structure import StructureAnalysis

        swings = StructureAnalysis.find_swing_points(
            df, Cfg.SWING_LEFT_BARS, Cfg.SWING_RIGHT_BARS
        )
```

> **注意**：方法內其餘 `df_1h` 引用也要改成 `df`（目前方法內沒有其他引用，只有 `swings` 一處）

---

## 新增 Tests

- 檔案: `trader/tests/test_v7_structure.py`
- 位置: `TestV7Integration` class 之前

### Test classes:

1. **class `TestV7PnlGate`** (3 tests)
   - `test_no_add_when_underwater_long` -- LONG 浮虧 (price < avg_entry) 不加倉
   - `test_no_add_when_underwater_short` -- SHORT 浮虧 (price > avg_entry) 不加倉
   - `test_add_allowed_when_in_profit` -- 浮盈中正常加倉

2. **class `TestV7BreakevenSL`** (2 tests)
   - `test_add_sl_at_least_breakeven_long` -- LONG 加倉 SL >= avg_entry
   - `test_add_sl_at_least_breakeven_short` -- SHORT 加倉 SL <= avg_entry

3. **class `TestV7MultiTimeframeTrailing`** (3 tests)
   - `test_stage3_uses_df_trail` -- Stage 3 有 df_trail → 用低時間框架 trailing
   - `test_stage2_uses_df_trail` -- Stage 2 有 df_trail → 同樣用低時間框架 trailing
   - `test_fallback_to_1h_without_df_trail` -- 沒有 df_trail → fallback 到 1H

---

## 驗證步驟

```bash
cd /home/rwfunder/文件/tradingbot/trading_bot
python -m pytest trader/tests/ -x -q
```

預期: **356 tests passed** (原 348 + 新增 8)

```bash
sudo systemctl restart trader.service
# 密碼: 0602
```

確認 service 啟動正常：
```bash
sudo systemctl status trader.service
journalctl -u trader.service --since "1 min ago" --no-pager
```

---

## Config 說明

`bot_config.json` 可選新增（不加也行，用 class default）：

```json
{
  "v7_min_signal_tier": "B",
  "v7_min_pnl_pct_for_add": 0.0,
  "v7_stage3_trail_timeframe": "15m"
}
```

- `v7_min_signal_tier`: `"B"` = 只做 A+B tier（Tier C 不進場）；`"C"` = 全做（舊行為）；`"A"` = 只做 A
- `v7_min_pnl_pct_for_add`: `0.0` = breakeven 才加倉；`-1.0` = 允許 1% 浮虧加倉；`0.5` = 需 0.5% 浮盈
- `v7_stage3_trail_timeframe`: `"15m"` = Stage 3 用 15m trailing；`"30m"` = 30m；`null` = 不啟用（用 1H）

---

## 改動檔案清單

| 檔案 | 改動 |
|------|------|
| `trader/config.py` | +3 config（MIN_SIGNAL_TIER / MIN_PNL_PCT_FOR_ADD / STAGE3_TRAIL_TIMEFRAME） |
| `trader/bot.py` | Tier 過濾 + Stage 3 fetch 15m + monitor 傳 df_trail |
| `trader/positions.py` | monitor 加 df_trail 參數 |
| `trader/strategies/base.py` | get_decision 加 **kwargs |
| `trader/strategies/v53_sop.py` | get_decision 加 **kwargs |
| `trader/strategies/v6_pyramid.py` | get_decision 加 **kwargs |
| `trader/strategies/v7_structure.py` | 浮盈門檻 + breakeven SL + df_trail trailing + **kwargs |
| `trader/tests/test_v7_structure.py` | +8 tests（PnlGate + BreakevenSL + MultiTimeframeTrailing） |

---

## 注意事項

- 這些改動**不影響既有持倉**（只影響新進場和新加倉判斷）
- 15m fetch 在 V7 Stage 2+ 持倉時觸發，每 cycle 多一次 API call（影響小）
- `**kwargs` 對 V53/V6 完全透明，不影響它們的行為
- **加倉判斷仍用 1H**（避免 15m 噪音導致過早加倉）；**trailing 用 15m**（防守動作，靈敏更好）
