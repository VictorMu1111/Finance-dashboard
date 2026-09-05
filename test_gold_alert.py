import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "smu715@gmail.com"
SENDER_PASSWORD = "zzeoqkzfmbteeoaq"
RECIPIENT_EMAIL = "smu715@gmail.com"
GOLD_TARGET_PRICE = 4900  # 台幣/公克

def get_gold_price_per_gram_twd():
    """取得黃金價格（台幣/公克）"""
    gold = yf.Ticker('GC=F').history(period='1d')['Close'].iloc[-1]
    usdtwd = yf.Ticker('USDTWD=X').history(period='1d')['Close'].iloc[-1]
    return gold * usdtwd / 31.1035

def send_gold_alert(price):
    """寄送黃金價格提醒"""
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = f"🚨 黃金價格達到 {price:.2f} 台幣/公克！"
    
    body = f"""
    <html>
    <body>
        <h2>🚨 黃金價格提醒</h2>
        <p>黃金價格已達到你的目標！</p>
        <h3>目前價格：{price:.2f} 台幣/公克</h3>
        <p>目標價格：{GOLD_TARGET_PRICE} 台幣/公克</p>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(body, 'html'))
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(SENDER_EMAIL, SENDER_PASSWORD)
    server.send_message(msg)
    server.quit()

def main():
    price = get_gold_price_per_gram_twd()
    print(f"💰 目前黃金價格: {price:.2f} 台幣/公克")
    
    if price >= GOLD_TARGET_PRICE:
        print(f"🎯 已達到目標 {GOLD_TARGET_PRICE}！寄送 Email...")
        try:
            send_gold_alert(price)
            print("✅ Email 已寄出！")
        except Exception as e:
            print(f"❌ 寄送失敗: {e}")
    else:
        diff = GOLD_TARGET_PRICE - price
        print(f"⏳ 尚未達到目標，還差 {diff:.2f} 台幣/公克")

if __name__ == "__main__":
    main()