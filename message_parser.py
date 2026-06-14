import re

def parse_message(text: str):
    """
    LINEからのメッセージを解析します。
    コマンド判定、またはデータ行の判定を行います。
    """
    text = text.strip()
    
    # --- コマンドの判定 ---
    if text == "見積書発行":
        return {"type": "command", "command": "issue_estimate"}
        
    if text == "請求書発行":
        return {"type": "command", "command": "issue_invoice"}
        
    if text == "リスト":
        return {"type": "command", "command": "list_items"}
        
    if text == "単価一覧":
        return {"type": "command", "command": "list_prices"}
        
    if text == "取説" or text == "ヘルプ":
        return {"type": "command", "command": "show_help"}
        
    # 「案件 鈴木邸」などの判定
    m_switch = re.match(r'^案件[\s　]+(.+)$', text)
    if m_switch:
        return {"type": "command", "command": "switch_project", "project_name": m_switch.group(1).strip()}
        
    # 「案件完了」の判定
    if text == "案件完了":
        return {"type": "command", "command": "complete_project"}
        
    # 「削除 2」などの判定
    m_delete = re.match(r'^削除[\s　]+(\d+)$', text)
    if m_delete:
        return {
            "type": "command", 
            "command": "delete_item", 
            "index": int(m_delete.group(1))
        }
        
    # 「登録 人工 20000円」などの判定
    m_register = re.match(r'^登録[\s　]+(.+)[\s　]+([\d\.,]+)[\D]*$', text)
    if m_register:
        item_name = m_register.group(1).strip()
        price = float(m_register.group(2).replace(',', ''))
        return {
            "type": "command",
            "command": "register_price",
            "item_name": item_name,
            "price": price
        }

    # --- データの判定 ---
    parts = re.split(r'[\s　]+', text)
    
    if len(parts) == 2 and "値引" in parts[0]:
        try:
            price_str = parts[-1].replace(',', '')
            price_m = re.match(r'^[\D]*([\d\.]+)[\D]*$', price_str)
            if not price_m:
                raise ValueError()
            price = float(price_m.group(1))
            
            return {
                "type": "item",
                "data": {
                    "item_name": parts[0],
                    "quantity": 1,
                    "unit": "式",
                    "price": -abs(price),
                    "total": -abs(price)
                }
            }
        except ValueError:
            return {"type": "error", "message": "値引きの金額は数値で入力してください。"}
            
    if len(parts) == 2 and "値引" not in parts[0]:
        try:
            qty_str = parts[-1]
            m = re.match(r'^([\d\.,]+)(.*)$', qty_str)
            if not m:
                raise ValueError()
                
            quantity = float(m.group(1).replace(',', ''))
            unit = m.group(2).strip()
            
            return {
                "type": "item",
                "data": {
                    "item_name": parts[0],
                    "quantity": quantity,
                    "unit": unit,
                    "price": None,
                    "total": None
                }
            }
        except ValueError:
            pass
            
    if len(parts) >= 3:
        try:
            price_str = parts[-1].replace(',', '')
            price_m = re.match(r'^[\D]*([\d\.]+)[\D]*$', price_str)
            if not price_m:
                raise ValueError()
            price = float(price_m.group(1))
            
            qty_str = parts[-2]
            m = re.match(r'^([\d\.,]+)(.*)$', qty_str)
            if not m:
                raise ValueError()
                
            quantity = float(m.group(1).replace(',', ''))
            unit = m.group(2).strip()
            
            item_name = " ".join(parts[:-2])
            
            if "値引" in item_name:
                price = -abs(price)
                
            return {
                "type": "item",
                "data": {
                    "item_name": item_name,
                    "quantity": quantity,
                    "unit": unit,
                    "price": price,
                    "total": quantity * price
                }
            }
        except ValueError:
            return {"type": "error", "message": "数量と単価は数値で入力してください。"}
    else:
        return {"type": "error", "message": "フォーマットが正しくありません。「品名 数量 単価」の形式で入力するか、「案件 〇〇邸」で案件を切り替えてください。"}
