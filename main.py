import os
from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from apscheduler.schedulers.background import BackgroundScheduler
import feedparser

# 載入 .env 檔案
load_dotenv()  # 確保 .env 檔案在程式根目錄中

# 讀取 LINE Channel Access Token 和 Secret
line_channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
line_channel_secret = os.getenv('LINE_CHANNEL_SECRET')

# 測試環境變數是否正確載入
print("LINE_CHANNEL_ACCESS_TOKEN:", line_channel_access_token)
print("LINE_CHANNEL_SECRET:", line_channel_secret)

# 檢查必要環境變數是否存在
if not line_channel_access_token:
    raise ValueError("LINE_CHANNEL_ACCESS_TOKEN is missing.")
if not line_channel_secret:
    raise ValueError("LINE_CHANNEL_SECRET is missing.")

# 初始化 Flask 應用
app = Flask(__name__)

# 初始化 LINE Bot API 和 Webhook Handler
line_bot_api = LineBotApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)

# 設定 webhook 端點
@app.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'


# 設定每天從 RSS 來源擷取新聞並推送到 LINE
def fetch_rss_and_send():
    rss_sources = {
        'Yahoo Finance': 'https://tw.news.yahoo.com/rss/finance',
        '鉅亨網台股': 'https://www.cnyes.com/rss/cat/tw_stock'
    }

    for source_name, rss_url in rss_sources.items():
        feed = feedparser.parse(rss_url)
        news = feed.entries[:5]  # 只取前 5 則新聞

        for entry in news:
            title = entry.title
            link = entry.link
            message = f'{title} - {link}'

            # 推送到 LINE 群組
            line_bot_api.push_message(
                'YOUR_GROUP_ID',  # 請替換為你的 LINE 群組 ID
                TextSendMessage(text=message)
            )


# 定時執行 RSS 擷取並推送
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_rss_and_send, 'interval', hours=1)  # 每小時執行一次
scheduler.start()

if __name__ == "__main__":
    app.run(debug=True)
