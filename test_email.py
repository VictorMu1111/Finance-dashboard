import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Email 設定
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "smu715@gmail.com"
SENDER_PASSWORD = "zzeoqkzfmbteeoaq"
RECIPIENT_EMAIL = "smu715@gmail.com"

def send_test_email():
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECIPIENT_EMAIL
        msg['Subject'] = "🧪 測試 Email - 金融儀表板提醒功能"

        body = """
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #FFB300;">🧪 Email 測試成功！</h2>
            <p>恭喜！你的 Email 提醒功能設定成功！</p>
            <p>當黃金價格達到目標時，你將會收到通知。</p>
            <hr>
            <p style="color: gray; font-size: 12px;">此為測試信件，請勿直接回覆。</p>
        </body>
        </html>
        """

        msg.attach(MIMEText(body, 'html'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()

        print("✅ Email 測試成功！請檢查你的信箱 smu715@gmail.com")
        return True
    except Exception as e:
        print(f"❌ Email 寄送失敗: {e}")
        return False

if __name__ == "__main__":
    send_test_email()