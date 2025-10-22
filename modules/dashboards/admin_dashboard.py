import streamlit as st
import sqlite3
import pandas as pd
from utils.auth import hash_password
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

DB_PATH = "database/muyulab.db"

def run_query(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    return cur

def run_insert_query(query, params=()):
    """Función específica para inserts que asegura el commit"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def test_email_credentials(email_user, email_pass):
    """Prueba las credenciales de email sin enviar mensaje"""
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_user, email_pass)
        return True
    except smtplib.SMTPAuthenticationError:
        return False
    except Exception:
        return False

def show_admin_dashboard():
    # Obtener información del usuario
    user = st.session_state.get("user", {})
    admin_nombre = user.get("nombre", "Administrador")

    # Mensaje de bienvenida personalizado en el sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### 👋 ¡Hola, **{admin_nombre}**!")
    st.sidebar.markdown("Bienvenido al panel de administración")
    st.sidebar.markdown("---")

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

    # Botón de cerrar sesión
    if st.sidebar.button("Cerrar sesión"):
        st.session_state.clear()
        st.rerun()

    # Puedes proteger secciones por rol, por ejemplo:
    if user.get("rol") == "cliente":
        st.info("Acceso solo a mensajes.")
        menu = "Mensajes"
    else:
        menu = st.sidebar.radio("Navegación", ["KAMs", "Instituciones", "Contactos", "Mensajes"])

    st.image("assets/muyu_logo.jpg", width=200)
    st.title(f"Muyu Lab Contact - :red[Gestión de Relaciones] ({user.get('rol','')})")

    # ---------------- KAMs ----------------
    if menu == "KAMs":
        st.subheader(":blue[Gestión de KAMs]")
        acciones_kam = ["Registrar KAM", "Modificar KAM", "Borrar KAM", "Ver KAMs", "Asignar Instituciones", "Configurar Email"]
        # Añadir opción de limpieza de duplicados en kam_institucion (solo para admins)
        acciones_kam.append("Limpiar duplicados asignaciones KAM")
        accion_kam = st.selectbox("Selecciona una acción:", acciones_kam)

        if accion_kam == "Registrar KAM":
            with st.form("kam_form"):
                nombre = st.text_input("Nombre completo")
                email = st.text_input("Email")
                telefono = st.text_input("Teléfono")
                password = st.text_input("Contraseña para login", type="password")
                st.markdown("### Configuración de Email (Opcional)")
                email_usuario = st.text_input("Email para envío de mensajes (ej: kam@empresa.com)")
                email_password = st.text_input("Contraseña de aplicación del email", type="password", help="Para Gmail, usa una contraseña de aplicación")
                submitted = st.form_submit_button("Guardar")
                
                if submitted and nombre and email and password:
                    # Verificar si el email ya existe
                    existing_kam = run_query("SELECT email FROM kams WHERE email = ?", (email,)).fetchone()
                    existing_user = run_query("SELECT email FROM users WHERE email = ?", (email,)).fetchone()
                    
                    if existing_kam or existing_user:
                        st.error(f"❌ El email '{email}' ya está registrado en el sistema. Por favor usa un email diferente.")
                    else:
                        try:
                            # Insertar KAM
                            run_query("INSERT INTO kams (nombre, email, telefono, email_usuario, email_password) VALUES (?, ?, ?, ?, ?)", 
                                     (nombre, email, telefono, email_usuario if email_usuario else None, email_password if email_password else None))
                            
                            # Insertar usuario
                            run_query("INSERT INTO users (nombre, email, password, rol) VALUES (?, ?, ?, ?)",
                                      (nombre, email, hash_password(password), "KAM"))
                            
                            st.success("✅ KAM y usuario creados correctamente")
                            
                            # Mostrar información de configuración
                            if email_usuario and email_password:
                                st.info("📧 **Configuración de email incluida:** El KAM podrá enviar mensajes desde el panel.")
                            else:
                                st.warning("⚠️ **Sin configuración de email:** El KAM necesitará configurar sus credenciales más tarde para enviar mensajes.")
                        except Exception as e:
                            st.error(f"❌ Error al crear KAM: {e}")
                            
                elif submitted:
                    st.warning("⚠️ Debes completar todos los campos obligatorios (Nombre, Email y Contraseña).")

        elif accion_kam == "Configurar Email":
            st.write("### Configurar Credenciales de Email para KAMs")
            kams = run_query("SELECT id, nombre, email, email_usuario FROM kams").fetchall()
            if kams:
                kam_dict = {f"{k[1]} | {k[2]}": k[0] for k in kams}
                kam_sel = st.selectbox("Selecciona KAM", list(kam_dict.keys()), key="config_kam")
                kam_id = kam_dict[kam_sel]
                kam_data = run_query("SELECT nombre, email, email_usuario, email_password FROM kams WHERE id = ?", (kam_id,)).fetchone()
                
                st.info("Configura las credenciales de email que usará este KAM para enviar mensajes")
                
                # Mostrar instrucciones detalladas
                with st.expander("📋 Instrucciones Detalladas", expanded=True):
                    st.markdown("""
                    **Para Gmail (Recomendado):**
                    
                    1. **Verificación en 2 pasos (OBLIGATORIO):**
                       - Ve a [Seguridad de Google](https://myaccount.google.com/security)
                       - Busca "Verificación en 2 pasos" y actívala
                    
                    2. **Generar Contraseña de Aplicación:**
                       - Ve a [Contraseñas de aplicación](https://myaccount.google.com/apppasswords)
                       - Selecciona "Aplicación: Mail"
                       - Selecciona "Dispositivo: Otro (nombre personalizado)"
                       - Escribe "MuyuLab" como nombre
                       - **Copia la contraseña de 16 caracteres que aparece**
                    
                    3. **⚠️ IMPORTANTE:**
                       - USA la contraseña de 16 caracteres (con espacios o sin espacios)
                       - NO uses la contraseña normal de Gmail
                       - El email debe ser una cuenta Gmail válida
                    
                    **Formato de contraseña:** `abcd efgh ijkl mnop` (16 caracteres)
                    """)
                
                with st.form("email_config_form"):
                    email_usuario = st.text_input(
                        "Email para envío (Gmail)", 
                        value=kam_data[2] or "", 
                        help="Debe ser una cuenta de Gmail válida"
                    )
                    email_password = st.text_input(
                        "Contraseña de aplicación (16 caracteres)", 
                        type="password", 
                        help="Contraseña generada en https://myaccount.google.com/apppasswords"
                    )
                    
                    # Validación básica
                    if email_usuario and not email_usuario.endswith('@gmail.com'):
                        st.warning("⚠️ Se recomienda usar una cuenta de Gmail para mejor compatibilidad")
                    
                    if email_password and len(email_password.replace(' ', '')) != 16:
                        st.warning("⚠️ La contraseña de aplicación debe tener exactamente 16 caracteres")
                    
                    submitted = st.form_submit_button("Guardar y Probar Configuración")
                    if submitted:
                        if email_usuario and email_password:
                            # Probar credenciales antes de guardar
                            with st.spinner("Probando credenciales..."):
                                test_result = test_email_credentials(email_usuario, email_password)
                            
                            if test_result:
                                # Guardar credenciales
                                run_query("UPDATE kams SET email_usuario = ?, email_password = ? WHERE id = ?", 
                                         (email_usuario, email_password, kam_id))
                                st.success("✅ Credenciales configuradas y probadas correctamente")
                                st.info(f"📧 **Email configurado para:** {kam_data[1]} → {email_usuario}")
                                st.balloons()
                            else:
                                st.error("❌ Las credenciales no funcionan. Verifica:")
                                st.markdown("""
                                - ✅ Verificación en 2 pasos activada en Gmail
                                - ✅ Contraseña de aplicación (no la contraseña normal)
                                - ✅ Email Gmail válido
                                - ✅ Conexión a internet estable
                                """)
                        else:
                            st.warning("⚠️ Debes completar ambos campos")
            else:
                st.info("No hay KAMs registrados.")

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
        elif accion_kam == "Limpiar duplicados asignaciones KAM":
            st.write("### Limpiar duplicados en kam_institucion")
            st.markdown("Este proceso detecta pares (kam_id, institucion_id) con más de una fila y permite eliminarlas. Se creará una copia de seguridad automática antes de modificar la base de datos.")
            col1, col2 = st.columns(2)
            with col1:
                do_run = st.button("🔍 Ejecutar análisis (dry-run)")
            with col2:
                do_apply = st.button("🗑️ Ejecutar limpieza (eliminar duplicados)")

            keep_choice = st.selectbox("Conservar fila:", ["first", "last"], index=0)
            add_index = st.checkbox("Crear índice único (kam_id, institucion_id) después de limpiar", value=False)

            def _backup_db(path):
                import shutil
                from datetime import datetime
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                dest = f"{path}.backup_{ts}"
                shutil.copy2(path, dest)
                return dest

            def _find_duplicates():
                rows = run_query("""
                    SELECT kam_id, institucion_id, COUNT(*) as cnt
                    FROM kam_institucion
                    GROUP BY kam_id, institucion_id
                    HAVING cnt > 1
                """).fetchall()
                return rows

            def _get_rows_for_pair(kam_id, inst_id):
                return run_query("SELECT id FROM kam_institucion WHERE kam_id = ? AND institucion_id = ? ORDER BY id", (kam_id, inst_id)).fetchall()

            if do_run or do_apply:
                db_path = DB_PATH
                st.info(f"Usando DB: {db_path}")
                backup_path = _backup_db(db_path)
                st.success(f"Backup creado en: {backup_path}")

                dups = _find_duplicates()
                if not dups:
                    st.success("No se encontraron duplicados en kam_institucion.")
                else:
                    st.write(f"Se encontraron {len(dups)} pares duplicados:")
                    for kam_id, inst_id, cnt in dups:
                        st.write(f"- kam_id={kam_id}, institucion_id={inst_id} → {cnt} filas")
                        rows = _get_rows_for_pair(kam_id, inst_id)
                        ids = [r[0] for r in rows]
                        st.write(f"  Filas: {ids}")

                        if do_apply:
                            # decide which to delete
                            if keep_choice == 'first':
                                keep_id = ids[0]
                                del_ids = ids[1:]
                            else:
                                keep_id = ids[-1]
                                del_ids = ids[:-1]

                            if del_ids:
                                for did in del_ids:
                                    run_query("DELETE FROM kam_institucion WHERE id = ?", (did,))
                                st.success(f"Eliminadas filas: {del_ids} (se conservó id {keep_id})")

                    if do_apply and add_index:
                        try:
                            run_query("CREATE UNIQUE INDEX IF NOT EXISTS idx_kam_institucion_unique ON kam_institucion (kam_id, institucion_id)")
                            st.success("Índice único creado: idx_kam_institucion_unique")
                        except Exception as e:
                            st.error(f"No se pudo crear el índice: {e}")
            else:
                st.info("Debes tener al menos un KAM y una institución para asignar.")

        elif accion_kam == "Ver KAMs":
            st.write("### Lista de KAMs")
            kams = run_query("SELECT id, nombre, email, telefono, email_usuario FROM kams").fetchall()
            if kams:
                st.write("**Formato:** Nombre | Email | Teléfono | Estado Email")
                for k in kams:
                    email_status = "✅ Configurado" if k[4] else "⚠️ No configurado"
                    st.write(f"**{k[1]}** | {k[2]} | {k[3] or 'Sin teléfono'} | {email_status}")
            else:
                st.info("No hay KAMs registrados.")

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
            
            # --- NUEVO: Información previa y plantilla descargable ---
            st.info("""
            **Formato requerido para la hoja de cálculo:**  
            El archivo debe contener las siguientes columnas (en este orden o con estos nombres exactos):
            - `nombre`: Nombre del contacto
            - `apellidos`: Apellidos del contacto
            - `cargo`: Cargo o rol (ejemplo: Director, Coordinador, etc.)
            - `email`: Email institucional del contacto
            - `telefono`: Número de teléfono (preferentemente compatible con WhatsApp)
            - `institucion`: Nombre exacto de la institución (debe coincidir con la base de datos o se creará nueva)
            """)
            
            st.markdown("**Ejemplo de archivo:**")
            ejemplo_csv = """nombre,apellidos,cargo,email,telefono,institucion
Juan,Pérez García,Director,juan.perez@universidad.edu,+34123456789,Universidad Nacional
María,López Ruiz,Coordinador,maria.lopez@tecnologico.edu,+34987654321,Instituto Tecnológico"""
            st.code(ejemplo_csv, language="csv")
            
            # Plantilla vacía para descargar
            import io
            import pandas as pd
            plantilla_df = pd.DataFrame(columns=["nombre", "apellidos", "cargo", "email", "telefono", "institucion"])
            plantilla_buffer = io.BytesIO()
            plantilla_df.to_excel(plantilla_buffer, index=False)
            plantilla_buffer.seek(0)
            st.download_button(
                label="📥 Descargar plantilla vacía (Excel)",
                data=plantilla_buffer,
                file_name="plantilla_contactos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            st.markdown("---")
            st.write("Puedes subir un archivo **CSV** o **Excel (.xlsx)** con los contactos a cargar.")
            
            # --- FIN NUEVO ---
            
            # Permitir subir CSV o Excel
            csv_file = st.file_uploader("Subir archivo CSV o Excel de contactos", type=["csv", "xlsx"])
            if csv_file is not None:
                # Detectar tipo de archivo y leer
                if csv_file.name.endswith(".csv"):
                    df = pd.read_csv(csv_file)
                elif csv_file.name.endswith(".xlsx"):
                    df = pd.read_excel(csv_file)
                else:
                    st.error("Formato de archivo no soportado. Usa CSV o Excel (.xlsx)")
                    return
                required_cols = {"nombre", "apellidos", "cargo", "email", "telefono", "institucion"}
                if required_cols.issubset(df.columns):
                    # Crear mapeos con nombres normalizados
                    inst_map_display = {nombre.strip(): iid for iid, nombre in instituciones}
                    roles_set = set(roles_list)
                    
                    st.info(f"📊 **Archivo cargado:** {len(df)} filas encontradas")
                    
                    # Mostrar datos de referencia en columnas
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**🏛️ Instituciones disponibles:**")
                        for nombre in inst_map_display.keys():
                            st.write(f"• {nombre}")
                    
                    with col2:
                        st.write("**👥 Cargos/Roles disponibles:**")
                        for role in roles_list:
                            st.write(f"• {role}")
                    
                    # PASO 1: VISTA PREVIA DE LOS DATOS
                    st.subheader("📋 Vista previa de los datos a cargar:")
                    
                    # Mostrar valores únicos del CSV para debugging
                    st.write("**🔍 Valores encontrados en tu CSV:**")
                    col_debug1, col_debug2 = st.columns(2)
                    
                    with col_debug1:
                        st.write("**Instituciones en tu CSV:**")
                        instituciones_csv = df['institucion'].unique()
                        for inst in instituciones_csv:
                            st.write(f"• '{inst}'")
                    
                    with col_debug2:
                        st.write("**Cargos en tu CSV:**")
                        cargos_csv = df['cargo'].unique()
                        for cargo in cargos_csv:
                            st.write(f"• '{cargo}'")
                    
                    # Análisis de coincidencias para ayudar al usuario
                    st.markdown("---")
                    st.write("**🔍 Análisis de coincidencias:**")
                    
                    # Verificar instituciones
                    st.write("**Instituciones:**")
                    instituciones_nuevas = []
                    for inst_csv in instituciones_csv:
                        encontrada = False
                        for inst_bd in inst_map_display.keys():
                            if inst_bd.lower().strip() == str(inst_csv).lower().strip():
                                st.write(f"✅ '{inst_csv}' → Coincide con '{inst_bd}'")
                                encontrada = True
                                break
                        if not encontrada:
                            st.write(f"🆕 '{inst_csv}' → **Nueva institución** (se creará automáticamente)")
                            instituciones_nuevas.append(str(inst_csv).strip())
                    
                    # Verificar cargos
                    st.write("**Cargos:**")
                    cargos_nuevos = []
                    for cargo_csv in cargos_csv:
                        if str(cargo_csv) in roles_set:
                            st.write(f"✅ '{cargo_csv}' → Válido")
                        else:
                            st.write(f"🆕 '{cargo_csv}' → **Nuevo cargo** (se creará automáticamente)")
                            cargos_nuevos.append(str(cargo_csv).strip())
                    
                    # Mostrar resumen de elementos nuevos
                    if instituciones_nuevas or cargos_nuevos:
                        st.info("ℹ️ **Se crearán automáticamente los siguientes elementos nuevos:**")
                        if instituciones_nuevas:
                            st.write(f"**Nuevas instituciones:** {', '.join(instituciones_nuevas)}")
                        if cargos_nuevos:
                            st.write(f"**Nuevos cargos:** {', '.join(cargos_nuevos)}")
                    
                    # RE-VALIDAR con creación automática
                    st.subheader("📋 Validación final con creación automática:")
                    validated_data_final = []
                    
                    for index, row in df.iterrows():
                        row_data = {
                            'fila': index + 1,
                            'nombre': str(row["nombre"]).strip(),
                            'apellidos': str(row["apellidos"]).strip(),
                            'cargo': str(row["cargo"]).strip(),
                            'email': str(row["email"]).strip(),
                            'telefono': str(row["telefono"]).strip(),
                            'institucion': str(row["institucion"]).strip(),
                            'errores': [],
                            'valido': True,
                            'nueva_institucion': False,
                            'nuevo_cargo': False
                        }
                        
                        # Verificar institución (existente o nueva)
                        institucion_id = None
                        for inst_name, inst_id in inst_map_display.items():
                            if inst_name.lower().strip() == row_data['institucion'].lower().strip():
                                institucion_id = inst_id
                                break
                        
                        if not institucion_id:
                            # Marcar como nueva institución
                            row_data['nueva_institucion'] = True
                            row_data['institucion_id'] = 'NUEVA'
                        else:
                            row_data['institucion_id'] = institucion_id
                        
                        # Verificar cargo (existente o nuevo)
                        if row_data['cargo'] not in roles_set:
                            row_data['nuevo_cargo'] = True
                        
                        # Validaciones básicas (solo datos obligatorios)
                        if not row_data['nombre']:
                            row_data['errores'].append("Nombre vacío")
                            row_data['valido'] = False
                        
                        if not row_data['email'] or "@" not in row_data['email']:
                            row_data['errores'].append("Email inválido")
                            row_data['valido'] = False
                        
                        validated_data_final.append(row_data)
                    
                    # Crear DataFrame para mostrar vista final
                    preview_final_df = pd.DataFrame([
                        {
                            'Fila': d['fila'],
                            'Nombre': d['nombre'],
                            'Apellidos': d['apellidos'],
                            'Cargo': f"🆕 {d['cargo']}" if d['nuevo_cargo'] else d['cargo'],
                            'Email': d['email'],
                            'Teléfono': d['telefono'],
                            'Institución': f"🆕 {d['institucion']}" if d['nueva_institucion'] else d['institucion'],
                            'Estado': '✅ Válido' if d['valido'] else f"❌ {', '.join(d['errores'])}"
                        }
                        for d in validated_data_final
                    ])
                    
                    st.dataframe(preview_final_df, use_container_width=True)
                    
                    # Resumen final
                    validos_final = sum(1 for d in validated_data_final if d['valido'])
                    invalidos_final = len(validated_data_final) - validos_final
                    
                    col_res1, col_res2, col_res3 = st.columns(3)
                    with col_res1:
                        st.metric("📊 Total filas", len(validated_data_final))
                    with col_res2:
                        st.metric("✅ Filas válidas", validos_final)
                    with col_res3:
                        st.metric("❌ Filas con errores", invalidos_final)

                    # PASO 2: BOTÓN PARA CONFIRMAR INSERCIÓN
                    if validos_final > 0:
                        st.markdown("---")
                        st.subheader("💾 Confirmar inserción a la base de datos")
                        
                        opciones_insercion = st.radio(
                            "¿Qué deseas hacer?",
                            [
                                f"Insertar las {validos_final} filas válidas (creando automáticamente elementos nuevos)",
                                "Cancelar - No insertar nada"
                            ]
                        )
                        
                        if opciones_insercion.startswith("Insertar"):
                            if st.button("🚀 CONFIRMAR INSERCIÓN A LA BASE DE DATOS", type="primary"):
                                # PASO 3: INSERCIÓN REAL CON CREACIÓN AUTOMÁTICA
                                progress_bar = st.progress(0)
                                status_text = st.empty()
                                
                                success_count = 0
                                datos_insertados = []
                                elementos_creados = []
                                
                                filas_validas = [d for d in validated_data_final if d['valido']]
                                total_steps = len(filas_validas) + len(instituciones_nuevas) + len(cargos_nuevos)
                                current_step = 0
                                
                                # CREAR NUEVAS INSTITUCIONES
                                instituciones_creadas = {}
                                for nueva_inst in instituciones_nuevas:
                                    current_step += 1
                                    progress_bar.progress(current_step / total_steps)
                                    status_text.text(f"Creando nueva institución: {nueva_inst}")
                                    
                                    try:
                                        run_insert_query(
                                            "INSERT INTO instituciones (nombre, ciudad, anio_programa) VALUES (?, ?, ?)",
                                            (nueva_inst, "Ciudad por definir", "2024")
                                        )
                                        # Obtener el ID de la institución recién creada
                                        new_inst_id = run_query("SELECT id FROM instituciones WHERE nombre = ?", (nueva_inst,)).fetchall()[0][0]
                                        instituciones_creadas[nueva_inst] = new_inst_id
                                        elementos_creados.append(f"✅ Institución creada: {nueva_inst}")
                                    except Exception as e:
                                        elementos_creados.append(f"❌ Error creando institución {nueva_inst}: {str(e)}")
                                
                                # CREAR NUEVOS CARGOS/ROLES
                                for nuevo_cargo in cargos_nuevos:
                                    current_step += 1
                                    progress_bar.progress(current_step / total_steps)
                                    status_text.text(f"Creando nuevo cargo: {nuevo_cargo}")
                                    
                                    try:
                                        run_insert_query(
                                            "INSERT INTO roles (nombre) VALUES (?)",
                                            (nuevo_cargo,)
                                        )
                                        elementos_creados.append(f"✅ Cargo creado: {nuevo_cargo}")
                                    except Exception as e:
                                        elementos_creados.append(f"❌ Error creando cargo {nuevo_cargo}: {str(e)}")
                                
                                # INSERTAR CONTACTOS
                                for row_data in filas_validas:
                                    current_step += 1
                                    progress_bar.progress(current_step / total_steps)
                                    status_text.text(f"Insertando contacto: {row_data['nombre']} {row_data['apellidos']}")
                                    
                                    try:
                                        # Determinar ID de institución
                                        if row_data['nueva_institucion']:
                                            final_inst_id = instituciones_creadas.get(row_data['institucion'])
                                        else:
                                            final_inst_id = row_data['institucion_id']
                                        
                                        if final_inst_id:
                                            run_insert_query(
                                                "INSERT INTO contactos (nombre, apellidos, cargo, email, telefono, institucion_id) VALUES (?, ?, ?, ?, ?, ?)",
                                                (row_data['nombre'], row_data['apellidos'], row_data['cargo'], 
                                                 row_data['email'], row_data['telefono'], final_inst_id)
                                            )
                                            
                                            success_count += 1
                                            datos_insertados.append(f"✅ Fila {row_data['fila']}: {row_data['nombre']} {row_data['apellidos']}")
                                        else:
                                            datos_insertados.append(f"❌ Fila {row_data['fila']}: Error con institución")
                                            
                                    except Exception as e:
                                        datos_insertados.append(f"❌ Fila {row_data['fila']}: Error - {str(e)}")
                                
                                # Limpiar barra de progreso
                                progress_bar.empty()
                                status_text.empty()
                                
                                # Mostrar resultados finales
                                st.success(f"🎉 **¡INSERCIÓN COMPLETADA!**")
                                st.info(f"📊 **{success_count} contactos insertados correctamente**")
                                
                                # Verificar total en base de datos
                                total_contactos = run_query("SELECT COUNT(*) FROM contactos").fetchall()[0][0]
                                st.info(f"📈 Total de contactos en la base de datos: {total_contactos}")
                                
                                # Mostrar elementos creados
                                if elementos_creados:
                                    st.subheader("🆕 Elementos nuevos creados:")
                                    for elemento in elementos_creados:
                                        st.write(elemento)
                                
                                # Mostrar detalle de inserción
                                st.subheader("📋 Detalle de la inserción:")
                                detalles_text = "\n".join(datos_insertados)
                                st.text_area("Resultados de inserción:", value=detalles_text, height=200, disabled=True)
                    else:
                        st.error("❌ No hay filas válidas para insertar. Corrige los errores en tu archivo CSV.")
                        
                else:
                    st.error(f"❌ El CSV debe tener las columnas: {', '.join(required_cols)}")
                    st.info("📝 **Formato correcto del CSV:**")
                    st.code("nombre,apellidos,cargo,email,telefono,institucion")
                    
                    st.markdown("**Ejemplo de archivo CSV válido:**")
                    ejemplo_csv = """nombre,apellidos,cargo,email,telefono,institucion
Juan,Pérez García,Director,juan.perez@universidad.edu,+34123456789,Universidad Nacional
María,López Ruiz,Coordinador,maria.lopez@tecnologico.edu,+34987654321,Instituto Tecnológico"""

                    st.code(ejemplo_csv)

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
