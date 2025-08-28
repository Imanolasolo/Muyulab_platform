# db_setup.py
import sqlite3
import os
from utils.auth import hash_password

DB_PATH = "database/muyulab.db"

def init_db():
    # asegurar que existe la carpeta "database"
    os.makedirs("database", exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabla de KAMs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS kams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        telefono TEXT
    )
    """)

    # Tabla de instituciones educativas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS instituciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        direccion TEXT,
        ciudad TEXT,
        provincia TEXT
    )
    """)

    # Relación KAM ↔ Institución
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS kam_institucion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kam_id INTEGER,
        institucion_id INTEGER,
        FOREIGN KEY (kam_id) REFERENCES kams (id),
        FOREIGN KEY (institucion_id) REFERENCES instituciones (id)
    )
    """)

    # Tabla de contactos
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contactos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        cargo TEXT CHECK(cargo IN ('directivo','docente','DECE')),
        email TEXT NOT NULL,
        telefono TEXT,
        institucion_id INTEGER,
        FOREIGN KEY (institucion_id) REFERENCES instituciones (id)
    )
    """)

    # Tabla de mensajes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mensajes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT,
        cuerpo TEXT NOT NULL,
        tipo TEXT,
        fecha_envio_programada TEXT,
        enviado INTEGER DEFAULT 0
    )
    """)

    # Crear tabla users si no existe
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        rol TEXT NOT NULL
    )
    """)
    # Insertar usuario admin si no existe
    cursor.execute("SELECT * FROM users WHERE email = ?", ("admin@muyulab.com",))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users (nombre, email, password, rol) VALUES (?, ?, ?, ?)",
            ("Administrador", "admin@muyulab.com", hash_password("admin123"), "admin")
        )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada en database/muyulab.db")
