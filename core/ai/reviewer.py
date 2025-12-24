# AI Reviewer Module
# Hauptmodul für die KI-gestützte Überprüfung und Korrektur von Artikelnummern.
# Nutzt die Provider aus ai_providers.py und Prompts aus ai_prompts.py.

import pandas as pd
from dataclasses import dataclass
from typing import Optional, Callable, List

from core.ai.providers import ACTIVE_PROVIDER
from core.ai.prompts import SYSTEM_PROMPT, build_user_prompt


# =============================================================================
# KONFIGURATION
# =============================================================================

# Für große Datensätze (3000+ Nummern) werden die Daten in kleinere Batches aufgeteilt
DEFAULT_BATCH_SIZE = 200  # Anzahl Einträge pro Batch (optimal für Token-Limits)


# =============================================================================
# DATENSTRUKTUREN
# =============================================================================

@dataclass
class ReviewResult:
    """Ergebnis der KI-Analyse mit bereinigten DataFrames und Verschiebungen."""
    
    # Original-Daten VOR der KI-Analyse (für Excel-Export)
    df_sicher_original: pd.DataFrame
    df_unsicher_original: pd.DataFrame
    df_spam_original: pd.DataFrame
    
    # Bereinigte Daten NACH der KI-Analyse
    df_sicher: pd.DataFrame
    df_unsicher: pd.DataFrame
    df_spam: pd.DataFrame
    
    # KI-Aktionen für Logs
    verschiebungen: list  # [{"artikelnummer": "...", "von": "...", "nach": "...", ...}]
    
    erfolg: bool = True
    fehler_msg: str = ""


# =============================================================================
# HILFSFUNKTIONEN
# =============================================================================

def _chunk_dataframe(df: pd.DataFrame, chunk_size: int) -> List[pd.DataFrame]:
    """Teilt ein DataFrame in kleinere Chunks auf."""
    if df.empty:
        return [df]
    return [df.iloc[i:i + chunk_size] for i in range(0, len(df), chunk_size)]


def _apply_verschiebungen(dfs: dict, verschiebungen: list) -> dict:
    """Wendet Verschiebungen und Korrekturen auf die DataFrames an."""
    for v in verschiebungen:
        artikelnummer = v.get("artikelnummer", "")
        korrektur = v.get("korrektur", "")
        von = v.get("von", "").lower()
        nach = v.get("nach", "").lower()
        
        # Validierung der Kategorie-Namen
        if von not in dfs or nach not in dfs:
            continue
        
        # Zeile finden
        maske = dfs[von]["Artikelnummer"] == artikelnummer
        if maske.any():
            zeile = dfs[von][maske].copy()
            
            # KORREKTUR anwenden
            if korrektur:
                zeile["Artikelnummer"] = korrektur
            
            # Verschieben
            dfs[von] = dfs[von][~maske]
            dfs[nach] = pd.concat([dfs[nach], zeile], ignore_index=True)
    
    return dfs


# =============================================================================
# HAUPTFUNKTION
# =============================================================================

