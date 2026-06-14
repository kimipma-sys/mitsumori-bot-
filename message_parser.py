import re

def parse_message(text: str):
    """
    LINEからのメッセージを解析します。
    "見積書発行" などのコマンドか、"品名 数量 単価" のデータ行を判定します。
    """
    text = text.strip()
    
    if text == "見積書発行":
        return {"type": "command", "command": "issue_estimate"}
    
    # 全角スペースまたは半角スペースで分割
    parts = re.split(r'[\s　]+', text)
    
    if len(parts) >= 3:
        # 末尾の2つを「数量」「単価」、残りを「品名」として扱う
        try:
            price = float(parts[-1].replace(',', ''))
            quantity = float(parts[-2].replace(',', ''))
            item_name = " ".join(parts[:-2])
            return {
                "type": "item",
                "data": {
                    "item_name": item_name,
                    "quantity": quantity,
                    "price": price,
                    "total": quantity * price
                }
            }
        except ValueError:
            return {"type": "error", "message": "数量と単価は数値で入力してください。"}
    else:
        return {"type": "error", "message": "フォーマットが正しくありません。「品名 数量 単価」の形式（スペース区切り）で入力してください。"}
