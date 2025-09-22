import streamlit as st
import sqlite3

DB_PATH = "database/muyulab.db"

def get_kam_email_settings(kam_email):
    """Obtiene la configuración de email de un KAM"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT email_usuario, email_password FROM kams WHERE email = ?", (kam_email,))
    result = cur.fetchone()
    conn.close()
    return result if result else (None, None)

def validate_email_credentials(email_user, email_pass):
    """Valida las credenciales de email probando la conexión"""
    import smtplib
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_user, email_pass)
        return True, "Credenciales válidas"
    except smtplib.SMTPAuthenticationError:
        return False, "Error de autenticación. Verifica tu email y contraseña de aplicación."
    except Exception as e:
        return False, f"Error de conexión: {str(e)}"

def show_email_config_instructions():
    """Muestra instrucciones para configurar email"""
    st.markdown("""
    ### 📧 Configuración de Email para KAMs
    
    **Para usar Gmail:**
    1. Activa la **verificación en 2 pasos** en tu cuenta Google
    2. Ve a [Contraseñas de aplicación](https://myaccount.google.com/apppasswords)
    3. Genera una nueva contraseña de aplicación para "Mail"
    4. Usa esa contraseña de 16 caracteres (no tu contraseña normal)
    
    **Para otros proveedores:**
    - **Outlook/Hotmail:** Usa tu email y contraseña normal (si tienes 2FA activado, genera una contraseña de aplicación)
    - **Yahoo:** Requiere contraseña de aplicación
    - **Empresariales:** Consulta con tu administrador de TI
    
    **Seguridad:**
    - Las credenciales se almacenan de forma segura en la base de datos
    - Solo tú puedes enviar emails desde tu cuenta
    - El administrador puede ayudarte a configurar o resetear tus credenciales
    """)
