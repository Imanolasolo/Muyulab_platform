# db_setup.py
import sqlite3
import os
import json
from datetime import datetime
from utils.auth import hash_password

DB_PATH = "database/muyulab.db"
MIGRATIONS_PATH = "database/migrations"
SCHEMA_VERSION_FILE = "database/schema_version.json"

def get_current_schema_version():
    """Obtiene la versión actual del esquema de la BD"""
    if os.path.exists(SCHEMA_VERSION_FILE):
        with open(SCHEMA_VERSION_FILE, 'r') as f:
            data = json.load(f)
            return data.get('version', 0)
    return 0

def set_schema_version(version):
    """Establece la versión del esquema"""
    os.makedirs("database", exist_ok=True)
    with open(SCHEMA_VERSION_FILE, 'w') as f:
        json.dump({
            'version': version,
            'updated_at': datetime.now().isoformat()
        }, f, indent=2)

def run_migrations():
    """Ejecuta migraciones pendientes"""
    current_version = get_current_schema_version()
    
    # Define las migraciones disponibles
    migrations = [
        # Migración 1: Datos básicos iniciales
        {
            'version': 1,
            'description': 'Datos iniciales del sistema',
            'sql': [
                "INSERT OR IGNORE INTO roles (nombre) VALUES ('Directivo')",
                "INSERT OR IGNORE INTO roles (nombre) VALUES ('Contraparte')",
                "INSERT OR IGNORE INTO roles (nombre) VALUES ('Líder pedagógico')",
                "INSERT OR IGNORE INTO roles (nombre) VALUES ('Docente acompañado')",
                "INSERT OR IGNORE INTO roles (nombre) VALUES ('Usuario Muyu App')",
            ]
        },
        # Migración 2: Datos de ejemplo (puedes agregar más aquí)
        {
            'version': 2,
            'description': 'Datos de ejemplo actualizados',
            'sql': [
                # Aquí puedes agregar nuevos registros que quieras sincronizar
            ]
        }
    ]
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for migration in migrations:
        if migration['version'] > current_version:
            print(f"Ejecutando migración {migration['version']}: {migration['description']}")
            try:
                for sql in migration['sql']:
                    cursor.execute(sql)
                conn.commit()
                set_schema_version(migration['version'])
                print(f"Migración {migration['version']} completada")
            except Exception as e:
                print(f"Error en migración {migration['version']}: {e}")
                conn.rollback()
                break
    
    conn.close()

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
        provincia TEXT,
        anio_programa INTEGER  -- Nuevo campo para el año del programa
    )
    """)

    # Verificar si la columna anio_programa existe, si no, agregarla (para migraciones)
    cursor.execute("PRAGMA table_info(instituciones)")
    columns = [col[1] for col in cursor.fetchall()]
    if "anio_programa" not in columns:
        cursor.execute("ALTER TABLE instituciones ADD COLUMN anio_programa INTEGER")

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
        cargo TEXT NOT NULL,
        email TEXT NOT NULL,
        telefono TEXT,
        institucion_id INTEGER,
        FOREIGN KEY (institucion_id) REFERENCES instituciones (id)
    )
    """)

    # Migración robusta: eliminar CHECK constraint en contactos.cargo si existe
    cursor.execute("PRAGMA table_info(contactos)")
    contacto_cols = cursor.fetchall()
    # Buscar si la tabla tiene el CHECK constraint (por definición de la columna cargo)
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='contactos'")
    contactos_sql = cursor.fetchone()
    if contactos_sql and "CHECK" in contactos_sql[0]:
        cursor.execute("ALTER TABLE contactos RENAME TO contactos_old")
        cursor.execute("""
        CREATE TABLE contactos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            cargo TEXT NOT NULL,
            email TEXT NOT NULL,
            telefono TEXT,
            institucion_id INTEGER,
            FOREIGN KEY (institucion_id) REFERENCES instituciones (id)
        )
        """)
        cursor.execute("INSERT INTO contactos (id, nombre, cargo, email, telefono, institucion_id) SELECT id, nombre, cargo, email, telefono, institucion_id FROM contactos_old")
        cursor.execute("DROP TABLE contactos_old")

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

    # Tabla de roles
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT UNIQUE NOT NULL
    )
    """)
    # Insertar roles por defecto si no existen
    default_roles = [
        "Directivo",
        "Contraparte",
        "Líder pedagógico",
        "Docente acompañado",
        "Usuario Muyu App"
    ]
    for role in default_roles:
        cursor.execute("INSERT OR IGNORE INTO roles (nombre) VALUES (?)", (role,))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada en database/muyulab.db")
