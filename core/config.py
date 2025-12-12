"""
Konfiguration und Konstanten für die Artikelnummer-Extraktion.
"""
import streamlit as st
from typing import List, Dict
from utils import load_blacklist_config

# --- KONFIGURATION LADEN ---
def get_config() -> dict:
    """Lädt die Blacklist-Konfiguration."""
    return load_blacklist_config()

# Regex Pattern für Artikelnummern
PATTERN_ALPHA = r"(?<![A-Z])([A-Z]{2,4})[\s._\u00A0]+(\d{3})[\s._\u00A0]+(\d{2})(?!\d)"
PATTERN_NUMERIC = r"(?<!\d)(\d{2})[\s._\u00A0]+(\d{3})[\s._\u00A0]+(\d{2})(?!\d)"
PATTERN = rf"(?i)(?:{PATTERN_ALPHA})|(?:{PATTERN_NUMERIC})"

# Spalten-Konstanten (DRY)
RESULT_COLUMNS: List[str] = ["Seite", "Artikelnummer", "Kontext"]

def get_column_config() -> Dict:
    """Gibt die Streamlit Column-Konfiguration zurück."""
    return {
        "Seite": st.column_config.NumberColumn("Seite", width="small"),
        "Artikelnummer": st.column_config.TextColumn("Artikelnummer", width="medium"),
        "Kontext": st.column_config.TextColumn("Kontext", width="large"),
    }
