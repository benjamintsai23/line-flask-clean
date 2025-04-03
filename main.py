from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import os
from dotenv import load_dotenv

# === 初始化環境變數 ===
load_dotenv()
line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")

if not line_channel_access_token or not line_channel_secret:
    raise ValueError("請確認已設定 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_CHANNEL_SECRET")

# === 初始化 App 與 LINE Bot API ===
app = Flask(__name__)
line_bot_api = LineBotApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)

group_ids = set()

# === 建立 Rich Menu（無圖片版本） ===
try:
    rich_menu = RichMenu(
        size={"width": 2500, "height": 843},
        selected=True,
        name="功能選單",
        chat_bar_text="📊 功能選單",
        areas=[
            RichMenuArea(
                bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                action=MessageAction(label="📈 市場資訊", text="市場資訊")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=834, y=0, width=833, height=843),
                action=MessageAction(label="📰 今日新聞", text="今日新聞")
            ),
            RichMenuArea(
                bounds=RichMenuBounds(x=1667, y=0, width=833, height=843),
                action=MessageAction(label="🤖 AI 股市觀點", text="AI 股市觀點")
            )
        ]
    )

    rich_menu_id = line_bot_api.create_rich_menu(rich_menu=rich_menu)
    line_bot_api.set_default_rich_menu(rich_menu_id)
    print("✅ Rich Menu 建立成功")
except Exception as e:
    print("❌ Rich Menu 建立失敗：", e)

# === 基本首頁 ===
@app.route("/")
def home():
    return "LINE Bot Webhook 啟動成功"

# === Webhook 入口 ===
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# === 處理使用者訊息 ===
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    if msg in ["功能", "選單"]:
        reply = "請點選下方功能選單喔！"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
    else:
        reply = f"你說的是：{msg}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

