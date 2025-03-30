import os
import feedparser
from flask import Flask, request, abort
from linebot import LineBotApi
from linebot.models import MessageEvent, TextSendMessage
from linebot.exceptions import InvalidSignatureError
from apscheduler.schedulers.background import BackgroundScheduler

# 設置 Flask 應用
app = Flask(__name__)

# 你的 LINE 渠道存取權杖與密鑰
line_bot_api = LineBotApi(os.getenv('S0iIaPNYEpVY22HfXkmgiJiGFcGtJlMVZUs3WStlSeETJjFj1YvJkUEhyTCVd24pBbaFFuuyxixbBsCNKiitOLG5UMA7wHMzQVIgJ1E1OoggZrDLTXid9UYzGN1ckYZdXTParo1RGCrbYht2MlYG4wdB04t89/1O/w1cDnyilFU='))
handler = WebhookHandler(os.getenv('faaa98f1f31315805b7deb6cff19e0fd'))

# 設定 RSS 源
rss_sources = {
    'Yahoo Finance': 'https://tw.news.yahoo.com/rss/finance',
    '鉅亨網台股': 'https://www.cnyes.com/rss/cat/tw_stock',
}

# 抓取 RSS 資料並發送的函數
def fetch_rss_and_send():
    for source_name, rss_url in rss_sources.items():
        # 解析 RSS
        feed = feedparser.parse(rss_url)
        news = feed.entries[:5]  # 只取前 5 則新聞

        # 依次將每則新聞發送到 LINE 群組
        for entry in news:
            title = entry.title
            link = entry.link
            message = f"【{source_name}】\n{title}\n{link}"
            # 發送新聞訊息到群組或指定的 LINE 使用者
            line_bot_api.broadcast(TextSendMessage(text=message))

# 使用 APScheduler 設定定時任務，每天 8:30 和 19:30 執行
scheduler = BackgroundScheduler()
scheduler.add_job(fetch_rss_and_send, 'cron', hour=8, minute=30)  # 8:30
scheduler.add_job(fetch_rss_and_send, 'cron', hour=19, minute=30)  # 19:30
scheduler.start()

# Webhook 路由
@app.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# 處理訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"我收到你的訊息：{user_text}")
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
