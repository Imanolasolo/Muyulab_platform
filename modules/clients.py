# Module for client-specific functionality
import streamlit as st
import sqlite3

DB_PATH = "database/muyulab.db"

def run_query(query, params=()):
    """Execute database query"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    return cur

def show_client_dashboard():
    """Client dashboard functionality"""
    st.header("Panel Cliente")
    st.info("Funcionalidad específica para clientes en desarrollo.")
