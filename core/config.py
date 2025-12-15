
## Hier werden Konfigurationsdaten und Konstanten für die Kernfunktionen der Anwendung definiert.

import streamlit as st
from typing import List, Dict
from utils import load_blacklist_config

# --- KONFIGURATION LADEN ---
# Lädt die Blacklist-Konfiguration aus der 
def get_config() -> dict:
   
    return load_blacklist_config()

# Regex Pattern für die extraktion der Artikelnummern
# Entweder werden alphabetische Präfixe (2-4 Buchstaben) oder numerische Präfixe (2 Ziffern) unterstützt aber in einem Match nicht gemischt

PATTERN_ALPHA = r"(?<![A-Z])([A-Z]{2,4})[\s._\u00A0]+(\d{3})[\s._\u00A0]+(\d{2})(?!\d)"
PATTERN_NUMERIC = r"(?<!\d)(\d{2})[\s._\u00A0]+(\d{3})[\s._\u00A0]+(\d{2})(?!\d)"
PATTERN = rf"(?i)(?:{PATTERN_ALPHA})|(?:{PATTERN_NUMERIC})"

# Spalten-Konstanten 
RESULT_COLUMNS: List[str] = ["Seite", "Artikelnummer", "Kontext"]

# Definiert wie die Spalten (Seite,Artikelnummer,Kontext) in UI dargestellt werden
def get_column_config() -> Dict:

    return {
        "Seite": st.column_config.NumberColumn("Seite", width="small"),
        "Artikelnummer": st.column_config.TextColumn("Artikelnummer", width="medium"),
        "Kontext": st.column_config.TextColumn("Kontext", width="large"),
    }
