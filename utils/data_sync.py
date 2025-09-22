import sqlite3
import os

DB_PATH = "database/muyulab.db"

# -------------------------------
# Funciones de utilidad
# -------------------------------

def get_connection():
    """Abrir conexión a SQLite"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def verificar_tabla_existe(nombre_tabla):
    """Verificar si una tabla existe en la base de datos"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?;
    """, (nombre_tabla,))
    existe = cur.fetchone() is not None
    conn.close()
    return existe

def verificar_columna_existe(nombre_tabla, nombre_columna):
    """Verificar si una columna existe en una tabla"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({nombre_tabla})")
    columnas = [fila[1] for fila in cur.fetchall()]
    conn.close()
    return nombre_columna in columnas

def ejecutar_migracion(nombre, sql):
    """Ejecutar un cambio en la base de datos"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        conn.close()
        print(f"✅ Migración completada: {nombre}")
        return True
    except Exception as e:
        print(f"⚠️ Error en migración {nombre}: {e}")
        return False

# -------------------------------
# Migraciones
# -------------------------------

def migrar_tabla_kam_institucion():
    """Crear tabla de relación KAM-Institución si no existe"""
    if not verificar_tabla_existe("kam_institucion"):
        sql = """
        CREATE TABLE kam_institucion (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kam_id INTEGER NOT NULL,
            institucion_id INTEGER NOT NULL,
            fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kam_id) REFERENCES kams (id) ON DELETE CASCADE,
            FOREIGN KEY (institucion_id) REFERENCES instituciones (id) ON DELETE CASCADE,
            UNIQUE(kam_id, institucion_id)
        )
        """
        return ejecutar_migracion("Tabla kam_institucion", sql)
    else:
        print("ℹ️ Tabla kam_institucion ya existe")
        return True

def migrar_campos_instituciones():
    """Agregar campos nuevos a la tabla instituciones"""
    campos_nuevos = [
        ("provincia", "TEXT"),
        ("pais", "TEXT"),
        ("direccion", "TEXT"),
        ("tipo_programa", "TEXT DEFAULT 'Muyu Lab'"),
        ("plan", "TEXT DEFAULT 'Pago'")
    ]
    
    for campo, tipo in campos_nuevos:
        if not verificar_columna_existe("instituciones", campo):
            sql = f"ALTER TABLE instituciones ADD COLUMN {campo} {tipo}"
            ejecutar_migracion(f"Campo {campo} en instituciones", sql)
        else:
            print(f"ℹ️ Campo {campo} ya existe en instituciones")

def migrar_campos_kams():
    """Agregar campos de email a la tabla kams"""
    campos_nuevos = [
        ("email_usuario", "TEXT"),
        ("email_password", "TEXT")
    ]
    
    for campo, tipo in campos_nuevos:
        if not verificar_columna_existe("kams", campo):
            sql = f"ALTER TABLE kams ADD COLUMN {campo} {tipo}"
            ejecutar_migracion(f"Campo {campo} en kams", sql)
        else:
            print(f"ℹ️ Campo {campo} ya existe en kams")

def ejecutar_todas_las_migraciones():
    """Ejecuta todas las migraciones pendientes"""
    print("🔄 Iniciando migraciones de base de datos...")
    
    migrar_tabla_kam_institucion()
    migrar_campos_instituciones()
    migrar_campos_kams()
    
    print("✅ Migraciones completadas")

# -------------------------------
# Sincronización
# -------------------------------

def auto_sync():
    """Función principal de sincronización"""
    try:
        print("🔄 Sincronización iniciada")
        
        if os.path.exists(DB_PATH):
            print("✅ Base de datos encontrada")
            ejecutar_todas_las_migraciones()
        else:
            print("⚠️ Base de datos no encontrada - se creará automáticamente")
            # Crea una BD vacía
            conn = get_connection()
            conn.close()
        
        print("✅ Sincronización completada")
        
    except Exception as e:
        print(f"⚠️ Error en sincronización: {e}")

# -------------------------------
# Funciones de compatibilidad
# -------------------------------

def get_current_version():
    return 4

def set_current_version(version):
    pass

def set_last_sync():
    pass

def sync_data():
    pass

# -------------------------------
# Ejecución de prueba
# -------------------------------
if __name__ == "__main__":
    auto_sync()
