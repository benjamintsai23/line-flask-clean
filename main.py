import os
import json
import requests
import feedparser
from bs4 import BeautifulSoup
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage, RichMenu, RichMenuSize, RichMenuArea, URIAction, MessageAction
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

# 自動推播函式
def fetch_news():
    results = []

    # Yahoo 財經
    yahoo_feed = feedparser.parse("https://tw.news.yahoo.com/rss/finance")
    yahoo_entries = yahoo_feed.entries[:6]
    if yahoo_entries:
        msg = "\U0001F4E2 Yahoo 財經新聞：\n"
        for e in yahoo_entries:
            msg += f"• {e.title}\n{e.link}\n"
        results.append(msg)

    # 鉅亨網（BeautifulSoup 抓）
    url = "https://www.cnyes.com/twstock/news"
    try:
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        news_items = soup.select(".newsList_item > a")[:6]
        msg = "\U0001F4E2 鉅亨網台股新聞：\n"
        for item in news_items:
            title = item.select_one("h3").get_text(strip=True)
            link = "https://www.cnyes.com" + item['href']
            msg += f"• {title}\n{link}\n"
        results.append(msg)
    except Exception as e:
        print("抓取鉅亨網失敗：", e)

    return results

# 市場資訊

def get_market_summary():
    url = "https://tw.stock.yahoo.com/"
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        index_box = soup.select_one("li[class*=Index]")
        name = index_box.select_one("span.Fz\\(16px\\)").text
        price = index_box.select_one("span.Fw\\(b\\).Fz\\(24px\\)").text
        change = index_box.select_one("span.Fz\\(20px\\)").text

        volume_box = soup.find_all("li", class_="D\\(f\\).Ai\\(c\\).Jc\\(sb\\).Mb\\(8px\\)")
        volume_text = ""
        for item in volume_box:
            if "成交金額" in item.text:
                volume_text = item.select_one("span.Fz\\(16px\\)").text
                break

        msg = f"\U0001F4C8 {name} 市場資訊（Yahoo 財經）：\n"
        msg += f"指數：{price}\n漲跌：{change}\n成交金額：{volume_text}"
        return msg
    except Exception as e:
        print("市場資訊查詢失敗：", e)
        return "⚠️ 查詢失敗，請稍後再試。"

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
                print(f"推播失敗：{e}")

scheduler.start()

@app.before_first_request
def setup_rich_menu():
    try:
        rich_menu_to_create = RichMenu(
            size=RichMenuSize(width=2500, height=843),
            selected=True,
            name="FinanceMenu",
            chat_bar_text="點我開啟功能選單",
            areas=[
                RichMenuArea(
                    bounds={"x": 0, "y": 0, "width": 1250, "height": 843},
                    action=MessageAction(label="今日新聞", text="今日新聞")
                ),
                RichMenuArea(
                    bounds={"x": 1251, "y": 0, "width": 1250, "height": 843},
                    action=MessageAction(label="市場資訊", text="市場資訊")
                )
            ]
        )
        rich_menu_id = line_bot_api.create_rich_menu(rich_menu=rich_menu_to_create)
        with open("richmenu.png", "rb") as f:
            line_bot_api.set_rich_menu_image(rich_menu_id, "image/png", f)
        line_bot_api.set_default_rich_menu(rich_menu_id)
        print("✅ Rich Menu 建立與綁定成功")
    except Exception as e:
        print("❌ Rich Menu 建立失敗：", e)

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
                        {"type": "button", "action": {"type": "message", "label": "📈 市場資訊", "text": "市場資訊"}}
                    ]
                }
            }
        )
        line_bot_api.reply_message(event.reply_token, flex_message)

    elif text == "今日新聞":
        news_list = fetch_news()
        for msg in news_list:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))

    elif text == "市場資訊":
        summary = get_market_summary()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=summary))

    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"你說的是：{text}"))

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

