from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from linebot.v3 import WebhookHandler
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, MessagingApiBlob, ReplyMessageRequest, TextMessage
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent, ImageMessageContent
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

def format_qty(qty, unit):
    q = int(qty) if qty.is_integer() else qty
    return f"{q}{unit}"

def format_cur(amount):
    if amount < 0:
        return f"-¥{abs(int(amount)):,}"
    return f"¥{int(amount):,}"

@handler.add(MessageEvent, message=ImageMessageContent)
def handle_image_message(event):
    user_id = event.source.user_id
    message_id = event.message.id
    
    project_name = database.get_active_project(user_id)
    if not project_name:
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text="案件が選択されていません。先に「案件 〇〇邸」と送信して、保存先の案件を指定してください。")]
                )
            )
        return
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_blob_api = MessagingApiBlob(api_client)
        
        # 画像データを取得して保存
        message_content = line_bot_blob_api.get_message_content(message_id)
        os.makedirs('static/evidence', exist_ok=True)
        filepath = f"static/evidence/{message_id}.jpg"
        with open(filepath, 'wb') as f:
            f.write(message_content)
            
        # データベースに一時保存（タイトルはまだNULL）
        database.add_evidence_image(user_id, project_name, filepath)
        
        reply_text = f"【{project_name}】に写真を追加しました！\n後で見返せるように、この写真の「タイトル」（例：コーナン領収書、現場写真 など）をテキストで入力してください。"
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    raw_text = event.message.text
    user_id = event.source.user_id
    
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    reply_messages = []
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        for text in lines:
            project_name = database.get_active_project(user_id)
            
            # --- エビデンスのタイトル待ち状態チェック ---
            if project_name:
                pending_evidence = database.get_pending_evidence(user_id, project_name)
                if pending_evidence:
                    database.set_evidence_title(pending_evidence['id'], text)
                    reply_messages.append(f"✅ 写真にタイトル「{text}」を設定しました！")
                    continue  # 次の行へ
                
            # --- 通常のコマンド解析 ---
            parsed = parse_message(text)
            
            if parsed['type'] == 'error':
                reply_messages.append(f"❌ {text} ({parsed['message']})")
                
            elif parsed['type'] == 'command':
                cmd = parsed['command']
                
                if cmd == 'switch_project':
                    new_project = parsed['project_name']
                    database.set_active_project(user_id, new_project)
                    reply_messages.append(f"🔄 作業案件を『{new_project}』に切り替えました。")
                    
                elif cmd == 'complete_project':
                    if not project_name:
                        reply_messages.append("❌ 案件が選択されていません。")
                    else:
                        database.clear_project(user_id, project_name)
                        reply_messages.append(f"🗑️ 案件『{project_name}』のデータをすべて整理（消去）しました。お疲れ様でした！")
                            
                elif cmd == 'show_help':
                    help_text = """【使い方（取説）】
■ 1. 案件の指定（必須）
「案件 〇〇邸」
※最初に入力してください。以降のデータがこの案件に保存されます。

■ 2. 項目の入力
「品名 数量 単価」
例: 単管パイプ 10本 500円
※改行して複数行を1回のメッセージで同時に送ることも可能です。

■ 3. 見積書・請求書の発行
「見積書発行」または「請求書発行」
※ExcelのダウンロードURLが届きます。発行してもデータは消えません。

■ 4. 写真の追加
スマホで写真を送るとタイトルを聞かれます。「現場写真」などと文字で返信すると、Excelの2枚目に自動で綺麗に貼り付けられます。

■ その他の便利コマンド
「リスト」: 現在の入力内容と合計金額を確認
「削除 [番号]」: 指定した番号の項目を削除（例: 削除 2）
「登録 [品名] [単価]」: 単価を辞書に記憶（次回から単価の入力を省略可能になります）
「単価一覧」: 登録した単価の一覧を確認
「案件完了」: 案件のデータを完全に消去"""
                    reply_messages.append(help_text)
                
                elif cmd in ['issue_estimate', 'issue_invoice']:
                    if not project_name:
                        reply_messages.append("❌ 案件が選択されていません。")
                    else:
                        items = database.get_items(user_id, project_name)
                        doc_type = "estimate" if cmd == 'issue_estimate' else "invoice"
                        doc_name = "見積書" if doc_type == "estimate" else "請求書"
                        evidence_list = database.get_all_evidence(user_id, project_name)
                        
                        if not items and not evidence_list:
                            reply_messages.append(f"❌ {doc_name}に記載する項目や写真がありません。")
                        else:
                            filename = excel_generator.generate_excel(user_id, items, project_name, doc_type=doc_type)
                            server_url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("SERVER_URL", "http://localhost:8000")
                            download_url = f"{server_url}/static/{filename}"
                            reply_messages.append(f"✅ 【{project_name}】の{doc_name}を発行しました！\n{download_url}")
                
                elif cmd == 'list_items':
                    if not project_name:
                        reply_messages.append("❌ 案件が選択されていません。")
                    else:
                        items = database.get_items(user_id, project_name)
                        lines_output = [f"【現在の入力内容：{project_name}】"]
                        total = 0
                        if items:
                            for i, item in enumerate(items, 1):
                                lines_output.append(f"{i}. {item['item_name']} {format_qty(item['quantity'], item['unit'])} {format_cur(item['total'])}")
                                total += item['total']
                            lines_output.append(f"\n合計金額: {format_cur(total)} (税別)")
                        else:
                            lines_output.append("・登録された品名はありません。")
                        
                        evidence_list = database.get_all_evidence(user_id, project_name)
                        if evidence_list:
                            lines_output.append(f"\n【登録済みの写真】: {len(evidence_list)}枚")
                            for ev in evidence_list:
                                lines_output.append(f"・{ev['title']}")
                                
                        reply_messages.append("\n".join(lines_output))
                
                elif cmd == 'delete_item':
                    if not project_name:
                        reply_messages.append("❌ 案件が選択されていません。")
                    else:
                        idx = parsed['index']
                        deleted_item = database.delete_item_by_index(user_id, project_name, idx)
                        if deleted_item:
                            reply_messages.append(f"🗑️ No.{idx} の項目（{deleted_item['item_name']}）を削除しました。")
                        else:
                            reply_messages.append(f"❌ No.{idx} の項目は見つかりませんでした。")
                
                elif cmd == 'register_price':
                    item_name = parsed['item_name']
                    price = parsed['price']
                    database.set_price(user_id, item_name, price)
                    reply_messages.append(f"📖 単価辞書に登録しました: {item_name} {format_cur(price)}")
                
                elif cmd == 'list_prices':
                    prices = database.get_all_prices(user_id)
                    if not prices:
                        reply_messages.append("❌ 登録されている単価辞書はありません。")
                    else:
                        lines_output = ["【登録済みの単価一覧】"]
                        for p in prices:
                            lines_output.append(f"・{p['item_name']}: {format_cur(p['price'])}")
                        reply_messages.append("\n".join(lines_output))
                    
            elif parsed['type'] == 'item':
                if not project_name:
                    reply_messages.append(f"❌ {text} (案件が選択されていません。先に「案件 〇〇邸」と送信してください)")
                else:
                    item_data = parsed['data']
                    
                    if item_data['price'] is None:
                        db_price = database.get_price(user_id, item_data['item_name'])
                        if db_price is not None:
                            item_data['price'] = db_price
                            item_data['total'] = item_data['quantity'] * db_price
                        else:
                            reply_messages.append(f"❌ 「{item_data['item_name']}」の単価が辞書に登録されていません。")
                            item_data = None
                    
                    if item_data:
                        database.add_item(user_id, project_name, item_data)
                        reply_messages.append(f"✅ {item_data['item_name']} {format_qty(item_data['quantity'], item_data['unit'])} を追加しました。")
        
        # 1通のメッセージにまとめて送信
        final_reply = "\n".join(reply_messages)
        
        # もし文字数が5000文字を超えるようなら（念のため）
        if len(final_reply) > 5000:
            final_reply = final_reply[:4900] + "\n\n※メッセージが長すぎるため省略されました。"
            
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=final_reply)]
            )
        )
