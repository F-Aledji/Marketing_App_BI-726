# Master-List Verification Module
# Vergleicht gefundene Artikelnummern mit einer Referenzliste

import pandas as pd
from typing import Set, Optional


def load_reference_list(uploaded_file) -> Set[str]:
    """
    Lädt eine Referenzliste aus einer Excel- oder CSV-Datei.
    
    Erwartet eine Spalte "Artikelnummer" oder die erste Spalte als Referenz.
    
    Args:
        uploaded_file: Streamlit UploadedFile (Excel oder CSV)
    
    Returns:
        Set von normalisierten Artikelnummern
    """
    filename = uploaded_file.name.lower()
    
    try:
        if filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pd.read_excel(uploaded_file)
        elif filename.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            raise ValueError(f"Nicht unterstütztes Format: {filename}")
        
        # Artikelnummer-Spalte finden
        if "Artikelnummer" in df.columns:
            col = "Artikelnummer"
        elif "artikelnummer" in df.columns:
            col = "artikelnummer"
        elif "Art-Nr" in df.columns:
            col = "Art-Nr"
        elif "ArtNr" in df.columns:
            col = "ArtNr"
        else:
            # Erste Spalte verwenden
            col = df.columns[0]
        
        # Normalisieren: Leerzeichen entfernen, uppercase
        reference_set = set()
        for val in df[col].dropna():
            # Konvertieren und normalisieren
            clean_val = str(val).strip().replace(" ", "").replace(".", "").replace("_", "").upper()
            if clean_val:
                reference_set.add(clean_val)
        
        return reference_set
        
    except Exception as e:
        raise ValueError(f"Fehler beim Laden der Referenzliste: {e}")


def _normalize_artikelnummer(nummer: str) -> str:
    """Normalisiert eine Artikelnummer für den Vergleich."""
    return str(nummer).strip().replace(" ", "").replace(".", "").replace("_", "").upper()


def verify_against_reference(
    df: pd.DataFrame,
    reference_set: Set[str]
) -> pd.DataFrame:
    """
    Fügt eine "Geprüft"-Spalte zum DataFrame hinzu.
    
    Args:
        df: DataFrame mit "Artikelnummer"-Spalte
        reference_set: Set von normalisierten Referenz-Artikelnummern
    
    Returns:
        DataFrame mit zusätzlicher "Geprüft"-Spalte (✅/❌)
    """
    if df.empty or "Artikelnummer" not in df.columns:
        df["Geprüft"] = ""
        return df
    
    df = df.copy()
    
    def check(nummer):
        normalized = _normalize_artikelnummer(nummer)
        return "✅" if normalized in reference_set else "❌"
    
    df["Geprüft"] = df["Artikelnummer"].apply(check)
    
    return df


def get_verification_stats(
    df_sicher: pd.DataFrame,
    df_unsicher: pd.DataFrame,
    df_spam: pd.DataFrame
) -> dict:
    """
    Berechnet Statistiken zur Verifizierung.
    
    Returns:
        Dict mit Anzahl verifizierter/nicht verifizierter Nummern
    """
    stats = {
        "sicher_verified": 0,
        "sicher_not_verified": 0,
        "unsicher_verified": 0,
        "unsicher_not_verified": 0,
        "spam_verified": 0,
        "spam_not_verified": 0
    }
    
    for name, df in [("sicher", df_sicher), ("unsicher", df_unsicher), ("spam", df_spam)]:
        if "Geprüft" in df.columns:
            stats[f"{name}_verified"] = (df["Geprüft"] == "✅").sum()
            stats[f"{name}_not_verified"] = (df["Geprüft"] == "❌").sum()
    
    return stats
