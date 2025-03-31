from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from dotenv import load_dotenv
import os

# 載入 .env 檔案
load_dotenv()

# 設定 LINE Channel Access Token 和 Secret
line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")

# 測試是否成功取得環境變數
if not line_channel_access_token:
    print("ERROR: LINE_CHANNEL_ACCESS_TOKEN is not set.")
if not line_channel_secret:
    print("ERROR: LINE_CHANNEL_SECRET is not set.")
else:
    print(f"LINE_CHANNEL_ACCESS_TOKEN: {line_channel_access_token}")
    print(f"LINE_CHANNEL_SECRET: {line_channel_secret}")

# 若環境變數未設置，則拋出錯誤
if not line_channel_access_token or not line_channel_secret:
    raise ValueError("LINE_CHANNEL_ACCESS_TOKEN or LINE_CHANNEL_SECRET is missing")

app = Flask(__name__)

# 初始化 LineBotApi 和 WebhookHandler
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

# 設定事件處理器
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    reply = f"您說了: {user_text}"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
    app.run(debug=True)
