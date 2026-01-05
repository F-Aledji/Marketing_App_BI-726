# AI Reviewer Module
# Hauptmodul für die KI-gestützte Überprüfung und Korrektur von Artikelnummern.
# Nutzt Provider aus providers.py und Prompts aus prompts.py.
# SEITENWEISES BATCHING: Daten werden nach Seitenbereichen gruppiert für bessere Muster-Analyse.

import pandas as pd
import time
import threading
from dataclasses import dataclass
from typing import Optional, Callable, List, Tuple, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.ai.providers import ACTIVE_PROVIDER
from core.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from core.utils.tracking import log_api_call


# =============================================================================
# KONFIGURATION
# =============================================================================

# Seiten pro Batch (KI sieht alle Kategorien pro Seitenbereich)
PAGES_PER_BATCH = 10 if "Gemini" in ACTIVE_PROVIDER.name else 20
MAX_PARALLEL_WORKERS = 4


# =============================================================================
# DATENSTRUKTUREN
# =============================================================================

@dataclass
class ReviewResult:
    """Ergebnis der KI-Analyse mit bereinigten DataFrames und Verschiebungen."""
    df_sicher_original: pd.DataFrame
    df_unsicher_original: pd.DataFrame
    df_sehr_unsicher_original: pd.DataFrame
    df_sicher: pd.DataFrame
    df_unsicher: pd.DataFrame
    df_sehr_unsicher: pd.DataFrame
    verschiebungen: list
    erfolg: bool = True
    fehler_msg: str = ""


# =============================================================================
# HILFSFUNKTIONEN
# =============================================================================

