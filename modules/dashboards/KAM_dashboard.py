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
    
    # Check if it's a SELECT query to fetch results
    if query.strip().upper().startswith('SELECT'):
        result = cur.fetchall()
        conn.close()
        return result
    else:
        # For INSERT, UPDATE, DELETE queries
        conn.commit()
        conn.close()
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

def get_kam_email_credentials(kam_email):
    """Obtiene las credenciales de email del KAM actual"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT email_usuario, email_password FROM kams WHERE email = ?", (kam_email,))
    result = cur.fetchone()
    conn.close()
    if result and result[0] and result[1]:
        return result[0], result[1]
    return None, None

def send_email_with_kam_credentials(dest_email, subject, body, kam_email):
    """Envía email usando las credenciales del KAM"""
    email_user, email_pass = get_kam_email_credentials(kam_email)
    
    if not email_user or not email_pass:
        st.error("⚠️ No tienes configuradas tus credenciales de email. Contacta al administrador para configurarlas.")
        return False
    
    msg = MIMEMultipart()
    msg["From"] = email_user
    msg["To"] = dest_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(email_user, email_pass)
            server.sendmail(email_user, dest_email, msg.as_string())
        return True
    except smtplib.SMTPAuthenticationError as e:
        if "Username and Password not accepted" in str(e):
            st.error("🔐 **Error de Autenticación Gmail**")
            st.markdown("""
            **Posibles soluciones:**
            
            1. **Verificar Contraseña de Aplicación:**
               - Asegúrate de usar una **contraseña de aplicación** (16 caracteres)
               - NO uses tu contraseña normal de Gmail
            
            2. **Configurar Cuenta Gmail:**
               - Activa la **verificación en 2 pasos**
               - Ve a [Contraseñas de aplicación](https://myaccount.google.com/apppasswords)
               - Genera una nueva contraseña para "Mail"
            
            3. **Verificar Email:**
               - Confirma que el email `{email_user}` sea correcto
               - Debe ser una cuenta Gmail válida
            
            4. **Contactar Administrador:**
               - Solicita que actualice tus credenciales de email
            """.format(email_user=email_user))
        else:
            st.error(f"Error de autenticación: {e}")
        return False
    except smtplib.SMTPRecipientsRefused:
        st.error(f"❌ El email '{dest_email}' no es válido o fue rechazado")
        return False
    except smtplib.SMTPServerDisconnected:
        st.error("❌ Error de conexión con el servidor de Gmail. Intenta nuevamente.")
        return False
    except Exception as e:
        st.error(f"❌ Error inesperado enviando email: {e}")
        return False

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

def show_kam_dashboard():
    # Obtener el email del KAM actual
    user = st.session_state.get("user", {})
    kam_email = user.get("email", "")
    
    # Obtener el ID y nombre del KAM actual
    kam_data = run_query("SELECT id, nombre FROM kams WHERE email = ?", (kam_email,))
    if not kam_data:
        st.error("❌ No se pudo encontrar tu información de KAM. Contacta al administrador.")
        return
    
    kam_id = kam_data[0][0]
    kam_nombre = kam_data[0][1]

    # Mensaje de bienvenida personalizado en el sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"### 👋 ¡Hola, **{kam_nombre}**!")
    st.sidebar.markdown("Bienvenido a tu panel KAM")
    st.sidebar.markdown("---")

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

    st.image("assets/muyu_logo.jpg", width=200)
    st.header("Panel KAM: :red[Seguimiento de Instituciones y Clientes]")

    # Ver instituciones ASIGNADAS al KAM
    st.subheader(":blue[Instituciones asignadas]")
    instituciones = run_query("""
        SELECT i.id, i.nombre, i.ciudad, i.anio_programa 
        FROM instituciones i 
        JOIN kam_institucion ki ON i.id = ki.institucion_id 
        WHERE ki.kam_id = ?
    """, (kam_id,))
    
    if instituciones:
        for inst in instituciones:
            st.markdown(f"**{inst[1]}** ({inst[2]}) - {inst[3]}")
    else:
        st.info("No tienes instituciones asignadas. Contacta al administrador para que te asigne instituciones.")
        return  # Si no tiene instituciones asignadas, no mostrar el resto del panel

    # ---------------- Contactos CRUD ----------------
    if menu == "Contactos":
        with st.expander("Administrar Contactos"):
            st.subheader(":blue[Gestión de Contactos]")
            acciones_contacto = [
                "Registrar contacto", "Modificar contacto", "Borrar contacto", "Ver contactos", "Carga masiva"
            ]
            accion_contacto = st.selectbox("Selecciona una acción:", acciones_contacto)

            # Solo mostrar instituciones ASIGNADAS al KAM
            instituciones = run_query("""
                SELECT i.id, i.nombre 
                FROM instituciones i 
                JOIN kam_institucion ki ON i.id = ki.institucion_id 
                WHERE ki.kam_id = ?
            """, (kam_id,))
            
            institucion_dict = {nombre: iid for iid, nombre in instituciones}
            roles = run_query("SELECT nombre FROM roles")
            roles_list = [r[0] for r in roles] if roles else []

            if accion_contacto == "Registrar contacto":
                if not instituciones:
                    st.warning("⚠️ No tienes instituciones asignadas. No puedes registrar contactos.")
                    return
                    
                institucion_nombre = st.selectbox("Institución", list(institucion_dict.keys()))
                institucion_id = institucion_dict[institucion_nombre]
                nombre = st.text_input("Nombre")
                apellidos = st.text_input("Apellidos")
                cargo = st.selectbox("Cargo", roles_list)
                email = st.text_input("Email institucional")
                telefono = st.text_input("Teléfono celular, :red[número compatible con WhatsApp]")
                if st.button("Guardar Contacto"):
                    run_query("INSERT INTO contactos (nombre, apellidos, cargo, email, telefono, institucion_id) VALUES (?, ?, ?, ?, ?, ?)",
                            (nombre, apellidos, cargo, email, telefono, institucion_id))
                    st.success("Contacto agregado correctamente")

            elif accion_contacto == "Ver contactos":
                st.write("### Lista de Contactos")
                # Solo mostrar contactos de instituciones asignadas al KAM
                contactos = run_query("""
                    SELECT c.nombre, c.apellidos, c.cargo, c.email, c.telefono, i.nombre as institucion
                    FROM contactos c 
                    JOIN instituciones i ON c.institucion_id = i.id
                    JOIN kam_institucion ki ON i.id = ki.institucion_id 
                    WHERE ki.kam_id = ?
                    ORDER BY i.nombre, c.nombre
                """, (kam_id,))
                
                if contactos:
                    # Agrupar por institución para mejor visualización
                    instituciones_agrupadas = {}
                    for c in contactos:
                        institucion = c[5]  # nombre de la institución
                        if institucion not in instituciones_agrupadas:
                            instituciones_agrupadas[institucion] = []
                        
                        nombre_completo = f"{c[0]} {c[1] or ''}".strip()
                        instituciones_agrupadas[institucion].append({
                            'nombre': nombre_completo,
                            'cargo': c[2],
                            'email': c[3],
                            'telefono': c[4]
                        })
                    
                    # Mostrar contactos agrupados por institución
                    for institucion, contactos_inst in instituciones_agrupadas.items():
                        st.markdown(f"#### 🏛️ **{institucion}**")
                        for contacto in contactos_inst:
                            st.write(f"• **{contacto['nombre']}** - {contacto['cargo']} | {contacto['email']} | {contacto['telefono']}")
                        st.markdown("---")
                else:
                    st.info("No hay contactos registrados en tus instituciones asignadas.")

            elif accion_contacto == "Modificar contacto":
                st.write("### Modificar Contacto")
                # Solo mostrar contactos de instituciones asignadas al KAM
                contactos = run_query("""
                    SELECT c.id, c.nombre, c.apellidos, c.cargo, c.email, c.telefono, c.institucion_id 
                    FROM contactos c 
                    JOIN instituciones i ON c.institucion_id = i.id
                    JOIN kam_institucion ki ON i.id = ki.institucion_id 
                    WHERE ki.kam_id = ?
                """, (kam_id,))
                
                if contactos:
                    contacto_dict = {f"{c[1]} {c[2] or ''} - {c[3]} | {c[4]} | {c[5]}".strip(): c[0] for c in contactos}
                    contacto_sel = st.selectbox("Selecciona contacto", list(contacto_dict.keys()), key="mod_contacto_kam")
                    contacto_id = contacto_dict[contacto_sel]
                    contacto_data = run_query("SELECT nombre, apellidos, cargo, email, telefono, institucion_id FROM contactos WHERE id = ?", (contacto_id,))
                    if contacto_data:
                        contacto_data = contacto_data[0]  # Get first row
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
                    st.info("No hay contactos registrados en tus instituciones asignadas.")

            elif accion_contacto == "Borrar contacto":
                st.write("### Borrar Contacto")
                # Solo mostrar contactos de instituciones asignadas al KAM
                contactos = run_query("""
                    SELECT c.id, c.nombre, c.apellidos, c.cargo, c.email, c.telefono 
                    FROM contactos c 
                    JOIN instituciones i ON c.institucion_id = i.id
                    JOIN kam_institucion ki ON i.id = ki.institucion_id 
                    WHERE ki.kam_id = ?
                """, (kam_id,))
                
                if contactos:
                    contacto_dict = {f"{c[1]} {c[2] or ''} - {c[3]} | {c[4]} | {c[5]}".strip(): c[0] for c in contactos}
                    contacto_sel = st.selectbox("Selecciona contacto", list(contacto_dict.keys()), key="del_contacto_kam")
                    contacto_id = contacto_dict[contacto_sel]
                    if st.button("Borrar contacto", key="borrar_contacto_kam"):
                        run_query("DELETE FROM contactos WHERE id = ?", (contacto_id,))
                        st.success("Contacto eliminado correctamente")
                        st.rerun()
                else:
                    st.info("No hay contactos registrados en tus instituciones asignadas.")

            elif accion_contacto == "Carga masiva":
                if not instituciones:
                    st.warning("⚠️ No tienes instituciones asignadas. No puedes realizar carga masiva.")
                    return
                    
                st.write("### Carga masiva de contactos")
                st.info("ℹ️ Solo puedes agregar contactos a las instituciones que tienes asignadas.")

                st.markdown("""
**Formato requerido para la hoja de cálculo:**

La plantilla debe tener los siguientes encabezados (en la primera fila):
- Institución
- Nombre
- Apellidos
- Cargo
- Directivo
- Email institucional
- Teléfono celular, número compatible con WhatsApp

Puedes descargar una plantilla de ejemplo en Excel para facilitar el proceso.
""")

                import pandas as pd
                import io
                def generar_plantilla_excel():
                    columnas = [
                        "Institución",
                        "Nombre",
                        "Apellidos",
                        "Cargo",
                        "Directivo",
                        "Email institucional",
                        "Teléfono celular, número compatible con WhatsApp"
                    ]
                    df = pd.DataFrame(columns=columnas)
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False)
                    return output.getvalue()

                st.download_button(
                    label="Descargar plantilla Excel de contactos",
                    data=generar_plantilla_excel(),
                    file_name="plantilla_contactos.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                csv_file = st.file_uploader("Subir archivo CSV o Excel de contactos", type=["csv", "xlsx"])
                if csv_file is not None:
                    # Detectar tipo de archivo y leer
                    import io
                    import pandas as pd
                    if csv_file.name.endswith(".csv"):
                        df = pd.read_csv(csv_file)
                    elif csv_file.name.endswith(".xlsx"):
                        df = pd.read_excel(csv_file)
                    else:
                        st.error("Formato de archivo no soportado. Usa CSV o Excel (.xlsx)")
                        return
                    # Normalizar nombres de columnas para aceptar variantes (mayúsculas, espacios, acentos)
                    import unicodedata, re
                    def _norm(s):
                        s = str(s or "").lower().strip()
                        s = unicodedata.normalize('NFKD', s)
                        s = ''.join(c for c in s if not unicodedata.combining(c))
                        s = re.sub(r'[^a-z0-9]', '', s)
                        return s

                    # Mapeo de variantes conocidas a nombres canónicos
                    variants = {
                        'nombre': ['nombre', 'name'],
                        'apellidos': ['apellidos', 'apellido', 'surname'],
                        'cargo': ['cargo', 'directivo', 'puesto', 'rol', 'position'],
                        'email': ['email', 'emailinstitucional', 'email_institucional', 'emailinstitucional', 'emailinstitucional'],
                        'telefono': ['telefono', 'telefonocelular', 'telefono_celular', 'telefono celular', 'telefono celular numero compatible con whatsapp', 'telefono celular numero compatible con whatsapp'],
                        'institucion': ['institucion', 'institucionnombre', 'institucion_nombre', 'institución', 'institucion']
                    }

                    # Construir mapa de columnas del archivo a nombres canónicos
                    col_map = {}
                    norms_to_canonical = {}
                    for canon, vals in variants.items():
                        for v in vals:
                            norms_to_canonical[_norm(v)] = canon

                    for col in list(df.columns):
                        n = _norm(col)
                        if n in norms_to_canonical:
                            col_map[col] = norms_to_canonical[n]

                    # Build mapping canonical -> original columns (in file order)
                    canonical_to_originals = {}
                    for orig_col in list(df.columns):
                        if orig_col in col_map:
                            canon = col_map[orig_col]
                            canonical_to_originals.setdefault(canon, []).append(orig_col)

                    # Priority lists for certain canonicals: prefer explicit 'cargo' over 'directivo'
                    priority_norms = {
                        'cargo': ['cargo', 'directivo', 'puesto', 'rol', 'position']
                    }

                    # Coalesce original columns into canonical columns using priority order
                    for canon in ["nombre", "apellidos", "cargo", "email", "telefono", "institucion"]:
                        originals = canonical_to_originals.get(canon, [])
                        if not originals:
                            continue
                        # If there is a priority ordering for this canonical, sort originals accordingly
                        if canon in priority_norms:
                            pri = priority_norms[canon]
                            def _prio_key(colname):
                                n = _norm(colname)
                                try:
                                    return pri.index(n)
                                except ValueError:
                                    return len(pri) + originals.index(colname)
                            originals = sorted(originals, key=_prio_key)

                        if len(originals) > 1:
                            try:
                                df[canon] = df[originals].bfill(axis=1).iloc[:, 0]
                            except Exception:
                                df[canon] = df[originals[0]]
                        else:
                            df[canon] = df[originals[0]]

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
                        
                    # Análisis y validación
                    if required_cols.issubset(df.columns):
                        # Validar cada fila ANTES de mostrar la tabla
                        validated_data = []
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
                                'valido': True
                            }
                            
                            # Buscar institución con coincidencia exacta e insensible a mayúsculas
                            institucion_id = None
                            institucion_encontrada = None
                            for inst_name, inst_id in inst_map_display.items():
                                if inst_name.lower().strip() == row_data['institucion'].lower().strip():
                                    institucion_id = inst_id
                                    institucion_encontrada = inst_name
                                    break
                            row_data['institucion_id'] = institucion_id
                            
                            # Validaciones mejoradas
                            if not institucion_id:
                                disponibles = list(inst_map_display.keys())
                                row_data['errores'].append(f"Institución '{row_data['institucion']}' no encontrada")
                                row_data['valido'] = False
                                st.write(f"❌ Fila {row_data['fila']}: Institución '{row_data['institucion']}' no coincide con ninguna de: {disponibles}")
                            
                            if row_data['cargo'] not in roles_set:
                                row_data['errores'].append(f"Cargo '{row_data['cargo']}' no válido")
                                row_data['valido'] = False
                                st.write(f"❌ Fila {row_data['fila']}: Cargo '{row_data['cargo']}' no coincide con ninguno de: {roles_list}")
                            
                            if not row_data['nombre']:
                                row_data['errores'].append("Nombre vacío")
                                row_data['valido'] = False
                            
                            if not row_data['email'] or "@" not in row_data['email']:
                                row_data['errores'].append("Email inválido")
                                row_data['valido'] = False
                            
                            validated_data.append(row_data)
                        
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
                                            new_inst_id = run_query("SELECT id FROM instituciones WHERE nombre = ?", (nueva_inst,))[0][0]
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
                                                # Evitar duplicados: comprobar si ya existe contacto con mismo email y misma institución
                                                exists = run_query(
                                                    "SELECT id FROM contactos WHERE email = ? AND institucion_id = ?",
                                                    (row_data['email'], final_inst_id)
                                                )
                                                if exists:
                                                    datos_insertados.append(f"⚠️ Fila {row_data['fila']}: Contacto ya existe (email) - se omitió: {row_data['nombre']} {row_data['apellidos']}")
                                                else:
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
                                    total_contactos = run_query("SELECT COUNT(*) FROM contactos")[0][0]
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

    if menu == "Mensajes":
        # Enviar mensaje
        with st.expander("Enviar y gestionar mensajes"):
            st.subheader(":orange[Enviar mensaje]")
            
            # Verificar si el KAM tiene credenciales configuradas
            email_user, email_pass = get_kam_email_credentials(kam_email)
            
            if not email_user or not email_pass:
                st.warning("⚠️ **Configuración de Email Requerida**")
                st.info("Para poder enviar mensajes, necesitas configurar tus credenciales de email. Contacta al administrador del sistema.")
                st.markdown("📧 **Email configurado:** No configurado")
                
                # Mostrar instrucciones para el usuario
                with st.expander("📖 Instrucciones para configurar Gmail", expanded=False):
                    st.markdown("""
                    **Pasos para configurar tu email:**
                    
                    1. **Activar verificación en 2 pasos:**
                       - Ve a [Seguridad de Google](https://myaccount.google.com/security)
                       - Activa la "Verificación en 2 pasos"
                    
                    2. **Generar contraseña de aplicación:**
                       - Ve a [Contraseñas de aplicación](https://myaccount.google.com/apppasswords)
                       - Selecciona "Mail" como aplicación
                       - Copia la contraseña de 16 caracteres
                    
                    3. **Contactar administrador:**
                       - Proporciona tu email de Gmail
                       - Proporciona la contraseña de aplicación generada
                    
                    **⚠️ Importante:** Nunca uses tu contraseña normal de Gmail
                    """)
            else:
                st.success(f"📧 **Email configurado:** {email_user}")
                
                # Botón para probar credenciales
                if st.button("🔍 Probar credenciales de email", key="test_email"):
                    test_result = test_email_credentials(email_user, email_pass)
                    if test_result:
                        st.success("✅ Credenciales de email funcionan correctamente")
                    else:
                        st.error("❌ Error con las credenciales. Contacta al administrador.")

            tipo = st.selectbox("Tipo de mensaje", [
                "Seguimiento", 
                "Recordatorio de agenda", 
                "Entrega de informe", 
                "Motivacional",
                "Resolución de dudas",
                "Tendencias"
            ])
            # Mensajes pregrabados filtrados por tipo
            mensajes_pre = run_query("SELECT id, titulo, cuerpo FROM mensajes WHERE tipo = ?", (tipo,))
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
            
            # Paso 2: Seleccionar contacto(s) de la institución asignada
            contactos_inst = run_query("""
                SELECT c.id, c.nombre, c.apellidos, c.cargo, c.email 
                FROM contactos c 
                WHERE c.institucion_id = ?
            """, (inst_id,)) if inst_id else []
            
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
                if not email_user or not email_pass:
                    st.error("No puedes enviar mensajes sin configurar tus credenciales de email.")
                else:
                    success_count = 0
                    for contacto_id in contacto_ids:
                        # Obtener datos del contacto
                        contacto_data = run_query("SELECT nombre, apellidos, email FROM contactos WHERE id = ?", (contacto_id,))
                        if contacto_data:
                            contacto_data = contacto_data[0]  # Get first row
                            solo_nombre = contacto_data[0].strip()  # Solo el nombre, sin apellidos
                            
                            # Crear mensaje personalizado
                            if usar_saludo:
                                mensaje_personalizado = f"{saludo_personalizado} {solo_nombre},\n\n{cuerpo_base}"
                            else:
                                mensaje_personalizado = cuerpo_base
                            
                            # Guardar mensaje en historial
                            run_query("INSERT INTO mensajes (titulo, cuerpo, tipo, fecha_envio_programada) VALUES (?, ?, ?, ?)",
                                    (titulo, mensaje_personalizado, tipo, str(fecha_hora_envio)))
                            
                            # Enviar email con credenciales del KAM
                            if contacto_data[2]:  # Si tiene email
                                if send_email_with_kam_credentials(contacto_data[2], titulo, mensaje_personalizado, kam_email):
                                    success_count += 1
                                else:
                                    st.warning(f"El email no pudo ser enviado a {contacto_data[2]}")
                    
                    if success_count > 0:
                        st.success(f"Mensaje enviado exitosamente a {success_count} contacto(s) desde {email_user}")
                    else:
                        st.error("No se pudo enviar el mensaje a ningún contacto.")
            
            # Botones de WhatsApp para cada contacto seleccionado
            if contacto_ids and titulo and cuerpo_base:
                st.subheader("Enviar por WhatsApp")
                for contacto_id in contacto_ids:
                    contacto_data = run_query("SELECT nombre, apellidos, telefono FROM contactos WHERE id = ?", (contacto_id,))
                    if contacto_data:
                        contacto_data = contacto_data[0]  # Get first row
                        solo_nombre = contacto_data[0].strip()  # Solo el nombre, sin apellidos
                        nombre_completo = f"{contacto_data[0]} {contacto_data[1] or ''}".strip()  # Para mostrar en el botón
                        telefono = contacto_data[2]
                        
                        # Crear mensaje personalizado para WhatsApp
                        if usar_saludo:
                            mensaje_wa = f"{saludo_personalizado} {solo_nombre},\n\n{cuerpo_base}"
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
            
            mensajes = run_query("SELECT titulo, tipo, fecha_envio_programada, enviado FROM mensajes ORDER BY fecha_envio_programada DESC")
            for m in mensajes:
                status = "✅ Enviado" if m[3] else "⏳ Pendiente"
                st.write(f"{m[0]} | {m[1]} | {m[2]} | {status}")
