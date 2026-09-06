# 📈 金融即時監控儀表板 (Finance Dashboard)

這是一個為個人投資者設計的專業級金融市場監控工具。透過串接 Yahoo Finance API 與 Google Sheets，實現了跨裝置的個人化追蹤清單與即時數據分析。

## ✨ 功能特色

### 🌍 全球市場一覽
- 即時匯率：TWD 對 USD, EUR, JPY, CNY, CHF, GBP
- 大宗商品：黃金、白銀、布萊特原油、德州原油
- 全球指數：亞洲、美洲、歐洲主要市場

### 📊 智慧視覺化分析
- 多樣化圖表：線圖、K 線圖切換
- Sparkline 迷你走勢圖：每張卡片下方顯示近期趨勢
- 自動標記區間最高/最低價
- Plotly 互動式圖表

### 📧 黃金價格 Email 提醒
- 每小時自動檢查黃金價格（台幣/公克）
- 可自訂目標價格（預設 4900）
- 達到目標時自動寄送 Email
- GitHub Actions 背景監控，電腦關機也能運作

### 💾 個人化雲端同步
- Google Sheets 跨裝置同步
- 智慧搜尋（支援中文名稱）

## 🚀 快速開始

### 本地運行
pip install -r requirements.txt
streamlit run finance_app.py

### 雲端部署 (Streamlit Cloud)
設定 Google Sheets Secrets 即可部署

## 🛠️ 技術棧
Streamlit / yfinance / Plotly / Google Sheets API / Pandas / GitHub Actions

## ⚖️ 授權
MIT License
