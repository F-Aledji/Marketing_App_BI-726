import streamlit as st
import sys, os
sys.path.append(os.path.abspath('.'))

from utils import render_sidebar

st.set_page_config(page_title="Infos", page_icon="ℹ️", layout="wide")
render_sidebar()

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
