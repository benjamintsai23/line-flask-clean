import os
import json
import requests
import feedparser
from bs4 import BeautifulSoup
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

line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")

if not line_channel_access_token or not line_channel_secret:
    raise ValueError("請確認已設定 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_CHANNEL_SECRET")

app = Flask(__name__)
line_bot_api = LineBotApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)

# 暫存群組 ID 和訂閱者清單
group_ids = set()

# 定時推播新聞
scheduler = BackgroundScheduler()

# 自動推播函式
def fetch_news():
    results = []

    # Yahoo 財經
    yahoo_feed = feedparser.parse("https://tw.news.yahoo.com/rss/finance")
    yahoo_entries = yahoo_feed.entries[:6]
    if yahoo_entries:
        msg = "📢 Yahoo 財經新聞：\n"
        for e in yahoo_entries:
            msg += f"• {e.title}\n{e.link}\n"
        results.append(msg)

    # 鉅亨網（改用 BeautifulSoup 抓）
    url = "https://www.cnyes.com/twstock/news"
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        news_items = soup.select(".newsList_item > a")[:6]
        msg = "📢 鉅亨網台股新聞：\n"
        for item in news_items:
            title = item.select_one("h3").get_text(strip=True)
            link = "https://www.cnyes.com" + item['href']
            msg += f"• {title}\n{link}\n"
        results.append(msg)
    except Exception as e:
        print("抓取鉅亨網失敗：", e)

    return results

# AI 股市觀點產生器（等級一：關鍵字比對）
def generate_market_insight():
    feed = feedparser.parse("https://tw.news.yahoo.com/rss/finance")
    if not feed.entries:
        return None

    keywords = ["台積電", "鴻海", "聯發科", "漲停", "減產", "庫藏股", "法說", "裁員"]
    for entry in feed.entries[:5]:
        for kw in keywords:
            if kw in entry.title:
                return f"🔍 今日觀點：{kw} 出現在熱門新聞中，投資人可留意其後續表現。"
    return "📌 今日觀點：目前市場新聞中無明顯熱點，請持續觀察盤勢發展。"

@scheduler.scheduled_job('cron', hour='8,19', minute=30)
def scheduled_push():
    news_list = fetch_news()
    insight = generate_market_insight()
    for gid in group_ids:
        for msg in news_list:
            try:
                if len(msg) <= 5000:
                    line_bot_api.push_message(gid, TextSendMessage(text=msg))
            except Exception as e:
                print(f"推播失敗：{e}")
        if insight:
            try:
                line_bot_api.push_message(gid, TextSendMessage(text=insight))
            except Exception as e:
                print(f"觀點推播失敗：{e}")

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
    uid = event.source.user_id

    if text in ["功能", "選單"]:
        flex_message = FlexSendMessage(
            alt_text="📊 功能選單",
            contents={
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {"type": "text", "text": "📊 功能選單", "weight": "bold", "size": "lg"},
                        {"type": "text", "text": "請選擇你要的功能：", "size": "sm", "margin": "md"}
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {"type": "button", "action": {"type": "message", "label": "📰 今日新聞", "text": "今日新聞"}},
                        {"type": "button", "action": {"type": "message", "label": "📈 市場資訊", "text": "市場資訊"}},
                        {"type": "button", "action": {"type": "message", "label": "📊 AI 股市觀點", "text": "AI 股市觀點"}}
                    ]
                }
            }
        )
        line_bot_api.reply_message(event.reply_token, flex_message)

    elif text == "今日新聞":
        news_list = fetch_news()
        for msg in news_list:
            if len(msg) <= 5000:
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))

    elif text == "AI 股市觀點":
        insight = generate_market_insight()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=insight))

    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"你說的是：{text}"))

    # 紀錄群組 ID
    if event.source.type == "group":
        gid = event.source.group_id
        group_ids.add(gid)
        print("✅ 群組 ID：", gid)

@app.route("/", methods=['GET'])
def home():
    return "LINE Bot 運行中"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

