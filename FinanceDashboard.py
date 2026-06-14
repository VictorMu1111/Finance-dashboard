import yfinance as yf
from typing import Dict, Any, Optional, List
from datetime import datetime

class FinanceService:
    """封裝 Yahoo Finance API 的金融數據服務"""
    
    def __init__(self):
        # 定義商品的 Yahoo Finance Ticker
        self.symbols = {
            "gold": "GC=F",      # 黃金期貨 (COMEX)
            "silver": "SI=F",    # 白銀期貨 (COMEX)
            "oil_brent": "BZ=F", # 北海布萊特原油期貨
            "oil_wti": "CL=F"    # 德州原油 (WTI) 期貨
        }

    def get_market_data(self, ticker_symbol: str) -> Optional[Dict[str, Any]]:
        """獲取指定標的的即時價格與變動率"""
        try:
            ticker = yf.Ticker(ticker_symbol)
            
            # 1. 嘗試從 fast_info 獲取即時數據
            info = ticker.fast_info
            current_price = getattr(info, 'last_price', None)
            prev_close = getattr(info, 'previous_close', None)
            currency = getattr(info, 'currency', 'USD')
            
            # 2. 如果是假日或 fast_info 失效，嘗試從 history 獲取最後一筆資料
            if current_price is None or current_price == 0:
                hist = ticker.history(period="5d")
                if not hist.empty:
                    current_price = hist['Close'].iloc[-1]
                    # 如果有至少兩天的資料，計算與前一天的變動
                    if len(hist) >= 2:
                        prev_close = hist['Close'].iloc[-2]
                    else:
                        prev_close = current_price
            
            # 安全處理價格計算
            price = float(current_price) if current_price is not None else 0.0
            change = float(current_price - prev_close) if (current_price is not None and prev_close is not None) else 0.0
            change_percent = (change / prev_close) * 100 if (prev_close is not None and prev_close != 0) else 0.0

            # 3. 計算今年以來 (YTD) 的漲跌幅
            ytd_change_percent = 0.0
            ytd_hist = ticker.history(period="ytd")
            if not ytd_hist.empty:
                # 取今年第一個交易日的開盤價
                first_open = ytd_hist['Open'].iloc[0]
                if first_open and first_open != 0:
                    ytd_change_percent = ((price - first_open) / first_open) * 100

            # 針對匯率標的 (Ticker 以 =X 結尾) 提供更高精度 (4位)，其餘維持 2 位
            precision = 4 if ticker_symbol.endswith('=X') else 2

            return {
                "symbol": ticker_symbol,
                "price": round(price, precision),
                "change": round(change, precision),
                "change_percent": round(change_percent, 2),
                "ytd_change": round(ytd_change_percent, 2),
                "currency": currency,
                "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        except Exception as e:
            print(f"獲取 {ticker_symbol} 數據時發生錯誤: {e}")
            return None

    def get_historical_data(self, ticker_symbol: str, period: str = "1mo"):
        """獲取歷史價格用於繪製圖表"""
        ticker = yf.Ticker(ticker_symbol)
        return ticker.history(period=period)

    def search_ticker(self, query: str) -> List[Dict[str, str]]:
        """搜尋股票代碼"""
        try:
            # 利用 yfinance 搜尋功能，回傳相關性最高的 8 個項目
            search = yf.Search(query, max_results=8)
            results = []
            for quote in search.quotes:
                symbol = quote.get("symbol")
                # 優先取得完整名稱，若無則取短名稱或代碼
                name = quote.get("longname") or quote.get("shortname") or symbol
                if symbol:
                    results.append({"symbol": symbol, "display": f"{name} ({symbol})"})
            return results
        except Exception as e:
            print(f"搜尋 {query} 時發生錯誤: {e}")
            return []