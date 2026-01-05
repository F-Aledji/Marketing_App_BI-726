# Session State Management
# Enthält Funktionen zum Speichern und Laden von Analyseergebnissen

import streamlit as st
import pandas as pd

from core.ai.reviewer import ReviewResult


def save_analysis_results(
    review_result: ReviewResult,
    dateiname: str
) -> None:
    """
    Speichert alle Analyseergebnisse in den Session State.
    
    Args:
        review_result: Das Ergebnis der KI-Analyse
        dateiname: Name der analysierten Datei
    """
    # KI-bereinigte DataFrames
    df_sicher = review_result.df_sicher
    df_unsicher = review_result.df_unsicher
    df_sehr_unsicher = review_result.df_sehr_unsicher
    
    # Aktuelle Daten speichern
    st.session_state["data_sicher"] = df_sicher
    st.session_state["data_unsicher"] = df_unsicher
    st.session_state["data_sehr_unsicher"] = df_sehr_unsicher
    st.session_state["datei_name"] = dateiname
    st.session_state["analyse_done"] = True
    
    # KI-Metadaten speichern
    st.session_state["ki_verschiebungen"] = review_result.verschiebungen
    st.session_state["ki_erfolg"] = True
    
    # Original-Daten für Excel-Export speichern
    st.session_state["data_sicher_original"] = review_result.df_sicher_original
    st.session_state["data_unsicher_original"] = review_result.df_unsicher_original
    st.session_state["data_sehr_unsicher_original"] = review_result.df_sehr_unsicher_original


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
        Tuple (df_sicher, df_unsicher, df_sehr_unsicher)
    """
    from core.config.config import prepare_for_display
    
    return (
        prepare_for_display(st.session_state.get("data_sicher", pd.DataFrame())),
        prepare_for_display(st.session_state.get("data_unsicher", pd.DataFrame())),
        prepare_for_display(st.session_state.get("data_sehr_unsicher", pd.DataFrame()))
    )
