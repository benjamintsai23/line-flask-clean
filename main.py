import os
import feedparser
from flask import Flask, request, abort
from apscheduler.schedulers.background import BackgroundScheduler
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# ✅ 從環境變數取得 Channel Access Token 和 Channel Secret
line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")

if not line_channel_access_token or not line_channel_secret:
    raise ValueError("❌ 請確認環境變數 LINE_CHANNEL_ACCESS_TOKEN 和 LINE_CHANNEL_SECRET 是否正確設定！")

# ✅ 初始化 Flask 和 LINE Bot
app = Flask(__name__)
line_bot_api = LineBotApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)

# ✅ 接收 Webhook 訊息處理
@app.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# ✅ 接收訊息時回傳原文字，並印出群組 ID（方便你取得 group_id）
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print("🔍 收到訊息：", event.message.text)
    print("📦 訊息來源：", event.source)

    # 如果是群組訊息就印出 group_id
    if hasattr(event.source, 'group_id'):
        print("✅ 群組 ID：", event.source.group_id)

    reply_text = f"你說的是：{event.message.text}"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

# ✅ RSS 來源設定（Yahoo & 鉅亨網）
RSS_FEEDS = [
    "https://tw.news.yahoo.com/rss/finance",
    "https://www.cnyes.com/rss/cat/tw_stock"
]

# ✅ 要推播的 LINE 群組 ID（請自行替換成你抓到的 group_id）
GROUP_ID = "請替換為你自己的群組 ID"

# ✅ 自動推播新聞
def fetch_and_push_news():
    for url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries[:3]:  # 每則只取 3 筆
            title = entry.title
            link = entry.link
            message = f"{title}\n{link}"
            try:
                line_bot_api.push_message(
                    GROUP_ID,
                    TextSendMessage(text=message)
                )
                print("✅ 推播成功：", title)
            except Exception as e:
                print("❌ 推播失敗：", e)

# ✅ 定時任務排程（每天 8:30、19:30 各推播一次）
scheduler = BackgroundScheduler(timezone="Asia/Taipei")
scheduler.add_job(fetch_and_push_news, 'cron', hour=8, minute=30)
scheduler.add_job(fetch_and_push_news, 'cron', hour=19, minute=30)
scheduler.start()

# ✅ 啟動 Flask
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Render 用不到 port=5000
    app.run(host="0.0.0.0", port=port)
