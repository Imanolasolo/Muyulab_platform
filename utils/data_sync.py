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

def auto_sync():
    """Verifica si necesita sincronizar y lo hace automáticamente"""
    if os.path.exists(SYNC_DATA_FILE):
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(SYNC_DATA_FILE))
        last_sync = get_last_sync()
        
        if last_sync is None or file_mod_time > datetime.fromisoformat(last_sync):
            print("Detectados cambios en datos de sincronización. Sincronizando...")
            sync_data()
