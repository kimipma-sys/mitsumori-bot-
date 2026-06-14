import sqlite3
import os

DB_PATH = 'items.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
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
    conn.commit()
    conn.close()

def add_item(user_id, item_data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO items (user_id, item_name, quantity, price, total)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, item_data['item_name'], item_data['quantity'], item_data['price'], item_data['total']))
    conn.commit()
    conn.close()
    return True

def get_items(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT item_name, quantity, price, total FROM items
        WHERE user_id = ? ORDER BY id ASC
    ''', (user_id,))
    rows = c.fetchall()
    conn.close()
    
    items = []
    for row in rows:
        items.append({
            'item_name': row[0],
            'quantity': row[1],
            'price': row[2],
            'total': row[3]
        })
    return items

def clear_items(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM items WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
