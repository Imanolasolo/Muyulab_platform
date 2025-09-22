import sqlite3
import json
import os
from datetime import datetime

DB_PATH = "database/muyulab.db"
SYNC_DATA_FILE = "database/sync_data.json"
LAST_SYNC_FILE = "database/last_sync.json"

def get_last_sync():
    """Obtiene la fecha de la última sincronización"""
    if os.path.exists(LAST_SYNC_FILE):
        with open(LAST_SYNC_FILE, 'r') as f:
            data = json.load(f)
            return data.get('last_sync')
    return None

def set_last_sync():
    """Marca la fecha actual como última sincronización"""
    os.makedirs("database", exist_ok=True)
    with open(LAST_SYNC_FILE, 'w') as f:
        json.dump({
            'last_sync': datetime.now().isoformat()
        }, f, indent=2)

def sync_data():
    """Sincroniza datos desde el archivo JSON"""
    if not os.path.exists(SYNC_DATA_FILE):
        print("No hay archivo de sincronización disponible")
        return
    
    with open(SYNC_DATA_FILE, 'r', encoding='utf-8') as f:
        sync_data = json.load(f)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Sincronizar roles
        if 'roles' in sync_data:
            for role in sync_data['roles']:
                cursor.execute("INSERT OR IGNORE INTO roles (nombre) VALUES (?)", (role['nombre'],))
        
        # Sincronizar instituciones
        if 'instituciones' in sync_data:
            for inst in sync_data['instituciones']:
                cursor.execute("""
                    INSERT OR IGNORE INTO instituciones (nombre, ciudad, anio_programa) 
                    VALUES (?, ?, ?)
                """, (inst['nombre'], inst['ciudad'], inst['anio_programa']))
        
        # Sincronizar mensajes plantilla
        if 'mensajes_plantilla' in sync_data:
            for msg in sync_data['mensajes_plantilla']:
                cursor.execute("""
                    INSERT OR IGNORE INTO mensajes (titulo, cuerpo, tipo, fecha_envio_programada) 
                    VALUES (?, ?, ?, ?)
                """, (msg['titulo'], msg['cuerpo'], msg['tipo'], datetime.now().date().isoformat()))
        
        conn.commit()
        set_last_sync()
        print("Sincronización completada exitosamente")
        
    except Exception as e:
        print(f"Error durante la sincronización: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_table_columns(table_name):
    """Obtiene las columnas existentes de una tabla"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cur.fetchall()]  # row[1] es el nombre de la columna
    conn.close()
    return columns

def column_exists(table_name, column_name):
    """Verifica si una columna existe en una tabla"""
    columns = get_table_columns(table_name)
    return column_name in columns

def run_migration_3():
    """Migración 3: Agregar campos País, Dirección, Tipo de programa y Plan a instituciones"""
    print("Ejecutando migración 3: Agregar campos País, Dirección, Tipo de programa y Plan a instituciones")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # Verificar y agregar cada columna solo si no existe
        columns_to_add = [
            ("pais", "TEXT"),
            ("direccion", "TEXT"), 
            ("tipo_programa", "TEXT DEFAULT 'Muyu Lab'"),
            ("plan", "TEXT DEFAULT 'Pago'")
        ]
        
        for column_name, column_definition in columns_to_add:
            if not column_exists("instituciones", column_name):
                cur.execute(f"ALTER TABLE instituciones ADD COLUMN {column_name} {column_definition}")
                print(f"✅ Columna '{column_name}' agregada a instituciones")
            else:
                print(f"ℹ️ Columna '{column_name}' ya existe en instituciones")
        
        conn.commit()
        print("✅ Migración 3 completada exitosamente")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error en migración 3: {e}")
        raise e
    finally:
        conn.close()

def auto_sync():
    """Sincronización automática de datos al iniciar la aplicación"""
    try:
        current_version = get_current_version()
        print(f"Versión actual de la base de datos: {current_version}")
        
        # Lista de migraciones disponibles
        migrations = {
            1: run_migration_1,
            2: run_migration_2, 
            3: run_migration_3,
            4: run_migration_4
        }
        
        # Ejecutar migraciones pendientes
        for version, migration_func in migrations.items():
            if current_version < version:
                try:
                    migration_func()
                    set_current_version(version)
                    print(f"✅ Migración {version} aplicada correctamente")
                except Exception as e:
                    print(f"❌ Error en migración {version}: {e}")
                    # No detener el proceso, continuar con la aplicación
                    break
        
        print("🔄 Sincronización automática completada")
        
    except Exception as e:
        print(f"⚠️ Error en sincronización automática: {e}")
        # No lanzar excepción para no detener la aplicación
