
import os
from dotenv import load_dotenv
from flask import Flask, request, abort
from linebot import LineBotApi
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from apscheduler.schedulers.background import BackgroundScheduler
import feedparser

# 載入 .env 檔案
load_dotenv()

# 設定 LINE Channel Access Token 和 Secret
line_channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
line_channel_secret = os.getenv('LINE_CHANNEL_SECRET')

# 檢查環境變數是否正確設定
if not line_channel_access_token:
    raise ValueError("LINE_CHANNEL_ACCESS_TOKEN is not set")
if not line_channel_secret:
    raise ValueError("LINE_CHANNEL_SECRET is not set")

# LINE Bot API 和 Webhook Handler
line_bot_api = LineBotApi(line_channel_access_token)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
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
    reply = f'您說的是: {user_text}'

    # 使用新的 MessagingApi 進行回覆
    line_bot_api.push_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

# 定期執行 RSS 來源
def fetch_rss_and_send():
    news = feedparser.parse('https://tw.news.yahoo.com/rss/finance')
    for entry in news.entries[:5]:  # 只取前五則新聞
        title = entry.title
        link = entry.link
        message = f'{title} - {link}'

        # 發送LINE訊息
        line_bot_api.push_message(
            'YOUR_GROUP_ID',  # 請填入你的 LINE 群組 ID
            TextSendMessage(text=message)
        )


# 定時任務設定
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_rss_and_send, 'interval', hours=1)  # 每小時執行一次
scheduler.start()

if __name__ == "__main__":
    app.run(debug=True)
