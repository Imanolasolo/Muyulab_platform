import streamlit as st
import sqlite3
import json
from datetime import datetime
from openai import OpenAI

# Conexión a SQLite
conn = sqlite3.connect("tickets.db")
c = conn.cursor()
c.execute("""CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT,
    descripcion TEXT,
    resumen TEXT,
    categoria TEXT,
    prioridad TEXT,
    estado TEXT,
    fecha TEXT
)""")
conn.commit()

# Cliente OpenAI
client = OpenAI()

st.title("📌 Sistema de Incidencias - Muyu App")

# Formulario usuario
usuario = st.text_input("Tu nombre o correo")
descripcion = st.text_area("Describe la incidencia")

if st.button("Enviar incidencia"):
    # Procesar con OpenAI
    prompt = f"""
    Clasifica y resume esta incidencia de soporte:
    {descripcion}
    Responde en JSON con claves: resumen, categoria, prioridad.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    
    try:
        # Parse JSON response safely
        response_content = response.choices[0].message.content
        # Remove markdown code blocks if present
        if response_content.startswith("```json"):
            response_content = response_content.strip("```json").strip("```").strip()
        
        datos = json.loads(response_content)
        
        # Validate required fields
        required_fields = ["resumen", "categoria", "prioridad"]
        if not all(field in datos for field in required_fields):
            raise ValueError("Missing required fields in OpenAI response")
        
        # Guardar en BD
        c.execute("INSERT INTO tickets (usuario, descripcion, resumen, categoria, prioridad, estado, fecha) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (usuario, descripcion, datos["resumen"], datos["categoria"], datos["prioridad"], "nuevo", datetime.now().isoformat()))
        conn.commit()
        st.success("✅ Incidencia registrada con éxito")
        
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        st.error(f"❌ Error procesando la respuesta: {str(e)}")
        # Fallback: save with default values
        c.execute("INSERT INTO tickets (usuario, descripcion, resumen, categoria, prioridad, estado, fecha) VALUES (?, ?, ?, ?, ?, ?, ?)",
                  (usuario, descripcion, descripcion[:100], "general", "media", "nuevo", datetime.now().isoformat()))
        conn.commit()
        st.warning("⚠️ Incidencia guardada con valores por defecto")

# Panel básico
st.subheader("📊 Tickets registrados")
tickets = c.execute("SELECT * FROM tickets").fetchall()
st.table(tickets)
