import streamlit as st
from FinanceDashboard import FinanceService
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import altair as alt
import json
import os
import time
from datetime import datetime

# 頁面設定
st.set_page_config(page_title="金融即時監控儀表板", page_icon="📈", layout="wide")

# --- Google Sheets 處理邏輯 ---
def get_gsheets_conn():
    return st.connection("gsheets", type=GSheetsConnection)

def fetch_watchlist_from_gs(conn, user_id):
    """從 Google Sheets 取得使用者的追蹤清單"""
    try:
        df = conn.read(ttl="1s") # 極短快取，確保讀取靈敏
        if df is not None and not df.empty and "user_id" in df.columns:
            user_data = df[df["user_id"] == user_id]
            if not user_data.empty:
                return json.loads(user_data.iloc[0]["watchlist"])
    except Exception:
        pass
    return ["AAPL", "TSLA", "NVDA", "2330.TW"] # 找不到則回傳預設值

def sync_watchlist_to_gs(conn, user_id, watchlist):
    """將清單同步回 Google Sheets"""
    try:
        # 讀取現有資料
        df = conn.read(ttl=0) # 強制不使用快取讀取最新狀態
        if df is None or df.empty:
            df = pd.DataFrame(columns=["user_id", "watchlist"])
        
        watchlist_json = json.dumps(watchlist)
        
        if user_id in df["user_id"].values:
            # 更新現有使用者
            df.loc[df["user_id"] == user_id, "watchlist"] = watchlist_json
        else:
            # 新增使用者
            new_row = pd.DataFrame([{"user_id": user_id, "watchlist": watchlist_json}])
            df = pd.concat([df, new_row], ignore_index=True)
        
        # 更新回 Google Sheets
        conn.update(data=df)
        # 清除快取，確保下次讀取是最新的資料
        st.cache_data.clear()
        st.cache_resource.clear()
        return True
    except Exception as e:
        st.sidebar.error(f"同步失敗: {e}")
        return False

