import streamlit as st
import sqlite3
from datetime import date
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import quote

DB_PATH = "database/muyulab.db"

def run_query(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    return cur

def send_email(dest_email, subject, body):
    EMAIL_USER = st.secrets["EMAIL_USER"]
    EMAIL_PASS = st.secrets["EMAIL_PASS"]
    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = dest_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, dest_email, msg.as_string())
        return True
    except Exception as e:
        st.error(f"Error enviando email: {e}")
        return False

def show_kam_dashboard():
    # Explicación del proceso en el sidebar
    with st.sidebar.expander("¿Cómo funciona el Panel KAM?", expanded=False):
        st.markdown("""
        **Guía rápida Panel KAM:**
        - Visualiza las instituciones asignadas y sus datos principales.
        - Administra contactos vinculados a tus instituciones.
        - Envía mensajes de seguimiento por email y WhatsApp.
        - Consulta y borra el historial de mensajes enviados.
        - Usa el botón 'Cerrar sesión' para salir del panel.
        """)

    # Botón de cerrar sesión
    if st.sidebar.button("Cerrar sesión", key="logout_kam"):
        st.session_state.clear()
        st.rerun()

    menu = st.sidebar.radio("Navegación", ["Contactos", "Mensajes"])

    st.header("Panel KAM: :red[Seguimiento de Instituciones y Clientes]")

    # Ver instituciones y año de programa
    st.subheader(":blue[Instituciones asignadas]")
    instituciones = run_query("SELECT id, nombre, ciudad, anio_programa FROM instituciones").fetchall()
    if instituciones:
        for inst in instituciones:
            st.markdown(f"**{inst[1]}** ({inst[2]}) - {inst[3]}")
    else:
        st.info("No hay instituciones registradas.")

   

    # ---------------- Contactos CRUD ----------------
    if menu == "Contactos":
        with st.expander("Administrar Contactos"):
            st.subheader(":blue[Gestión de Contactos]")
            acciones_contacto = [
                "Registrar contacto", "Modificar contacto", "Borrar contacto", "Ver contactos", "Carga masiva"
            ]
            accion_contacto = st.selectbox("Selecciona una acción:", acciones_contacto)

            instituciones = run_query("SELECT id, nombre FROM instituciones").fetchall()
            institucion_dict = {nombre: iid for iid, nombre in instituciones}
            roles = run_query("SELECT nombre FROM roles").fetchall()
            roles_list = [r[0] for r in roles] if roles else []

            if accion_contacto == "Registrar contacto":
                institucion_nombre = st.selectbox("Institución", list(institucion_dict.keys())) if instituciones else None
                institucion_id = institucion_dict[institucion_nombre] if institucion_nombre else None
                nombre = st.text_input("Nombre y Apellido")
                cargo = st.selectbox("Cargo", roles_list)
                email = st.text_input("Email institucional")
                telefono = st.text_input("Teléfono celular, :red[número compatible con WhatsApp]")
                if st.button("Guardar Contacto"):
                    if institucion_id:
                        run_query("INSERT INTO contactos (nombre, cargo, email, telefono, institucion_id) VALUES (?, ?, ?, ?, ?)",
                                (nombre, cargo, email, telefono, institucion_id))
                        st.success("Contacto agregado correctamente")
                    else:
                        st.warning("Debes registrar al menos una institución antes de agregar contactos.")

            elif accion_contacto == "Ver contactos":
                st.write("### Lista de Contactos")
                contactos = run_query("SELECT nombre, cargo, email, telefono FROM contactos").fetchall()
                for c in contactos:
                    st.write(f"{c[0]} - {c[1]} | {c[2]} | {c[3]}")

            elif accion_contacto == "Modificar contacto":
                st.write("### Modificar Contacto")
                contactos = run_query("SELECT id, nombre, cargo, email, telefono, institucion_id FROM contactos").fetchall()
                if contactos:
                    contacto_dict = {f"{c[1]} - {c[2]} | {c[3]} | {c[4]}": c[0] for c in contactos}
                    contacto_sel = st.selectbox("Selecciona contacto", list(contacto_dict.keys()), key="mod_contacto_kam")
                    contacto_id = contacto_dict[contacto_sel]
                    contacto_data = run_query("SELECT nombre, cargo, email, telefono, institucion_id FROM contactos WHERE id = ?", (contacto_id,)).fetchone()
                    new_nombre = st.text_input("Nuevo nombre", value=contacto_data[0], key="edit_contacto_nombre_kam")
                    new_cargo = st.selectbox("Nuevo cargo", roles_list, index=roles_list.index(contacto_data[1]) if contacto_data[1] in roles_list else 0, key="edit_contacto_cargo_kam")
                    new_email = st.text_input("Nuevo email", value=contacto_data[2], key="edit_contacto_email_kam")
                    new_telefono = st.text_input("Nuevo teléfono", value=contacto_data[3], key="edit_contacto_tel_kam")
                    inst_names = list(institucion_dict.keys())
                    inst_ids = list(institucion_dict.values())
                    try:
                        inst_index = inst_ids.index(contacto_data[4])
                    except ValueError:
                        inst_index = 0
                    new_inst = st.selectbox("Nueva institución", inst_names, index=inst_index, key="edit_contacto_inst_kam")
                    new_inst_id = institucion_dict[new_inst]
                    if st.button("Guardar cambios contacto", key="guardar_cambios_contacto_kam"):
                        run_query("UPDATE contactos SET nombre = ?, cargo = ?, email = ?, telefono = ?, institucion_id = ? WHERE id = ?",
                                (new_nombre, new_cargo, new_email, new_telefono, new_inst_id, contacto_id))
                        st.success("Contacto modificado correctamente")
                        st.rerun()
                else:
                    st.info("No hay contactos registrados.")

            elif accion_contacto == "Borrar contacto":
                st.write("### Borrar Contacto")
                contactos = run_query("SELECT id, nombre, cargo, email, telefono FROM contactos").fetchall()
                if contactos:
                    contacto_dict = {f"{c[1]} - {c[2]} | {c[3]} | {c[4]}": c[0] for c in contactos}
                    contacto_sel = st.selectbox("Selecciona contacto", list(contacto_dict.keys()), key="del_contacto_kam")
                    contacto_id = contacto_dict[contacto_sel]
                    if st.button("Borrar contacto", key="borrar_contacto_kam"):
                        run_query("DELETE FROM contactos WHERE id = ?", (contacto_id,))
                        st.success("Contacto eliminado correctamente")
                        st.rerun()
                else:
                    st.info("No hay contactos registrados.")

            elif accion_contacto == "Carga masiva":
                st.write("### Carga masiva de contactos")
                csv_file = st.file_uploader("Subir archivo CSV de contactos", type=["csv"])
                if csv_file is not None:
                    import pandas as pd
                    df = pd.read_csv(csv_file)
                    required_cols = {"nombre", "cargo", "email", "telefono", "institucion"}
                    if required_cols.issubset(df.columns):
                        inst_map = {nombre: iid for iid, nombre in instituciones}
                        roles_set = set(roles_list)
                        success, fail = 0, 0
                        for _, row in df.iterrows():
                            nombre = row["nombre"]
                            cargo = row["cargo"]
                            email = row["email"]
                            telefono = row["telefono"]
                            institucion = row["institucion"]
                            institucion_id = inst_map.get(institucion)
                            if institucion_id and cargo in roles_set:
                                run_query("INSERT INTO contactos (nombre, cargo, email, telefono, institucion_id) VALUES (?, ?, ?, ?, ?)",
                                        (nombre, cargo, email, telefono, institucion_id))
                                success += 1
                            else:
                                fail += 1
                        st.success(f"Contactos cargados: {success}")
                        if fail:
                            st.warning(f"Contactos no cargados por error de rol o institución: {fail}")
                    else:
                        st.error(f"El CSV debe tener las columnas: {', '.join(required_cols)}")


    
    if menu == "Mensajes":
    # Enviar mensaje de seguimiento
        with st.expander("Enviar y gestionar mensajes"):
            st.subheader(":orange[Enviar mensaje de seguimiento]")
            tipo = st.selectbox("Tipo de mensaje", ["Seguimiento", "Recordatorio de agenda", "Entrega de informe", "Motivacional"])
            # Mensajes pregrabados filtrados por tipo
            mensajes_pre = run_query("SELECT id, titulo, cuerpo FROM mensajes WHERE tipo = ?", (tipo,)).fetchall()
            msg_pre_dict = {f"{m[1]}: {m[2][:30]}...": m for m in mensajes_pre} if mensajes_pre else {}
            msg_pre_sel = st.selectbox("Mensaje pregrabado (opcional)", ["(Escribir manualmente)"] + list(msg_pre_dict.keys()), key="msg_pre")
            pre_titulo = ""
            pre_cuerpo = ""
            if msg_pre_sel != "(Escribir manualmente)":
                pre_titulo = msg_pre_dict[msg_pre_sel][1]
                pre_cuerpo = msg_pre_dict[msg_pre_sel][2]

            destinatario_tipo = st.radio("Enviar a:", ["Institución", "Contacto"])
            if destinatario_tipo == "Institución":
                inst_options = {
                    f"{i[1]} ({i[2] if len(i) > 2 else ''}) - {i[3] if len(i) > 3 else ''}": i[0]
                    for i in instituciones
                }
                inst_sel = st.selectbox("Selecciona institución", list(inst_options.keys())) if instituciones else None
                inst_id = inst_options[inst_sel] if inst_sel else None
                contactos_inst = run_query("SELECT id, nombre, cargo, email FROM contactos WHERE institucion_id = ?", (inst_id,)).fetchall() if inst_id else []
                if contactos_inst:
                    contacto_dict = {f"{c[1]} - {c[2]} | {c[3]}": c[0] for c in contactos_inst}
                    contacto_sel = st.selectbox("Selecciona contacto de la institución", list(contacto_dict.keys()), key="cont_inst")
                    contacto_id = contacto_dict[contacto_sel]
                else:
                    contacto_id = None
                    st.info("No hay contactos registrados en esta institución.")
                titulo = st.text_input("Título", value=pre_titulo, key="titulo_inst")
                cuerpo = st.text_area("Cuerpo del mensaje", value=pre_cuerpo, key="cuerpo_inst")
                fecha_envio = st.date_input("Fecha de envío", value=date.today(), key="fecha_inst")
                if st.button("Enviar mensaje a contacto de institución") and contacto_id and cuerpo:
                    run_query("INSERT INTO mensajes (titulo, cuerpo, tipo, fecha_envio_programada) VALUES (?, ?, ?, ?)",
                            (titulo, cuerpo, tipo, str(fecha_envio)))
                    # Obtener email del contacto
                    contacto_email = run_query("SELECT email FROM contactos WHERE id = ?", (contacto_id,)).fetchone()
                    if contacto_email:
                        if send_email(contacto_email[0], titulo, cuerpo):
                            st.success("Mensaje programado y email enviado al contacto seleccionado de la institución.")
                        else:
                            st.warning("Mensaje programado, pero el email no pudo ser enviado.")
                    else:
                        st.warning("Mensaje programado, pero no se encontró el email del contacto.")
                # Botón para enviar por WhatsApp
                contacto_tel = run_query("SELECT telefono FROM contactos WHERE id = ?", (contacto_id,)).fetchone() if contacto_id else None
                if contacto_tel and contacto_tel[0]:
                    telefono_wa = contacto_tel[0].replace("+", "").replace(" ", "")
                    if telefono_wa.startswith("0"):
                        telefono_wa = "593" + telefono_wa[1:]
                    whatsapp_text = f"Asunto: {titulo}\nCuerpo: {cuerpo}"
                    whatsapp_url = f"https://wa.me/{telefono_wa}?text={quote(whatsapp_text)}"
                    st.markdown(f"[Enviar por WhatsApp](<{whatsapp_url}>)", unsafe_allow_html=True)
                else:
                    st.warning("No se encontró un número de teléfono válido para el contacto seleccionado.")
            else:
                contactos = run_query("SELECT c.id, c.nombre, c.cargo, c.email, i.nombre FROM contactos c LEFT JOIN instituciones i ON c.institucion_id = i.id").fetchall()
                cont_options = {f"{c[1]} ({c[2]}) - {c[3]} | {c[4]}": c[0] for c in contactos}
                cont_sel = st.selectbox("Selecciona contacto", list(cont_options.keys())) if contactos else None
                cont_id = cont_options[cont_sel] if cont_sel else None
                titulo = st.text_input("Título", value=pre_titulo, key="titulo_cont")
                cuerpo = st.text_area("Cuerpo del mensaje", value=pre_cuerpo, key="cuerpo_cont")
                fecha_envio = st.date_input("Fecha de envío", value=date.today(), key="fecha_cont")
                if st.button("Enviar mensaje a contacto") and cont_id and cuerpo:
                    run_query("INSERT INTO mensajes (titulo, cuerpo, tipo, fecha_envio_programada) VALUES (?, ?, ?, ?)",
                            (titulo, cuerpo, tipo, str(fecha_envio)))
                    contacto_email = run_query("SELECT email FROM contactos WHERE id = ?", (cont_id,)).fetchone()
                    if contacto_email:
                        if send_email(contacto_email[0], titulo, cuerpo):
                            st.success("Mensaje programado y email enviado al contacto seleccionado.")
                        else:
                            st.warning("Mensaje programado, pero el email no pudo ser enviado.")
                    else:
                        st.warning("Mensaje programado, pero no se encontró el email del contacto.")
                # Botón para enviar por WhatsApp
                contacto_tel2 = run_query("SELECT telefono FROM contactos WHERE id = ?", (cont_id,)).fetchone() if cont_id else None
                if contacto_tel2 and contacto_tel2[0]:
                    telefono_wa2 = contacto_tel2[0].replace("+", "").replace(" ", "")
                    if telefono_wa2.startswith("0"):
                        telefono_wa2 = "593" + telefono_wa2[1:]
                    whatsapp_text2 = f"Asunto: {titulo}\nCuerpo: {cuerpo}"
                    whatsapp_url2 = f"https://wa.me/{telefono_wa2}?text={quote(whatsapp_text2)}"
                    st.markdown(f"[Enviar por WhatsApp](<{whatsapp_url2}>)", unsafe_allow_html=True)
                else:
                    st.warning("No se encontró un número de teléfono válido para el contacto seleccionado.")

            # Historial de mensajes
            st.subheader("Historial de mensajes enviados")
            st.markdown(":red[Esta acción eliminará todos los mensajes del historial.]")
            borrar = st.button("🗑️ Borrar historial de mensajes", key="borrar_historial")
            if borrar:
                run_query("DELETE FROM mensajes")
                st.success("Historial de mensajes borrado.")
                st.rerun()
            mensajes = run_query("SELECT titulo, tipo, fecha_envio_programada, enviado FROM mensajes ORDER BY fecha_envio_programada DESC").fetchall()
            for m in mensajes:
                status = "✅ Enviado" if m[3] else "⏳ Pendiente"
                st.write(f"{m[0]} | {m[1]} | {m[2]} | {status}")
