# WS Bestellnummer Suche App


import streamlit as st
import pandas as pd
import warnings
from dotenv import load_dotenv

load_dotenv()
warnings.filterwarnings("ignore", category=UserWarning)

# Core-Module
from core.config.config import get_column_config, prepare_for_display
from core.extraction.extractors import analyze_pdf
from core.analysis.analyzers import check_ocr_quality
from core.export.exporters import export_to_excel_with_logs
from core.ai.reviewer import review_dataframes
from core.ai.providers import get_active_provider_name

# UI-Module
from core.ui.sidebar import show_sidebar
from core.ui.state import save_analysis_results, get_display_dataframes
from core.ui.tabs import render_data_tab, render_ki_verschiebungen_tab, render_ki_hinweis

# =============================================================================
# HELPER FUNCTIONS (First for Script Execution)
# =============================================================================

def _run_analysis(uploaded_file) -> None:
    """Führt die komplette Analyse-Pipeline aus."""
    with st.spinner("Suche läuft..."):
        bytes_data = uploaded_file.getvalue()
        
        # OCR-Qualitätsprüfung
        if check_ocr_quality(bytes_data):
            st.warning("⚠️ **Achtung:** Gescannte Datei erkannt. Ergebnisse könnten unvollständig sein.")
        
        # PDF-Extraktion
        df_sicher, df_unsicher, df_sehr_unsicher = analyze_pdf(uploaded_file)
        total = len(df_sicher) + len(df_unsicher) + len(df_sehr_unsicher)
        
        if total == 0:
            st.warning("Nichts gefunden.")
            st.session_state["analyse_done"] = False
            return
        
        st.success(f"✅ {total} Treffer gefunden!")
    
    # KI-Analyse mit Progress
    progress_container = st.empty()
    status_text = st.empty()
    
    def update_progress(current: int, total_batches: int, text: str):
        progress = current / total_batches if total_batches > 0 else 1.0
        progress_container.progress(progress, text=f"🤖 KI prüft Daten... {current}/{total_batches}")
        status_text.caption(text)
    
    status_text.caption(f"✨ {get_active_provider_name()} startet Analyse...")
    review_result = review_dataframes(
        df_sicher, df_unsicher, df_sehr_unsicher,
        progress_callback=update_progress,
        dateiname=uploaded_file.name
    )
    
    progress_container.empty()
    status_text.empty()
    
    # Ergebnis speichern - auch bei KI-Fehler die Original-Daten anzeigen
    if review_result.erfolg:
        save_analysis_results(
            review_result,
            uploaded_file.name
        )
    else:
        # Bei KI-Fehler: Original-Daten trotzdem speichern und anzeigen
        save_analysis_results(
            review_result,  # Enthält Original-Daten bei Fehler
            uploaded_file.name
        )
        # Fehler-Flag für Warnung setzen
        st.session_state["ki_erfolg"] = False
        st.session_state["ki_fehler"] = review_result.fehler_msg


def _render_export_section(display_sicher, display_unsicher, display_sehr_unsicher) -> None:
    """Rendert den Excel-Export Bereich."""
    st.divider()
    st.subheader("📥 Excel Export")
    
    excel_data = export_to_excel_with_logs(
        prepare_for_display(st.session_state.get("data_sicher_original", display_sicher)),
        prepare_for_display(st.session_state.get("data_unsicher_original", display_unsicher)),
        prepare_for_display(st.session_state.get("data_sehr_unsicher_original", display_sehr_unsicher)),
        display_sicher,
        display_unsicher,
        display_sehr_unsicher,
        st.session_state.get("ki_verschiebungen", []),
        st.session_state.get("datei_name", "export")
    )
    
    st.download_button(
        "💾 Excel herunterladen",
        excel_data,
        f"{st.session_state.get('datei_name', 'export')}_extraktion.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


def _render_results() -> None:
    """Rendert das Ergebnis-Cockpit mit Tabs und Export."""
    st.divider()
    
    ki_verschiebungen = st.session_state.get("ki_verschiebungen", [])
    render_ki_hinweis(ki_verschiebungen)
    
    # Metriken
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🟢 Sicher", len(st.session_state.get("data_sicher", [])))
    with col2:
        st.metric("🟡 Unsicher", len(st.session_state.get("data_unsicher", [])))
    with col3:
        st.metric("� Sehr Unsicher", len(st.session_state.get("data_sehr_unsicher", [])))
    
    # Display-Daten und Config
    display_sicher, display_unsicher, display_sehr_unsicher = get_display_dataframes()
    column_config = get_column_config()
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🟢 Sicher", "🟡 Unsicher", "🟠 Sehr Unsicher", "✨ KI Verschoben"])
    
    with tab1:
        render_data_tab("Sichere Treffer", "Von beiden Engines gefunden und KI-geprüft.", display_sicher, column_config)
    
    with tab2:
        render_data_tab("Unsichere Treffer", "Nur von einer Engine gefunden. Bitte prüfen.", display_unsicher, column_config)
    
    with tab3:
        render_data_tab("Sehr Unsichere Treffer", "Verdächtig (Telefon, HRB, etc.). Manuelle Prüfung empfohlen.", display_sehr_unsicher, column_config)
    
    with tab4:
        render_ki_verschiebungen_tab(ki_verschiebungen)
    
    # Export
    _render_export_section(display_sicher, display_unsicher, display_sehr_unsicher)


# =============================================================================
# MAIN UI EXECUTION
# =============================================================================

# --- PAGE CONFIG ---
st.set_page_config(page_title="Artikelnummer Suche", page_icon="🎯", layout="wide")
show_sidebar()

# --- HEADER ---
st.title("WS Artikelnummer-Suche App")
uploaded_file = st.file_uploader("PDF hier reinziehen", type=["pdf"])

# --- ANALYSE-LOGIK ---
if uploaded_file and st.button("🔍 Suche starten", type="primary"):
    _run_analysis(uploaded_file)

# --- FEHLERANZEIGE (Warnung bei KI-Fehler) ---
if st.session_state.get("ki_erfolg") == False and st.session_state.get("analyse_done"):
    st.warning(f"⚠️ **KI-Analyse fehlgeschlagen:** {st.session_state.get('ki_fehler', 'Unbekannter Fehler')}\n\n"
               "Die Daten werden ungeprüft angezeigt. Bitte führen Sie eine manuelle Prüfung durch.")

# --- ERGEBNIS-COCKPIT ---
if st.session_state.get("analyse_done", False):
    _render_results()
