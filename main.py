from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
from apscheduler.schedulers.background import BackgroundScheduler
import feedparser
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()
line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")

if not line_channel_access_token or not line_channel_secret:
    raise ValueError("LINE_CHANNEL_ACCESS_TOKEN or LINE_CHANNEL_SECRET is missing!")

# 建立 Flask app 與 LINE Bot API
app = Flask(__name__)
line_bot_api = LineBotApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)

# 儲存目前抓到的群組 ID
group_ids = set()

# 處理訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    source_type = event.source.type

    # 顯示來源資訊
    if source_type == "group":
        group_id = event.source.group_id
        print(f"📣 來自群組 ID：{group_id}")
        group_ids.add(group_id)
    elif source_type == "room":
        room_id = event.source.room_id
        print(f"👥 來自多人聊天室 ID：{room_id}")
    else:
        print("👤 來自 1 對 1 聊天")

    # 回覆原始訊息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"你說的是：{user_text}")
    )

# 定時任務：推播 Yahoo 與鉅亨網新聞
def push_finance_news():
    urls = [
        "https://tw.news.yahoo.com/rss/finance",
        "https://www.cnyes.com/rss/cat/tw_stock"
    ]
    for url in urls:
        feed = feedparser.parse(url)
        entries = feed.entries[:5]  # 取前 5 筆
        for entry in entries:
            title = entry.title
            link = entry.link
            msg = f"{title}\n{link}"
            for gid in group_ids:
                line_bot_api.push_message(gid, TextSendMessage(text=msg))

# Webhook 路由
@app.route("/webhook", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# 啟動定時推播任務
scheduler = BackgroundScheduler()
scheduler.add_job(push_finance_news, "interval", hours=1)
scheduler.start()

# 部署到 Render 不需要設定 port，直接 run app 即可
if __name__ == "__main__":
    app.run()
