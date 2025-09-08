import streamlit as st
import sqlite3
from datetime import date

DB_PATH = "database/muyulab.db"

def run_query(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    return cur

def show_kam_dashboard():
    # Botón de cerrar sesión
    if st.sidebar.button("Cerrar sesión", key="logout_kam"):
        st.session_state.clear()
        st.rerun()

    st.header("Panel KAM: Seguimiento de Instituciones y Clientes")

    # Ver instituciones y año de programa
    st.subheader("Instituciones asignadas")
    instituciones = run_query("SELECT id, nombre, ciudad, anio_programa FROM instituciones").fetchall()
    if instituciones:
        for inst in instituciones:
            st.markdown(f"**{inst[1]}** ({inst[2]}) - {inst[3]}")
    else:
        st.info("No hay instituciones registradas.")

    # Ver contactos (clientes)
    st.subheader("Contactos registrados")
    contactos = run_query("SELECT c.id, c.nombre, c.cargo, c.email, i.nombre FROM contactos c LEFT JOIN instituciones i ON c.institucion_id = i.id").fetchall()
    if contactos:
        for c in contactos:
            st.markdown(f"**{c[1]}** - {c[2]} | {c[3]} | Institución: {c[4]}")
    else:
        st.info("No hay contactos registrados.")

    # Enviar mensaje de seguimiento
    st.subheader("Enviar mensaje de seguimiento")
    tipo = st.selectbox("Tipo de mensaje", ["Seguimiento", "Recordatorio de agenda", "Entrega de informe", "Motivacional"])
    destinatario_tipo = st.radio("Enviar a:", ["Institución", "Contacto"])
    if destinatario_tipo == "Institución":
        inst_options = {f"{i[1]} ({i[2]}) - {i[3]}": i[0] for i in instituciones}
        inst_sel = st.selectbox("Selecciona institución", list(inst_options.keys())) if instituciones else None
        inst_id = inst_options[inst_sel] if inst_sel else None
        titulo = st.text_input("Título", key="titulo_inst")
        cuerpo = st.text_area("Cuerpo del mensaje", key="cuerpo_inst")
        fecha_envio = st.date_input("Fecha de envío", value=date.today(), key="fecha_inst")
        if st.button("Enviar mensaje a institución") and inst_id and cuerpo:
            run_query("INSERT INTO mensajes (titulo, cuerpo, tipo, fecha_envio_programada) VALUES (?, ?, ?, ?)",
                      (titulo, cuerpo, tipo, str(fecha_envio)))
            st.success("Mensaje programado para la institución seleccionada.")
    else:
        cont_options = {f"{c[1]} ({c[2]}) - {c[3]} | {c[4]}": c[0] for c in contactos}
        cont_sel = st.selectbox("Selecciona contacto", list(cont_options.keys())) if contactos else None
        cont_id = cont_options[cont_sel] if cont_sel else None
        titulo = st.text_input("Título", key="titulo_cont")
        cuerpo = st.text_area("Cuerpo del mensaje", key="cuerpo_cont")
        fecha_envio = st.date_input("Fecha de envío", value=date.today(), key="fecha_cont")
        if st.button("Enviar mensaje a contacto") and cont_id and cuerpo:
            run_query("INSERT INTO mensajes (titulo, cuerpo, tipo, fecha_envio_programada) VALUES (?, ?, ?, ?)",
                      (titulo, cuerpo, tipo, str(fecha_envio)))
            st.success("Mensaje programado para el contacto seleccionado.")

    # Historial de mensajes
    st.subheader("Historial de mensajes enviados")
    mensajes = run_query("SELECT titulo, tipo, fecha_envio_programada, enviado FROM mensajes ORDER BY fecha_envio_programada DESC").fetchall()
    for m in mensajes:
        status = "✅ Enviado" if m[3] else "⏳ Pendiente"
        st.write(f"{m[0]} | {m[1]} | {m[2]} | {status}")
