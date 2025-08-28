import sqlite3
from utils.auth import hash_password, verify_password

DB_PATH = "database/muyulab.db"

def create_user(nombre, email, password, rol):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    hashed = hash_password(password)
    cur.execute("INSERT INTO users (nombre, email, password, rol) VALUES (?, ?, ?, ?)", (nombre, email, hashed, rol))
    conn.commit()
    conn.close()

def authenticate_user(email, password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, nombre, email, password, rol FROM users WHERE email = ?", (email,))
    user = cur.fetchone()
    conn.close()
    if user and verify_password(password, user[3]):
        return {"id": user[0], "nombre": user[1], "email": user[2], "rol": user[4]}
    return None
