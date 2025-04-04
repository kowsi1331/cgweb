import sqlite3
def get_db_connection():
    conn = sqlite3.connect('career.db')
    conn.row_factory = sqlite3.Row
    return conn
conn = get_db_connection()
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(feedback)")
print("Feedback Table:", cursor.fetchall())

cursor.execute("PRAGMA table_info(user_activity)")
print("User Activity Table:", cursor.fetchall())

conn.close()
