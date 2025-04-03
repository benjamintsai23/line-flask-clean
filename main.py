import os
import json
import requests
import feedparser
from bs4 import BeautifulSoup
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage,
    RichMenu, RichMenuArea, RichMenuBounds, URIAction, MessageAction
)
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

# === 初始化環境 ===
load_dotenv()
line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")

if not line_channel_access_token or not line_channel_secret:
    raise ValueError("請確認已設定 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_CHANNEL_SECRET")

app = Flask(__name__)
line_bot_api = LineBotApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)

# === 記錄群組 ID ===
group_ids = set()

# === 建立 Rich Menu ===
@app.before_first_request
def setup_rich_menu():
    try:
        rich_menu = RichMenu(
            size={"width": 2500, "height": 843},
            selected=True,
            name="財經主選單",
            chat_bar_text="功能選單",
            areas=[
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                    action=MessageAction(label="今日新聞", text="今日新聞")
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=834, y=0, width=833, height=843),
                    action=MessageAction(label="市場資訊", text="市場資訊")
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=1667, y=0, width=833, height=843),
                    action=MessageAction(label="AI 股市觀點", text="AI 股市觀點")
                )
            ]
        )

        rich_menu_id = line_bot_api.create_rich_menu(rich_menu)

        # 上傳圖片
        with open("richmenu.png", "rb") as f:
            line_bot_api.set_rich_menu_image(rich_menu_id, "image/png", f)

        # 綁定至所有用戶
        line_bot_api.set_default_rich_menu(rich_menu_id)
        print("✅ Rich Menu 已建立並綁定成功")
    except Exception as e:
        print("⚠️ Rich Menu 建立失敗：", e)

# === 抓新聞 ===
def fetch_news():
    results = []
    yahoo_feed = feedparser.parse("https://tw.news.yahoo.com/rss/finance")
    yahoo_entries = yahoo_feed.entries[:5]
    if yahoo_entries:
        msg = "📢 Yahoo 財經新聞：\n"
        for e in yahoo_entries:
            msg += f"• {e.title}\n{e.link}\n"
        results.append(msg)

    try:
        resp = requests.get("https://www.cnyes.com/twstock/news", timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        news_items = soup.select(".newsList_item > a")[:5]
        msg = "📢 鉅亨網台股新聞：\n"
        for item in news_items:
            title = item.select_one("h3").get_text(strip=True)
            link = "https://www.cnyes.com" + item['href']
            msg += f"• {title}\n{link}\n"
        results.append(msg)
    except Exception as e:
        print("❌ 鉅亨新聞錯誤：", e)
    return results

# === 查市場資訊 ===
def get_market_summary():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get("https://tw.stock.yahoo.com/", headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        index_box = soup.select_one("li[class*=Index]")
        name = index_box.select_one("span.Fz\\(16px\\)").text
        price = index_box.select_one("span.Fw\\(b\\).Fz\\(24px\\)").text
        change = index_box.select_one("span.Fz\\(20px\\)").text
        msg = f"📈 {name} 市場資訊：\n指數：{price}\n漲跌：{change}"
        return msg
    except Exception as e:
        print("市場資訊錯誤：", e)
        return "⚠️ 查詢失敗，請稍後再試。"

# === AI 股市觀點（等級一） ===
def ai_stock_comment():
    try:
        yahoo_feed = feedparser.parse("https://tw.news.yahoo.com/rss/finance")
        top_news = yahoo_feed.entries[0]
        title = top_news.title
        if "台積電" in title:
            comment = "💡 台積電消息可能影響大盤表現，請留意半導體走勢。"
        elif "鴻海" in title:
            comment = "📌 鴻海相關消息，代表電子類股有機會波動。"
        else:
            comment = "🔍 根據新聞內容，建議關注主流產業與資金動向。"
        return f"📈 AI 股市觀點：\n{title}\n{comment}"
    except:
        return "⚠️ AI 分析失敗，請稍後再試。"

# === 定時推播 ===
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

# === Webhook 入口 ===
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
    if text in ["功能", "選單"]:
        flex = FlexSendMessage(
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
                        {"type": "button", "action": {"type": "message", "label": "🤖 AI 股市觀點", "text": "AI 股市觀點"}}
                    ]
                }
            }
        )
        line_bot_api.reply_message(event.reply_token, flex)
        return

    if text == "今日新聞":
        for msg in fetch_news():
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))
        return

    if text == "市場資訊":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=get_market_summary()))
        return

    if text == "AI 股市觀點":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ai_stock_comment()))
        return

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"你說的是：{text}"))

    if event.source.type == "group":
        group_id = event.source.group_id
        group_ids.add(group_id)
        print("✅ 群組 ID：", group_id)

@app.route("/", methods=['GET'])
def index():
    return "LINE Bot 正常運作中"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
