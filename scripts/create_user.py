from datetime import datetime, timezone
import sqlite3
from werkzeug.security import generate_password_hash

email = input('Email: ').strip().lower()
name = input('Name: ').strip()
password = input('Password: ').strip()

pw_hash = generate_password_hash(password)
now = datetime.now(timezone.utc).isoformat()

conn = sqlite3.connect('dlo.db')
cur = conn.cursor()

cur.execute(
    """
    INSERT INTO users (email, name, password_hash, created_at)
    VALUES (?, ?, ?, ?)
    """,
    (email, name, pw_hash, now),
)
conn.commit()
print('User created:', email)

