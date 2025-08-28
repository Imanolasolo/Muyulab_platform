# app.py
import streamlit as st
import sqlite3
from db_setup import init_db
from utils.login import require_login

st.set_page_config(page_title="Muyu Lab", layout="wide")

# Inicializar BD
init_db()

DB_PATH = "database/muyulab.db"

def run_query(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    return cur

require_login()
user = st.session_state.get("user", {})

st.set_page_config(page_title="Muyu Lab CRM", layout="wide")
st.title(f"Muyu Lab - Gestión de Relaciones ({user.get('rol','')})")

# Opcional: Mostrar botón de logout
if st.sidebar.button("Cerrar sesión"):
    st.session_state.clear()
    st.rerun()

# Puedes proteger secciones por rol, por ejemplo:
if user.get("rol") == "cliente":
    st.info("Acceso solo a mensajes.")
    menu = "Mensajes"
else:
    menu = st.sidebar.radio("Navegación", ["KAMs", "Instituciones", "Contactos", "Mensajes"])

# ---------------- KAMs ----------------
if menu == "KAMs":
    st.subheader("Gestión de KAMs")

    with st.form("kam_form"):
        nombre = st.text_input("Nombre completo")
        email = st.text_input("Email")
        telefono = st.text_input("Teléfono")
        submitted = st.form_submit_button("Guardar")
        if submitted and nombre and email:
            run_query("INSERT INTO kams (nombre, email, telefono) VALUES (?, ?, ?)", (nombre, email, telefono))
            st.success("KAM agregado correctamente")

    st.write("### Lista de KAMs")
    kams = run_query("SELECT id, nombre, email, telefono FROM kams").fetchall()
    for k in kams:
        st.write(f"{k[1]} | {k[2]} | {k[3]}")

# ---------------- Instituciones ----------------
elif menu == "Instituciones":
    st.subheader("Gestión de Instituciones")

    with st.form("inst_form"):
        nombre = st.text_input("Nombre de institución")
        direccion = st.text_input("Dirección")
        ciudad = st.text_input("Ciudad")
        provincia = st.text_input("Provincia")
        submitted = st.form_submit_button("Guardar")
        if submitted and nombre:
            run_query("INSERT INTO instituciones (nombre, direccion, ciudad, provincia) VALUES (?, ?, ?, ?)",
                      (nombre, direccion, ciudad, provincia))
            st.success("Institución agregada correctamente")

    st.write("### Lista de Instituciones")
    insts = run_query("SELECT id, nombre, ciudad, provincia FROM instituciones").fetchall()
    for i in insts:
        st.write(f"{i[1]} ({i[2]}, {i[3]})")

# ---------------- Contactos ----------------
elif menu == "Contactos":
    st.subheader("Gestión de Contactos")

    institucion_id = st.number_input("ID Institución", min_value=1, step=1)
    nombre = st.text_input("Nombre y Apellido")
    cargo = st.selectbox("Cargo", ["directivo", "docente", "DECE"])
    email = st.text_input("Email institucional")
    telefono = st.text_input("Teléfono celular")
    if st.button("Guardar Contacto"):
        run_query("INSERT INTO contactos (nombre, cargo, email, telefono, institucion_id) VALUES (?, ?, ?, ?, ?)",
                  (nombre, cargo, email, telefono, institucion_id))
        st.success("Contacto agregado correctamente")

    st.write("### Lista de Contactos")
    contactos = run_query("SELECT nombre, cargo, email, telefono FROM contactos").fetchall()
    for c in contactos:
        st.write(f"{c[0]} - {c[1]} | {c[2]} | {c[3]}")

# ---------------- Mensajes ----------------
elif menu == "Mensajes":
    st.subheader("Registro de Mensajes")

    with st.form("msg_form"):
        titulo = st.text_input("Título")
        cuerpo = st.text_area("Cuerpo del mensaje")
        tipo = st.selectbox("Tipo", ["recordatorio", "motivacional", "aviso"])
        fecha = st.date_input("Fecha programada")
        submitted = st.form_submit_button("Guardar")
        if submitted and cuerpo:
            run_query("INSERT INTO mensajes (titulo, cuerpo, tipo, fecha_envio_programada) VALUES (?, ?, ?, ?)",
                      (titulo, cuerpo, tipo, str(fecha)))
            st.success("Mensaje guardado correctamente")

    st.write("### Lista de Mensajes")
    mensajes = run_query("SELECT titulo, tipo, fecha_envio_programada, enviado FROM mensajes").fetchall()
    for m in mensajes:
        status = "✅ Enviado" if m[3] else "⏳ Pendiente"
        st.write(f"{m[0]} | {m[1]} | {m[2]} | {status}")
