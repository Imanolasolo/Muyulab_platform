# app.py
import streamlit as st
import sqlite3
from db_setup import init_db
from utils.login import require_login
from utils.data_sync import auto_sync
from modules.dashboards.KAM_dashboard import show_kam_dashboard
from modules.dashboards.admin_dashboard import show_admin_dashboard

st.set_page_config(page_title="Muyu Lab", layout="wide")

# Inicializar BD primero
try:
    init_db()
    # Sincronización simplificada
    auto_sync()
except Exception as e:
    st.error(f"Error en inicialización: {e}")

DB_PATH = "database/muyulab.db"

def run_query(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    return cur

require_login()
user = st.session_state.get("user", {})

# Redirección automática para KAM
if user.get("rol", "").lower() == "kam":
    show_kam_dashboard()
    st.stop()

# Redirección automática para administradores
if user.get("rol", "").lower() in ["admin", "administrador"] or user.get("rol", "") == "":
    show_admin_dashboard()
    st.stop()

# Si llegamos aquí, es un rol no reconocido
st.title("Muyu Lab Contact - :red[Acceso Restringido]")
st.error("❌ No tienes permisos para acceder a esta aplicación.")
st.info("Contacta al administrador si crees que esto es un error.")

if st.button("Cerrar sesión"):
    st.session_state.clear()
    st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; font-size: 14px; margin-top: 50px;'>
        Proudly created by <strong>Muyu Education</strong> 2025
    </div>
    """, 
    unsafe_allow_html=True
)