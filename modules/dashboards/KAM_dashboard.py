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
    # Botón de cerrar sesión
    if st.sidebar.button("Cerrar sesión", key="logout_kam"):
        st.session_state.clear()
        st.rerun()

    st.header("Panel KAM: :red[Seguimiento de Instituciones y Clientes]")

    # Ver instituciones y año de programa
    st.subheader(":blue[Instituciones asignadas]")
    instituciones = run_query("SELECT id, nombre, ciudad, anio_programa FROM instituciones").fetchall()
    if instituciones:
        for inst in instituciones:
            st.markdown(f"**{inst[1]}** ({inst[2]}) - {inst[3]}")
    else:
        st.info("No hay instituciones registradas.")

    # Ver contactos (clientes)
    st.subheader(":blue[Contactos registrados]")
    contactos = run_query("SELECT c.id, c.nombre, c.cargo, c.email, i.nombre FROM contactos c LEFT JOIN instituciones i ON c.institucion_id = i.id").fetchall()
    if contactos:
        for c in contactos:
            st.markdown(f"**{c[1]}** - {c[2]} | {c[3]} | Institución: {c[4]}")
    else:
        st.info("No hay contactos registrados.")

    # Enviar mensaje de seguimiento
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
        inst_options = {f"{i[1]} ({i[2]}) - {i[3]}": i[0] for i in instituciones}
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
    st.subheader(":orange[Historial de mensajes enviados]")
    mensajes = run_query("SELECT titulo, tipo, fecha_envio_programada, enviado FROM mensajes ORDER BY fecha_envio_programada DESC").fetchall()
    for m in mensajes:
        status = "✅ Enviado" if m[3] else "⏳ Pendiente"
        st.write(f"{m[0]} | {m[1]} | {m[2]} | {status}")
