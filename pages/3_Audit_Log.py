import streamlit as st
import pandas as pd
import os
import sys
sys.path.append(os.path.abspath('.'))

from utils import render_sidebar

st.set_page_config(page_title="Audit Log", page_icon="📜", layout="wide")
render_sidebar()

# --- PFAD ZUR LOG-DATEI ---
LOG_FILE = os.path.join("data", "audit_log.csv")

# --- INHALT ---
st.title("📜 Audit Log")
st.markdown("---")

st.markdown("""
## Änderungshistorie

Hier werden alle Änderungen an der Blacklist protokolliert. 
Jede Änderung wird mit Benutzer, Zeitstempel und Beschreibung dokumentiert.
""")

# --- AUDIT LOG AUS CSV LADEN ---
if os.path.exists(LOG_FILE):
    try:
        df_log = pd.read_csv(LOG_FILE, encoding="utf-8")
        # Neueste Einträge zuerst
        df_log = df_log.sort_values(by="Timestamp", ascending=False)
        
        st.success(f"📊 {len(df_log)} Einträge geladen")
        st.dataframe(df_log, width='stretch', hide_index=True)
        
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")
else:
    st.info("📭 Noch keine Einträge vorhanden. Änderungen an der Blacklist werden hier protokolliert.")

st.markdown("---")

# --- LOG STRUKTUR INFO ---
with st.expander("ℹ️ Log-Struktur Info"):
    st.markdown("""
    Jeder Eintrag enthält:
    
    | Feld | Beschreibung |
    |------|--------------|
    | **Timestamp** | Datum und Uhrzeit der Änderung |
    | **User** | Name der Person, die die Änderung durchgeführt hat |
    | **Action** | Art der Änderung (Add Prefix / Add Number / Remove) |
    | **Value** | Betroffener Wert (Prefix oder Nummer) |
    | **Reason** | Erklärung warum die Änderung vorgenommen wurde |
    """)