def _create_page_batches(
    df_sicher: pd.DataFrame,
    df_unsicher: pd.DataFrame,
    df_sehr_unsicher: pd.DataFrame,
    pages_per_batch: int = PAGES_PER_BATCH
) -> List[Tuple[int, pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    """
    Erstellt Batches nach Seitenbereichen statt nach Kategorien.
    
    Returns:
        Liste von (batch_idx, df_sicher_chunk, df_unsicher_chunk, df_sehr_unsicher_chunk)
    """
    # Alle Seiten ermitteln
    all_pages = set()
    for df in [df_sicher, df_unsicher, df_sehr_unsicher]:
        if not df.empty and "Seite" in df.columns:
            all_pages.update(df["Seite"].unique())
    
    if not all_pages:
        return []
    
    # Seiten sortieren und in Gruppen aufteilen
    sorted_pages = sorted(all_pages)
    page_groups = [
        sorted_pages[i:i + pages_per_batch] 
        for i in range(0, len(sorted_pages), pages_per_batch)
    ]
    
    batches = []
    for idx, page_group in enumerate(page_groups, start=1):
        # Für jede Seitengruppe die entsprechenden Zeilen filtern
        sicher_chunk = df_sicher[df_sicher["Seite"].isin(page_group)] if not df_sicher.empty else pd.DataFrame()
        unsicher_chunk = df_unsicher[df_unsicher["Seite"].isin(page_group)] if not df_unsicher.empty else pd.DataFrame()
        sehr_unsicher_chunk = df_sehr_unsicher[df_sehr_unsicher["Seite"].isin(page_group)] if not df_sehr_unsicher.empty else pd.DataFrame()
        
        # Nur hinzufügen wenn mindestens ein Eintrag vorhanden
        if len(sicher_chunk) + len(unsicher_chunk) + len(sehr_unsicher_chunk) > 0:
            batches.append((idx, sicher_chunk, unsicher_chunk, sehr_unsicher_chunk))
    
    return batches


def _apply_verschiebungen(dfs: dict, verschiebungen: list) -> dict:
    """Wendet Verschiebungen und Korrekturen auf die DataFrames an."""
    for v in verschiebungen:
        artikelnummer = v.get("artikelnummer", "")
        korrektur = v.get("korrektur", "")
        von = v.get("von", "").lower().replace(" ", "_")  # "Sehr Unsicher" -> "sehr_unsicher"
        nach = v.get("nach", "").lower().replace(" ", "_")
        
        if von not in dfs or nach not in dfs:
            continue
        
        maske = dfs[von]["Artikelnummer"] == artikelnummer
        if maske.any():
            zeile = dfs[von][maske].copy()
            if korrektur:
                zeile["Artikelnummer"] = korrektur
            dfs[von] = dfs[von][~maske]
            dfs[nach] = pd.concat([dfs[nach], zeile], ignore_index=True)
    
    return dfs


def _create_error_result(
    df_sicher_original: pd.DataFrame,
    df_unsicher_original: pd.DataFrame,
    df_sehr_unsicher_original: pd.DataFrame,
    fehler_msg: str
) -> ReviewResult:
    """Erstellt ein Fehler-ReviewResult mit Original-Daten."""
    return ReviewResult(
        df_sicher_original=df_sicher_original,
        df_unsicher_original=df_unsicher_original,
        df_sehr_unsicher_original=df_sehr_unsicher_original,
        df_sicher=df_sicher_original,
        df_unsicher=df_unsicher_original,
        df_sehr_unsicher=df_sehr_unsicher_original,
        verschiebungen=[],
        erfolg=False,
        fehler_msg=fehler_msg
    )


def _process_page_batch(
    batch_info: Tuple[int, pd.DataFrame, pd.DataFrame, pd.DataFrame],
    dateiname: str,
    total_batches: int
) -> Tuple[int, List[dict], Optional[str]]:
    """
    Verarbeitet einen Seiten-Batch (alle Kategorien zusammen). Thread-safe.
    
    Args:
        batch_info: (batch_idx, df_sicher, df_unsicher, df_sehr_unsicher)
    """
    batch_idx, df_sicher, df_unsicher, df_sehr_unsicher = batch_info
    start_time = time.time()
    total_entries = len(df_sicher) + len(df_unsicher) + len(df_sehr_unsicher)
    
    try:
        user_prompt = build_user_prompt(df_sicher, df_unsicher, df_sehr_unsicher)
        ai_response = ACTIVE_PROVIDER.analyze(user_prompt, SYSTEM_PROMPT)
        verschiebungen = ai_response.data.get("verschiebungen", [])
        
        duration = time.time() - start_time
        log_api_call(
            dateiname=dateiname,
            provider=ACTIVE_PROVIDER.name,
            batch_nummer=batch_idx,
            batch_total=total_batches,
            anzahl_eintraege=total_entries,
            dauer_sekunden=duration,
            status="success",
            input_tokens=ai_response.input_tokens,
            output_tokens=ai_response.output_tokens
        )
        return (batch_idx, verschiebungen, None)
        
    except Exception as e:
        duration = time.time() - start_time
        log_api_call(
            dateiname=dateiname,
            provider=ACTIVE_PROVIDER.name,
            batch_nummer=batch_idx,
            batch_total=total_batches,
            anzahl_eintraege=total_entries,
            dauer_sekunden=duration,
            status="error",
            fehler_msg=str(e)
        )
        return (batch_idx, [], str(e))


# =============================================================================
# HAUPTFUNKTION
# =============================================================================

def review_dataframes(
    df_sicher: pd.DataFrame,
    df_unsicher: pd.DataFrame,
    df_sehr_unsicher: pd.DataFrame,
    pages_per_batch: int = PAGES_PER_BATCH,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    dateiname: str = "unbekannt"
) -> ReviewResult:
    """
    Hauptfunktion zur Überprüfung und Korrektur der DataFrames mit KI.
    
    NEU: Seitenweises Batching - KI sieht alle Kategorien pro Seitenbereich.
    
    Args:
        df_sicher: DataFrame mit sicheren Treffern
        df_unsicher: DataFrame mit unsicheren Treffern
        df_sehr_unsicher: DataFrame mit sehr unsicheren Treffern
        pages_per_batch: Anzahl Seiten pro Datenpaket
        progress_callback: Funktion(current, total, text) für UI-Updates
        dateiname: Name der Datei für Tracking-Logs
    
    Returns:
        ReviewResult mit bereinigten DataFrames und Verschiebungs-Logs
    """
    # Original-Daten sichern
    originals = {
        "sicher": df_sicher.copy(),
        "unsicher": df_unsicher.copy(),
        "sehr_unsicher": df_sehr_unsicher.copy()
    }
    
    total = len(df_sicher) + len(df_unsicher) + len(df_sehr_unsicher)
    
    # Leere Daten = Sofort zurück
    if total == 0:
        return ReviewResult(
            df_sicher_original=originals["sicher"],
            df_unsicher_original=originals["unsicher"],
            df_sehr_unsicher_original=originals["sehr_unsicher"],
            df_sicher=df_sicher,
            df_unsicher=df_unsicher,
            df_sehr_unsicher=df_sehr_unsicher,
            verschiebungen=[],
            erfolg=True
        )
    
    try:
        dfs = {k: v.copy() for k, v in originals.items()}
        alle_verschiebungen = []
        errors = []
        
        # Seiten-Batches erstellen
        batches = _create_page_batches(df_sicher, df_unsicher, df_sehr_unsicher, pages_per_batch)
        total_batches = len(batches)
        
        # Falls keine Batches (z.B. leere Seiten-Spalte), Single-Call
        if total_batches == 0:
            total_batches = 1
            batches = [(1, df_sicher, df_unsicher, df_sehr_unsicher)]
        
        # === SINGLE-CALL für kleine Datensätze ===
        if total_batches <= 1:
            if progress_callback:
                progress_callback(1, 1, "🤖 Analysiere alle Daten...")
            
            start_time = time.time()
            try:
                user_prompt = build_user_prompt(df_sicher, df_unsicher, df_sehr_unsicher)
                ai_response = ACTIVE_PROVIDER.analyze(user_prompt, SYSTEM_PROMPT)
                alle_verschiebungen = ai_response.data.get("verschiebungen", [])
                
                log_api_call(
                    dateiname=dateiname,
                    provider=ACTIVE_PROVIDER.name,
                    batch_nummer=1,
                    batch_total=1,
                    anzahl_eintraege=total,
                    dauer_sekunden=time.time() - start_time,
                    status="success",
                    input_tokens=ai_response.input_tokens,
                    output_tokens=ai_response.output_tokens
                )
            except Exception as e:
                log_api_call(
                    dateiname=dateiname,
                    provider=ACTIVE_PROVIDER.name,
                    batch_nummer=1,
                    batch_total=1,
                    anzahl_eintraege=total,
                    dauer_sekunden=time.time() - start_time,
                    status="error",
                    fehler_msg=str(e)
                )
                return _create_error_result(
                    originals["sicher"], originals["unsicher"], originals["sehr_unsicher"],
                    f"KI-Analyse fehlgeschlagen: {str(e)}"
                )
        
        # === PARALLELE VERARBEITUNG für große Datensätze ===
        else:
            if progress_callback:
                progress_callback(0, total_batches, f"🤖 KI analysiert {total_batches} Seitenbereiche...")
            
            completed_count = 0
            progress_lock = threading.Lock()
            
            def update_progress():
                nonlocal completed_count
                with progress_lock:
                    completed_count += 1
                    if progress_callback:
                        progress_callback(
                            completed_count, total_batches,
                            f"🤖 KI arbeitet... {completed_count}/{total_batches} abgeschlossen"
                        )
            
            with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
                futures = {
                    executor.submit(
                        _process_page_batch, batch, dateiname, total_batches
                    ): batch[0] for batch in batches
                }
                
                for future in as_completed(futures):
                    batch_idx, verschiebungen, error = future.result()
                    if error:
                        errors.append(f"Seitenbereich {batch_idx}: {error}")
                    else:
                        alle_verschiebungen.extend(verschiebungen)
                    update_progress()
                
                # Alle Batches fehlgeschlagen?
                if errors and len(errors) == total_batches:
                    return _create_error_result(
                        originals["sicher"], originals["unsicher"], originals["sehr_unsicher"],
                        f"KI-Analyse fehlgeschlagen ({len(errors)} Seitenbereiche). {errors[0]}"
                    )
        
        # Verschiebungen anwenden
        dfs = _apply_verschiebungen(dfs, alle_verschiebungen)
        
        # Erfolgs-/Warnungsmeldung
        success_msg = f"✅ Fertig! {len(alle_verschiebungen)} Korrekturen angewendet."
        if errors and len(errors) < total_batches:
            success_msg = f"⚠️ {len(alle_verschiebungen)} Korrekturen, aber {len(errors)} Seitenbereiche fehlgeschlagen."
        
        if progress_callback:
            progress_callback(1, 1, success_msg)
        
        return ReviewResult(
            df_sicher_original=originals["sicher"],
            df_unsicher_original=originals["unsicher"],
            df_sehr_unsicher_original=originals["sehr_unsicher"],
            df_sicher=dfs["sicher"],
            df_unsicher=dfs["unsicher"],
            df_sehr_unsicher=dfs["sehr_unsicher"],
            verschiebungen=alle_verschiebungen,
            erfolg=True
        )
        
    except Exception as e:
        return _create_error_result(
            originals["sicher"], originals["unsicher"], originals["sehr_unsicher"],
            f"KI-Analyse fehlgeschlagen: {str(e)}"
        )


def get_active_provider_name() -> str:
    """Gibt den Namen des aktiven Providers zurück."""
    from core.ai.providers import get_active_provider_name as _get_name
    return _get_name()
