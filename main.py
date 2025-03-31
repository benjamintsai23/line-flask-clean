import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, SourceGroup
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()
line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")

# 檢查環境變數
if not line_channel_access_token or not line_channel_secret:
    raise ValueError("請確認已正確設置 LINE_CHANNEL_ACCESS_TOKEN 和 LINE_CHANNEL_SECRET")

# 初始化 Flask 與 LINE API
app = Flask(__name__)
line_bot_api = LineBotApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)

@app.route("/webhook", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# 處理文字訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text

    # 如果是群組訊息
    if isinstance(event.source, SourceGroup):
        group_id = event.source.group_id
        print(f"✅ 來自群組的訊息，group_id 是：{group_id}")
        reply = f"你說的是：{user_text}"
    else:
        reply = f"你說的是：{user_text}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

# 啟動 Flask 應用
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
