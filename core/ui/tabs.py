# Tab Rendering Functions
# Enthält wiederverwendbare Funktionen für die UI-Tabs

import streamlit as st
import pandas as pd
from typing import List, Dict, Any


def render_data_tab(
    title: str,
    caption: str,
    data: pd.DataFrame,
    column_config: Dict
) -> None:
    """
    Rendert einen Standard-Datentab mit Titel, Beschreibung und DataFrame.
    
    Args:
        title: Überschrift des Tabs (z.B. "Sichere Treffer")
        caption: Kurze Beschreibung unter der Überschrift
        data: DataFrame zum Anzeigen (bereits für Display vorbereitet)
        column_config: Streamlit Column-Config für das DataFrame
    """
    st.subheader(title)
    st.caption(caption)
    
    if not data.empty:
        st.dataframe(
            data,
            use_container_width=True,
            hide_index=True,
            column_config=column_config
        )
    else:
        st.info(f"Keine {title.lower()} gefunden.")


def render_ki_verschiebungen_tab(verschiebungen: List[Dict[str, Any]]) -> None:
    """
    Rendert den Tab für KI-Verschiebungen mit Statistiken und Tabelle.
    
    Args:
        verschiebungen: Liste der Verschiebungs-Dicts aus dem ReviewResult
    """
    st.subheader("KI-Verschiebungen & Korrekturen")
    st.caption("Übersicht aller Änderungen, die die KI vorgenommen hat, mit Begründungen.")
    
    if not verschiebungen:
        st.info("✅ Die KI hat keine Änderungen vorgenommen. Alle Einträge waren korrekt klassifiziert.")
        return
    
    # Statistiken berechnen
    stats = calculate_verschiebung_stats(verschiebungen)
    
    # Statistik-Metriken anzeigen
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("→ Spam", stats["zu_spam"])
    with col2:
        st.metric("→ Sicher", stats["zu_sicher"])
    with col3:
        st.metric("Korrekturen", stats["korrekturen"])
    
    # DataFrame für die Anzeige
    logs_data = [
        {
            "Artikelnummer": v.get("artikelnummer", ""),
            "Korrektur": v.get("korrektur", "") or "—",
            "Von": v.get("von", ""),
            "Nach": v.get("nach", ""),
            "Begründung": v.get("begruendung", "")
        }
        for v in verschiebungen
    ]
    df_logs = pd.DataFrame(logs_data)
    
    st.dataframe(
        df_logs,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Artikelnummer": st.column_config.TextColumn("Original", width="medium"),
            "Korrektur": st.column_config.TextColumn("Korrigiert zu", width="medium"),
            "Von": st.column_config.TextColumn("Von", width="small"),
            "Nach": st.column_config.TextColumn("Nach", width="small"),
            "Begründung": st.column_config.TextColumn("Begründung", width="large")
        }
    )


def calculate_verschiebung_stats(verschiebungen: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Berechnet Statistiken über Verschiebungen (nur einmal).
    
    Returns:
        Dict mit zu_spam, zu_sicher, zu_unsicher, korrekturen
    """
    return {
        "zu_spam": sum(1 for v in verschiebungen if v.get("nach", "").lower() == "spam"),
        "zu_sicher": sum(1 for v in verschiebungen if v.get("nach", "").lower() == "sicher"),
        "zu_unsicher": sum(1 for v in verschiebungen if v.get("nach", "").lower() == "unsicher"),
        "korrekturen": sum(1 for v in verschiebungen if v.get("korrektur"))
    }


def render_ki_hinweis(verschiebungen: List[Dict[str, Any]]) -> None:
    """
    Zeigt einen kompakten Hinweis über KI-Verschiebungen an.
    """
    if not verschiebungen:
        return
    
    stats = calculate_verschiebung_stats(verschiebungen)
    
    hinweis_teile = []
    if stats["zu_spam"] > 0:
        hinweis_teile.append(f"{stats['zu_spam']}× → Spam")
    if stats["zu_sicher"] > 0:
        hinweis_teile.append(f"{stats['zu_sicher']}× → Sicher")
    if stats["zu_unsicher"] > 0:
        hinweis_teile.append(f"{stats['zu_unsicher']}× → Unsicher")
    
    if hinweis_teile:
        st.info(f"🤖 **KI-Analyse:** {', '.join(hinweis_teile)} verschoben")
