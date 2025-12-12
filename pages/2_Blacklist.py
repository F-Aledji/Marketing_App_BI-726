import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Blacklist", page_icon="🚫", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://via.placeholder.com/150x50?text=LOGO", use_container_width=True)
    st.markdown("---")
    st.markdown("[🔗 Externer Link (Platzhalter)](https://example.com)")

# --- SESSION WARNUNG ---
st.warning("⚠️ **Hinweis:** Wenn Sie die Hauptseite verlassen, wird die aktuelle Session zurückgesetzt. Analyseergebnisse gehen verloren, falls nicht gespeichert!")

# --- INITIALISIERUNG ---
if "blacklist" not in st.session_state:
    st.session_state["blacklist"] = []

if "audit_log" not in st.session_state:
    st.session_state["audit_log"] = []

# --- HILFSFUNKTION: AUDIT LOG EINTRAG ---
def add_audit_entry(benutzer: str, aktion: str, artikelnummer: str, begruendung: str):
    """Fügt einen Eintrag zum Audit-Log hinzu."""
    st.session_state["audit_log"].append({
        "Zeitstempel": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Benutzer": benutzer,
        "Aktion": aktion,
        "Artikelnummer": artikelnummer,
        "Begründung": begruendung
    })

# --- INHALT ---
st.title("🚫 Blacklist")
st.markdown("---")

st.markdown("## Gesperrte Artikelnummern verwalten")

# --- AKTUELLE BLACKLIST ---
st.subheader("📋 Aktuelle Blacklist")

if st.session_state["blacklist"]:
    df_blacklist = pd.DataFrame(st.session_state["blacklist"])
    st.dataframe(df_blacklist, use_container_width=True, hide_index=True)
else:
    st.info("Keine Einträge in der Blacklist vorhanden.")

st.markdown("---")

# --- NEUE NUMMER HINZUFÜGEN ---
st.subheader("➕ Nummer zur Blacklist hinzufügen")

col1, col2 = st.columns(2)

with col1:
    benutzer_name = st.text_input("👤 Ihr Name *", placeholder="z.B. Max Mustermann")
    artikel_nummer = st.text_input("🔢 Artikelnummer *", placeholder="z.B. 62 070 97")

with col2:
    grund = st.selectbox("📌 Grund", [
        "Falsche Erkennung",
        "Duplikat",
        "Veraltet/Auslaufend",
        "Testdaten",
        "Sonstiges"
    ])
    begruendung = st.text_area("📝 Begründung *", placeholder="Erklären Sie kurz, warum diese Nummer gesperrt wird...")

if st.button("✅ Zur Blacklist hinzufügen", type="primary"):
    if not benutzer_name.strip():
        st.error("Bitte geben Sie Ihren Namen ein.")
    elif not artikel_nummer.strip():
        st.error("Bitte geben Sie eine Artikelnummer ein.")
    elif not begruendung.strip():
        st.error("Bitte geben Sie eine Begründung ein.")
    else:
        # Zur Blacklist hinzufügen
        st.session_state["blacklist"].append({
            "Artikelnummer": artikel_nummer.strip(),
            "Grund": grund,
            "Hinzugefügt von": benutzer_name.strip(),
            "Datum": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        
        # Audit-Log Eintrag
        add_audit_entry(
            benutzer=benutzer_name.strip(),
            aktion="Hinzugefügt",
            artikelnummer=artikel_nummer.strip(),
            begruendung=f"{grund}: {begruendung.strip()}"
        )
        
        st.success(f"✅ '{artikel_nummer}' wurde zur Blacklist hinzugefügt und im Audit-Log protokolliert.")
        st.rerun()

st.markdown("---")

# --- NUMMER ENTFERNEN ---
st.subheader("➖ Nummer von Blacklist entfernen")

if st.session_state["blacklist"]:
    nummern_liste = [item["Artikelnummer"] for item in st.session_state["blacklist"]]
    
    col1, col2 = st.columns(2)
    
    with col1:
        benutzer_entfernen = st.text_input("👤 Ihr Name (für Entfernung) *", placeholder="z.B. Max Mustermann", key="remove_user")
        nummer_entfernen = st.selectbox("Nummer auswählen", nummern_liste)
    
    with col2:
        begruendung_entfernen = st.text_area("📝 Begründung für Entfernung *", placeholder="Warum wird diese Nummer entsperrt?", key="remove_reason")
    
    if st.button("🗑️ Von Blacklist entfernen", type="secondary"):
        if not benutzer_entfernen.strip():
            st.error("Bitte geben Sie Ihren Namen ein.")
        elif not begruendung_entfernen.strip():
            st.error("Bitte geben Sie eine Begründung ein.")
        else:
            # Aus Blacklist entfernen
            st.session_state["blacklist"] = [
                item for item in st.session_state["blacklist"] 
                if item["Artikelnummer"] != nummer_entfernen
            ]
            
            # Audit-Log Eintrag
            add_audit_entry(
                benutzer=benutzer_entfernen.strip(),
                aktion="Entfernt",
                artikelnummer=nummer_entfernen,
                begruendung=begruendung_entfernen.strip()
            )
            
            st.success(f"✅ '{nummer_entfernen}' wurde von der Blacklist entfernt und im Audit-Log protokolliert.")
            st.rerun()
else:
    st.info("Keine Einträge zum Entfernen vorhanden.")
