from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side
import datetime
import os

def generate_estimate_excel(user_id, items):
    wb = Workbook()
    ws = wb.active
    ws.title = "見積書"
    
    # Header
    ws['A1'] = "御見積書"
    ws['A1'].font = Font(size=20, bold=True)
    ws.merge_cells('A1:E1')
    ws['A1'].alignment = Alignment(horizontal='center')
    
    # Date
    ws['E2'] = datetime.datetime.now().strftime("%Y年%m月%d日")
    ws['E2'].alignment = Alignment(horizontal='right')
    
    # Total Calculation
    total_amount = sum(item['total'] for item in items)
    tax = int(total_amount * 0.1)
    grand_total = total_amount + tax
    
    ws['A4'] = f"御見積金額: ¥{grand_total:,} (税込)"
    ws['A4'].font = Font(size=14, bold=True)
    ws.merge_cells('A4:D4')
    
    # Table Headers
    headers = ["No.", "品名・工事名", "数量", "単価", "金額"]
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=7, column=col)
        cell.value = header
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal='center')
        
    # Table Content
    row_num = 8
    for i, item in enumerate(items, 1):
        ws.cell(row=row_num, column=1, value=i)
        ws.cell(row=row_num, column=2, value=item['item_name'])
        ws.cell(row=row_num, column=3, value=item['quantity'])
        ws.cell(row=row_num, column=4, value=f"¥{int(item['price']):,}")
        ws.cell(row=row_num, column=5, value=f"¥{int(item['total']):,}")
        row_num += 1
        
    # Subtotals
    ws.cell(row=row_num+1, column=4, value="小計").font = Font(bold=True)
    ws.cell(row=row_num+1, column=5, value=f"¥{int(total_amount):,}")
    
    ws.cell(row=row_num+2, column=4, value="消費税(10%)").font = Font(bold=True)
    ws.cell(row=row_num+2, column=5, value=f"¥{int(tax):,}")
    
    ws.cell(row=row_num+3, column=4, value="合計").font = Font(bold=True)
    ws.cell(row=row_num+3, column=5, value=f"¥{int(grand_total):,}")
    
    # Adjust column widths
    ws.column_dimensions['A'].width = 5
    ws.column_dimensions['B'].width = 35
    ws.column_dimensions['C'].width = 10
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 15
    
    # Ensure static directory exists
    os.makedirs('static', exist_ok=True)
    
    filename = f"estimate_{user_id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    filepath = os.path.join('static', filename)
    wb.save(filepath)
    
    return filename
