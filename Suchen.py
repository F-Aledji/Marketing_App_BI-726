# WS Bestellnummer Suche App
import streamlit as st
import warnings

# Core-Module importieren
from core.config import get_column_config, prepare_for_display
from core.extractors import analyze_pdf
from core.analyzers import check_ocr_quality
from core.exporters import export_to_excel
from core.ai_reviewer import review_dataframes, get_active_provider_name
from sidebar import show_sidebar

warnings.filterwarnings("ignore", category=UserWarning)

# --- PAGE CONFIG ---
st.set_page_config(page_title="Artikelnummer Suche", page_icon="🎯", layout="wide")
show_sidebar()

# --- UI START ---
st.title(" WS Artikelnummer-Suche App")

uploaded_file = st.file_uploader("PDF hier reinziehen", type=["pdf"])

if uploaded_file:
    # Button Start
    if st.button("🔍 Suche starten", type="primary"):
        with st.spinner("Suche läuft..."):
            bytes_data = uploaded_file.getvalue()
            
            # OCR-Qualitätsprüfung (nur beim Starten, nicht beim Upload)
            if check_ocr_quality(bytes_data):
                st.warning("⚠️ **Achtung:** Diese Datei scheint gescannt zu sein (wenig extrahierbarer Text). Die Ergebnisse könnten unvollständig sein.")
            
            # Schritt 1: PDF-Extraktion
            df_sicher, df_unsicher, df_spam = analyze_pdf(uploaded_file)
            
            total = len(df_sicher) + len(df_unsicher) + len(df_spam)
            if total == 0:
                st.warning("Nichts gefunden.")
                st.session_state["analyse_done"] = False
            else:
                st.success(f"✅ {total} Treffer gefunden!")
        
        # Schritt 2: KI-Analyse (außerhalb des ersten Spinners für separate Anzeige)
        if total > 0:
            with st.spinner(f"🤖 {get_active_provider_name()} prüft Ergebnisse..."):
                review_result = review_dataframes(df_sicher, df_unsicher, df_spam)
                
                if review_result.erfolg:
                    # KI-bereinigte DataFrames verwenden
                    df_sicher = review_result.df_sicher
                    df_unsicher = review_result.df_unsicher
                    df_spam = review_result.df_spam
                    
                    # Session State speichern (mit KI-Korrekturen)
                    st.session_state["data_sicher"] = df_sicher
                    st.session_state["data_unsicher"] = df_unsicher
                    st.session_state["data_spam"] = df_spam
                    st.session_state["datei_name"] = uploaded_file.name
                    st.session_state["analyse_done"] = True
                    
                    # KI-Verschiebungen speichern für Anzeige
                    st.session_state["ki_verschiebungen"] = review_result.verschiebungen
                    st.session_state["ki_erfolg"] = True
                else:
                    # KI-Fehler: Fehlermeldung speichern, keine Ergebnisse anzeigen
                    st.session_state["ki_erfolg"] = False
                    st.session_state["ki_fehler"] = review_result.fehler_msg
                    st.session_state["analyse_done"] = False

# --- FEHLERANZEIGE BEI KI-PROBLEM ---
if st.session_state.get("ki_erfolg") == False:
    st.error(f"❌ {st.session_state.get('ki_fehler', 'Unbekannter Fehler bei der KI-Analyse')}")

# --- 3-TAB COCKPIT ---
if st.session_state.get("analyse_done", False):
    st.divider()
    
    # KI-Analyse Hinweis (wenn Verschiebungen vorhanden)
    ki_verschiebungen = st.session_state.get("ki_verschiebungen", [])
    if ki_verschiebungen:
        # Zähle Verschiebungen nach Richtung
        zu_spam = sum(1 for v in ki_verschiebungen if v.get("nach", "").lower() == "spam")
        zu_sicher = sum(1 for v in ki_verschiebungen if v.get("nach", "").lower() == "sicher")
        zu_unsicher = sum(1 for v in ki_verschiebungen if v.get("nach", "").lower() == "unsicher")
        
        # Kompakte Anzeige der Verschiebungen
        hinweis_teile = []
        if zu_spam > 0:
            hinweis_teile.append(f"{zu_spam}× → Spam")
        if zu_sicher > 0:
            hinweis_teile.append(f"{zu_sicher}× → Sicher")
        if zu_unsicher > 0:
            hinweis_teile.append(f"{zu_unsicher}× → Unsicher")
        
        st.info(f"🤖 **KI-Analyse:** {', '.join(hinweis_teile)} verschoben")
    
    # Metrics Übersicht
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🟢 Sicher", len(st.session_state.get("data_sicher", [])))
    with col2:
        st.metric("🟡 Unsicher", len(st.session_state.get("data_unsicher", [])))
    with col3:
        st.metric("🔴 Spam", len(st.session_state.get("data_spam", [])))
    
    # Column Config laden
    column_config = get_column_config()
    
    # DataFrames für Anzeige vorbereiten (ohne interne Spalten wie Kontext)
    display_sicher = prepare_for_display(st.session_state["data_sicher"])
    display_unsicher = prepare_for_display(st.session_state["data_unsicher"])
    display_spam = prepare_for_display(st.session_state["data_spam"])
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["🟢 Sicher", "🟡 Unsicher", "🔴 Spam"])
    
    # --- TAB 1: SICHER ---
    with tab1:
        st.subheader("Sichere Treffer")
        st.caption("Diese Nummern wurden von beiden Engines gefunden und von der KI geprüft.")
        
        if not display_sicher.empty:
            st.dataframe(
                display_sicher,
                width="stretch",
                hide_index=True,
                column_config=column_config
            )
        else:
            st.info("Keine sicheren Treffer gefunden.")
    
    # --- TAB 2: UNSICHER ---
    with tab2:
        st.subheader("Unsichere Treffer")
        st.caption("Diese Nummern wurden von nur einer Engine gefunden. Bitte überprüfen.")
        
        if not display_unsicher.empty:
            st.dataframe(
                display_unsicher,
                width="stretch",
                hide_index=True,
                column_config=column_config
            )
        else:
            st.info("Keine unsicheren Treffer gefunden.")
    
    # --- TAB 3: SPAM ---
    with tab3:
        st.subheader("Spam / Falsch-Positive")
        st.caption("Diese Nummern wurden als Spam erkannt (womöglich falsche Nummern, Telefonnummern, HRB-Nummern, etc.).")
        
        if not display_spam.empty:
            st.dataframe(
                display_spam,
                width="stretch",
                hide_index=True,
                column_config=column_config
            )
        else:
            st.info("Keine Spam-Treffer gefunden.")
    
    # --- EXPORT ---
    st.divider()
    st.subheader("📥 Excel Export")
    
    # Export mit Display-Spalten (ohne Kontext)
    excel_data = export_to_excel(
        display_sicher,
        display_unsicher,
        display_spam,
        st.session_state.get("datei_name", "export")
    )
    
    col_exp1, col_exp2 = st.columns([1, 3])
    with col_exp1:
        st.download_button(
            "💾 Tabellen in eine Excel herunterladen", 
            excel_data, 
            f"{st.session_state.get('datei_name', 'export')}_extraktion.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
