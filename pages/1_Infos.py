import streamlit as st

st.set_page_config(page_title="Infos", page_icon="ℹ️", layout="wide")

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://via.placeholder.com/150x50?text=LOGO", use_container_width=True)
    st.markdown("---")
    st.markdown("[🔗 Externer Link (Platzhalter)](https://example.com)")

# --- SESSION WARNUNG ---
st.warning("⚠️ **Hinweis:** Wenn Sie die Hauptseite verlassen, wird die aktuelle Session zurückgesetzt. Analyseergebnisse gehen verloren, falls nicht gespeichert!")

# --- INHALT ---
st.title("ℹ️ Infos")
st.markdown("---")

st.markdown("""
## Platzhalter für Informationen

Hier können allgemeine Informationen zur Anwendung eingefügt werden:

- **Version:** 1.0.0
- **Autor:** [Platzhalter]
- **Beschreibung:** [Platzhalter]

### Anleitung
1. [Platzhalter für Schritt 1]
2. [Platzhalter für Schritt 2]
3. [Platzhalter für Schritt 3]

### Kontakt
[Platzhalter für Kontaktinformationen]
""")