def main():
    fin_svc = FinanceService()
    conn = get_gsheets_conn()

    # --- 側邊欄 ---
    st.sidebar.title("⚙️ 管理面板")
    
    # 1. 自動更新
    auto_refresh = st.sidebar.toggle("自動更新 (每分鐘)", value=False)
    refresh_status = st.sidebar.empty()  # 建立一個佔位符用來顯示倒數

    if auto_refresh:
        refresh_status.caption(f"⏳ 上次更新: {datetime.now().strftime('%H:%M:%S')}")

    # 2. 使用者識別與追蹤清單管理
    st.sidebar.markdown("---")
    user_id = st.sidebar.text_input("👤 使用者帳號 (用於儲存清單)", value="default_user").strip()
    st.sidebar.subheader("📋 編輯追蹤清單")
    
    # 使用 session_state 來儲存每個使用者獨立的清單
    # 增加判斷：如果 user_id 改變，則重新從雲端抓取清單
    if 'watchlist' not in st.session_state or st.session_state.get('last_user_id') != user_id:
        st.session_state.watchlist = fetch_watchlist_from_gs(conn, user_id)
        st.session_state.last_user_id = user_id
        st.rerun()
    
    # 搜尋功能：輸入名稱或代碼
    search_query = st.sidebar.text_input("🔍 搜尋名稱或代碼 (如: 台積電, NVDA)", "")
    if search_query:
        search_results = fin_svc.search_ticker(search_query)
        if search_results:
            # 將搜尋結果轉換為對應字典，方便顯示選單
            options = {r["display"]: r["symbol"] for r in search_results}
            selected_display = st.sidebar.selectbox("請選擇正確的項目:", list(options.keys()))
            if st.sidebar.button("➕ 加入追蹤"):
                symbol_to_add = options[selected_display]
                if symbol_to_add not in st.session_state.watchlist:
                    st.session_state.watchlist.append(symbol_to_add)
                    sync_watchlist_to_gs(conn, user_id, st.session_state.watchlist)
                    st.rerun()
        else:
            st.sidebar.warning("找不到相符的結果")

    st.sidebar.write("---")
    st.sidebar.write("目前追蹤中:")
    for ticker in st.session_state.watchlist:
        c_t, c_b = st.sidebar.columns([3, 1])
        c_t.code(ticker)
        if c_b.button("🗑️", key=f"del_{ticker}"):
            st.session_state.watchlist.remove(ticker)
            sync_watchlist_to_gs(conn, user_id, st.session_state.watchlist)
            st.rerun()

    if st.sidebar.button("💾 強制同步至雲端"):
        if sync_watchlist_to_gs(conn, user_id, st.session_state.watchlist):
            st.sidebar.success("同步成功！")

    # --- 主介面 ---
    st.title("📈 金融即時監控儀表板")
    st.caption(f"最後更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (市場數據延遲約 15 分鐘)")

    # --- 0. 匯率區塊 (以台幣為基準) ---
    with st.container(border=True):
        st.markdown("#### 💱 即時匯率 (對台幣 TWD)")
        ex_cols = st.columns(6)
        exchanges = [
            ("🇺🇸 美金", "USDTWD=X"),
            ("🇪🇺 歐元", "EURTWD=X"),
            ("🇨🇳 人民幣", "CNYTWD=X"),
            ("🇯🇵 日幣", "JPYTWD=X"),
            ("🇨🇭 瑞士法郎", "CHFTWD=X"),
            ("🇬🇧 英鎊", "GBPTWD=X")
        ]
        for idx, (name, symbol) in enumerate(exchanges):
            data = fin_svc.get_market_data(symbol)
            if data:
                # 針對日幣匯率強制顯示至小數點第三位，其餘使用原數值顯示
                display_val = f"{data['price']:.3f}" if symbol == "JPYTWD=X" else f"{data['price']}"
                
                ex_cols[idx].metric(
                    label=name,
                    value=display_val,
                    delta=f"{data['change_percent']}% | YTD: {data['ytd_change']}%"
                )

    # --- 1. 大宗商品區塊 (黃金, 白銀, 原油) ---
    with st.container(border=True):
        st.markdown("#### 🔋 能源與貴金屬")
        c1, c2, c3, c4 = st.columns(4)
        
        commodities = [
            ("🥇 現貨黃金", fin_svc.symbols["gold"]),
            ("🥈 現貨白銀", fin_svc.symbols["silver"]),
            ("🛢️ 布萊特原油", fin_svc.symbols["oil_brent"]),
            ("🛢️ 德州原油(WTI)", fin_svc.symbols["oil_wti"])
        ]

        cols = [c1, c2, c3, c4]
        for idx, (name, symbol) in enumerate(commodities):
            data = fin_svc.get_market_data(symbol)
            if data:
                cols[idx].metric(
                    label=name, 
                    value=f"{data['price']} {data['currency']}", 
                    delta=f"{data['change_percent']}% | YTD: {data['ytd_change']}%"
                )

    # --- 2. 世界各大指數區 ---
    with st.container(border=True):
        st.markdown("#### 🌐 全球股市指數")
        
        # 定義指數區域與代碼
        index_regions = {
            "亞洲市場": {
                "台股大盤": "^TWII", "日經 225": "^N225", "韓國綜合": "^KS11", 
                "香港恆生": "^HSI", "上證指數": "000001.SS", "深圳成指": "399001.SZ",
                "泰國 SET": "^SET.BK", "新加坡 STI": "^STI"
            },
            "美洲市場": {
                "標普 500": "^GSPC", "道瓊工業": "^DJI", "那斯達克": "^IXIC", "費城半導體": "^SOX"
            },
            "歐洲市場": {
                "德國 DAX": "^GDAXI", "法國 CAC": "^FCHI", "英國 FTSE": "^FTSE", 
                "瑞士 SMI": "^SSMI", "俄羅斯 MOEX": "IMOEX.ME"
            }
        }

        # 使用 Tabs 分類顯示區域
        tabs = st.tabs(list(index_regions.keys()))
        
        for i, (region, tickers) in enumerate(index_regions.items()):
            with tabs[i]:
                ticker_list = list(tickers.items())
                for start_idx in range(0, len(ticker_list), 4):
                    row_tickers = ticker_list[start_idx:start_idx+4]
                    cols = st.columns(4) # 固定 4 欄
                    for col_idx, (name, symbol) in enumerate(row_tickers):
                        data = fin_svc.get_market_data(symbol)
                        if data:
                            cols[col_idx].metric(
                                label=name,
                                value=f"{data['price']}",
                                delta=f"今日: {data['change_percent']}% | YTD: {data['ytd_change']}%"
                            )
                        else:
                            cols[col_idx].caption(f"{name} (無數據)")

    # --- 3. 個股追蹤清單 (Watchlist) ---
    st.markdown("#### 🔍 自定義個股監控")
    if not st.session_state.watchlist:
        st.info("目前清單為空，請從左側管理面板新增代碼。")
    else:
        for ticker in st.session_state.watchlist:
            with st.expander(f"📊 {ticker} 走勢詳情", expanded=True):
                data = fin_svc.get_market_data(ticker)
                if data:
                    cl, cr = st.columns([1, 3])
                    with cl:
                        st.metric(
                            f"{ticker} 價格", 
                            f"{data['price']} {data['currency']}", 
                            f"{data['change']} ({data['change_percent']}%)"
                        )
                        st.caption(f"更新: {data['last_update']}")
                    with cr:
                        hist = fin_svc.get_historical_data(ticker, period="1mo")
                        if not hist.empty:
                            chart_data = hist.reset_index()
                            
                            # 找出期間最高與最低價
                            max_p = chart_data['Close'].max()
                            min_p = chart_data['Close'].min()
                            
                            # 建立基礎圖層
                            base = alt.Chart(chart_data).encode(
                                x=alt.X('Date:T', title='日期'),
                                y=alt.Y('Close:Q', title='收盤價', scale=alt.Scale(zero=False)),
                                tooltip=['Date', 'Close']
                            )
                            
                            # 1. 主線條圖層
                            line = base.mark_line(color='#1f77b4')
                            
                            # 2. 最高點標記層 (紅色點 + 標籤)
                            hi_pt = base.transform_filter(alt.datum.Close == max_p).mark_point(color='red', size=60, filled=True)
                            hi_lbl = base.transform_filter(alt.datum.Close == max_p).mark_text(dy=-12, color='red', fontWeight='bold').encode(
                                text=alt.Text('Close:Q', format='.2f')
                            )
                            
                            # 3. 最低點標記層 (綠色點 + 標籤)
                            lo_pt = base.transform_filter(alt.datum.Close == min_p).mark_point(color='green', size=60, filled=True)
                            lo_lbl = base.transform_filter(alt.datum.Close == min_p).mark_text(dy=15, color='green', fontWeight='bold').encode(
                                text=alt.Text('Close:Q', format='.2f')
                            )
                            
                            # 將所有圖層疊加顯示
                            st.altair_chart((line + hi_pt + hi_lbl + lo_pt + lo_lbl).properties(height=200), use_container_width=True)
                        else:
                            st.warning("暫無歷史趨勢數據")

    # 自動刷新
    if auto_refresh:
        # 改用倒數計時，讓使用者知道程式還在運作
        for i in range(60, 0, -1):
            refresh_status.caption(f"🔄 將在 {i} 秒後自動更新...")
            time.sleep(1)
            # 如果在倒數過程中使用者關閉了開關，Streamlit 會自動觸發重新執行
            # 這裡的 sleep(1) 讓程式每秒都能釋放控制權來偵測 UI 變動
        st.rerun()
    elif st.sidebar.button("🔄 手動刷新數據"):
        st.rerun()

if __name__ == "__main__":
    main()