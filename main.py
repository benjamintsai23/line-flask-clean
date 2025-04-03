import os
import json
import requests
import feedparser
from bs4 import BeautifulSoup
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, FlexSendMessage,
    RichMenu, RichMenuArea, RichMenuBounds, MessageAction
)
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

line_channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
line_channel_secret = os.getenv("LINE_CHANNEL_SECRET")

if not line_channel_access_token or not line_channel_secret:
    raise ValueError("請確認已設定 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_CHANNEL_SECRET")

app = Flask(__name__)
line_bot_api = LineBotApi(line_channel_access_token)
handler = WebhookHandler(line_channel_secret)

# 建立 Rich Menu
@app.before_first_request
def create_and_set_rich_menu():
    try:
        rich_menu = RichMenu(
            size={"width": 2500, "height": 843},
            selected=True,
            name="財經功能選單",
            chat_bar_text="📊 開啟功能選單",
            areas=[
                RichMenuArea(
                    bounds=RichMenuBounds(x=0, y=0, width=833, height=843),
                    action=MessageAction(label="今日新聞", text="今日新聞")
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=833, y=0, width=834, height=843),
                    action=MessageAction(label="市場資訊", text="市場資訊")
                ),
                RichMenuArea(
                    bounds=RichMenuBounds(x=1667, y=0, width=833, height=843),
                    action=MessageAction(label="功能選單", text="功能")
                )
            ]
        )
        rich_menu_id = line_bot_api.create_rich_menu(rich_menu=rich_menu)

        with open("rich_menu_image.png", "rb") as f:
            line_bot_api.set_rich_menu_image(rich_menu_id, "image/png", f)

        line_bot_api.set_default_rich_menu(rich_menu_id)
        print("✅ Rich Menu 已建立並設為預設")
    except Exception as e:
        print("⚠️ 建立 Rich Menu 發生錯誤：", e)

# 其餘程式邏輯...

@app.route("/", methods=['GET'])
def home():
    return "LINE Bot 運行中"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

