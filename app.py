# app.py
import streamlit as st
import sqlite3
from db_setup import init_db
from utils.login import require_login
from utils.data_sync import auto_sync
from modules.dashboards.KAM_dashboard import show_kam_dashboard

st.set_page_config(page_title="Muyu Lab", layout="wide")

# Inicializar BD y sincronizar datos
init_db()
auto_sync()  # Sincronización automática al iniciar

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

st.title(f"Muyu Lab - :red[Gestión de Relaciones] ({user.get('rol','')})")

# Explicación del proceso en el sidebar
with st.sidebar.expander("¿Cómo funciona la plataforma?", expanded=False):
    st.markdown("""
    **Guía rápida de administración:**
    - Utiliza el menú de navegación para gestionar KAMs, instituciones, contactos y mensajes.
    - Cada sección permite registrar, modificar, borrar y visualizar registros.
    - Los KAMs pueden ser asignados a instituciones.
    - Los contactos deben estar vinculados a una institución y tener un cargo válido.
    - Los mensajes pueden programarse y gestionarse desde la sección correspondiente.
    - Usa el botón 'Cerrar sesión' para salir de la plataforma.
    """)

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
    st.subheader(":blue[Gestión de KAMs]")
    acciones_kam = ["Registrar KAM", "Modificar KAM", "Borrar KAM", "Ver KAMs", "Asignar Instituciones"]
    accion_kam = st.selectbox("Selecciona una acción:", acciones_kam)

    if accion_kam == "Registrar KAM":
        with st.form("kam_form"):
            nombre = st.text_input("Nombre completo")
            email = st.text_input("Email")
            telefono = st.text_input("Teléfono")
            password = st.text_input("Contraseña para login", type="password")
            submitted = st.form_submit_button("Guardar")
            if submitted and nombre and email and password:
                run_query("INSERT INTO kams (nombre, email, telefono) VALUES (?, ?, ?)", (nombre, email, telefono))
                from utils.auth import hash_password
                run_query("INSERT OR IGNORE INTO users (nombre, email, password, rol) VALUES (?, ?, ?, ?)",
                          (nombre, email, hash_password(password), "KAM"))
                st.success("KAM y usuario creados correctamente")
            elif submitted:
                st.warning("Debes completar todos los campos, incluyendo la contraseña.")

    elif accion_kam == "Ver KAMs":
        st.write("### Lista de KAMs")
        kams = run_query("SELECT id, nombre, email, telefono FROM kams").fetchall()
        for k in kams:
            st.write(f"{k[1]} | {k[2]} | {k[3]}")

    elif accion_kam == "Modificar KAM":
        st.write("### Modificar KAM")
        kams = run_query("SELECT id, nombre, email, telefono FROM kams").fetchall()
        if kams:
            kam_dict = {f"{k[1]} | {k[2]} | {k[3]}": k[0] for k in kams}
            kam_sel = st.selectbox("Selecciona KAM", list(kam_dict.keys()), key="mod_kam")
            kam_id = kam_dict[kam_sel]
            kam_data = run_query("SELECT nombre, email, telefono FROM kams WHERE id = ?", (kam_id,)).fetchone()
            new_nombre = st.text_input("Nuevo nombre", value=kam_data[0], key="edit_kam_nombre")
            new_email = st.text_input("Nuevo email", value=kam_data[1], key="edit_kam_email")
            new_telefono = st.text_input("Nuevo teléfono", value=kam_data[2], key="edit_kam_tel")
            if st.button("Guardar cambios KAM"):
                run_query("UPDATE kams SET nombre = ?, email = ?, telefono = ? WHERE id = ?", (new_nombre, new_email, new_telefono, kam_id))
                run_query("UPDATE users SET nombre = ?, email = ? WHERE email = ? AND rol = ?", (new_nombre, new_email, kam_data[1], "KAM"))
                st.success("KAM modificado correctamente")
                st.rerun()
        else:
            st.info("No hay KAMs registrados.")

    elif accion_kam == "Borrar KAM":
        st.write("### Borrar KAM")
        kams = run_query("SELECT id, nombre, email, telefono FROM kams").fetchall()
        if kams:
            kam_dict = {f"{k[1]} | {k[2]} | {k[3]}": k[0] for k in kams}
            kam_sel = st.selectbox("Selecciona KAM", list(kam_dict.keys()), key="del_kam")
            kam_id = kam_dict[kam_sel]
            kam_data = run_query("SELECT nombre, email FROM kams WHERE id = ?", (kam_id,)).fetchone()
            if st.button("Borrar KAM"):
                run_query("DELETE FROM kams WHERE id = ?", (kam_id,))
                run_query("DELETE FROM users WHERE email = ? AND rol = ?", (kam_data[1], "KAM"))
                st.success("KAM eliminado correctamente")
                st.rerun()
        else:
            st.info("No hay KAMs registrados.")

    elif accion_kam == "Asignar Instituciones":
        st.write("### Asignar Instituciones a KAM")
        kams = run_query("SELECT id, nombre FROM kams").fetchall()
        instituciones = run_query("SELECT id, nombre FROM instituciones").fetchall()
        if kams and instituciones:
            kam_dict = {k[1]: k[0] for k in kams}
            inst_dict = {i[1]: i[0] for i in instituciones}
            selected_kam = st.selectbox("Selecciona KAM", list(kam_dict.keys()), key="asig_kam")
            selected_insts = st.multiselect("Selecciona instituciones", list(inst_dict.keys()), key="asig_insts")
            if st.button("Asignar instituciones") and selected_kam and selected_insts:
                kam_id = kam_dict[selected_kam]
                for inst_name in selected_insts:
                    inst_id = inst_dict[inst_name]
                    run_query("INSERT OR IGNORE INTO kam_institucion (kam_id, institucion_id) VALUES (?, ?)", (kam_id, inst_id))
                st.success("Instituciones asignadas al KAM correctamente")
        else:
            st.info("Debes tener al menos un KAM y una institución para asignar.")

