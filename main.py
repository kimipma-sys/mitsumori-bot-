from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, ReplyMessageRequest, TextMessage
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import os
from dotenv import load_dotenv

from message_parser import parse_message
import database
import excel_generator

load_dotenv()
database.init_db()

app = FastAPI()

# Mount the static directory so files can be downloaded
os.makedirs('static', exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

channel_secret = os.getenv('LINE_CHANNEL_SECRET', 'YOUR_CHANNEL_SECRET')
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', 'YOUR_CHANNEL_ACCESS_TOKEN')

configuration = Configuration(access_token=channel_access_token)
handler = WebhookHandler(channel_secret)

@app.post("/callback")
async def callback(request: Request, x_line_signature: str = Header(None)):
    body = await request.body()
    body_str = body.decode('utf-8')
    try:
        handler.handle(body_str, x_line_signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    text = event.message.text
    user_id = event.source.user_id
    parsed = parse_message(text)
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        if parsed['type'] == 'error':
            reply_text = parsed['message']
            
        elif parsed['type'] == 'command' and parsed['command'] == 'issue_estimate':
            # 1. Get items for this user
            items = database.get_items(user_id)
            if not items:
                reply_text = "見積書に記載する項目がありません。先に品名と金額を入力してください。"
            else:
                # 2. Generate Excel
                filename = excel_generator.generate_estimate_excel(user_id, items)
                
                # 3. Clear database for this user
                database.clear_items(user_id)
                
                # We assume the server will be accessed via ngrok, but wait, 
                # we don't know the ngrok URL dynamically here.
                # A quick trick is to instruct the user to set SERVER_URL in .env
                server_url = os.getenv("SERVER_URL", "http://localhost:8000")
                download_url = f"{server_url}/static/{filename}"
                
                reply_text = f"見積書を発行しました！以下のURLからダウンロードしてください。\n\n{download_url}\n\n※データはリセットされました。"
                
        elif parsed['type'] == 'item':
            item_data = parsed['data']
            database.add_item(user_id, item_data)
            reply_text = f"追加しました:\n品名: {item_data['item_name']}\n金額: ¥{int(item_data['total']):,}"
            
        else:
            reply_text = "不明なエラーが発生しました。"
            
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )
