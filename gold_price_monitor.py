"""
黃金價格監控腳本 - 獨立運作，不需要 Streamlit
"""
import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import json
import os

# ========== 設定 ==========
TARGET_PRICE = 4900  # 目標價格（台幣/公克）
SENDER_EMAIL = "smu715@gmail.com"
SENDER_PASSWORD = "zzeoqkzfmbteeoaq"
RECIPIENT_EMAIL = "smu715@gmail.com"

# 狀態檔案（記錄上次通知時間）
STATE_FILE = "gold_alert_state.json"

def get_gold_price_per_gram_twd():
    """取得黃金價格（台幣/公克）"""
    gold = yf.Ticker('GC=F').history(period='1d')['Close'].iloc[-1]
    usdtwd = yf.Ticker('USDTWD=X').history(period='1d')['Close'].iloc[-1]
    return gold * usdtwd / 31.1035

def load_state():
    """讀取上次通知狀態"""
    try:
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"last_notified_date": None}

def save_state(state):
    """儲存通知狀態"""
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def send_gold_alert_email(price):
    """寄送黃金價格提醒 Email"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = f"🚨 黃金價格達到 {price:.2f} 台幣/公克！"
        
        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #DAA520;">🚨 黃金價格提醒</h2>
            <p>黃金價格已達到你的目標！</p>
            <table style="border-collapse: collapse; margin: 20px 0;">
                <tr>
                    <td style="padding: 10px; background: #f9f9f9; border: 1px solid #ddd;"><strong>目前價格：</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd; font-size: 24px; color: red;"><strong>{price:.2f} 台幣/公克</strong></td>
                </tr>
                <tr>
                    <td style="padding: 10px; background: #f9f9f9; border: 1px solid #ddd;"><strong>目標價格：</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{TARGET_PRICE} 台幣/公克</td>
                </tr>
                <tr>
                    <td style="padding: 10px; background: #f9f9f9; border: 1px solid #ddd;"><strong>檢查時間：</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
            </table>
            <p>建議您可以考慮獲利了結或調整投資策略。</p>
            <hr>
            <p style="color: gray; font-size: 12px;">此為自動通知信件，請勿直接回覆。</p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Email 已寄出！價格: {price:.2f} 台幣/公克")
        return True
    except Exception as e:
        print(f"❌ Email 寄送失敗: {e}")
        return False

def main():
    print(f"⏰ 檢查黃金價格... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        price = get_gold_price_per_gram_twd()
        print(f"💰 目前黃金價格: {price:.2f} 台幣/公克")
        
        if price >= TARGET_PRICE:
            # 檢查今天是否已經通知過
            state = load_state()
            today = datetime.now().strftime('%Y-%m-%d')
            
            if state.get("last_notified_date") != today:
                print(f"🎯 已達到目標 {TARGET_PRICE}！寄送 Email...")
                if send_gold_alert_email(price):
                    state["last_notified_date"] = today
                    save_state(state)
                    print("✅ 通知完成！今天不會再重複寄送")
            else:
                print(f"ℹ️ 今天已經通知過了，不會重複寄送")
        else:
            diff = TARGET_PRICE - price
            print(f"⏳ 尚未達到目標，還差 {diff:.2f} 台幣/公克")
    
    except Exception as e:
        print(f"❌ 檢查失敗: {e}")

if __name__ == "__main__":
    main()