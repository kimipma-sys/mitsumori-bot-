import sqlite3
import os

DB_PATH = 'items.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 見積り項目のテーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            quantity REAL NOT NULL,
            price REAL NOT NULL,
            total REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    try:
        c.execute('ALTER TABLE items ADD COLUMN unit TEXT DEFAULT ""')
    except sqlite3.OperationalError:
        pass # カラムが既に存在する場合は無視
        
    # 単価辞書のテーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            item_name TEXT NOT NULL,
            price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, item_name)
        )
    ''')
    
    # エビデンス(画像)のテーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            filepath TEXT NOT NULL,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def add_item(user_id, item_data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    unit = item_data.get('unit', '')
    c.execute('''
        INSERT INTO items (user_id, item_name, quantity, unit, price, total)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, item_data['item_name'], item_data['quantity'], unit, item_data['price'], item_data['total']))
    conn.commit()
    conn.close()
    return True

def get_items(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT id, item_name, quantity, price, total, unit FROM items
        WHERE user_id = ? ORDER BY id ASC
    ''', (user_id,))
    rows = c.fetchall()
    conn.close()
    
    items = []
    for row in rows:
        items.append({
            'db_id': row[0],
            'item_name': row[1],
            'quantity': row[2],
            'price': row[3],
            'total': row[4],
            'unit': row[5] if len(row) > 5 and row[5] else ''
        })
    return items

def delete_item_by_index(user_id, index):
    """指定された順番（1始まり）のアイテムを削除する"""
    items = get_items(user_id)
    if 0 <= index - 1 < len(items):
        item_id = items[index - 1]['db_id']
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('DELETE FROM items WHERE id = ?', (item_id,))
        conn.commit()
        conn.close()
        return items[index - 1]
    return None

def clear_items(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM items WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def set_price(user_id, item_name, price):
    """単価を辞書に登録（上書き）する"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO prices (user_id, item_name, price)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, item_name) DO UPDATE SET price=excluded.price
    ''', (user_id, item_name, price))
    conn.commit()
    conn.close()

def get_price(user_id, item_name):
    """辞書から単価を取得する"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT price FROM prices WHERE user_id = ? AND item_name = ?
    ''', (user_id, item_name))
    row = c.fetchone()
    conn.close()
    if row:
        return row[0]
    return None

def get_all_prices(user_id):
    """登録されているすべての単価を取得する"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT item_name, price FROM prices WHERE user_id = ? ORDER BY item_name ASC
    ''', (user_id,))
    rows = c.fetchall()
    conn.close()
    
    prices = []
    for row in rows:
        prices.append({
            'item_name': row[0],
            'price': row[1]
        })
    return prices

# --- エビデンス画像用の関数 ---

def add_evidence_image(user_id, filepath):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO evidence (user_id, filepath) VALUES (?, ?)', (user_id, filepath))
    conn.commit()
    conn.close()

def get_pending_evidence(user_id):
    """タイトル待ち（titleがNULL）の最新のエビデンスを取得"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, filepath FROM evidence WHERE user_id = ? AND title IS NULL ORDER BY id DESC LIMIT 1', (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {'id': row[0], 'filepath': row[1]}
    return None

def set_evidence_title(evidence_id, title):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE evidence SET title = ? WHERE id = ?', (title, evidence_id))
    conn.commit()
    conn.close()

def get_all_evidence(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT filepath, title FROM evidence WHERE user_id = ? AND title IS NOT NULL ORDER BY id ASC', (user_id,))
    rows = c.fetchall()
    conn.close()
    
    evidence_list = []
    for row in rows:
        evidence_list.append({
            'filepath': row[0],
            'title': row[1]
        })
    return evidence_list

def clear_evidence(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM evidence WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
