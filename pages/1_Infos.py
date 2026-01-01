import streamlit as st
from core.ui.sidebar import show_sidebar

# Konfiguration der Seite
st.set_page_config(page_title="Infos", page_icon="ℹ️", layout="wide")
show_sidebar()




# --- INHALT ---
st.title("ℹ️ Infos")
st.markdown("---")

st.markdown("""
## Artikelnummer-Suche App

Diese Anwendung extrahiert Artikelnummern aus PDF-Dateien und klassifiziert sie automatisch.

### Features
- **Dual-Engine Extraktion:** Zwei Such-Engines werden kombiniert um eine höhere Trefferquote zu erzielen
- **KI-Prüfung:** Automatische Erkennung von falschen Treffern mittels KI
- **3-Kategorien System:** Sicher, Unsicher, Spam(Löschkandidaten)

### Kategorien erklärt
| Kategorie | Bedeutung |
|-----------|-----------|
| 🟢 **Sicher** | Von beiden Engines gefunden, KI-geprüft |
| 🟡 **Unsicher** | Nur von einer Engine gefunden |
| 🔴 **Spam** | Wahrscheinlich falsche Nummern (Tel, Fax, etc.) |

---

## Blacklist
Die Anwendung verwendet eine Blacklist um unerwünschte Artikelnummern und Präfix-Zeichen zu filtern.
Treffer, die auf der Blacklist für Nummern oder Präfixe stehen, werden komplett aussortiert.
Treffer, in deren Umfeld "verbotene" Wörter (z.B. Tel, Fax) stehen, werden als Spam klassifiziert.
Die Blacklist (gesperrte Prefixe, Nummern, Kontext-Wörter) wird zentral durch IT Data Analytics gepflegt.

**Änderungswünsche bitte als Jira-Ticket einreichen (siehe Sidebar).**

Bitte im Ticket angeben:
- Welcher Wert soll hinzugefügt/entfernt werden?
- Begründung für die Änderung
- Beispiel-PDF falls relevant


---

### Kontakt
Bei Fragen oder Problemen wenden Sie sich über das Ticketsystem an das BI-Team.
""")