# ---------------- Instituciones ----------------
elif menu == "Instituciones":
    st.subheader(":blue[Gestión de Instituciones]")
    acciones = ["Crear institución", "Modificar institución", "Borrar institución", "Ver instituciones"]
    accion = st.selectbox("Selecciona una acción:", acciones)

    if accion == "Crear institución":
        with st.form("inst_form"):
            nombre = st.text_input("Nombre de institución")
            direccion = st.text_input("Dirección")
            ciudad = st.text_input("Ciudad")
            provincia = st.text_input("Provincia/Estado")
            pais = st.text_input("País")
            anio_programa = st.selectbox("Año de programa", [f"Año {i}" for i in range(1, 7)])
            tipo_programa = st.selectbox("Tipo de programa", ["Muyu Lab", "Muyu App", "Muyu Scalelab"])
            plan = st.selectbox("Plan", ["Pago", "Apadrinado"])
            submitted = st.form_submit_button("Guardar")
            if submitted and nombre:
                run_query("INSERT INTO instituciones (nombre, direccion, ciudad, provincia, pais, anio_programa, tipo_programa, plan) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          (nombre, direccion, ciudad, provincia, pais, anio_programa, tipo_programa, plan))
                st.success("Institución agregada correctamente")

    elif accion == "Ver instituciones":
        st.write("### Lista de Instituciones")
        insts = run_query("SELECT id, nombre, direccion, ciudad, provincia, pais, anio_programa, tipo_programa, plan FROM instituciones").fetchall()
        for i in insts:
            st.write(f"**{i[1]}** | {i[2] or 'Sin dirección'} | {i[3] or 'Sin ciudad'}, {i[4] or 'Sin provincia'}, {i[5] or 'Sin país'} | {i[6] or 'Sin año'} | {i[7] or 'Muyu Lab'} | {i[8] or 'Pago'}")

    elif accion == "Modificar institución":
        st.write("### Modificar Institución")
        insts = run_query("SELECT id, nombre, direccion, ciudad, provincia, pais, anio_programa, tipo_programa, plan FROM instituciones").fetchall()
        if insts:
            inst_dict = {f"{i[1]} ({i[3]}, {i[5]}) - {i[6]} - {i[7]}": i[0] for i in insts}
            inst_sel = st.selectbox("Selecciona institución", list(inst_dict.keys()), key="mod_inst")
            inst_id = inst_dict[inst_sel]
            inst_data = run_query("SELECT nombre, direccion, ciudad, provincia, pais, anio_programa, tipo_programa, plan FROM instituciones WHERE id = ?", (inst_id,)).fetchone()
            
            new_nombre = st.text_input("Nuevo nombre", value=inst_data[0] or "", key="edit_nombre")
            new_direccion = st.text_input("Nueva dirección", value=inst_data[1] or "", key="edit_direccion")
            new_ciudad = st.text_input("Nueva ciudad", value=inst_data[2] or "", key="edit_ciudad")
            new_provincia = st.text_input("Nueva provincia/estado", value=inst_data[3] or "", key="edit_provincia")
            new_pais = st.text_input("Nuevo país", value=inst_data[4] or "", key="edit_pais")
            
            anios = [f"Año {i}" for i in range(1, 7)]
            try:
                anio_index = anios.index(inst_data[5]) if inst_data[5] else 0
            except (ValueError, TypeError):
                anio_index = 0
            new_anio = st.selectbox("Nuevo año de programa", anios, index=anio_index, key="edit_anio")
            
            tipos_programa = ["Muyu Lab", "Muyu App", "Muyu Scalelab"]
            try:
                tipo_index = tipos_programa.index(inst_data[6]) if inst_data[6] else 0
            except (ValueError, TypeError):
                tipo_index = 0
            new_tipo_programa = st.selectbox("Nuevo tipo de programa", tipos_programa, index=tipo_index, key="edit_tipo")
            
            planes = ["Pago", "Apadrinado"]
            try:
                plan_index = planes.index(inst_data[7]) if inst_data[7] else 0
            except (ValueError, TypeError):
                plan_index = 0
            new_plan = st.selectbox("Nuevo plan", planes, index=plan_index, key="edit_plan")
            
            if st.button("Guardar cambios"):
                run_query("UPDATE instituciones SET nombre = ?, direccion = ?, ciudad = ?, provincia = ?, pais = ?, anio_programa = ?, tipo_programa = ?, plan = ? WHERE id = ?", 
                         (new_nombre, new_direccion, new_ciudad, new_provincia, new_pais, new_anio, new_tipo_programa, new_plan, inst_id))
                st.success("Institución modificada correctamente")
                st.rerun()
        else:
            st.info("No hay instituciones registradas.")

    elif accion == "Borrar institución":
        st.write("### Borrar Institución")
        insts = run_query("SELECT id, nombre, ciudad, pais, tipo_programa, plan FROM instituciones").fetchall()
        if insts:
            inst_dict = {f"{i[1]} ({i[2]}, {i[3]}) - {i[4]} - {i[5]}": i[0] for i in insts}
            inst_sel = st.selectbox("Selecciona institución", list(inst_dict.keys()), key="del_inst")
            inst_id = inst_dict[inst_sel]
            if st.button("Borrar institución"):
                run_query("DELETE FROM instituciones WHERE id = ?", (inst_id,))
                st.success("Institución eliminada correctamente")
                st.rerun()
        else:
            st.info("No hay instituciones registradas.")

# ---------------- Contactos ----------------
elif menu == "Contactos":
    st.subheader(":blue[Gestión de Contactos]")
    acciones_contacto = ["Registrar contacto", "Modificar contacto", "Borrar contacto", "Ver contactos", "Carga masiva"]
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
            contacto_sel = st.selectbox("Selecciona contacto", list(contacto_dict.keys()), key="mod_contacto")
            contacto_id = contacto_dict[contacto_sel]
            contacto_data = run_query("SELECT nombre, apellidos, cargo, email, telefono, institucion_id FROM contactos WHERE id = ?", (contacto_id,)).fetchone()
            new_nombre = st.text_input("Nuevo nombre", value=contacto_data[0], key="edit_contacto_nombre")
            new_apellidos = st.text_input("Nuevos apellidos", value=contacto_data[1] or "", key="edit_contacto_apellidos")
            new_cargo = st.selectbox("Nuevo cargo", roles_list, index=roles_list.index(contacto_data[2]) if contacto_data[2] in roles_list else 0, key="edit_contacto_cargo")
            new_email = st.text_input("Nuevo email", value=contacto_data[3], key="edit_contacto_email")
            new_telefono = st.text_input("Nuevo teléfono", value=contacto_data[4], key="edit_contacto_tel")
            inst_names = list(institucion_dict.keys())
            inst_ids = list(institucion_dict.values())
            try:
                inst_index = inst_ids.index(contacto_data[5])
            except ValueError:
                inst_index = 0
            new_inst = st.selectbox("Nueva institución", inst_names, index=inst_index, key="edit_contacto_inst")
            new_inst_id = institucion_dict[new_inst]
            if st.button("Guardar cambios contacto"):
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
            contacto_sel = st.selectbox("Selecciona contacto", list(contacto_dict.keys()), key="del_contacto")
            contacto_id = contacto_dict[contacto_sel]
            if st.button("Borrar contacto"):
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

# ---------------- Mensajes ----------------
elif menu == "Mensajes":
    st.subheader(":blue[Gestión de Mensajes]")
    acciones_msg = ["Registrar mensaje", "Modificar mensaje", "Borrar mensaje", "Ver mensajes"]
    accion_msg = st.selectbox("Selecciona una acción:", acciones_msg)

    if accion_msg == "Registrar mensaje":
        with st.form("msg_form"):
            titulo = st.text_input("Título")
            cuerpo = st.text_area("Cuerpo del mensaje")
            tipo = st.selectbox("Tipo", [
                "Recordatorio de agenda",
                "Entrega de informe",
                "Motivacional",
                "Seguimiento",
                "Resolución de dudas",
                "Tendencias"
            ])
            fecha = st.date_input("Fecha programada")
            submitted = st.form_submit_button("Guardar")
            if submitted and cuerpo:
                run_query("INSERT INTO mensajes (titulo, cuerpo, tipo, fecha_envio_programada) VALUES (?, ?, ?, ?)",
                          (titulo, cuerpo, tipo, str(fecha)))
                st.success("Mensaje guardado correctamente")

    elif accion_msg == "Ver mensajes":
        st.write("### Lista de Mensajes")
        mensajes = run_query("SELECT titulo, tipo, fecha_envio_programada, enviado FROM mensajes").fetchall()
        for m in mensajes:
            status = "✅ Enviado" if m[3] else "⏳ Pendiente"
            st.write(f"{m[0]} | {m[1]} | {m[2]} | {status}")

    elif accion_msg == "Modificar mensaje":
        st.write("### Modificar Mensaje")
        mensajes = run_query("SELECT id, titulo, tipo, fecha_envio_programada, cuerpo FROM mensajes").fetchall()
        if mensajes:
            msg_dict = {f"{m[1]} | {m[2]} | {m[3]}": m[0] for m in mensajes}
            msg_sel = st.selectbox("Selecciona mensaje", list(msg_dict.keys()), key="mod_msg")
            msg_id = msg_dict[msg_sel]
            msg_data = run_query("SELECT titulo, cuerpo, tipo, fecha_envio_programada FROM mensajes WHERE id = ?", (msg_id,)).fetchone()
            new_titulo = st.text_input("Nuevo título", value=msg_data[0], key="edit_msg_titulo")
            new_cuerpo = st.text_area("Nuevo cuerpo", value=msg_data[1], key="edit_msg_cuerpo")
            tipos = [
                "Recordatorio de agenda",
                "Entrega de informe",
                "Motivacional",
                "Seguimiento",
                "Resolución de dudas",
                "Tendencias"
            ]
            try:
                tipo_index = tipos.index(msg_data[2])
            except ValueError:
                tipo_index = 0
            new_tipo = st.selectbox("Nuevo tipo", tipos, index=tipo_index, key="edit_msg_tipo")
            new_fecha = st.date_input("Nueva fecha programada", value=msg_data[3], key="edit_msg_fecha")
            if st.button("Guardar cambios mensaje"):
                run_query("UPDATE mensajes SET titulo = ?, cuerpo = ?, tipo = ?, fecha_envio_programada = ? WHERE id = ?",
                          (new_titulo, new_cuerpo, new_tipo, str(new_fecha), msg_id))
                st.success("Mensaje modificado correctamente")
                st.rerun()
        else:
            st.info("No hay mensajes registrados.")

    elif accion_msg == "Borrar mensaje":
        st.write("### Borrar Mensaje")
        mensajes = run_query("SELECT id, titulo, tipo, fecha_envio_programada FROM mensajes").fetchall()
        if mensajes:
            msg_dict = {f"{m[1]} | {m[2]} | {m[3]}": m[0] for m in mensajes}
            msg_sel = st.selectbox("Selecciona mensaje", list(msg_dict.keys()), key="del_msg")
            msg_id = msg_dict[msg_sel]
            if st.button("Borrar mensaje"):
                run_query("DELETE FROM mensajes WHERE id = ?", (msg_id,))
                st.success("Mensaje eliminado correctamente")
                st.rerun()
        else:
            st.info("No hay mensajes registrados.")
