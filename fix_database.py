import sqlite3
import os

DB_PATH = "database/muyulab.db"

def fix_database():
    """Agrega las columnas faltantes a la base de datos"""
    if not os.path.exists(DB_PATH):
        print("La base de datos no existe. Ejecuta la aplicación primero.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Verificar columnas existentes en la tabla kams
        cursor.execute("PRAGMA table_info(kams)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Columnas actuales en kams: {columns}")
        
        # Agregar columnas faltantes
        if "email_usuario" not in columns:
            cursor.execute("ALTER TABLE kams ADD COLUMN email_usuario TEXT")
            print("✅ Columna email_usuario agregada")
        else:
            print("ℹ️ Columna email_usuario ya existe")
            
        if "email_password" not in columns:
            cursor.execute("ALTER TABLE kams ADD COLUMN email_password TEXT")
            print("✅ Columna email_password agregada")
        else:
            print("ℹ️ Columna email_password ya existe")
        
        conn.commit()
        print("🎉 Base de datos actualizada correctamente")
        
    except Exception as e:
        print(f"❌ Error al actualizar la base de datos: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_database()
