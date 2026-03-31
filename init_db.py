import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect("parkir.db")
c = conn.cursor()

# ===== TABLE USERS =====
c.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")

password = generate_password_hash("jawa")
c.execute(
    "INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)",
    ("admin", password)
)

# ===== TABLE PARKIR =====
c.execute("""
CREATE TABLE IF NOT EXISTS parkir (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plat TEXT NOT NULL,
    jenis TEXT NOT NULL,
    waktu_masuk TEXT NOT NULL,
    waktu_keluar TEXT,
    kode_bayar TEXT
)
""")

conn.commit()
conn.close()

print("DB OK - Semua tabel berhasil dibuat!")