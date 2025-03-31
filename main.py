import os
import feedparser
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FlexSendMessage
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

def send_flex_menu(reply_token):
    flex_message = FlexSendMessage(
        alt_text="📊 財經功能選單",
        contents={
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://i.imgur.com/f7cB9gE.png",
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📊 財經功能選單", "weight": "bold", "size": "lg", "margin": "md"},
                    {"type": "text", "text": "請選擇你想要的功能 👇", "size": "sm", "color": "#666666", "wrap": True},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "button",
                                "action": {"type": "message", "label": "📰 今日新聞", "text": "今日新聞"},
                                "style": "primary"
                            },
                            {
                                "type": "button",
                                "action": {"type": "message", "label": "📈 市場資訊", "text": "市場資訊"},
                                "style": "primary"
                            },
                            {
                                "type": "button",
                                "action": {"type": "message", "label": "📊 功能選單", "text": "功能"},
                                "style": "secondary"
                            }
                        ]
                    }
                ]
            }
        }
    )
    line_bot_api.reply_message(reply_token, flex_message)

# 處理訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()

    # 回覆功能選單
    if text in ["功能", "選單", "？"]:
        send_flex_menu(event.reply_token)
        return
    elif text == "今日新聞":
        fetch_and_send_news(preview=True, reply_token=event.reply_token)
        return
    else:
        # 回覆原本的「你說的是」
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"你說的是：{text}")
        )

    if event.source.type == "group":
        group_id = event.source.group_id
        group_ids.add(group_id)
        print("✅ 已收到群組訊息，Group ID：", group_id)

# 抓取新聞並推播
def fetch_and_send_news(preview=False, reply_token=None):
    rss_sources = {
        "Yahoo 財經新聞": "https://tw.news.yahoo.com/rss/finance",
        "鉅亨網台股新聞": "https://www.cnyes.com/rss/cat/tw_stock"
    }

    for source, rss_url in rss_sources.items():
        feed = feedparser.parse(rss_url)
        entries = feed.entries[:5]  # 每來源最多 5 則
        messages = [f"📌【{source}】"]
        for entry in entries:
            messages.append(f"・{entry.title}\n{entry.link}")

        full_message = "\n\n".join(messages)

        if preview and reply_token:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=full_message))
        else:
            for gid in group_ids:
                try:
                    line_bot_api.push_message(gid, TextSendMessage(text=full_message))
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
