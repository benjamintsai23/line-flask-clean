import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from apscheduler.schedulers.background import BackgroundScheduler
import feedparser
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# 設定 LINE Channel Access Token 和 Secret
line_channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
line_channel_secret = os.getenv('LINE_CHANNEL_SECRET')

# 確認環境變數是否正確設定
if not line_channel_access_token:
    raise ValueError("LINE_CHANNEL_ACCESS_TOKEN is not set")
if not line_channel_secret:
    raise ValueError("LINE_CHANNEL_SECRET is not set")

# 設定 Flask 應用
app = Flask(__name__)

# 設定 LINE Bot API 和 Webhook Handler
line_bot_api = LineBotApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)

# 設定每日抓取 RSS 並發送到 LINE
def fetch_rss_and_send():
    rss_feed_url = 'https://tw.news.yahoo.com/rss/finance'  # 這裡放置你的 RSS Feed URL
    feed = feedparser.parse(rss_feed_url)
    for entry in feed.entries[:5]:  # 只取前五條新聞
        title = entry.title
        link = entry.link
        message = f'{title} - {link}'
        line_bot_api.push_message(
            'YOUR_GROUP_ID',  # 請換成你的 LINE 群組 ID
            TextSendMessage(text=message)
        )

# 定時執行 RSS 抓取
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_rss_and_send, 'interval', hours=1)  # 每小時執行一次
scheduler.start()

# Webhook 設定
@app.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    reply = f"你說的是: {user_text}"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)  # 設定端口為 5000
