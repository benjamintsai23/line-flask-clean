from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import os

app = Flask(__name__)

# 環境變數設定
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# ===== 建立 Rich Menu（只需執行一次） =====
if os.getenv('CREATE_RICH_MENU') == '1':
    from PIL import Image

    rich_menu = RichMenu(
        size={"width": 2500, "height": 843},
        selected=True,
        name="主選單",
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
    print(f"Rich Menu ID: {rich_menu_id}")

    # 上傳圖片
    with open("richmenu.png", 'rb') as f:
        line_bot_api.set_rich_menu_image(rich_menu_id, 'image/png', f)

    # 綁定到所有用戶
    line_bot_api.set_default_rich_menu(rich_menu_id)
    print("Rich Menu 建立並綁定成功")


@app.route("/")
def home():
    return "LINE Bot is running"

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

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    uid = event.source.user_id

    if msg in ["功能", "選單"]:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請點選下方功能選單喔！")
        )
    elif msg == "今日新聞":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="這裡是今日新聞！")
        )
    elif msg == "市場資訊":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="這裡是市場資訊！")
        )
    elif msg == "AI 股市觀點":
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="這裡是 AI 股市觀點！")
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"你說的是：{msg}")
        )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


