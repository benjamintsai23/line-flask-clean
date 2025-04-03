from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()
line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")

if not line_channel_access_token or not line_channel_secret:
    raise ValueError("請確認已設定 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_CHANNEL_SECRET")

app = Flask(__name__)
line_bot_api = LineBotApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)

@app.route("/")
def home():
    return "LINE Bot Webhook 啟動成功！"

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

    if msg == "功能":
        flex_message = {
            "type": "flex",
            "altText": "請選擇下方功能選單",
            "contents": {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": "請選擇想使用的功能",
                            "weight": "bold",
                            "size": "md"
                        },
                        {
                            "type": "button",
                            "action": {
                                "type": "message",
                                "label": "📄 今日新聞",
                                "text": "今日新聞"
                            },
                            "style": "primary"
                        },
                        {
                            "type": "button",
                            "action": {
                                "type": "message",
                                "label": "📊 行情資訊",
                                "text": "行情資訊"
                            },
                            "style": "primary"
                        },
                        {
                            "type": "button",
                            "action": {
                                "type": "message",
                                "label": "📈 AI 股市觀點",
                                "text": "AI 股市觀點"
                            },
                            "style": "primary"
                        }
                    ]
                }
            }
        }
        line_bot_api.reply_message(event.reply_token, FlexSendMessage.new_from_json_dict(flex_message))
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="您輸入的是：" + msg))

if __name__ == "__main__":
    app.run(debug=True)

