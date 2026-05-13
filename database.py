
import sqlite3

conn = sqlite3.connect("bot.db", check_same_thread=False)
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS users (
    uid INTEGER PRIMARY KEY,
    gender TEXT,
    age INTEGER,
    language TEXT,
    premium INTEGER DEFAULT 0,
    reputation INTEGER DEFAULT 100
)
''')

conn.commit()
