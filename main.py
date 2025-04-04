# ✅ 整合功能：今日新聞、台股市場資訊、AI 股市觀點

import os
import requests
import feedparser
from bs4 import BeautifulSoup
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 📢 今日新聞：Yahoo RSS + 鉅亨網爬蟲
def fetch_news():
    result = []

    # Yahoo 財經
    yahoo = feedparser.parse("https://tw.news.yahoo.com/rss/finance")
    if yahoo.entries:
        msg = "\U0001F4E2 Yahoo 財經新聞：\n"
        for e in yahoo.entries[:5]:
            msg += f"\u2022 {e.title}\n{e.link}\n"
        result.append(msg)

    # 鉅亨網
    try:
        url = "https://www.cnyes.com/twstock/news"
        resp = requests.get(url, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(".newsList_item > a")[:5]
        msg = "\U0001F4E2 鉅亨網台股新聞：\n"
        for item in items:
            title = item.select_one("h3").text.strip()
            link = "https://www.cnyes.com" + item['href']
            msg += f"\u2022 {title}\n{link}\n"
        result.append(msg)
    except Exception as e:
        result.append("⚠️ 鉅亨新聞載入失敗")

    return result

# 📈 市場資訊：加權指數、漲跌、成交金額
def fetch_market():
    try:
        url = "https://tw.stock.yahoo.com/"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        index = soup.select_one("li[class*=Index]")
        name = index.select_one("span.Fz\\(16px\\)").text
        price = index.select_one("span.Fw\\(b\\).Fz\\(24px\\)").text
        change = index.select_one("span.Fz\\(20px\\)").text

        volume = "N/A"
        for i in soup.find_all("li", class_="D\(f\).Ai\(c\).Jc\(sb\).Mb\(8px\)"):
            if "成交金額" in i.text:
                volume = i.select_one("span.Fz\\(16px\\)").text
                break

        return f"\U0001F4C8 {name} 即時資訊：\n指數：{price}\n漲跌：{change}\n成交金額：{volume}"
    except:
        return "⚠️ 市場資訊讀取失敗"

# 🤖 AI 股市觀點：簡單摘要（假設新聞已抓好）
def ai_stock_view():
    news = fetch_news()
    if news:
        first_news = news[0].split('\n')[1]  # 取第一則新聞標題
        if "升" in first_news or "漲" in first_news:
            opinion = "該新聞標題偏多，可能與市場正面情緒有關。"
        elif "跌" in first_news or "降" in first_news:
            opinion = "該新聞標題偏空，可能與利空消息有關。"
        else:
            opinion = "該新聞為中性，提供資訊供參考。"
        return f"\U0001F916 FinBot 股市觀點：\n{first_news}\n\n{opinion}"
    return "⚠️ 無法提供 AI 觀點"

# Webhook 接收
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# 使用者輸入處理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    if msg == "今日新聞":
        for text in fetch_news():
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))
            return
    elif msg == "市場資訊":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=fetch_market()))
    elif msg == "AI 股市觀點":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ai_stock_view()))
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請使用功能選單點選項目喔～"))

# 預設首頁
@app.route("/")
def home():
    return "LINE Bot is running"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



