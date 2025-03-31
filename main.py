import os
import feedparser
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
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

# 暫存群組 ID 與 訂閱用戶 ID
group_ids = set()
subscriber_user_ids = set()

@app.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# 處理訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    text = event.message.text.strip()

    # 功能選單
    if text in ["功能", "選單", "？"]:
        menu = """📊 LINE 財經群組功能選單：
1️⃣ 功能：顯示這個選單
2️⃣ 每天推播最新財經新聞（早上 8:30、晚上 19:30）
3️⃣ 私訊「我要訂閱」可接收個人新聞通知
（更多功能即將加入...）"""
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=menu)
        )
        return

    # 訂閱新聞（限私訊）
    if text == "我要訂閱":
        if event.source.type == "user":
            user_id = event.source.user_id
            subscriber_user_ids.add(user_id)
            print("✅ 已加入訂閱名單 User ID：", user_id)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="✅ 你已成功訂閱新聞推播！")
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="⚠️ 請私訊我「我要訂閱」才能收到個人通知！")
            )
        return

    # 預設回覆
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"你說的是：{text}")
    )

    # 記錄群組 ID
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
        if 'yahoo' in rss_url:
            msg_header = "📌 Yahoo 財經 今日新聞：\n"
        else:
            msg_header = "📌 鉅亨網台股 今日新聞：\n"

        msg_body = "\n".join([f"・{entry.title}" for entry in entries])
        msg = msg_header + msg_body

        # 群組推播
        for gid in group_ids:
            try:
                line_bot_api.push_message(gid, TextSendMessage(text=msg))
            except Exception as e:
                print(f"❌ 推播到 {gid} 發生錯誤：{e}")

        # 個人推播
        for uid in subscriber_user_ids:
            try:
                line_bot_api.push_message(uid, TextSendMessage(text=msg))
            except Exception as e:
                print(f"❌ 推播到訂閱者 {uid} 發生錯誤：{e}")

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
