import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

def send_report():
    """レポートをメールで送信"""
    # メール設定
    sender_email = os.environ['EMAIL_ADDRESS']
    sender_password = os.environ['EMAIL_PASSWORD']
    receiver_email = os.environ['EMAIL_TO']

    # メールの作成
    msg = MIMEMultipart()
    msg['Subject'] = f'AI Agent GitHub Trend Report - {datetime.now().strftime("%Y-%m-%d")}'
    msg['From'] = sender_email
    msg['To'] = receiver_email

    # レポートの読み込み
    try:
        with open('ai_agent_trends_report.md', 'r', encoding='utf-8') as f:
            report_content = f.read()
    except FileNotFoundError:
        print("レポートファイルが見つかりません")
        return
    except Exception as e:
        print(f"レポートの読み込み中にエラーが発生しました: {e}")
        return

    # テキスト部分の追加
    msg.attach(MIMEText(report_content, 'plain', 'utf-8'))

    # メール送信
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        print("メールが正常に送信されました。")
    except Exception as e:
        print(f"メール送信中にエラーが発生しました: {e}")
    finally:
        server.quit()

if __name__ == "__main__":
    send_report()