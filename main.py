import os
import json
import feedparser
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
)
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

# 取得 LINE Bot 憑證
line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")

if not line_channel_access_token or not line_channel_secret:
    raise ValueError("請確認已設定環境變數 LINE_CHANNEL_ACCESS_TOKEN 和 LINE_CHANNEL_SECRET")

app = Flask(__name__)
line_bot_api = LineBotApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)

# 暫存群組 ID 和訂閱者清單
group_ids = set()
SUBSCRIBERS_FILE = "subscribers.json"

# 讀取訂閱者清單
if os.path.exists(SUBSCRIBERS_FILE):
    with open(SUBSCRIBERS_FILE, "r") as f:
        personal_subscribers = set(json.load(f))
else:
    personal_subscribers = set()

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

    if text in ["功能", "選單", "？"]:
        flex_message = FlexSendMessage(
            alt_text="📊 財經功能選單",
            contents={
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "📊 財經功能選單", "weight": "bold", "size": "lg"},
                        {"type": "text", "text": "請選擇你想要的功能 👇", "size": "sm", "margin": "md"}
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {"type": "button", "action": {"type": "message", "label": "📰 今日新聞", "text": "今日新聞"}, "style": "primary"},
                        {"type": "button", "action": {"type": "message", "label": "📈 市場資訊", "text": "市場資訊"}, "style": "primary"},
                        {"type": "button", "action": {"type": "message", "label": "📊 功能選單", "text": "功能"}, "style": "secondary"}
                    ]
                }
            }
        )
        line_bot_api.reply_message(event.reply_token, flex_message)
        return

    if text == "市場資訊":
        msg = get_market_info()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    if text == "我要訂閱":
        if event.source.type == "user":
            personal_subscribers.add(user_id)
            with open(SUBSCRIBERS_FILE, "w") as f:
                json.dump(list(personal_subscribers), f)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 你已成功訂閱！將會收到個人新聞通知。"))
        else:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text="⚠️ 請私訊我『我要訂閱』才能收到個人通知！"))
        return

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"你說的是：{text}"))

    if event.source.type == "group":
        group_id = event.source.group_id
        group_ids.add(group_id)
        print("✅ 已收到群組訊息，Group ID：", group_id)

def fetch_and_send_news():
    rss_list = [
        ("Yahoo 財經", "https://tw.news.yahoo.com/rss/finance"),
        ("鉅亨網台股", "https://www.cnyes.com/rss/cat/tw_stock")
    ]

    for source_name, rss_url in rss_list:
        feed = feedparser.parse(rss_url)
        entries = feed.entries[:5]
        if not entries:
            continue

        msg = f"📌 {source_name} 今日新聞：\n" + "\n".join([f"・{entry.title}" for entry in entries])
        for gid in group_ids:
            try:
                line_bot_api.push_message(gid, TextSendMessage(text=msg))
            except Exception as e:
                print(f"❌ 群組推播失敗：{e}")
        for uid in personal_subscribers:
            try:
                line_bot_api.push_message(uid, TextSendMessage(text=msg))
            except Exception as e:
                print(f"❌ 個人推播失敗：{e}")

def get_market_info():
    try:
        response = requests.get("https://tw.stock.yahoo.com")
        text = response.text
        index = text.split('加權指數')[1].split('</span>')[0].split('>')[-1]
        return f"📈 台股加權指數：{index}（資料來源：Yahoo）"
    except Exception as e:
        return "⚠️ 無法取得市場資訊，請稍後再試。"

scheduler = BackgroundScheduler()
scheduler.add_job(fetch_and_send_news, 'cron', hour='8,19', minute=30)
scheduler.start()

@app.route("/", methods=['GET'])
def index():
    return "LINE Bot Webhook 伺服器運行中！"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
