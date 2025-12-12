import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Audit Log", page_icon="📜", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://via.placeholder.com/150x50?text=LOGO", use_container_width=True)
    st.markdown("---")
    st.markdown("[🔗 Externer Link (Platzhalter)](https://example.com)")

# --- SESSION WARNUNG ---
st.warning("⚠️ **Hinweis:** Wenn Sie die Hauptseite verlassen, wird die aktuelle Session zurückgesetzt. Analyseergebnisse gehen verloren, falls nicht gespeichert!")

# --- AUDIT LOG INITIALISIERUNG ---
if "audit_log" not in st.session_state:
    st.session_state["audit_log"] = []

# --- INHALT ---
st.title("📜 Audit Log")
st.markdown("---")

st.markdown("""
## Änderungshistorie

Hier werden alle Änderungen an der Blacklist protokolliert. 
Jede Änderung wird mit Benutzer, Zeitstempel und Beschreibung dokumentiert.
""")

# --- AUDIT LOG ANZEIGE ---
if st.session_state["audit_log"]:
    df_log = pd.DataFrame(st.session_state["audit_log"])
    # Neueste Einträge zuerst
    df_log = df_log.sort_values(by="Zeitstempel", ascending=False)
    
    st.dataframe(df_log, use_container_width=True, hide_index=True)
    
    # Export-Option
    if st.button("📥 Log als CSV exportieren"):
        csv = df_log.to_csv(index=False)
        st.download_button(
            label="💾 Download CSV",
            data=csv,
            file_name=f"audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
else:
    st.info("📭 Noch keine Einträge vorhanden. Änderungen an der Blacklist werden hier protokolliert.")

st.markdown("---")

# --- LOG STRUKTUR INFO ---
with st.expander("ℹ️ Log-Struktur Info"):
    st.markdown("""
    Jeder Eintrag enthält:
    
    | Feld | Beschreibung |
    |------|--------------|
    | **Zeitstempel** | Datum und Uhrzeit der Änderung |
    | **Benutzer** | Name der Person, die die Änderung durchgeführt hat |
    | **Aktion** | Art der Änderung (Hinzugefügt/Entfernt/Bearbeitet) |
    | **Artikelnummer** | Betroffene Artikelnummer |
    | **Begründung** | Erklärung warum die Änderung vorgenommen wurde |
    """)
