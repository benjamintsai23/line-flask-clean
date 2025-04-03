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
from dotenv import load_dotenv

# === 環境變數 ===
load_dotenv()
line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")

if not line_channel_access_token or not line_channel_secret:
    raise ValueError("請設定 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_CHANNEL_SECRET")

app = Flask(__name__)
line_bot_api = LineBotApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)

# === 記錄群組 ID ===
group_ids = set()

# === 市場資訊 ===
def get_market_summary():
    try:
        res = requests.get("https://tw.stock.yahoo.com/", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
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
        return f"📈 {name}（Yahoo 財經）\n指數：{price}\n漲跌：{change}\n成交金額：{volume_text}"
    except Exception as e:
        print("市場資訊失敗：", e)
        return "⚠️ 市場資訊查詢失敗"

# === 新聞摘要 ===
def fetch_news():
    results = []
    # Yahoo
    yahoo_feed = feedparser.parse("https://tw.news.yahoo.com/rss/finance")
    msg = "📢 Yahoo 財經新聞：\n"
    for entry in yahoo_feed.entries[:5]:
        msg += f"• {entry.title}\n{entry.link}\n"
    results.append(msg)
    # 鉅亨網
    try:
        resp = requests.get("https://www.cnyes.com/twstock/news", timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(".newsList_item > a")[:5]
        msg = "📢 鉅亨網台股新聞：\n"
        for item in items:
            title = item.select_one("h3").get_text(strip=True)
            link = "https://www.cnyes.com" + item['href']
            msg += f"• {title}\n{link}\n"
        results.append(msg)
    except Exception as e:
        print("鉅亨網失敗：", e)
    return results

# === AI 股市觀點 ===
def generate_ai_view():
    keywords = ["AI", "晶片", "NVIDIA", "半導體", "台積電"]
    feed = feedparser.parse("https://tw.news.yahoo.com/rss/finance")
    for entry in feed.entries:
        if any(k in entry.title for k in keywords):
            return f"🤖 AI 股市觀點：\n{entry.title}\n{entry.link}"
    return "🤖 今日無明顯 AI 股市新聞"

# === Rich Menu 設定 ===
def setup_rich_menu():
    try:
        rich_menu = RichMenu(
            size={"width": 2500, "height": 843},
            selected=True,
            name="財經主選單",
            chat_bar_text="📊 功能選單",
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
        rich_menu_id = line_bot_api.create_rich_menu(rich_menu=rich_menu)
        with open("richmenu.png", 'rb') as f:
            line_bot_api.set_rich_menu_image(rich_menu_id, "image/png", f)
        line_bot_api.set_default_rich_menu(rich_menu_id)
        print("✅ Rich Menu 建立成功")
    except Exception as e:
        print("❌ Rich Menu 錯誤：", e)

# 啟動 Rich Menu
setup_rich_menu()

# === Webhook ===
@app.route("/", methods=['GET'])
def home():
    return "LINE Bot 運作中"

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

    if text == "功能" or text == "選單":
        msg = "請點選下方功能選單喔！"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))

    elif text == "今日新聞":
        news = fetch_news()
        for msg in news:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))

    elif text == "市場資訊":
        summary = get_market_summary()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=summary))

    elif text == "AI 股市觀點":
        view = generate_ai_view()
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=view))

    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"你說的是：{text}"))

    if event.source.type == "group":
        gid = event.source.group_id
        group_ids.add(gid)
        print("✅ 加入群組 ID：", gid)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

