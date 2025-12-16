# Utility-Funktionen für die Artikelnummer-Suche App


import streamlit as st
import json
import os

# Pfade definieren
DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "blacklist.json")

# Lädt die Blacklist (Prefixe, Nummern und Context-Wörter) aus der JSON.
# Es stellt sicher dass alle erwarteten Felder vorhanden sind (Schema-Validierung).
def load_blacklist_config() -> dict:
 
    # Default-Schema mit allen erwarteten Feldern
    default_config = {
        "bad_prefixes": [],
        "bad_numbers": [],
        "context_bad_words": ["Tel", "Fax", "Hotline", "Seite", "HRB", "Telefon", "Mobil"],
        "context_good_words": ["Art", "Best", "Nr", "Order", "Artikel", "Bestellung", "Art-Nr"]
    }
    
    if not os.path.exists(DATA_FILE):
        # Fallback, falls Datei noch nicht existiert
        return default_config
    
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded_config = json.load(f)
        
        # Merge: Stelle sicher, dass alle Keys existieren (Schema-Migration)
        for key, default_value in default_config.items():
            if key not in loaded_config:
                loaded_config[key] = default_value
        
        return loaded_config
    except Exception as e:
        st.error(f"Fehler beim Laden der Config: {e}")
        return default_config