import sqlite3

db_path = "insurance_bills.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
table_name = "bills"
ID_COLUMN = "bill_id"
TAG_COLUMN = "keyword_tags"

cursor.execute(f"""
    UPDATE {table_name}
    SET {TAG_COLUMN} = ?
    WHERE bill_id = ?
""", ("['reinsurance']",1765431))

conn.commit()
conn.close()
