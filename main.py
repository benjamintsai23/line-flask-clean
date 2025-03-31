import os
import feedparser
import requests
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

# 取得 LINE Bot 憑證
line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")

timezone = os.getenv("TZ", "Asia/Taipei")
os.environ["TZ"] = timezone

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

# 查詢即時股價
def query_stock(query):
    url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_{query}.tw"
    response = requests.get(url)
    data = response.json()
    if data['msgArray']:
        stock = data['msgArray'][0]
        name = stock['n']
        z = stock['z']  # 最新成交價
        o = stock['o']  # 開盤價
        h = stock['h']  # 最高價
        l = stock['l']  # 最低價
        return f"{name} ({query})\n最新：{z}\n開盤：{o}\n最高：{h}\n最低：{l}"
    else:
        return "查無此股票資訊，請確認代號或名稱。"

# 處理訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()

    if text in ["功能", "選單", "？"]:
        contents = {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://i.imgur.com/Zu4asfP.png",
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "📊 FinBot 主選單", "weight": "bold", "size": "xl"},
                    {"type": "text", "text": "請選擇以下功能：", "size": "sm", "color": "#666666"}
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {"type": "button", "action": {"type": "message", "label": "📈 市場資訊", "text": "市場資訊"}},
                    {"type": "button", "action": {"type": "message", "label": "📰 今日新聞", "text": "今日新聞"}},
                    {"type": "button", "action": {"type": "message", "label": "🔍 個股報價", "text": "個股報價"}}
                ],
                "flex": 0
            }
        }
        line_bot_api.reply_message(
            event.reply_token,
            FlexSendMessage(alt_text="功能選單", contents=contents)
        )
        return

    if text == "今日新聞":
        rss_list = [
            ("Yahoo 財經", "https://tw.news.yahoo.com/rss/finance"),
            ("鉅亨網台股", "https://www.cnyes.com/rss/cat/tw_stock")
        ]
        messages = []
        for source, url in rss_list:
            feed = feedparser.parse(url)
            entries = feed.entries[:5]
            news_text = f"📌 {source} 今日新聞："
            for entry in entries:
                news_text += f"\n• {entry.title}"
            messages.append(TextSendMessage(text=news_text))
        line_bot_api.reply_message(event.reply_token, messages)
        return

    if text == "市場資訊" or text == "個股報價":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請輸入股票名稱或代號（例如：台積電 或 2330）")
        )
        return

    # 查詢股票代號
    if text.isdigit():
        result = query_stock(text)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=result))
        return

    # 額外可加入名稱對應查詢（略）

    # 一般回覆
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"你說的是：{text}")
    )

    # 收集群組 ID
    if event.source.type == "group":
        group_id = event.source.group_id
        group_ids.add(group_id)
        print("✅ 已收到群組訊息，Group ID：", group_id)

# 抓取新聞並推播

def fetch_and_send_news():
    rss_list = [
        ("Yahoo 財經", "https://tw.news.yahoo.com/rss/finance"),
        ("鉅亨網台股", "https://www.cnyes.com/rss/cat/tw_stock")
    ]

    for source, rss_url in rss_list:
        feed = feedparser.parse(rss_url)
        entries = feed.entries[:5]
        news_text = f"📌 {source} 最新新聞："
        for entry in entries:
            news_text += f"\n• {entry.title}"

        for gid in group_ids:
            try:
                line_bot_api.push_message(gid, TextSendMessage(text=news_text))
            except Exception as e:
                print(f"❌ 推播到 {gid} 發生錯誤：{e}")

# 啟動排程器
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_and_send_news, 'cron', hour='8,19', minute=30)
scheduler.start()

@app.route("/", methods=['GET'])
def index():
    return "LINE Bot Webhook 伺服器運行中！"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

