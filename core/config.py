
## Hier werden Konfigurationsdaten und Konstanten für die Kernfunktionen der Anwendung definiert.
import pandas as pd
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
# INTERNAL_COLUMNS: Alle Spalten während der Verarbeitung (inkl. Kontext für KI-Analyse)
# DISPLAY_COLUMNS: Nur die Spalten die im Frontend und Excel angezeigt werden
INTERNAL_COLUMNS: List[str] = ["Seite", "Artikelnummer", "Kontext"]
DISPLAY_COLUMNS: List[str] = ["Seite", "Artikelnummer"]

# Legacy-Konstante für Abwärtskompatibilität (wird intern verwendet)
RESULT_COLUMNS: List[str] = INTERNAL_COLUMNS

# Definiert wie die Spalten in der UI dargestellt werden (nur Display-Spalten)
def get_column_config() -> Dict:
    return {
        "Seite": st.column_config.NumberColumn("Seite", width="small"),
        "Artikelnummer": st.column_config.TextColumn("Artikelnummer", width="medium"),
    }


# Hilfsfunktion: Entfernt interne Spalten und gibt nur Display-Spalten zurück
# Ein DataFrame für die Anzeige vorbereiten
# Entfernt Kontext nur die jediglich für die KI Analyse genutzt wird
def prepare_for_display(df) -> "pd.DataFrame":
    if df.empty:
        return pd.DataFrame(columns=DISPLAY_COLUMNS)
    # Nur Spalten behalten die in DISPLAY_COLUMNS definiert sind
    available_cols = [col for col in DISPLAY_COLUMNS if col in df.columns]
    return df[available_cols].copy()
