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
                nombre = st.text_input("Nombre")
                apellidos = st.text_input("Apellidos")
                cargo = st.selectbox("Cargo", roles_list)
                email = st.text_input("Email institucional")
                telefono = st.text_input("Teléfono celular, :red[número compatible con WhatsApp]")
                if st.button("Guardar Contacto"):
                    if institucion_id:
                        run_query("INSERT INTO contactos (nombre, apellidos, cargo, email, telefono, institucion_id) VALUES (?, ?, ?, ?, ?, ?)",
                                (nombre, apellidos, cargo, email, telefono, institucion_id))
                        st.success("Contacto agregado correctamente")
                    else:
                        st.warning("Debes registrar al menos una institución antes de agregar contactos.")

            elif accion_contacto == "Ver contactos":
                st.write("### Lista de Contactos")
                contactos = run_query("SELECT nombre, apellidos, cargo, email, telefono FROM contactos").fetchall()
                for c in contactos:
                    nombre_completo = f"{c[0]} {c[1] or ''}".strip()
                    st.write(f"{nombre_completo} - {c[2]} | {c[3]} | {c[4]}")

            elif accion_contacto == "Modificar contacto":
                st.write("### Modificar Contacto")
                contactos = run_query("SELECT id, nombre, apellidos, cargo, email, telefono, institucion_id FROM contactos").fetchall()
                if contactos:
                    contacto_dict = {f"{c[1]} {c[2] or ''} - {c[3]} | {c[4]} | {c[5]}".strip(): c[0] for c in contactos}
                    contacto_sel = st.selectbox("Selecciona contacto", list(contacto_dict.keys()), key="mod_contacto_kam")
                    contacto_id = contacto_dict[contacto_sel]
                    contacto_data = run_query("SELECT nombre, apellidos, cargo, email, telefono, institucion_id FROM contactos WHERE id = ?", (contacto_id,)).fetchone()
                    new_nombre = st.text_input("Nuevo nombre", value=contacto_data[0], key="edit_contacto_nombre_kam")
                    new_apellidos = st.text_input("Nuevos apellidos", value=contacto_data[1] or "", key="edit_contacto_apellidos_kam")
                    new_cargo = st.selectbox("Nuevo cargo", roles_list, index=roles_list.index(contacto_data[2]) if contacto_data[2] in roles_list else 0, key="edit_contacto_cargo_kam")
                    new_email = st.text_input("Nuevo email", value=contacto_data[3], key="edit_contacto_email_kam")
                    new_telefono = st.text_input("Nuevo teléfono", value=contacto_data[4], key="edit_contacto_tel_kam")
                    inst_names = list(institucion_dict.keys())
                    inst_ids = list(institucion_dict.values())
                    try:
                        inst_index = inst_ids.index(contacto_data[5])
                    except ValueError:
                        inst_index = 0
                    new_inst = st.selectbox("Nueva institución", inst_names, index=inst_index, key="edit_contacto_inst_kam")
                    new_inst_id = institucion_dict[new_inst]
                    if st.button("Guardar cambios contacto", key="guardar_cambios_contacto_kam"):
                        run_query("UPDATE contactos SET nombre = ?, apellidos = ?, cargo = ?, email = ?, telefono = ?, institucion_id = ? WHERE id = ?",
                                (new_nombre, new_apellidos, new_cargo, new_email, new_telefono, new_inst_id, contacto_id))
                        st.success("Contacto modificado correctamente")
                        st.rerun()
                else:
                    st.info("No hay contactos registrados.")

            elif accion_contacto == "Borrar contacto":
                st.write("### Borrar Contacto")
                contactos = run_query("SELECT id, nombre, apellidos, cargo, email, telefono FROM contactos").fetchall()
                if contactos:
                    contacto_dict = {f"{c[1]} {c[2] or ''} - {c[3]} | {c[4]} | {c[5]}".strip(): c[0] for c in contactos}
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
                    required_cols = {"nombre", "apellidos", "cargo", "email", "telefono", "institucion"}
                    if required_cols.issubset(df.columns):
                        inst_map = {nombre: iid for iid, nombre in instituciones}
                        roles_set = set(roles_list)
                        success, fail = 0, 0
                        for _, row in df.iterrows():
                            nombre = row["nombre"]
                            apellidos = row["apellidos"]
                            cargo = row["cargo"]
                            email = row["email"]
                            telefono = row["telefono"]
                            institucion = row["institucion"]
                            institucion_id = inst_map.get(institucion)
                            if institucion_id and cargo in roles_set:
                                run_query("INSERT INTO contactos (nombre, apellidos, cargo, email, telefono, institucion_id) VALUES (?, ?, ?, ?, ?, ?)",
                                        (nombre, apellidos, cargo, email, telefono, institucion_id))
                                success += 1
                            else:
                                fail += 1
                        st.success(f"Contactos cargados: {success}")
                        if fail:
                            st.warning(f"Contactos no cargados por error de rol o institución: {fail}")
                    else:
                        st.error(f"El CSV debe tener las columnas: {', '.join(required_cols)}")

    if menu == "Mensajes":
        # Enviar mensaje
        with st.expander("Enviar y gestionar mensajes"):
            st.subheader(":orange[Enviar mensaje]")
            tipo = st.selectbox("Tipo de mensaje", [
                "Seguimiento", 
                "Recordatorio de agenda", 
                "Entrega de informe", 
                "Motivacional",
                "Resolución de dudas",
                "Tendencias"
            ])
            # Mensajes pregrabados filtrados por tipo
            mensajes_pre = run_query("SELECT id, titulo, cuerpo FROM mensajes WHERE tipo = ?", (tipo,)).fetchall()
            msg_pre_dict = {f"{m[1]}: {m[2][:30]}...": m for m in mensajes_pre} if mensajes_pre else {}
            msg_pre_sel = st.selectbox("Mensaje pregrabado (opcional)", ["(Escribir manualmente)"] + list(msg_pre_dict.keys()), key="msg_pre")
            pre_titulo = ""
            pre_cuerpo = ""
            if msg_pre_sel != "(Escribir manualmente)":
                pre_titulo = msg_pre_dict[msg_pre_sel][1]
                pre_cuerpo = msg_pre_dict[msg_pre_sel][2]

            # Paso 1: Seleccionar institución
            inst_options = {
                f"{i[1]} ({i[2] if len(i) > 2 else ''}) - {i[3] if len(i) > 3 else ''}": i[0]
                for i in instituciones
            }
            inst_sel = st.selectbox("Selecciona institución", list(inst_options.keys())) if instituciones else None
            inst_id = inst_options[inst_sel] if inst_sel else None
            
            # Paso 2: Seleccionar contacto(s) de la institución
            contactos_inst = run_query("SELECT id, nombre, apellidos, cargo, email FROM contactos WHERE institucion_id = ?", (inst_id,)).fetchall() if inst_id else []
            if contactos_inst:
                contacto_options = {f"{c[1]} {c[2] or ''} - {c[3]} | {c[4]}".strip(): c[0] for c in contactos_inst}
                contactos_seleccionados = st.multiselect("Selecciona contacto(s) de la institución", list(contacto_options.keys()), key="contactos_multi")
                contacto_ids = [contacto_options[contacto] for contacto in contactos_seleccionados]
            else:
                contacto_ids = []
                st.info("No hay contactos registrados en esta institución.")
            
            # Paso 3: Configurar mensaje
            titulo = st.text_input("Título", value=pre_titulo, key="titulo_msg")
            
            # Configuración del saludo personalizado
            st.subheader("Personalización del mensaje")
            usar_saludo = st.checkbox("Incluir saludo personalizado", value=True, key="usar_saludo")
            
            if usar_saludo:
                saludo_personalizado = st.text_input("Saludo personalizado (se agregará el nombre automáticamente)", 
                                                   value="Hola", key="saludo_custom")
                st.info("💡 El saludo se personalizará automáticamente para cada contacto. Ejemplo: 'Hola María,'")
            
            # Cuerpo del mensaje base
            cuerpo_base = st.text_area("Cuerpo del mensaje (sin saludo)", value=pre_cuerpo, key="cuerpo_msg")
            
            # Vista previa del mensaje para el primer contacto seleccionado
            if contacto_ids and usar_saludo:
                primer_contacto = run_query("SELECT nombre, apellidos FROM contactos WHERE id = ?", (contacto_ids[0],)).fetchone()
                if primer_contacto:
                    nombre_ejemplo = f"{primer_contacto[0]} {primer_contacto[1] or ''}".strip()
                    mensaje_ejemplo = f"{saludo_personalizado} {nombre_ejemplo},\n\n{cuerpo_base}"
                    st.text_area("Vista previa del mensaje personalizado:", value=mensaje_ejemplo, height=100, disabled=True, key="preview")
            
            # Paso 4: Fecha y hora de envío
            col1, col2 = st.columns(2)
            with col1:
                fecha_envio = st.date_input("Fecha de envío", value=date.today(), key="fecha_envio")
            with col2:
                import datetime
                hora_envio = st.time_input("Hora de envío", value=datetime.time(9, 0), key="hora_envio")
            
            # Combinar fecha y hora
            fecha_hora_envio = datetime.datetime.combine(fecha_envio, hora_envio)
            
            # Botón de envío
            if st.button("Enviar mensaje") and contacto_ids and cuerpo_base:
                success_count = 0
                for contacto_id in contacto_ids:
                    # Obtener datos del contacto
                    contacto_data = run_query("SELECT nombre, apellidos, email FROM contactos WHERE id = ?", (contacto_id,)).fetchone()
                    if contacto_data:
                        nombre_completo = f"{contacto_data[0]} {contacto_data[1] or ''}".strip()
                        
                        # Crear mensaje personalizado
                        if usar_saludo:
                            mensaje_personalizado = f"{saludo_personalizado} {nombre_completo},\n\n{cuerpo_base}"
                        else:
                            mensaje_personalizado = cuerpo_base
                        
                        # Guardar mensaje en historial
                        run_query("INSERT INTO mensajes (titulo, cuerpo, tipo, fecha_envio_programada) VALUES (?, ?, ?, ?)",
                                (titulo, mensaje_personalizado, tipo, str(fecha_hora_envio)))
                        
                        # Enviar email
                        if contacto_data[2]:  # Si tiene email
                            if send_email(contacto_data[2], titulo, mensaje_personalizado):
                                success_count += 1
                            else:
                                st.warning(f"El email no pudo ser enviado a {contacto_data[2]}")
                
                if success_count > 0:
                    st.success(f"Mensaje enviado exitosamente a {success_count} contacto(s).")
                else:
                    st.error("No se pudo enviar el mensaje a ningún contacto.")
            
            # Botones de WhatsApp para cada contacto seleccionado
            if contacto_ids and titulo and cuerpo_base:
                st.subheader("Enviar por WhatsApp")
                for contacto_id in contacto_ids:
                    contacto_data = run_query("SELECT nombre, apellidos, telefono FROM contactos WHERE id = ?", (contacto_id,)).fetchone()
                    if contacto_data:
                        nombre_completo = f"{contacto_data[0]} {contacto_data[1] or ''}".strip()
                        telefono = contacto_data[2]
                        
                        # Crear mensaje personalizado para WhatsApp
                        if usar_saludo:
                            mensaje_wa = f"{saludo_personalizado} {nombre_completo},\n\n{cuerpo_base}"
                        else:
                            mensaje_wa = cuerpo_base
                        
                        if telefono:
                            telefono_wa = telefono.replace("+", "").replace(" ", "")
                            if telefono_wa.startswith("0"):
                                telefono_wa = "593" + telefono_wa[1:]
                            whatsapp_text = f"Asunto: {titulo}\n\n{mensaje_wa}"
                            whatsapp_url = f"https://wa.me/{telefono_wa}?text={quote(whatsapp_text)}"
                            st.markdown(f"[📱 Enviar a {nombre_completo}](<{whatsapp_url}>)", unsafe_allow_html=True)
                        else:
                            st.warning(f"No hay número de teléfono para {nombre_completo}")

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
