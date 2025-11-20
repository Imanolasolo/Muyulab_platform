"""
Extracción de contactos desde Gmail usando credenciales de email existentes.
Usa IMAP para acceder al buzón y extraer contactos de correos enviados/recibidos.
"""

import imaplib
import email
from email.header import decode_header
import re
from collections import defaultdict
import streamlit as st

def extract_email_info(email_string):
    """
    Extrae nombre y email de strings como 'Juan Pérez <juan@example.com>' o 'juan@example.com'
    """
    if not email_string:
        return None, None
    
    # Patrón para "Nombre <email@domain.com>"
    match = re.match(r'(.+?)\s*<(.+?)>', email_string)
    if match:
        name = match.group(1).strip().strip('"')
        email_addr = match.group(2).strip()
        return name, email_addr
    
    # Solo email
    match = re.match(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', email_string)
    if match:
        return None, match.group(1).strip()
    
    return None, None

def connect_to_gmail(email_user, email_password):
    """
    Conecta a Gmail usando IMAP con las credenciales proporcionadas.
    """
    try:
        # Conectar a Gmail IMAP
        mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        mail.login(email_user, email_password)
        return mail, None
    except imaplib.IMAP4.error as e:
        return None, f"Error de autenticación IMAP: {str(e)}"
    except Exception as e:
        return None, f"Error de conexión: {str(e)}"

def extract_contacts_from_emails(email_user, email_password, max_emails=200):
    """
    Extrae contactos únicos desde los correos de Gmail.
    
    Args:
        email_user: Email del usuario
        email_password: Contraseña de aplicación de Gmail
        max_emails: Número máximo de correos a analizar
        
    Returns:
        list: Lista de diccionarios con contactos únicos
        str: Mensaje de error si falla
    """
    mail, error = connect_to_gmail(email_user, email_password)
    if error:
        return None, error
    
    try:
        contacts = defaultdict(lambda: {'email': '', 'nombre': '', 'count': 0})
        
        # Analizar carpetas: Enviados e Inbox
        folders_to_check = [
            '"[Gmail]/Sent Mail"',  # Enviados
            '"[Gmail]/Enviados"',   # Enviados (español)
            'INBOX'                  # Recibidos
        ]
        
        total_processed = 0
        
        for folder in folders_to_check:
            try:
                # Seleccionar carpeta
                status, _ = mail.select(folder, readonly=True)
                if status != 'OK':
                    continue
                
                # Buscar últimos correos
                status, messages = mail.search(None, 'ALL')
                if status != 'OK':
                    continue
                
                email_ids = messages[0].split()
                # Tomar los últimos N correos
                recent_ids = email_ids[-max_emails:] if len(email_ids) > max_emails else email_ids
                
                for email_id in recent_ids:
                    if total_processed >= max_emails:
                        break
                    
                    try:
                        # Obtener el correo
                        status, msg_data = mail.fetch(email_id, '(RFC822)')
                        if status != 'OK':
                            continue
                        
                        # Parse del email
                        for response_part in msg_data:
                            if isinstance(response_part, tuple):
                                msg = email.message_from_bytes(response_part[1])
                                
                                # Extraer From
                                from_header = msg.get('From', '')
                                if from_header:
                                    name, email_addr = extract_email_info(from_header)
                                    if email_addr and email_addr.lower() != email_user.lower():
                                        contacts[email_addr.lower()]['email'] = email_addr
                                        if name and not contacts[email_addr.lower()]['nombre']:
                                            contacts[email_addr.lower()]['nombre'] = name
                                        contacts[email_addr.lower()]['count'] += 1
                                
                                # Extraer To (solo de enviados)
                                if folder != 'INBOX':
                                    to_header = msg.get('To', '')
                                    if to_header:
                                        # Puede tener múltiples destinatarios
                                        to_addresses = to_header.split(',')
                                        for to_addr in to_addresses:
                                            name, email_addr = extract_email_info(to_addr)
                                            if email_addr and email_addr.lower() != email_user.lower():
                                                contacts[email_addr.lower()]['email'] = email_addr
                                                if name and not contacts[email_addr.lower()]['nombre']:
                                                    contacts[email_addr.lower()]['nombre'] = name
                                                contacts[email_addr.lower()]['count'] += 1
                                
                                # Extraer Cc
                                cc_header = msg.get('Cc', '')
                                if cc_header:
                                    cc_addresses = cc_header.split(',')
                                    for cc_addr in cc_addresses:
                                        name, email_addr = extract_email_info(cc_addr)
                                        if email_addr and email_addr.lower() != email_user.lower():
                                            contacts[email_addr.lower()]['email'] = email_addr
                                            if name and not contacts[email_addr.lower()]['nombre']:
                                                contacts[email_addr.lower()]['nombre'] = name
                                            contacts[email_addr.lower()]['count'] += 1
                        
                        total_processed += 1
                        
                    except Exception as e:
                        # Ignorar errores en correos individuales
                        continue
                
                if total_processed >= max_emails:
                    break
                    
            except Exception as e:
                # Ignorar errores en carpetas individuales
                continue
        
        # Cerrar conexión
        mail.close()
        mail.logout()
        
        # Convertir a lista y ordenar por frecuencia
        contacts_list = []
        for email_addr, data in contacts.items():
            # Separar nombre en nombre y apellidos
            full_name = data['nombre'] or ''
            parts = full_name.split(' ', 1)
            nombre = parts[0] if parts else ''
            apellidos = parts[1] if len(parts) > 1 else ''
            
            contacts_list.append({
                'nombre': nombre,
                'apellidos': apellidos,
                'email': data['email'],
                'telefono': '',
                'cargo': 'Contacto',
                'institucion': 'Red de contactos',
                'frecuencia': data['count']
            })
        
        # Ordenar por frecuencia descendente
        contacts_list.sort(key=lambda x: x['frecuencia'], reverse=True)
        
        return contacts_list, None
        
    except Exception as e:
        return None, f"Error procesando correos: {str(e)}"

def get_contacts_from_gmail_simple(email_user, email_password, max_emails=200, progress_callback=None):
    """
    Versión simplificada para usar en la UI con callback de progreso.
    
    Args:
        email_user: Email del usuario
        email_password: Contraseña de aplicación
        max_emails: Número máximo de correos a analizar
        progress_callback: Función para actualizar progreso (opcional)
        
    Returns:
        list: Lista de contactos o None si falla
        str: Mensaje de error si falla
    """
    if progress_callback:
        progress_callback("Conectando a Gmail...", 0.1)
    
    contacts, error = extract_contacts_from_emails(email_user, email_password, max_emails)
    
    if progress_callback:
        progress_callback("Contactos extraídos!", 1.0)
    
    return contacts, error
