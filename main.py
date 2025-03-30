import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# 設定環境變數的 Channel Access Token 和 Secret
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

app = Flask(__name__)

@app.route("/webhook", methods=['POST'])
def callback():
    # 取得 X-Line-Signature header
    signature = request.headers['X-Line-Signature']
    # 取得 request body
    body = request.get_data(as_text=True)

    try:
        # 解析來自 Line 的訊息
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 取得使用者發送的文字訊息
    user_text = event.message.text
    source_type = event.source.type

    # 如果訊息來自群組
    if source_type == "group":
        print(f"群組ID 是：", event.source.group_id)

    # 正常回覆訊息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"我收到你的訊息：{user_text}")
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
