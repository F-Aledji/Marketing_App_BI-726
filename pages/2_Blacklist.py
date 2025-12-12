import streamlit as st
import sys, os
# Damit Python die utils.py im Hauptordner findet:
sys.path.append(os.path.abspath('.'))

from utils import render_sidebar, load_blacklist_config, save_blacklist_config, log_change

st.set_page_config(page_title="Blacklist", page_icon="🚫")
render_sidebar()

st.title("🚫 Filter Verwaltung")

# 1. Config laden
config = load_blacklist_config()

tab1, tab2 = st.tabs(["🔤 Prefixe (Wörter)", "🔢 Ganze Nummern"])

# --- TAB 1: PREFIXE ---
with tab1:
    st.info("Hier sperrst du Anfänge von Nummern (z.B. 'TEL', 'CK'). Alles was so anfängt, wird blockiert.")
    
    # Anzeigen
    st.write(f"Aktuell: {', '.join(config['bad_prefixes'])}")
    
    # Hinzufügen
    col1, col2 = st.columns(2)
    new_prefix = col1.text_input("Neues Prefix", key="in_pref").upper()
    user = col2.text_input("Dein Name", key="user1")
    
    if st.button("Prefix sperren"):
        if not new_prefix:
            st.error("Bitte Prefix eingeben")
        elif new_prefix in config['bad_prefixes']:
            st.warning("Existiert schon!")
        else:
            config['bad_prefixes'].append(new_prefix)
            save_blacklist_config(config)
            log_change(user, "Add Prefix", new_prefix, "Manuell via UI")
            st.success(f"{new_prefix} gesperrt!")
            st.rerun()

# --- TAB 2: GANZE NUMMERN ---
with tab2:
    st.info("Hier sperrst du exakte Nummern (z.B. eine Referenznummer).")
    
    st.dataframe(config['bad_numbers'])
    
    c1, c2 = st.columns(2)
    new_num = c1.text_input("Ganze Nummer (ohne Leerzeichen)", key="in_num")
    user2 = c2.text_input("Dein Name", key="user2")
    
    if st.button("Nummer sperren"):
        if new_num and new_num not in config['bad_numbers']:
            config['bad_numbers'].append(new_num)
            save_blacklist_config(config)
            log_change(user2, "Add Number", new_num, "Manuell via UI")
            st.success("Gespeichert!")
            st.rerun()