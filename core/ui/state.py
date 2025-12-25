# Session State Management
# Enthält Funktionen zum Speichern und Laden von Analyseergebnissen

import streamlit as st
import pandas as pd
from typing import Optional, Set

from core.ai.reviewer import ReviewResult
from core.analysis.verification import verify_against_reference


def save_analysis_results(
    review_result: ReviewResult,
    dateiname: str,
    reference_set: Optional[Set[str]] = None
) -> None:
    """
    Speichert alle Analyseergebnisse in den Session State.
    
    Args:
        review_result: Das Ergebnis der KI-Analyse
        dateiname: Name der analysierten Datei
        reference_set: Optional, Set mit Referenz-Artikelnummern für Verifizierung
    """
    # KI-bereinigte DataFrames
    df_sicher = review_result.df_sicher
    df_unsicher = review_result.df_unsicher
    df_spam = review_result.df_spam
    
    # Verifizierung gegen Referenzliste (falls geladen)
    if reference_set:
        df_sicher = verify_against_reference(df_sicher, reference_set)
        df_unsicher = verify_against_reference(df_unsicher, reference_set)
        df_spam = verify_against_reference(df_spam, reference_set)
    
    # Aktuelle Daten speichern
    st.session_state["data_sicher"] = df_sicher
    st.session_state["data_unsicher"] = df_unsicher
    st.session_state["data_spam"] = df_spam
    st.session_state["datei_name"] = dateiname
    st.session_state["analyse_done"] = True
    
    # KI-Metadaten speichern
    st.session_state["ki_verschiebungen"] = review_result.verschiebungen
    st.session_state["ki_erfolg"] = True
    
    # Original-Daten für Excel-Export speichern
    st.session_state["data_sicher_original"] = review_result.df_sicher_original
    st.session_state["data_unsicher_original"] = review_result.df_unsicher_original
    st.session_state["data_spam_original"] = review_result.df_spam_original


def save_analysis_error(fehler_msg: str) -> None:
    """
    Speichert einen KI-Analysefehler in den Session State.
    
    Args:
        fehler_msg: Die Fehlermeldung
    """
    st.session_state["ki_erfolg"] = False
    st.session_state["ki_fehler"] = fehler_msg
    st.session_state["analyse_done"] = False


def get_display_dataframes() -> tuple:
    """
    Lädt die Display-DataFrames aus dem Session State.
    
    Returns:
        Tuple (df_sicher, df_unsicher, df_spam)
    """
    from core.config.config import prepare_for_display
    
    return (
        prepare_for_display(st.session_state.get("data_sicher", pd.DataFrame())),
        prepare_for_display(st.session_state.get("data_unsicher", pd.DataFrame())),
        prepare_for_display(st.session_state.get("data_spam", pd.DataFrame()))
    )
