# AI Reviewer Module
# Hauptmodul für die KI-gestützte Überprüfung und Korrektur von Artikelnummern.
# Nutzt Provider aus providers.py und Prompts aus prompts.py.

import pandas as pd
import time
import threading
from dataclasses import dataclass
from typing import Optional, Callable, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.ai.providers import ACTIVE_PROVIDER
from core.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from core.utils.tracking import log_api_call


# =============================================================================
# KONFIGURATION
# =============================================================================

# Batch-Größe je nach Provider (Gemini ist bei großen Batches instabiler)
DEFAULT_BATCH_SIZE = 50 if "Gemini" in ACTIVE_PROVIDER.name else 200
MAX_PARALLEL_WORKERS = 4


# =============================================================================
# DATENSTRUKTUREN
# =============================================================================

@dataclass
class ReviewResult:
    """Ergebnis der KI-Analyse mit bereinigten DataFrames und Verschiebungen."""
    df_sicher_original: pd.DataFrame
    df_unsicher_original: pd.DataFrame
    df_spam_original: pd.DataFrame
    df_sicher: pd.DataFrame
    df_unsicher: pd.DataFrame
    df_spam: pd.DataFrame
    verschiebungen: list
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
    df_spam_original: pd.DataFrame,
    fehler_msg: str
) -> ReviewResult:
    """Erstellt ein Fehler-ReviewResult mit Original-Daten."""
    return ReviewResult(
        df_sicher_original=df_sicher_original,
        df_unsicher_original=df_unsicher_original,
        df_spam_original=df_spam_original,
        df_sicher=df_sicher_original,
        df_unsicher=df_unsicher_original,
        df_spam=df_spam_original,
        verschiebungen=[],
        erfolg=False,
        fehler_msg=fehler_msg
    )


def _log_and_return_batch_result(
    batch_idx: int,
    batch_df: pd.DataFrame,
    dateiname: str,
    total_batches: int,
    start_time: float,
    ai_response=None,
    error: Exception = None
) -> Tuple[int, List[dict], Optional[str]]:
    """Loggt API-Call und gibt Batch-Ergebnis zurück."""
    duration = time.time() - start_time
    
    if error:
        log_api_call(
            dateiname=dateiname,
            provider=ACTIVE_PROVIDER.name,
            batch_nummer=batch_idx,
            batch_total=total_batches,
            anzahl_eintraege=len(batch_df),
            dauer_sekunden=duration,
            status="error",
            fehler_msg=str(error)
        )
        return (batch_idx, [], str(error))
    
    log_api_call(
        dateiname=dateiname,
        provider=ACTIVE_PROVIDER.name,
        batch_nummer=batch_idx,
        batch_total=total_batches,
        anzahl_eintraege=len(batch_df),
        dauer_sekunden=duration,
        status="success",
        input_tokens=ai_response.input_tokens,
        output_tokens=ai_response.output_tokens
    )
    return (batch_idx, ai_response.data.get("verschiebungen", []), None)


def _process_batch(
    batch_info: Tuple[int, str, pd.DataFrame],
    columns: list,
    dateiname: str,
    total_batches: int
) -> Tuple[int, List[dict], Optional[str]]:
    """Verarbeitet einen einzelnen Batch. Thread-safe."""
    batch_idx, kategorie, batch_df = batch_info
    start_time = time.time()
    
    try:
        empty_df = pd.DataFrame(columns=columns)
        prompts = {
            "sicher": (batch_df, empty_df, empty_df),
            "unsicher": (empty_df, batch_df, empty_df),
            "spam": (empty_df, empty_df, batch_df)
        }
        user_prompt = build_user_prompt(*prompts[kategorie])
        ai_response = ACTIVE_PROVIDER.analyze(user_prompt, SYSTEM_PROMPT)
        return _log_and_return_batch_result(
            batch_idx, batch_df, dateiname, total_batches, start_time, ai_response
        )
    except Exception as e:
        return _log_and_return_batch_result(
            batch_idx, batch_df, dateiname, total_batches, start_time, error=e
        )


# =============================================================================
# HAUPTFUNKTION
# =============================================================================

