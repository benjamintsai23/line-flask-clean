from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import os

app = Flask(__name__)

# ====== 設定 LINE BOT 資訊 ======
line_bot_api = LineBotApi(os.environ.get("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET"))

# ====== 建立 Rich Menu（首次部署時呼叫） ======
def create_rich_menu():
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
    rich_menu_id = line_bot_api.create_rich_menu(rich_menu=rich_menu)

    # 上傳圖片（用你上傳的 richmenu.png）
    with open("richmenu.png", 'rb') as f:
        line_bot_api.set_rich_menu_image(rich_menu_id, 'image/png', f)

    # 綁定 Rich Menu
    line_bot_api.set_default_rich_menu(rich_menu_id)

# ====== Webhook Home ======
@app.route("/", methods=['GET'])
def home():
    return "LINE Bot Webhook is running."

# ====== Webhook 入口點 ======
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

# ====== 訊息處理 ======
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text
    if msg == "功能" or msg == "選單":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請點選下方功能選單喔！"))
    elif msg == "今日新聞":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="這是今日新聞 ✉️"))
    elif msg == "市場資訊":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="這是市場資訊 📈"))
    elif msg == "AI 股市觀點":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="這是 AI 股市觀點 🤖"))
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"你說的是：{msg}"))

if __name__ == "__main__":
    if os.environ.get("CREATE_RICH_MENU") == "1":
        create_rich_menu()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))

