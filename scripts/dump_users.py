import sqlite3

conn = sqlite3.connect('dlo.db')
cur = conn.cursor()

print('tables:', [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")])
print('users columns:', cur.execute('PRAGMA table_info(users)').fetchall())
try:
    rows = cur.execute('SELECT id, email, name, password_hash FROM users').fetchall()
except Exception as e:
    print('query error:', e)
    rows = []
print('users rows:', rows)

