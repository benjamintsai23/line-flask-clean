import os
import json
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
)
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import feedparser

load_dotenv()

line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")

app = Flask(__name__)
line_bot_api = LineBotApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)

# 暫存群組 ID
group_ids = set()

# 投資名言
quotes = [
    "投資最大的風險，是你不知道自己在做什麼。 — 巴菲特",
    "別人恐懼時我貪婪，別人貪婪時我恐懼。 — 巴菲特",
    "市場短期是投票機，長期是秤重機。 — 葛拉漢"
]

# 推播新聞與名言
scheduler = BackgroundScheduler()

def fetch_news():
    sources = [
        ("Yahoo 財經", "https://tw.news.yahoo.com/rss/finance"),
        ("鉅亨網台股", "https://www.cnyes.com/rss/cat/tw_stock")
    ]
    messages = []
    for name, url in sources:
        feed = feedparser.parse(url)
        items = feed.entries[:5]
        if items:
            msg = f"\n📌 {name}：\n" + "\n".join(f"・{item.title}" for item in items)
            messages.append(msg)
    return messages

@scheduler.scheduled_job('cron', hour='8,13', minute=30)
def scheduled_push():
    news = fetch_news()
    quote = f"💬 今日投資名言：\n{quotes[0]}"
    for gid in group_ids:
        try:
            for msg in news:
                line_bot_api.push_message(gid, TextSendMessage(text=msg))
            line_bot_api.push_message(gid, TextSendMessage(text=quote))
        except Exception as e:
            print(f"❌ 推播錯誤: {e}")

scheduler.start()

@app.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()
    user_id = event.source.user_id

    if event.source.type == "group":
        group_id = event.source.group_id
        group_ids.add(group_id)

    if text in ["功能", "選單"]:
        flex = {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📊 財經選單", "weight": "bold", "size": "xl"},
                    {"type": "text", "text": "選擇你要查的資訊：", "size": "sm", "margin": "md"}
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "button", "style": "primary", "action": {"type": "message", "label": "熱門股排行", "text": "熱門股排行"}},
                    {"type": "button", "style": "primary", "action": {"type": "message", "label": "盤前快訊", "text": "盤前快訊"}},
                    {"type": "button", "style": "primary", "action": {"type": "message", "label": "每日名言", "text": "每日名言"}}
                ]
            }
        }
        line_bot_api.reply_message(event.reply_token, FlexSendMessage("功能選單", contents=flex))

    elif text == "每日名言":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=quotes[0]))

    elif text == "盤前快訊":
        messages = fetch_news()
        for msg in messages:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))

    elif text == "熱門股排行":
        hot = "🔥 今日熱門股排行（模擬）:\n1. 台積電\n2. 鴻海\n3. 聯電\n4. 長榮\n5. 開發金"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=hot))

    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"你說的是：{text}"))

@app.route("/", methods=['GET'])
def index():
    return "Line Bot 財經助手運行中"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