def review_dataframes(
    df_sicher: pd.DataFrame,
    df_unsicher: pd.DataFrame,
    df_spam: pd.DataFrame,
    batch_size: int = DEFAULT_BATCH_SIZE,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    dateiname: str = "unbekannt"
) -> ReviewResult:
    """
    Hauptfunktion zur Überprüfung und Korrektur der DataFrames mit KI.
    
    Args:
        df_sicher: DataFrame mit sicheren Treffern
        df_unsicher: DataFrame mit unsicheren Treffern
        df_spam: DataFrame mit Spam-Treffern
        batch_size: Anzahl Einträge pro Datenpaket
        progress_callback: Funktion(current, total, text) für UI-Updates
        dateiname: Name der Datei für Tracking-Logs
    
    Returns:
        ReviewResult mit bereinigten DataFrames und Verschiebungs-Logs
    """
    # Original-Daten sichern
    originals = {
        "sicher": df_sicher.copy(),
        "unsicher": df_unsicher.copy(),
        "spam": df_spam.copy()
    }
    
    total = len(df_sicher) + len(df_unsicher) + len(df_spam)
    
    # Leere Daten = Sofort zurück
    if total == 0:
        return ReviewResult(
            df_sicher_original=originals["sicher"],
            df_unsicher_original=originals["unsicher"],
            df_spam_original=originals["spam"],
            df_sicher=df_sicher,
            df_unsicher=df_unsicher,
            df_spam=df_spam,
            verschiebungen=[],
            erfolg=True
        )
    
    try:
        dfs = {k: v.copy() for k, v in originals.items()}
        alle_verschiebungen = []
        errors = []
        
        # Datenpakete erstellen
        batches = []
        for kategorie in ["sicher", "unsicher", "spam"]:
            for chunk in _chunk_dataframe(dfs[kategorie], batch_size):
                if not chunk.empty:
                    batches.append((len(batches) + 1, kategorie, chunk))
        
        total_batches = len(batches)
        
        # === SINGLE-CALL für kleine Datensätze ===
        if total <= batch_size * 3 or total_batches <= 1:
            if progress_callback:
                progress_callback(1, 1, "🤖 Analysiere alle Daten...")
            
            start_time = time.time()
            try:
                user_prompt = build_user_prompt(df_sicher, df_unsicher, df_spam)
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
                    originals["sicher"], originals["unsicher"], originals["spam"],
                    f"KI-Analyse fehlgeschlagen: {str(e)}"
                )
        
        # === PARALLELE VERARBEITUNG für große Datensätze ===
        else:
            if progress_callback:
                progress_callback(0, total_batches, f"🤖 KI analysiert {total_batches} Datenpakete...")
            
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
                        _process_batch, batch, df_sicher.columns.tolist(), dateiname, total_batches
                    ): batch[0] for batch in batches
                }
                
                for future in as_completed(futures):
                    batch_idx, verschiebungen, error = future.result()
                    if error:
                        errors.append(f"Datenpaket {batch_idx}: {error}")
                    else:
                        alle_verschiebungen.extend(verschiebungen)
                    update_progress()
                
                # Alle Batches fehlgeschlagen?
                if errors and len(errors) == total_batches:
                    return _create_error_result(
                        originals["sicher"], originals["unsicher"], originals["spam"],
                        f"KI-Analyse fehlgeschlagen ({len(errors)} Datenpakete). {errors[0]}"
                    )
        
        # Verschiebungen anwenden
        dfs = _apply_verschiebungen(dfs, alle_verschiebungen)
        
        # Erfolgs-/Warnungsmeldung
        success_msg = f"✅ Fertig! {len(alle_verschiebungen)} Korrekturen angewendet."
        if errors and len(errors) < total_batches:
            success_msg = f"⚠️ {len(alle_verschiebungen)} Korrekturen, aber {len(errors)} Datenpakete fehlgeschlagen."
        
        if progress_callback:
            progress_callback(1, 1, success_msg)
        
        return ReviewResult(
            df_sicher_original=originals["sicher"],
            df_unsicher_original=originals["unsicher"],
            df_spam_original=originals["spam"],
            df_sicher=dfs["sicher"],
            df_unsicher=dfs["unsicher"],
            df_spam=dfs["spam"],
            verschiebungen=alle_verschiebungen,
            erfolg=True
        )
        
    except Exception as e:
        return _create_error_result(
            originals["sicher"], originals["unsicher"], originals["spam"],
            f"KI-Analyse fehlgeschlagen: {str(e)}"
        )


def get_active_provider_name() -> str:
    """Gibt den Namen des aktiven Providers zurück."""
    from core.ai.providers import get_active_provider_name as _get_name
    return _get_name()
