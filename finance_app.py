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
        df = conn.read(ttl="1s")
        if df is not None and not df.empty and "user_id" in df.columns:
            # 確保 user_id 為字串以利比對
            df['user_id'] = df['user_id'].astype(str)
            user_data = df[df["user_id"] == str(user_id)]
            if not user_data.empty:
                return json.loads(user_data.iloc[0]["watchlist"])
    except Exception as e:
        st.sidebar.warning(f"讀取雲端清單失敗 (使用預設值): {e}")
    return ["AAPL", "TSLA", "NVDA", "2330.TW"] # 找不到則回傳預設值

def sync_watchlist_to_gs(conn, user_id, watchlist):
    """將清單同步回 Google Sheets"""
    try:
        # 1. 強制讀取最新資料並建立副本，避免影響快取
        raw_df = conn.read(ttl=0).copy()
        
        # 2. 初始化或整理 Dataframe
        if raw_df is None or raw_df.empty:
            df = pd.DataFrame(columns=["user_id", "watchlist"])
        else:
            # 只保留必要的欄位，避免 GSheets 自動生成的索引欄位干擾
            valid_cols = [c for c in ["user_id", "watchlist"] if c in raw_df.columns]
            df = raw_df[valid_cols]
            if "user_id" not in df.columns: df["user_id"] = None
            if "watchlist" not in df.columns: df["watchlist"] = None

        # 確保類型一致
        df = df.astype({"user_id": str, "watchlist": str})
        user_id_str = str(user_id).strip()
        watchlist_json = json.dumps(watchlist)
        
        if user_id_str in df["user_id"].values:
            # 更新現有使用者
            df.loc[df["user_id"] == user_id_str, "watchlist"] = watchlist_json
        else:
            # 新增使用者
            new_row = pd.DataFrame([{"user_id": user_id_str, "watchlist": watchlist_json}])
            df = pd.concat([df, new_row], ignore_index=True)
        
        # 3. 寫回雲端 (確保只寫入 user_id 與 watchlist)
        df = df[["user_id", "watchlist"]]
        conn.update(data=df)
        
        # 4. 清除讀取快取，強制下次重新抓取
        st.cache_data.clear()
        return True
    except Exception as e:
        # 顯示具體的錯誤訊息，幫助除錯
        st.sidebar.error(f"同步失敗: {str(e)}")
        return False

def main():
    # --- CSS 注入：美化邊框、陰影與指標卡片 ---
    st.markdown("""
        <style>
        [data-testid="stMetric"] {
            background-color: rgba(151, 166, 195, 0.15) !important;
            padding: 15px;
            border-radius: 10px;
            border: 1px solid rgba(151, 166, 195, 0.2);
        }
        [data-testid="stMetricValue"] div {
            color: inherit !important;
        }
        .section-header {
            background: linear-gradient(90deg, rgba(30,136,229,1) 0%, rgba(21,101,192,1) 100%);
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-weight: bold;
        }
        </style>
    """, unsafe_allow_html=True)

    fin_svc = FinanceService()
    conn = get_gsheets_conn()

    # --- 側邊欄 ---
    st.sidebar.markdown("<h2 style='color: #1E88E5;'>⚙️ 管理面板</h2>", unsafe_allow_html=True)
    
    # 1. 自動更新
    auto_refresh = st.sidebar.toggle("自動更新 (每分鐘)", value=False)
    refresh_status = st.sidebar.empty()  # 建立一個佔位符用來顯示倒數
    
    # 2. 圖表類型選擇
    chart_type = st.sidebar.radio("圖表樣式", ["線圖 (Line)", "K 線圖 (K-Line)"], horizontal=True)

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
                    with st.sidebar.spinner("同步中..."):
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
            with st.sidebar.spinner("同步中..."):
                st.session_state.watchlist.remove(ticker)
                sync_watchlist_to_gs(conn, user_id, st.session_state.watchlist)
                st.rerun()

    if st.sidebar.button("💾 強制同步至雲端"):
        with st.sidebar.spinner("正在同步雲端資料..."):
            if sync_watchlist_to_gs(conn, user_id, st.session_state.watchlist):
                st.sidebar.success("同步成功！")

    # --- 主介面 ---
    st.markdown("<h1 style='text-align: center; color: #1E88E5;'>📈 金融即時監控儀表板</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: gray;'>最後更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (數據延遲約 15 分鐘)</p>", unsafe_allow_html=True)

    # --- 0. 匯率區塊 (以台幣為基準) ---
    with st.container(border=True):
        st.markdown('<div class="section-header">💱 即時匯率 (對台幣 TWD)</div>', unsafe_allow_html=True)
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
        st.markdown('<div class="section-header">🔋 能源與貴金屬</div>', unsafe_allow_html=True)
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
        st.markdown('<div class="section-header">🌐 全球股市指數</div>', unsafe_allow_html=True)
        
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
    with st.container(border=True):
        st.markdown('<div class="section-header">🔍 自定義個股監控</div>', unsafe_allow_html=True)
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
                                
                                if chart_type == "K 線圖 (K-Line)":
                                    # --- K 線圖邏輯 (紅漲綠跌) ---
                                    # 判斷漲跌顏色條件
                                    color_condition = alt.condition(
                                        "datum.Open <= datum.Close",
                                        alt.value("#FF0000"),  # 漲：紅
                                        alt.value("#00AD00")   # 跌：綠
                                    )
                                    
                                    base = alt.Chart(chart_data).encode(
                                        x=alt.X('Date:T', title='日期'),
                                        color=color_condition,
                                        tooltip=['Date', 'Open', 'High', 'Low', 'Close']
                                    )
                                    
                                    # 影線 (High/Low)
                                    rule = base.mark_rule().encode(
                                        y=alt.Y('Low:Q', title='價格', scale=alt.Scale(zero=False)),
                                        y2='High:Q'
                                    )
                                    
                                    # 實體 (Open/Close)
                                    bar = base.mark_bar().encode(
                                        y='Open:Q',
                                        y2='Close:Q'
                                    )
                                    
                                    st.altair_chart((rule + bar).properties(height=200), use_container_width=True)
                                    
                                else:
                                    # --- 原有的智慧線圖邏輯 ---
                                    max_p = chart_data['Close'].max()
                                    min_p = chart_data['Close'].min()
                                    
                                    base = alt.Chart(chart_data).encode(
                                        x=alt.X('Date:T', title='日期'),
                                        y=alt.Y('Close:Q', title='收盤價', scale=alt.Scale(zero=False)),
                                        tooltip=['Date', 'Close']
                                    )
                                    line = base.mark_line(color='#1f77b4')
                                    hi_pt = base.transform_filter(alt.datum.Close == max_p).mark_point(color='red', size=60, filled=True)
                                    hi_lbl = base.transform_filter(alt.datum.Close == max_p).mark_text(dy=-12, color='red', fontWeight='bold').encode(
                                        text=alt.Text('Close:Q', format='.2f')
                                    )
                                    lo_pt = base.transform_filter(alt.datum.Close == min_p).mark_point(color='green', size=60, filled=True)
                                    lo_lbl = base.transform_filter(alt.datum.Close == min_p).mark_text(dy=15, color='green', fontWeight='bold').encode(
                                        text=alt.Text('Close:Q', format='.2f')
                                    )
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