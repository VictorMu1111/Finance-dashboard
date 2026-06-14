# 📈 金融即時監控儀表板 (Finance Dashboard)

這是一個為個人投資者設計的專業級金融市場監控工具。透過串接 Yahoo Finance API 與 Google Sheets，實現了跨裝置的個人化追蹤清單與即時數據分析，並具備優雅的視覺化介面。

## ✨ 功能特色
- **🌍 全球市場一覽**
    - **即時匯率**：監控 TWD 對 USD, EUR, JPY (3位精度), CNY, CHF, GBP 之匯率。
    - **大宗商品**：即時追蹤黃金、白銀、布萊特原油 (Brent) 及 德州原油 (WTI)。
    - **全球指數**：分區管理亞洲 (台、日、韓、港、陸、泰、星)、美洲 (四大指數) 與歐洲主要市場。
- **📊 智慧視覺化分析**
    - **多樣化圖表**：支援傳統「線圖」與專業「K 線圖 (紅漲綠跌配色)」切換。
    - **自動標記**：智慧偵測並標註區間內的最高價與最低價。
    - **動態刻度**：圖表 Y 軸自動根據波動縮放，捕捉微小價格變化。
- **💾 個人化雲端同步**
    - **Google Sheets 整合**：透過 User ID 識別，實現跨裝置 (手機/電腦) 同步追蹤清單。
    - **智慧搜尋**：支援輸入公司名稱 (如：台積電) 自動查找正確代碼 (2330.TW)。
- **⏱️ 效能與監控**
    - **YTD 追蹤**：自動計算「年初至今」漲跌幅，掌握長線趨勢。
    - **自動刷新**：內建每分鐘自動更新開關，適合看盤長期開啟。

## 💡 使用小技巧 (Tips)

1. **快速搜尋**：在搜尋框輸入中文名稱（如「蘋果」或「輝達」）即可快速找到對應美股代碼，無需死背 Ticker。
2. **跨裝置同步**：在「使用者帳號」輸入你專屬的 ID，你在電腦上加入的股票，手機開啟同網址並輸入相同 ID 即可看到。
3. **觀察壓力與支撐**：智慧線圖上的紅色與綠色點能幫你快速判斷一個月內的相對高低點。
4. **日幣精確觀察**：系統針對日幣匯率特別強化至小數點後三位，方便精準捕捉匯率轉折。
5. **看盤模式**：開啟側邊欄的「自動更新」，App 將成為你的桌面副螢幕。

## 🚀 快速開始

### 本地運行
1. **安裝環境**：
   ```bash
   pip install -r requirements.txt
   ```
2. **執行**：
   ```bash
   streamlit run finance_app.py
   ```

### 雲端部署 (Streamlit Cloud)
部署時請確保在 **Secrets** 設定中填入 Google Sheets 的 Service Account 資訊：
```toml
[connections.gsheets]
spreadsheet = "你的 Google Sheet URL"
type = "service_account"
# ... 其他 JSON 欄位 ...
```

## 🛠️ 技術棧
- **Frontend/App**: [Streamlit](https://streamlit.io/)
- **Data**: [yfinance](https://github.com/ranaroussi/yfinance)
- **Visualization**: [Altair](https://altair-viz.github.io/)
- **Database**: [Google Sheets API](https://developers.google.com/sheets/api)
- **Analysis**: [Pandas](https://pandas.pydata.org/)

## ⚖️ 授權條款
本專案採用 [MIT License](LICENSE.md) 授權。