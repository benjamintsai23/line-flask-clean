from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import os
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

@app.route("/")
def home():
    return "LINE Bot Ready"

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

# Flex Message 功能選單
from linebot.models import FlexSendMessage

def get_flex_function_menu():
    bubble = {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": "📊 功能選單",
                    "weight": "bold",
                    "size": "xl",
                    "color": "#1E90FF"
                },
                {
                    "type": "separator"
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "action": {
                                "type": "message",
                                "label": "今日新聞",
                                "text": "今日新聞"
                            },
                            "style": "primary",
                            "color": "#005BBB"
                        },
                        {
                            "type": "button",
                            "action": {
                                "type": "message",
                                "label": "市場資訊",
                                "text": "市場資訊"
                            },
                            "style": "primary",
                            "color": "#0077CC"
                        },
                        {
                            "type": "button",
                            "action": {
                                "type": "message",
                                "label": "AI 股市觀點",
                                "text": "AI 股市觀點"
                            },
                            "style": "primary",
                            "color": "#3399FF"
                        }
                    ]
                }
            ]
        }
    }
    return FlexSendMessage(alt_text="請選擇功能", contents=bubble)

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()

    if msg in ["功能", "選單", "主選單"]:
        flex_msg = get_flex_function_menu()
        line_bot_api.reply_message(event.reply_token, flex_msg)
    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"你說的是：{msg}"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
