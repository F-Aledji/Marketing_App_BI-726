import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime

# Pfade definieren
DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "blacklist.json")
LOG_FILE = os.path.join(DATA_DIR, "audit_log.csv")

# --- SPEICHERUNG / LADEN ---

def load_blacklist_config():
    """Lädt die Blacklist (Prefixe und Nummern) aus der JSON."""
    if not os.path.exists(DATA_FILE):
        # Fallback, falls Datei noch nicht existiert
        return {"bad_prefixes": [], "bad_numbers": []}
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Fehler beim Laden der Config: {e}")
        return {"bad_prefixes": [], "bad_numbers": []}

def save_blacklist_config(config):
    """Speichert die Config zurück in die JSON."""
    # Ordner erstellen falls nicht existent
    os.makedirs(DATA_DIR, exist_ok=True)
    
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def log_change(user, action, value, reason):
    """Schreibt einen Eintrag ins Audit-Log (CSV)."""
    os.makedirs(DATA_DIR, exist_ok=True)
    file_exists = os.path.exists(LOG_FILE)
    
    entry = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "User": user,
        "Action": action,
        "Value": value,
        "Reason": reason
    }
    
    df = pd.DataFrame([entry])
    # Hängt die Zeile unten an (mode='a')
    df.to_csv(LOG_FILE, mode='a', header=not file_exists, index=False, encoding="utf-8")

# --- UI KOMPONENTEN ---

def render_sidebar():
    """Zentrale Sidebar für alle Seiten"""
    with st.sidebar:
        # Streamlit generiert die Links für den 'pages' Ordner automatisch
        pass