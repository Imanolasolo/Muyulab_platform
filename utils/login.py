import streamlit as st
from modules.users import authenticate_user
from utils.auth import create_jwt, decode_jwt
from urllib.parse import quote

def login_form():
    st.subheader("Bienvenidos a :red[MuyuLAB], tu plataforma de gestión educativa")
    col1, col2 = st.columns([2, 2])
    with col1:
        st.subheader(":blue[Iniciar sesión]")
        email = st.text_input("Email")
        password = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            user = authenticate_user(email, password)
            if user:
                token = create_jwt(user)
                st.session_state["jwt_token"] = token
                st.session_state["user"] = user
                st.success(f"Bienvenido, {user['nombre']} ({user['rol']})")
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    with col2:
        with st.expander("Instrucciones de acceso"):
            st.markdown("""
            - Los KAMs (Key Account Managers) y administradores deben iniciar sesión con sus credenciales.
            - Si no tienes una cuenta, contacta al administrador del sistema.
            - Asegúrate de usar un email institucional válido.
            """)
            whatsapp_text = "Hola, necesito ayuda con mi cuenta de MuyuLAB."
            whatsapp_url = f"https://wa.me/+593993513082?text={quote(whatsapp_text)}"
            st.markdown(f"[Registro por WhatsApp](<{whatsapp_url}>)", unsafe_allow_html=True)

def require_login():
    token = st.session_state.get("jwt_token")
    if not token or not decode_jwt(token):
        login_form()
        st.stop()
