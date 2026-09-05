import streamlit as st
from FinanceDashboard import FinanceService
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import plotly.graph_objects as go
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
            df['user_id'] = df['user_id'].astype(str)
            user_data = df[df["user_id"] == str(user_id)]
            if not user_data.empty:
                return json.loads(user_data.iloc[0]["watchlist"])
    except Exception as e:
        st.sidebar.warning(f"讀取雲端清單失敗 (使用預設值): {e}")
    return ["AAPL", "TSLA", "NVDA", "2330.TW"]

def sync_watchlist_to_gs(conn, user_id, watchlist):
    """將清單同步回 Google Sheets"""
    try:
        raw_df = conn.read(ttl=0).copy()
        if raw_df is None or raw_df.empty:
            df = pd.DataFrame(columns=["user_id", "watchlist"])
        else:
            valid_cols = [c for c in ["user_id", "watchlist"] if c in raw_df.columns]
            df = raw_df[valid_cols]
            if "user_id" not in df.columns: df["user_id"] = None
            if "watchlist" not in df.columns: df["watchlist"] = None
        df = df.astype({"user_id": str, "watchlist": str})
        user_id_str = str(user_id).strip()
        watchlist_json = json.dumps(watchlist)
        if user_id_str in df["user_id"].values:
            df.loc[df["user_id"] == user_id_str, "watchlist"] = watchlist_json
        else:
            new_row = pd.DataFrame([{"user_id": user_id_str, "watchlist": watchlist_json}])
            df = pd.concat([df, new_row], ignore_index=True)
        df = df[["user_id", "watchlist"]]
        conn.update(data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.sidebar.error(f"同步失敗: {str(e)}")
        return False


# --- 歷史資料快取函式 ---
@st.cache_data(ttl=300)
def get_historical_data_cached(_fin_svc, symbol, period):
    """快取歷史資料，避免重複下載"""
    try:
        hist = _fin_svc.get_historical_data(symbol, period=period)
        return hist
    except Exception as e:
        return None

@st.cache_data(ttl=300)
def get_market_data_cached(_fin_svc, symbol):
    """快取即時市場數據"""
    try:
        return _fin_svc.get_market_data(symbol)
    except Exception as e:
        return None

@st.cache_data(ttl=300)
def get_cny_twd_history(_fin_svc, period="3mo"):
    """計算人民幣兌台幣歷史匯率 (CNYTWD = USDTWD / USDCNY)"""
    try:
        usdtwd = _fin_svc.get_historical_data("USDTWD=X", period=period)
        usdcny = _fin_svc.get_historical_data("USDCNY=X", period=period)
        
        if usdtwd is not None and not usdtwd.empty and usdcny is not None and not usdcny.empty:
            df = pd.DataFrame({
                "USDTWD": usdtwd["Close"],
                "USDCNY": usdcny["Close"]
            }).dropna()
            
            df["Close"] = df["USDTWD"] / df["USDCNY"]
            df["Open"] = df["Close"]
            df["High"] = df["Close"]
            df["Low"] = df["Close"]
            
            return df[["Open", "High", "Low", "Close"]]
        return None
    except Exception as e:
        st.warning(f"計算人民幣兌台幣失敗: {e}")
        return None

@st.cache_data(ttl=300)
def get_cny_twd_market_data(_fin_svc):
    """計算人民幣兌台幣即時匯率"""
    try:
        usdtwd = _fin_svc.get_market_data("USDTWD=X")
        usdcny = _fin_svc.get_market_data("USDCNY=X")
        
        if usdtwd and usdcny:
            price = usdtwd["price"] / usdcny["price"]
            change_percent = usdtwd["change_percent"] - usdcny["change_percent"]
            return {
                "price": price,
                "change_percent": change_percent,
                "ytd_change": 0,
                "currency": "TWD"
            }
        return None
    except Exception as e:
        return None


# --- 共用：繪製卡片 + 按鈕函式 ---
def render_card_with_button(col, name, symbol, value_str, delta_str, btn_key, session_key_symbol, session_key_name):
    """繪製帶有歷史走勢按鈕的卡片"""
    delta_val = 0.0
    try:
        delta_val = float(delta_str.split('%')[0].replace('▲', '').replace('▼', '').replace('今日: ', '').strip())
    except:
        pass
    delta_color = "green" if delta_val >= 0 else "red"
    delta_arrow = "▲" if delta_val >= 0 else "▼"

    with col:
        st.markdown(f"""
        <div style="
            background-color: rgba(151, 166, 195, 0.15);
            padding: 12px;
            border-radius: 10px;
            border: 1px solid rgba(151, 166, 195, 0.2);
            margin-bottom: 5px;
            text-align: center;
        ">
            <div style="font-size: 13px; font-weight: bold;">{name}</div>
            <div style="font-size: 20px; font-weight: bold; margin: 5px 0;">{value_str}</div>
            <div style="font-size: 12px; color: {delta_color};">
                {delta_arrow} {delta_str}
            </div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("📊 歷史走勢", key=btn_key, use_container_width=True):
            if st.session_state[session_key_symbol] == symbol:
                st.session_state[session_key_symbol] = None
                st.session_state[session_key_name] = ""
            else:
                st.session_state[session_key_symbol] = symbol
                st.session_state[session_key_name] = name


def render_plotly_chart(chart_data, title, price_fmt=".3f", line_color="#1E88E5", chart_type="線圖 (Line)"):
    """使用 Plotly 繪製圖表（自動最佳化 Y 軸）"""
    fig = go.Figure()
    
    if chart_type == "K 線圖 (K-Line)":
        # K 線圖
        fig.add_trace(go.Candlestick(
            x=chart_data['Date'],
            open=chart_data['Open'],
            high=chart_data['High'],
            low=chart_data['Low'],
            close=chart_data['Close'],
            name="價格",
            increasing_line_color='red',   # 漲：紅
            decreasing_line_color='green',  # 跌：綠
            increasing_fillcolor='red',
            decreasing_fillcolor='green'
        ))
    else:
        # 線圖 + 面積 + 最高/最低點
        fig.add_trace(go.Scatter(
            x=chart_data['Date'],
            y=chart_data['Close'],
            mode='lines',
            name='收盤價',
            line=dict(color=line_color, width=2),
            fill='tozeroy',
            fillcolor=f'rgba({int(line_color[1:3],16)},{int(line_color[3:5],16)},{int(line_color[5:7],16)},0.2)'
        ))
        
        # 最高點
        max_idx = chart_data['Close'].idxmax()
        fig.add_trace(go.Scatter(
            x=[chart_data.loc[max_idx, 'Date']],
            y=[chart_data.loc[max_idx, 'Close']],
            mode='markers+text',
            name='最高',
            marker=dict(color='red', size=12),
            text=[f"{chart_data.loc[max_idx, 'Close']:.3f}"],
            textposition='top center'
        ))
        
        # 最低點
        min_idx = chart_data['Close'].idxmin()
        fig.add_trace(go.Scatter(
            x=[chart_data.loc[min_idx, 'Date']],
            y=[chart_data.loc[min_idx, 'Close']],
            mode='markers+text',
            name='最低',
            marker=dict(color='green', size=12),
            text=[f"{chart_data.loc[min_idx, 'Close']:.3f}"],
            textposition='bottom center'
        ))
    
    # 設定佈局（自動最佳化 Y 軸）
    fig.update_layout(
        title=title,
        xaxis_title="日期",
        yaxis_title="價格",
        height=350,
        hovermode='x unified',
        template='plotly_white',
        yaxis=dict(
            tickformat=price_fmt,
            tickfont=dict(size=11),
            rangemode='normal',  # 自動選取最佳範圍
            showgrid=True,
            griddash='dot'
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)


def main():
    # --- CSS 注入 ---
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

    # 初始化所有 session_state
    for key, default in [
        ("selected_currency", None), ("selected_currency_name", ""),
        ("selected_commodity", None), ("selected_commodity_name", ""),
        ("selected_index", None), ("selected_index_name", "")
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    # --- 側邊欄 ---
    st.sidebar.markdown("<h2 style='color: #1E88E5;'>⚙️ 管理面板</h2>", unsafe_allow_html=True)

    auto_refresh = st.sidebar.toggle("自動更新 (每分鐘)", value=False)
    refresh_status = st.sidebar.empty()

    chart_type = st.sidebar.radio("圖表樣式", ["線圖 (Line)", "K 線圖 (K-Line)"], horizontal=True)
    period_default = st.sidebar.selectbox("預設時間區間", ["1週", "1個月", "3個月", "6個月", "1年"], index=2)

    if auto_refresh:
        refresh_status.caption(f"⏳ 上次更新: {datetime.now().strftime('%H:%M:%S')}")

    st.sidebar.markdown("---")
    user_id = st.sidebar.text_input("👤 使用者帳號 (用於儲存清單)", value="default_user").strip()
    st.sidebar.subheader("📋 編輯追蹤清單")

    if 'watchlist' not in st.session_state or st.session_state.get('last_user_id') != user_id:
        st.session_state.watchlist = fetch_watchlist_from_gs(conn, user_id)
        st.session_state.last_user_id = user_id
        st.rerun()

    search_query = st.sidebar.text_input("🔍 搜尋名稱或代碼 (如: 台積電, NVDA)", "")
    if search_query:
        search_results = fin_svc.search_ticker(search_query)
        if search_results:
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

    # =========================================================
    # --- 0. 匯率區塊 ---
    # =========================================================
    with st.container(border=True):
        st.markdown('<div class="section-header">💱 即時匯率 (對台幣 TWD)</div>', unsafe_allow_html=True)

        exchanges = [
            ("🇺🇸 美金", "USDTWD=X", None),
            ("🇪🇺 歐元", "EURTWD=X", None),
            ("🇨🇳 人民幣", "CNYTWD=X", "custom"),  # 使用 custom 標記
            ("🇯🇵 日幣", "JPYTWD=X", None),
            ("🇨🇭 瑞士法郎", "CHFTWD=X", None),
            ("🇬🇧 英鎊", "GBPTWD=X", None)
        ]

        ex_cols = st.columns(6)
        for idx, (name, symbol, custom) in enumerate(exchanges):
            if custom == "custom":
                # 人民幣：使用計算的即時匯率
                data = get_cny_twd_market_data(fin_svc)
            else:
                data = get_market_data_cached(fin_svc, symbol)
            
            if data:
                display_val = f"{data['price']:.3f}"
                render_card_with_button(
                    col=ex_cols[idx],
                    name=name,
                    symbol=symbol,
                    value_str=display_val,
                    delta_str=f"{data['change_percent']}% | YTD: {data['ytd_change']}%",
                    btn_key=f"ex_btn_{symbol}",
                    session_key_symbol="selected_currency",
                    session_key_name="selected_currency_name"
                )

        # 匯率歷史資料
        if st.session_state.selected_currency:
            with st.expander(f"📈 {st.session_state.selected_currency_name} 歷史匯率走勢", expanded=True):
                selected_symbol = st.session_state.selected_currency
                selected_name = st.session_state.selected_currency_name
                period_map = {"1週": "5d", "1個月": "1mo", "3個月": "3mo", "6個月": "6mo", "1年": "1y"}
                period_key = period_map.get(period_default, "3mo")

                # 如果是人民幣，使用計算的歷史資料
                if selected_symbol == "CNYTWD=X":
                    hist = get_cny_twd_history(fin_svc, period_key)
                else:
                    hist = get_historical_data_cached(fin_svc, selected_symbol, period_key)

                if hist is not None and not hist.empty:
                    chart_data = hist.reset_index()
                    chart_data['Date'] = pd.to_datetime(chart_data['Date'])

                    col_high, col_low, col_start, col_end = st.columns(4)
                    col_high.metric("區間最高", f"{chart_data['Close'].max():.3f}")
                    col_low.metric("區間最低", f"{chart_data['Close'].min():.3f}")
                    col_start.metric("區間起始", f"{chart_data['Close'].iloc[0]:.3f}")
                    col_end.metric("區間結束", f"{chart_data['Close'].iloc[-1]:.3f}")

                    st.markdown("##### 收盤價走勢")

                    # 使用 Plotly 繪圖
                    render_plotly_chart(
                        chart_data=chart_data,
                        title=f"{selected_name} 歷史匯率走勢",
                        price_fmt=".3f",
                        line_color="#1E88E5",
                        chart_type=chart_type
                    )

                    with st.expander("📋 查看詳細數據表格"):
                        display_hist = chart_data[['Date', 'Open', 'High', 'Low', 'Close']].copy()
                        display_hist['Date'] = display_hist['Date'].dt.strftime('%Y-%m-%d')
                        display_hist = display_hist.sort_values('Date', ascending=False).reset_index(drop=True)
                        st.dataframe(display_hist.style.format({
                            'Open': '{:.3f}', 'High': '{:.3f}', 'Low': '{:.3f}', 'Close': '{:.3f}'
                        }), use_container_width=True)
                else:
                    st.warning(f"⚠️ 暫無 {selected_name} 的歷史資料")

    # =========================================================
    # --- 1. 大宗商品區塊 ---
    # =========================================================
    with st.container(border=True):
        st.markdown('<div class="section-header">🔋 能源與貴金屬</div>', unsafe_allow_html=True)

        commodities = [
            ("🥇 現貨黃金", fin_svc.symbols["gold"]),
            ("🥈 現貨白銀", fin_svc.symbols["silver"]),
            ("🛢️ 布萊特原油", fin_svc.symbols["oil_brent"]),
            ("🛢️ 德州原油(WTI)", fin_svc.symbols["oil_wti"])
        ]

        cmd_cols = st.columns(4)
        for idx, (name, symbol) in enumerate(commodities):
            data = get_market_data_cached(fin_svc, symbol)
            if data:
                render_card_with_button(
                    col=cmd_cols[idx],
                    name=name,
                    symbol=symbol,
                    value_str=f"{data['price']} {data['currency']}",
                    delta_str=f"{data['change_percent']}% | YTD: {data['ytd_change']}%",
                    btn_key=f"cmd_btn_{symbol}",
                    session_key_symbol="selected_commodity",
                    session_key_name="selected_commodity_name"
                )

        if st.session_state.selected_commodity:
            with st.expander(f"📈 {st.session_state.selected_commodity_name} 歷史走勢", expanded=True):
                selected_symbol = st.session_state.selected_commodity
                selected_name = st.session_state.selected_commodity_name
                period_map = {"1週": "5d", "1個月": "1mo", "3個月": "3mo", "6個月": "6mo", "1年": "1y"}
                period_key = period_map.get(period_default, "3mo")

                hist = get_historical_data_cached(fin_svc, selected_symbol, period_key)

                if hist is not None and not hist.empty:
                    chart_data = hist.reset_index()
                    chart_data['Date'] = pd.to_datetime(chart_data['Date'])

                    col_high, col_low, col_start, col_end = st.columns(4)
                    col_high.metric("區間最高", f"{chart_data['Close'].max():.3f}")
                    col_low.metric("區間最低", f"{chart_data['Close'].min():.3f}")
                    col_start.metric("區間起始", f"{chart_data['Close'].iloc[0]:.3f}")
                    col_end.metric("區間結束", f"{chart_data['Close'].iloc[-1]:.3f}")

                    st.markdown("##### 收盤價走勢")

                    render_plotly_chart(
                        chart_data=chart_data,
                        title=f"{selected_name} 歷史走勢",
                        price_fmt=".3f",
                        line_color="#FFB300",
                        chart_type=chart_type
                    )

                    with st.expander("📋 查看詳細數據表格"):
                        display_hist = chart_data[['Date', 'Open', 'High', 'Low', 'Close']].copy()
                        display_hist['Date'] = display_hist['Date'].dt.strftime('%Y-%m-%d')
                        display_hist = display_hist.sort_values('Date', ascending=False).reset_index(drop=True)
                        st.dataframe(display_hist.style.format({
                            'Open': '{:.3f}', 'High': '{:.3f}', 'Low': '{:.3f}', 'Close': '{:.3f}'
                        }), use_container_width=True)
                else:
                    st.warning(f"⚠️ 暫無 {selected_name} 的歷史資料")

    # =========================================================
    # --- 2. 世界各大指數區 ---
    # =========================================================
    with st.container(border=True):
        st.markdown('<div class="section-header">🌐 全球股市指數</div>', unsafe_allow_html=True)

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

        tabs = st.tabs(list(index_regions.keys()))
        for i, (region, tickers) in enumerate(index_regions.items()):
            with tabs[i]:
                ticker_list = list(tickers.items())
                for start_idx in range(0, len(ticker_list), 4):
                    row_tickers = ticker_list[start_idx:start_idx + 4]
                    cols = st.columns(4)
                    for col_idx, (name, symbol) in enumerate(row_tickers):
                        data = get_market_data_cached(fin_svc, symbol)
                        if data:
                            render_card_with_button(
                                col=cols[col_idx],
                                name=name,
                                symbol=symbol,
                                value_str=f"{data['price']}",
                                delta_str=f"今日: {data['change_percent']}% | YTD: {data['ytd_change']}%",
                                btn_key=f"idx_btn_{symbol}",
                                session_key_symbol="selected_index",
                                session_key_name="selected_index_name"
                            )
                        else:
                            with cols[col_idx]:
                                st.caption(f"{name} (無數據)")

        # 指數歷史資料
        if st.session_state.selected_index:
            with st.expander(f"📈 {st.session_state.selected_index_name} 歷史走勢", expanded=True):
                selected_symbol = st.session_state.selected_index
                selected_name = st.session_state.selected_index_name
                period_map = {"1週": "5d", "1個月": "1mo", "3個月": "3mo", "6個月": "6mo", "1年": "1y"}
                period_key = period_map.get(period_default, "3mo")

                hist = get_historical_data_cached(fin_svc, selected_symbol, period_key)

                if hist is not None and not hist.empty:
                    chart_data = hist.reset_index()
                    chart_data['Date'] = pd.to_datetime(chart_data['Date'])

                    col_high, col_low, col_start, col_end = st.columns(4)
                    col_high.metric("區間最高", f"{chart_data['Close'].max():,.3f}")
                    col_low.metric("區間最低", f"{chart_data['Close'].min():,.3f}")
                    col_start.metric("區間起始", f"{chart_data['Close'].iloc[0]:,.3f}")
                    col_end.metric("區間結束", f"{chart_data['Close'].iloc[-1]:,.3f}")

                    st.markdown("##### 收盤價走勢")

                    render_plotly_chart(
                        chart_data=chart_data,
                        title=f"{selected_name} 歷史走勢",
                        price_fmt=",.3f",
                        line_color="#7B1FA2",
                        chart_type=chart_type
                    )

                    with st.expander("📋 查看詳細數據表格"):
                        display_hist = chart_data[['Date', 'Open', 'High', 'Low', 'Close']].copy()
                        display_hist['Date'] = display_hist['Date'].dt.strftime('%Y-%m-%d')
                        display_hist = display_hist.sort_values('Date', ascending=False).reset_index(drop=True)
                        st.dataframe(display_hist.style.format({
                            'Open': '{:,.3f}', 'High': '{:,.3f}', 'Low': '{:,.3f}', 'Close': '{:,.3f}'
                        }), use_container_width=True)
                else:
                    st.warning(f"⚠️ 暫無 {selected_name} 的歷史資料")

    # =========================================================
    # --- 3. 個股追蹤清單 (Watchlist) ---
    # =========================================================
    with st.container(border=True):
        st.markdown('<div class="section-header">🔍 自定義個股監控</div>', unsafe_allow_html=True)

        if not st.session_state.watchlist:
            st.info("目前清單為空，請從左側管理面板新增代碼。")
        else:
            for ticker in st.session_state.watchlist:
                with st.expander(f"📊 {ticker} 走勢詳情", expanded=False):
                    data = get_market_data_cached(fin_svc, ticker)
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
                            hist = get_historical_data_cached(fin_svc, ticker, "1mo")
                            if hist is not None and not hist.empty:
                                chart_data = hist.reset_index()
                                chart_data['Date'] = pd.to_datetime(chart_data['Date'])
                                render_plotly_chart(
                                    chart_data=chart_data,
                                    title=f"{ticker} 收盤價走勢",
                                    price_fmt=".3f",
                                    line_color="#1f77b4",
                                    chart_type=chart_type
                                )
                            else:
                                st.warning("暫無歷史趨勢數據")

    # --- 自動刷新 ---
    if auto_refresh:
        for i in range(60, 0, -1):
            refresh_status.caption(f"🔄 將在 {i} 秒後自動更新...")
            time.sleep(1)
        st.rerun()
    elif st.sidebar.button("🔄 手動刷新數據"):
        st.rerun()


if __name__ == "__main__":
    main()