def review_dataframes(
    df_sicher: pd.DataFrame,
    df_unsicher: pd.DataFrame,
    df_spam: pd.DataFrame,
    batch_size: int = DEFAULT_BATCH_SIZE,
    progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> ReviewResult:
    """
    Hauptfunktion zur Überprüfung und Korrektur der DataFrames mit KI.
    
    Unterstützt Batch-Verarbeitung für große Datensätze (3000+ Nummern).
    
    Args:
        df_sicher: DataFrame mit sicheren Treffern
        df_unsicher: DataFrame mit unsicheren Treffern
        df_spam: DataFrame mit Spam-Treffern
        batch_size: Anzahl Einträge pro Batch (Standard: 200)
        progress_callback: Optional - Funktion(current_batch, total_batches, status_text)
                          für Live-Updates in der UI
    
    Returns:
        ReviewResult mit bereinigten DataFrames und Verschiebungs-Logs
    """
    # Original-Daten sichern für Excel-Export
    df_sicher_original = df_sicher.copy()
    df_unsicher_original = df_unsicher.copy()
    df_spam_original = df_spam.copy()
    
    # Prüfen ob überhaupt Daten vorhanden sind
    total = len(df_sicher) + len(df_unsicher) + len(df_spam)
    if total == 0:
        return ReviewResult(
            df_sicher_original=df_sicher_original,
            df_unsicher_original=df_unsicher_original,
            df_spam_original=df_spam_original,
            df_sicher=df_sicher,
            df_unsicher=df_unsicher,
            df_spam=df_spam,
            verschiebungen=[],
            erfolg=True
        )
    
    try:
        # Arbeits-DataFrames initialisieren
        dfs = {
            "sicher": df_sicher.copy(),
            "unsicher": df_unsicher.copy(),
            "spam": df_spam.copy()
        }
        
        alle_verschiebungen = []
        
        # Batches für jede Kategorie erstellen
        batches = []
        for kategorie in ["sicher", "unsicher", "spam"]:
            chunks = _chunk_dataframe(dfs[kategorie], batch_size)
            for chunk in chunks:
                if not chunk.empty:
                    batches.append((kategorie, chunk))
        
        # Wenn wenige Daten: Ein einzelner API-Call (effizienter)
        if total <= batch_size * 3:
            # Klassischer Single-Call
            if progress_callback:
                progress_callback(1, 1, "🤖 Analysiere alle Daten...")
            
            user_prompt = build_user_prompt(df_sicher, df_unsicher, df_spam)
            result = ACTIVE_PROVIDER.analyze(user_prompt, SYSTEM_PROMPT)
            alle_verschiebungen = result.get("verschiebungen", [])
        else:
            # Batch-Verarbeitung für große Datensätze
            total_batches = len(batches)
            
            for i, (kategorie, batch_df) in enumerate(batches, 1):
                if progress_callback:
                    progress_callback(i, total_batches, f"🤖 Batch {i}/{total_batches}: {len(batch_df)} {kategorie.capitalize()}-Einträge...")
                
                # Leere DataFrames für die anderen Kategorien
                empty_df = pd.DataFrame(columns=df_sicher.columns)
                
                if kategorie == "sicher":
                    user_prompt = build_user_prompt(batch_df, empty_df, empty_df)
                elif kategorie == "unsicher":
                    user_prompt = build_user_prompt(empty_df, batch_df, empty_df)
                else:
                    user_prompt = build_user_prompt(empty_df, empty_df, batch_df)
                
                result = ACTIVE_PROVIDER.analyze(user_prompt, SYSTEM_PROMPT)
                batch_verschiebungen = result.get("verschiebungen", [])
                alle_verschiebungen.extend(batch_verschiebungen)
        
        # Alle Verschiebungen anwenden
        dfs = _apply_verschiebungen(dfs, alle_verschiebungen)
        
        if progress_callback:
            progress_callback(1, 1, f"✅ Fertig! {len(alle_verschiebungen)} Korrekturen angewendet.")
        
        return ReviewResult(
            df_sicher_original=df_sicher_original,
            df_unsicher_original=df_unsicher_original,
            df_spam_original=df_spam_original,
            df_sicher=dfs["sicher"],
            df_unsicher=dfs["unsicher"],
            df_spam=dfs["spam"],
            verschiebungen=alle_verschiebungen,
            erfolg=True
        )
        
    except Exception as e:
        return ReviewResult(
            df_sicher_original=df_sicher_original,
            df_unsicher_original=df_unsicher_original,
            df_spam_original=df_spam_original,
            df_sicher=df_sicher_original,
            df_unsicher=df_unsicher_original,
            df_spam=df_spam_original,
            verschiebungen=[],
            erfolg=False,
            fehler_msg=f"KI-Analyse fehlgeschlagen: {str(e)}"
        )


# Re-export für Abwärtskompatibilität
def get_active_provider_name() -> str:
    """Gibt den Namen des aktiven Providers zurück."""
    from core.ai.providers import get_active_provider_name as _get_name
    return _get_name()
