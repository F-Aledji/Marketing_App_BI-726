# Konfigurationsdaten und Konstanten für die Kernfunktionen der Anwendung

import os
import json
import pandas as pd
import streamlit as st
from typing import List, Dict

# =============================================================================
# PFADE & KONSTANTEN
# =============================================================================

DATA_DIR = "data"
BLACKLIST_FILE = os.path.join(DATA_DIR, "blacklist.json")

# Regex Pattern für die Extraktion der Artikelnummern
PATTERN_ALPHA = r"(?<![A-Z])([A-Z]{2,4})[\s._\u00A0]+(\d{3})[\s._\u00A0]+(\d{2})(?!\d)"
PATTERN_NUMERIC = r"(?<!\d)(\d{2})[\s._\u00A0]+(\d{3})[\s._\u00A0]+(\d{2})(?!\d)"
PATTERN = rf"(?i)(?:{PATTERN_ALPHA})|(?:{PATTERN_NUMERIC})"

# Spalten-Konstanten
INTERNAL_COLUMNS: List[str] = ["Seite", "Artikelnummer", "Kontext"]
DISPLAY_COLUMNS: List[str] = ["Seite", "Artikelnummer"]


# =============================================================================
# BLACKLIST CONFIG (ehemals in utils.py)
# =============================================================================

def get_config() -> dict:
    """
    Lädt die Blacklist-Konfiguration aus der JSON-Datei.
    Enthält Prefixe, Nummern und Context-Wörter für die Filterung.
    """
    default_config = {
        "bad_prefixes": [],
        "bad_numbers": [],
        "context_bad_words": ["Tel", "Fax", "Hotline", "Seite", "HRB", "Telefon", "Mobil"],
        "context_good_words": ["Art", "Best", "Nr", "Order", "Artikel", "Bestellung", "Art-Nr"]
    }
    
    if not os.path.exists(BLACKLIST_FILE):
        return default_config
    
    try:
        with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
            loaded_config = json.load(f)
        
        # Schema-Migration: Fehlende Keys ergänzen
        for key, default_value in default_config.items():
            if key not in loaded_config:
                loaded_config[key] = default_value
        
        return loaded_config
    except Exception as e:
        st.error(f"Fehler beim Laden der Config: {e}")
        return default_config


# =============================================================================
# UI HELPERS
# =============================================================================

def get_column_config() -> Dict:
    """Definiert wie die Spalten in der UI dargestellt werden."""
    return {
        "Seite": st.column_config.NumberColumn("Seite", width="small"),
        "Artikelnummer": st.column_config.TextColumn("Artikelnummer", width="medium"),
        "Geprüft": st.column_config.TextColumn("Geprüft", width="small"),
    }


def prepare_for_display(df) -> "pd.DataFrame":
    """Entfernt interne Spalten und gibt nur Display-Spalten zurück."""
    if df.empty:
        return pd.DataFrame(columns=DISPLAY_COLUMNS)
    
    display_cols = list(DISPLAY_COLUMNS)
    if "Geprüft" in df.columns:
        display_cols.append("Geprüft")
    
    available_cols = [col for col in display_cols if col in df.columns]
    return df[available_cols].copy()


def get_clean_string(p1: str, p2: str, p3: str) -> str:
    """Gibt die reine Nummer ohne Leerzeichen zurück."""
    return f"{p1}{p2}{p3}"
