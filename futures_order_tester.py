# -*- coding: utf-8 -*-
"""
Binance Futures Testnet 下單測試工具
用於測試：
1. 獲取餘額
2. 開倉（做多/做空）
3. 關閉倉位
"""

import ccxt
import json
import requests
import time
import hmac
import hashlib
from urllib.parse import urlencode
from datetime import datetime


class FuturesOrderTester:
    """Binance Futures Testnet 下單測試器"""

    def __init__(self, config_file: str = "bot_config.json"):
        self.config = self.load_config(config_file)
        self.base_url = "https://testnet.binancefuture.com"
        self.api_key = self.config['api_key']
        self.api_secret = self.config['api_secret'].strip()  # 移除可能的換行符

        # 也初始化 ccxt 作為備用
        self.exchange = self.init_ccxt_exchange()

        print("="*60)
        print("🧪 Binance Futures Testnet 下單測試工具")
        print("="*60)
        print(f"📡 API Base URL: {self.base_url}")
        print(f"🔑 API Key: {self.api_key[:10]}...{self.api_key[-4:]}")
        print("="*60)

    def load_config(self, config_file: str) -> dict:
        """載入配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 載入配置失敗: {e}")
            raise

    def init_ccxt_exchange(self):
        """初始化 ccxt 交易所（用於獲取市場數據）"""
        try:
            exchange = ccxt.binance({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            })
            exchange.set_sandbox_mode(True)
            return exchange
        except Exception as e:
            print(f"⚠️ ccxt 初始化失敗: {e}")
            return None

    def _sign_request(self, params: dict) -> str:
        """生成請求簽名"""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _get_headers(self) -> dict:
        """獲取請求頭"""
        return {
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/x-www-form-urlencoded'
        }

    def _make_request(self, method: str, endpoint: str, params: dict = None, signed: bool = True) -> dict:
        """發送 API 請求"""
        url = f"{self.base_url}{endpoint}"

        if params is None:
            params = {}

        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._sign_request(params)

        headers = self._get_headers()

        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, data=params, headers=headers, timeout=30)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, params=params, headers=headers, timeout=30)
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}")

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ API 錯誤: {response.status_code}")
                print(f"   響應: {response.text}")
                return {"error": response.text, "code": response.status_code}

        except Exception as e:
            print(f"❌ 請求失敗: {e}")
            return {"error": str(e)}

    def get_server_time(self) -> int:
        """獲取服務器時間"""
        result = self._make_request('GET', '/fapi/v1/time', signed=False)
        if 'serverTime' in result:
            return result['serverTime']
        return int(time.time() * 1000)

    def get_balance(self) -> dict:
        """
        獲取 Futures 餘額
        使用 /fapi/v2/balance 端點（而非 sapi）
        """
        print("\n" + "-"*60)
        print("💰 獲取帳戶餘額...")
        print("-"*60)

        result = self._make_request('GET', '/fapi/v2/balance')

        if 'error' in result:
            print(f"❌ 獲取餘額失敗: {result['error']}")
            return None

        # 找到 USDT 餘額
        usdt_balance = None
        for asset in result:
            if asset.get('asset') == 'USDT':
                usdt_balance = {
                    'asset': 'USDT',
                    'balance': float(asset.get('balance', 0)),
                    'availableBalance': float(asset.get('availableBalance', 0)),
                    'crossWalletBalance': float(asset.get('crossWalletBalance', 0)),
                    'crossUnPnl': float(asset.get('crossUnPnl', 0))
                }
                break

        if usdt_balance:
            print(f"✅ USDT 餘額:")
            print(f"   ├─ 總餘額: ${usdt_balance['balance']:.4f}")
            print(f"   ├─ 可用餘額: ${usdt_balance['availableBalance']:.4f}")
            print(f"   ├─ 跨倉餘額: ${usdt_balance['crossWalletBalance']:.4f}")
            print(f"   └─ 未實現盈虧: ${usdt_balance['crossUnPnl']:.4f}")
            return usdt_balance
        else:
            print("❌ 未找到 USDT 餘額")
            return None

    def get_account_info(self) -> dict:
        """獲取帳戶信息"""
        print("\n" + "-"*60)
        print("📊 獲取帳戶信息...")
        print("-"*60)

        result = self._make_request('GET', '/fapi/v2/account')

        if 'error' in result:
            print(f"❌ 獲取帳戶信息失敗: {result['error']}")
            return None

        print(f"✅ 帳戶信息:")
        print(f"   ├─ 總餘額: ${float(result.get('totalWalletBalance', 0)):.4f}")
        print(f"   ├─ 可用餘額: ${float(result.get('availableBalance', 0)):.4f}")
        print(f"   ├─ 未實現盈虧: ${float(result.get('totalUnrealizedProfit', 0)):.4f}")
        print(f"   └─ 保證金餘額: ${float(result.get('totalMarginBalance', 0)):.4f}")

        return result

    def get_current_price(self, symbol: str = "BTCUSDT") -> float:
        """獲取當前價格"""
        result = self._make_request('GET', '/fapi/v1/ticker/price', {'symbol': symbol}, signed=False)
        if 'price' in result:
            return float(result['price'])
        return 0

    def get_positions(self) -> list:
        """獲取當前持倉"""
        print("\n" + "-"*60)
        print("📋 獲取當前持倉...")
        print("-"*60)

        result = self._make_request('GET', '/fapi/v2/positionRisk')

        if 'error' in result:
            print(f"❌ 獲取持倉失敗: {result['error']}")
            return []

        # 過濾有倉位的
        active_positions = []
        for pos in result:
            position_amt = float(pos.get('positionAmt', 0))
            if position_amt != 0:
                active_positions.append({
                    'symbol': pos.get('symbol'),
                    'positionAmt': position_amt,
                    'entryPrice': float(pos.get('entryPrice', 0)),
                    'markPrice': float(pos.get('markPrice', 0)),
                    'unRealizedProfit': float(pos.get('unRealizedProfit', 0)),
                    'liquidationPrice': float(pos.get('liquidationPrice', 0)),
                    'leverage': int(pos.get('leverage', 1)),
                    'positionSide': pos.get('positionSide', 'BOTH')
                })

        if active_positions:
            print(f"✅ 當前有 {len(active_positions)} 個活躍倉位:")
            for pos in active_positions:
                direction = "做多 🟢" if pos['positionAmt'] > 0 else "做空 🔴"
                pnl_emoji = "📈" if pos['unRealizedProfit'] >= 0 else "📉"
                print(f"\n   📌 {pos['symbol']} ({direction})")
                print(f"      ├─ 倉位數量: {pos['positionAmt']}")
                print(f"      ├─ 入場價格: ${pos['entryPrice']:.2f}")
                print(f"      ├─ 標記價格: ${pos['markPrice']:.2f}")
                print(f"      ├─ {pnl_emoji} 未實現盈虧: ${pos['unRealizedProfit']:.4f}")
                print(f"      ├─ 強平價格: ${pos['liquidationPrice']:.2f}")
                print(f"      └─ 槓桿: {pos['leverage']}x")
        else:
            print("📭 目前沒有活躍倉位")

        return active_positions

    def set_leverage(self, symbol: str = "BTCUSDT", leverage: int = 1) -> bool:
        """設置槓桿"""
        print(f"\n⚙️ 設置 {symbol} 槓桿為 {leverage}x...")

        params = {
            'symbol': symbol,
            'leverage': leverage
        }

        result = self._make_request('POST', '/fapi/v1/leverage', params)

        if 'error' in result:
            print(f"❌ 設置槓桿失敗: {result['error']}")
            return False

        print(f"✅ 槓桿設置成功: {result.get('leverage')}x")
        return True

    def get_symbol_precision(self, symbol: str) -> int:
        """獲取交易對的數量精度"""
        precision_map = {
            'BTCUSDT': 3,
            'ETHUSDT': 3,
            'SOLUSDT': 1,
            'DOGEUSDT': 0,
            'ADAUSDT': 0,
            'LINKUSDT': 2,
        }
        return precision_map.get(symbol, 3)

    def calculate_quantity(self, symbol: str, usdt_amount: float, current_price: float, leverage: int) -> float:
        """
        計算訂單數量，確保訂單價值 >= 100 USDT
        """
        import math

        precision = self.get_symbol_precision(symbol)

        # 計算原始數量
        raw_quantity = (usdt_amount * leverage) / current_price

        # 向上取整到指定精度，確保訂單價值不會因為精度問題低於最小值
        multiplier = 10 ** precision
        quantity = math.ceil(raw_quantity * multiplier) / multiplier

        # 驗證訂單價值
        order_value = quantity * current_price
        min_notional = 100  # Binance Futures 最小訂單價值

        # 如果還是小於最小值，增加數量
        if order_value < min_notional:
            quantity = math.ceil((min_notional / current_price) * multiplier) / multiplier
            print(f"⚠️ 調整數量以滿足最小訂單價值 ${min_notional}")

        return quantity

    def open_long_position(self, symbol: str = "BTCUSDT", usdt_amount: float = 100) -> dict:
        """
        開多倉（做多）
        使用指定的 USDT 金額購買
        """
        print("\n" + "="*60)
        print(f"🟢 開多倉: {symbol}")
        print(f"💵 投入金額: ${usdt_amount} USDT")
        print("="*60)

        # 設置槓桿
        leverage = self.config.get('leverage', 1)
        self.set_leverage(symbol, leverage)

        # 獲取當前價格
        current_price = self.get_current_price(symbol)
        if current_price <= 0:
            print("❌ 無法獲取當前價格")
            return None

        print(f"📊 當前價格: ${current_price:.2f}")

        # 計算數量（確保滿足最小訂單價值）
        quantity = self.calculate_quantity(symbol, usdt_amount, current_price, leverage)
        order_value = quantity * current_price

        print(f"📦 計算數量: {quantity} {symbol.replace('USDT', '')}")
        print(f"💰 訂單價值: ${order_value:.2f} USDT")
        print(f"⚡ 槓桿: {leverage}x")

        # 轉換數量為字符串，避免浮點精度問題
        precision = self.get_symbol_precision(symbol)
        quantity_str = f"{quantity:.{precision}f}"

        # 下市價單
        params = {
            'symbol': symbol,
            'side': 'BUY',
            'type': 'MARKET',
            'quantity': quantity_str
        }

        result = self._make_request('POST', '/fapi/v1/order', params)

        if 'error' in result:
            print(f"❌ 開倉失敗: {result['error']}")
            return None

        print(f"\n✅ 開倉成功!")
        print(f"   ├─ 訂單ID: {result.get('orderId')}")
        print(f"   ├─ 交易對: {result.get('symbol')}")
        print(f"   ├─ 方向: {result.get('side')}")
        print(f"   ├─ 數量: {result.get('origQty')}")
        print(f"   ├─ 成交均價: ${float(result.get('avgPrice', 0)):.2f}")
        print(f"   └─ 狀態: {result.get('status')}")

        return result

    def open_short_position(self, symbol: str = "BTCUSDT", usdt_amount: float = 100) -> dict:
        """
        開空倉（做空）
        使用指定的 USDT 金額
        """
        print("\n" + "="*60)
        print(f"🔴 開空倉: {symbol}")
        print(f"💵 投入金額: ${usdt_amount} USDT")
        print("="*60)

        # 設置槓桿
        leverage = self.config.get('leverage', 1)
        self.set_leverage(symbol, leverage)

        # 獲取當前價格
        current_price = self.get_current_price(symbol)
        if current_price <= 0:
            print("❌ 無法獲取當前價格")
            return None

        print(f"📊 當前價格: ${current_price:.2f}")

        # 計算數量（確保滿足最小訂單價值）
        quantity = self.calculate_quantity(symbol, usdt_amount, current_price, leverage)
        order_value = quantity * current_price

        print(f"📦 計算數量: {quantity} {symbol.replace('USDT', '')}")
        print(f"💰 訂單價值: ${order_value:.2f} USDT")
        print(f"⚡ 槓桿: {leverage}x")

        # 轉換數量為字符串，避免浮點精度問題
        precision = self.get_symbol_precision(symbol)
        quantity_str = f"{quantity:.{precision}f}"

        # 下市價單
        params = {
            'symbol': symbol,
            'side': 'SELL',
            'type': 'MARKET',
            'quantity': quantity_str
        }

        result = self._make_request('POST', '/fapi/v1/order', params)

        if 'error' in result:
            print(f"❌ 開倉失敗: {result['error']}")
            return None

        print(f"\n✅ 開倉成功!")
        print(f"   ├─ 訂單ID: {result.get('orderId')}")
        print(f"   ├─ 交易對: {result.get('symbol')}")
        print(f"   ├─ 方向: {result.get('side')}")
        print(f"   ├─ 數量: {result.get('origQty')}")
        print(f"   ├─ 成交均價: ${float(result.get('avgPrice', 0)):.2f}")
        print(f"   └─ 狀態: {result.get('status')}")

        return result

    def close_position(self, symbol: str = "BTCUSDT") -> dict:
        """
        關閉指定交易對的倉位
        """
        print("\n" + "="*60)
        print(f"🔒 關閉倉位: {symbol}")
        print("="*60)

        # 獲取當前持倉
        positions = self.get_positions()

        # 找到對應的倉位
        target_position = None
        for pos in positions:
            if pos['symbol'] == symbol:
                target_position = pos
                break

        if not target_position:
            print(f"❌ 未找到 {symbol} 的活躍倉位")
            return None

        position_amt = target_position['positionAmt']

        # 確定平倉方向
        if position_amt > 0:
            # 持有多倉，需要賣出平倉
            close_side = 'SELL'
            close_qty = abs(position_amt)
            print(f"📊 當前持有多倉: {position_amt}")
        else:
            # 持有空倉，需要買入平倉
            close_side = 'BUY'
            close_qty = abs(position_amt)
            print(f"📊 當前持有空倉: {position_amt}")

        print(f"🔄 平倉方向: {close_side}")
        print(f"📦 平倉數量: {close_qty}")

        # 轉換數量為字符串，避免浮點精度問題
        precision = self.get_symbol_precision(symbol)
        close_qty_str = f"{close_qty:.{precision}f}"

        # 下市價單平倉
        params = {
            'symbol': symbol,
            'side': close_side,
            'type': 'MARKET',
            'quantity': close_qty_str,
            'reduceOnly': 'true'  # 僅平倉
        }

        result = self._make_request('POST', '/fapi/v1/order', params)

        if 'error' in result:
            print(f"❌ 平倉失敗: {result['error']}")
            return None

        print(f"\n✅ 平倉成功!")
        print(f"   ├─ 訂單ID: {result.get('orderId')}")
        print(f"   ├─ 交易對: {result.get('symbol')}")
        print(f"   ├─ 方向: {result.get('side')}")
        print(f"   ├─ 數量: {result.get('origQty')}")
        print(f"   ├─ 成交均價: ${float(result.get('avgPrice', 0)):.2f}")
        print(f"   └─ 狀態: {result.get('status')}")

        # 顯示實現盈虧
        entry_price = target_position['entryPrice']
        exit_price = float(result.get('avgPrice', 0))
        pnl = target_position['unRealizedProfit']

        print(f"\n💰 交易結果:")
        print(f"   ├─ 入場價格: ${entry_price:.2f}")
        print(f"   ├─ 出場價格: ${exit_price:.2f}")
        pnl_emoji = "🟢 盈利" if pnl >= 0 else "🔴 虧損"
        print(f"   └─ {pnl_emoji}: ${pnl:.4f}")

        return result

    def close_all_positions(self) -> list:
        """關閉所有倉位"""
        print("\n" + "="*60)
        print("🔒 關閉所有倉位")
        print("="*60)

        positions = self.get_positions()

        if not positions:
            print("📭 沒有需要關閉的倉位")
            return []

        results = []
        for pos in positions:
            result = self.close_position(pos['symbol'])
            if result:
                results.append(result)
            time.sleep(0.5)  # 避免頻率限制

        return results

    def run_interactive(self):
        """交互式測試菜單"""
        while True:
            print("\n" + "="*60)
            print("📋 Binance Futures Testnet 測試菜單")
            print("="*60)
            print("1. 查看餘額")
            print("2. 查看帳戶信息")
            print("3. 查看當前持倉")
            print("4. 開多倉 (BTC, 100 USDT)")
            print("5. 開空倉 (BTC, 100 USDT)")
            print("6. 關閉 BTC 倉位")
            print("7. 關閉所有倉位")
            print("8. 自訂開倉")
            print("0. 退出")
            print("-"*60)

            try:
                choice = input("請選擇操作 (0-8): ").strip()

                if choice == '0':
                    print("\n👋 再見!")
                    break
                elif choice == '1':
                    self.get_balance()
                elif choice == '2':
                    self.get_account_info()
                elif choice == '3':
                    self.get_positions()
                elif choice == '4':
                    self.open_long_position("BTCUSDT", 100)
                elif choice == '5':
                    self.open_short_position("BTCUSDT", 100)
                elif choice == '6':
                    self.close_position("BTCUSDT")
                elif choice == '7':
                    self.close_all_positions()
                elif choice == '8':
                    self.custom_order_menu()
                else:
                    print("❌ 無效選擇，請重新輸入")

            except KeyboardInterrupt:
                print("\n\n👋 用戶中斷，退出程序")
                break
            except Exception as e:
                print(f"❌ 發生錯誤: {e}")

    def custom_order_menu(self):
        """自訂開倉菜單"""
        print("\n" + "-"*60)
        print("🛠️ 自訂開倉")
        print("-"*60)

        # 選擇交易對
        print("可用交易對: BTCUSDT, ETHUSDT, SOLUSDT, DOGEUSDT, ADAUSDT, LINKUSDT")
        symbol = input("請輸入交易對 (默認 BTCUSDT): ").strip().upper()
        if not symbol:
            symbol = "BTCUSDT"

        # 選擇方向
        direction = input("方向 (long/short, 默認 long): ").strip().lower()
        if direction not in ['long', 'short']:
            direction = 'long'

        # 輸入金額
        try:
            amount = float(input("投入金額 USDT (默認 100): ").strip() or "100")
        except:
            amount = 100

        print(f"\n📋 確認訂單:")
        print(f"   交易對: {symbol}")
        print(f"   方向: {'做多 🟢' if direction == 'long' else '做空 🔴'}")
        print(f"   金額: ${amount} USDT")

        confirm = input("\n確認下單? (y/n): ").strip().lower()
        if confirm == 'y':
            if direction == 'long':
                self.open_long_position(symbol, amount)
            else:
                self.open_short_position(symbol, amount)
        else:
            print("❌ 已取消下單")


def main():
    """主程序"""
    print("\n")
    print("╔" + "═"*58 + "╗")
    print("║" + " "*15 + "Binance Futures Testnet" + " "*20 + "║")
    print("║" + " "*18 + "下單測試工具 v1.0" + " "*21 + "║")
    print("╚" + "═"*58 + "╝")
    print()

    try:
        tester = FuturesOrderTester()

        # 首先測試連線
        print("\n🔍 測試 API 連線...")
        balance = tester.get_balance()

        if balance:
            print("\n✅ API 連線成功!")
            tester.run_interactive()
        else:
            print("\n❌ API 連線失敗，請檢查:")
            print("   1. API Key 和 Secret 是否正確")
            print("   2. 網路連線是否正常")
            print("   3. Testnet 是否可用")

    except Exception as e:
        print(f"\n❌ 程序啟動失敗: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
