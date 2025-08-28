import streamlit as st
from modules.users import authenticate_user
from utils.auth import create_jwt, decode_jwt

def login_form():
    st.subheader("Iniciar sesión")
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

def require_login():
    token = st.session_state.get("jwt_token")
    if not token or not decode_jwt(token):
        login_form()
        st.stop()
