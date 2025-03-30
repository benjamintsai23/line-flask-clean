import os
from flask import Flask, request, abort
from linebot import LineBotApi
from linebot.models import MessageEvent, TextSendMessage
from linebot.exceptions import InvalidSignatureError

# 設置 Flask 應用
app = Flask(__name__)

# 你的 LINE 渠道存取權杖與密鑰
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# Webhook 路由
@app.route("/webhook", methods=['POST'])
def callback():
    # 取得 X-Line-Signature header
    signature = request.headers['X-Line-Signature']
    
    # 取得 request body
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
    source_type = event.source.type

    # 如果是群組訊息，顯示群組ID
    if source_type == "group":
        print(f"群組ID: {event.source.group_id}")

    # 正常回覆訊息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=f"我收到你的訊息：{user_text}")
    )

if __name__ == "__main__":
    # 運行 Flask 應用
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
