import os
import json
import requests
import feedparser
from bs4 import BeautifulSoup
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FollowEvent, JoinEvent, FlexSendMessage
)
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")

if not line_channel_access_token or not line_channel_secret:
    raise ValueError("請確認已設定 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_CHANNEL_SECRET")

app = Flask(__name__)
line_bot_api = LineBotApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)

# 儲存群組 ID
group_ids = set()

# 自訂 Flex 選單
flex_menu = FlexSendMessage(
    alt_text="📊 FinBot 功能選單",
    contents={
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "FinBot 功能選單", "weight": "bold", "size": "xl", "margin": "md"},
                {"type": "text", "text": "請點選以下按鈕操作 👇", "size": "sm", "color": "#aaaaaa", "margin": "md"}
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {"type": "button", "style": "primary", "action": {"type": "message", "label": "📰 今日新聞", "text": "今日新聞"}},
                {"type": "button", "style": "primary", "action": {"type": "message", "label": "📈 市場資訊", "text": "市場資訊"}},
                {"type": "button", "style": "secondary", "action": {"type": "message", "label": "📊 功能選單", "text": "功能"}}
            ]
        }
    }
)

# 自動抓新聞
def fetch_news():
    results = []
    yahoo_feed = feedparser.parse("https://tw.news.yahoo.com/rss/finance")
    yahoo_entries = yahoo_feed.entries[:6]
    if yahoo_entries:
        msg = "\n📢 Yahoo 財經新聞：\n" + "\n".join([f"\u2022 {e.title}\n{e.link}" for e in yahoo_entries])
        results.append(msg)

    try:
        resp = requests.get("https://www.cnyes.com/twstock/news", timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        news_items = soup.select(".newsList_item > a")[:6]
        msg = "\n📢 鉅亨網台股新聞：\n"
        for item in news_items:
            title = item.select_one("h3").get_text(strip=True)
            link = "https://www.cnyes.com" + item['href']
            msg += f"\u2022 {title}\n{link}\n"
        results.append(msg)
    except Exception as e:
        print("鉅亨新聞錯誤：", e)

    return results

# 定時推播
scheduler = BackgroundScheduler()
@scheduler.scheduled_job('cron', hour='8,19', minute=30)
def scheduled_push():
    news_list = fetch_news()
    for msg in news_list:
        for gid in group_ids:
            try:
                line_bot_api.push_message(gid, TextSendMessage(text=msg))
            except Exception as e:
                print("推播失敗：", e)

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
        line_bot_api.reply_message(event.reply_token, flex_menu)
    elif text == "今日新聞":
        for msg in fetch_news():
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
    elif text == "市場資訊":
        try:
            r = requests.get("https://www.twse.com.tw/rwd/zh/afterTrading/MI_5MINS_INDEX?response=json")
            data = r.json()["data"]
            t_index = [d for d in data if d[0] == "台灣加權股價指數"]
            if t_index:
                msg = f"📈 加權指數：{t_index[0][1]} 點\n漲跌：{t_index[0][2]} ({t_index[0][3]})"
            else:
                msg = "查無加權指數資訊。"
        except:
            msg = "查詢失敗，請稍後再試。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"你說的是：{text}"))

    if event.source.type == "group":
        gid = event.source.group_id
        group_ids.add(gid)
        print("✅ 收到群組訊息，ID：", gid)

@handler.add(JoinEvent)
def welcome_group(event):
    gid = event.source.group_id
    group_ids.add(gid)
    welcome = "👋 歡迎加入 FinBot 財經群組！\n輸入『功能』或點選選單查看所有功能喔！"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=welcome))

@app.route("/", methods=['GET'])
def home():
    return "LINE Bot 已上線"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


