import os
import feedparser
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

# 暫存群組 ID
group_ids = set()

@app.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# Flex Message 選單樣板
menu_flex = {
    "type": "bubble",
    "body": {
        "type": "box",
        "layout": "vertical",
        "spacing": "md",
        "contents": [
            {
                "type": "text",
                "text": "📊 財經小幫手選單",
                "size": "xl",
                "weight": "bold",
                "color": "#1E2F97"
            },
            {
                "type": "separator"
            },
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#1E2F97",
                        "action": {
                            "type": "message",
                            "label": "📰 今日新聞",
                            "text": "今日新聞"
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#1E2F97",
                        "action": {
                            "type": "message",
                            "label": "📈 即時股價",
                            "text": "查股價"
                        }
                    },
                    {
                        "type": "button",
                        "style": "secondary",
                        "action": {
                            "type": "message",
                            "label": "🛠 工具選單",
                            "text": "功能"
                        }
                    }
                ]
            }
        ]
    }
}

# 處理訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()

    # 回覆 Flex 選單
    if text in ["功能", "選單", "？"]:
        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="📊 財經選單", contents=menu_flex)
        )
        return

    # 回覆原本的「你說的是」
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"你說的是：{text}")
    )

    # 顯示群組 ID（幫你記錄用）
    if event.source.type == "group":
        group_id = event.source.group_id
        group_ids.add(group_id)
        print("✅ 已收到群組訊息，Group ID：", group_id)

# 抓取新聞並推播

def fetch_and_send_news():
    rss_list = [
        "https://tw.news.yahoo.com/rss/finance",
        "https://www.cnyes.com/rss/cat/tw_stock"
    ]

    for rss_url in rss_list:
        feed = feedparser.parse(rss_url)
        entries = feed.entries[:5]  # 每來源最多 5 則
        for entry in entries:
            msg = f"{entry.title}\n{entry.link}"
            for gid in group_ids:
                try:
                    line_bot_api.push_message(gid, TextSendMessage(text=msg))
                except Exception as e:
                    print(f"❌ 推播到 {gid} 發生錯誤：{e}")

# 啟動排程器
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_and_send_news, 'cron', hour='8,19', minute=30)  # 早上 8:30 & 晚上 19:30
scheduler.start()

@app.route("/", methods=['GET'])
def index():
    return "LINE Bot Webhook 伺服器運行中！"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
