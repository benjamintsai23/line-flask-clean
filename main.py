import os
import feedparser
from flask import Flask, request, abort
from apscheduler.schedulers.background import BackgroundScheduler
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv

# 讀取 .env 環境變數
load_dotenv()

# 設定 LINE 的 access token 和 secret
line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")

if not line_channel_access_token:
    raise ValueError("LINE_CHANNEL_ACCESS_TOKEN is missing!")
if not line_channel_secret:
    raise ValueError("LINE_CHANNEL_SECRET is missing!")

# Flask app 與 LINE 處理器
app = Flask(__name__)
line_bot_api = LineBotApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)

# 接收 LINE webhook
@app.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# 處理用戶訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
   @handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print("收到訊息來源：", event.source)
    )

# 從 RSS 擷取新聞並送出
def fetch_rss_and_send():
    url = "https://tw.news.yahoo.com/rss/finance"
    news = feedparser.parse(url).entries[:5]  # 只取前 5 條

    for entry in news:
        title = entry.title
        link = entry.link
        message = f"{title}\n{link}"

        line_bot_api.push_message(
            os.getenv("LINE_GROUP_ID", "<YOUR_GROUP_ID_HERE>"),
            TextSendMessage(text=message)
        )

# 啟用定時任務
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_rss_and_send, 'interval', hours=1)  # 每小時
scheduler.start()

# 啟動 app (透過 Render 自動接受 PORT)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
# 手動觸發一次新聞推播（部署後自動刪掉）
fetch_rss_and_send()
