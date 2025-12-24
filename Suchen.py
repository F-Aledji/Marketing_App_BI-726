# WS Bestellnummer Suche App
import streamlit as st
import warnings
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Core-Module importieren
from core.config.config import get_column_config, prepare_for_display
from core.extraction.extractors import analyze_pdf
from core.analysis.analyzers import check_ocr_quality
from core.analysis.verification import verify_against_reference, get_verification_stats
from core.export.exporters import export_to_excel_with_logs
from core.ai.reviewer import review_dataframes
from core.ai.providers import get_active_provider_name
from core.ui.sidebar import show_sidebar

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
        
        # Schritt 2: KI-Analyse mit Progress-Feedback
        if total > 0:
            progress_container = st.empty()
            status_text = st.empty()
            
            def update_progress(current: int, total_batches: int, text: str):
                """Callback für Live-Progress-Updates."""
                progress = current / total_batches if total_batches > 0 else 1.0
                progress_container.progress(progress, text=f"Batch {current}/{total_batches}")
                status_text.caption(text)
            
            status_text.caption(f"✨ {get_active_provider_name()} startet Analyse...")
            review_result = review_dataframes(
                df_sicher, df_unsicher, df_spam,
                progress_callback=update_progress,
                dateiname=uploaded_file.name
            )
            
            # Progress-Container ausblenden nach Abschluss
            progress_container.empty()
            status_text.empty()
            
            if review_result.erfolg:
                # KI-bereinigte DataFrames verwenden
                df_sicher = review_result.df_sicher
                df_unsicher = review_result.df_unsicher
                df_spam = review_result.df_spam
                
                # Verifizierung gegen Referenzliste (falls geladen)
                if st.session_state.get("reference_set"):
                    ref_set = st.session_state["reference_set"]
                    df_sicher = verify_against_reference(df_sicher, ref_set)
                    df_unsicher = verify_against_reference(df_unsicher, ref_set)
                    df_spam = verify_against_reference(df_spam, ref_set)
                
                # Session State speichern (mit KI-Korrekturen und ggf. Verifizierung)
                st.session_state["data_sicher"] = df_sicher
                st.session_state["data_unsicher"] = df_unsicher
                st.session_state["data_spam"] = df_spam
                st.session_state["datei_name"] = uploaded_file.name
                st.session_state["analyse_done"] = True
                
                st.session_state["ki_verschiebungen"] = review_result.verschiebungen
                st.session_state["ki_erfolg"] = True
                
                # Original-Daten für Excel-Export speichern
                st.session_state["data_sicher_original"] = review_result.df_sicher_original
                st.session_state["data_unsicher_original"] = review_result.df_unsicher_original
                st.session_state["data_spam_original"] = review_result.df_spam_original
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
    
    # Tabs für das Frontend
    tab1, tab2, tab3, tab4 = st.tabs(["🟢 Sicher", "🟡 Unsicher", "🔴 Spam", "✨ KI Verschoben"])
    
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
    
    # --- TAB 4: KI VERSCHOBEN (NEU) ---
    with tab4:
        st.subheader("KI-Verschiebungen & Korrekturen")
        st.caption("Übersicht aller Änderungen, die die KI vorgenommen hat, mit Begründungen.")
        
        ki_verschiebungen = st.session_state.get("ki_verschiebungen", [])
        
        if ki_verschiebungen:
            # DataFrame für die Anzeige erstellen
            import pandas as pd
            logs_data = []
            for v in ki_verschiebungen:
                logs_data.append({
                    "Artikelnummer": v.get("artikelnummer", ""),
                    "Korrektur": v.get("korrektur", "") or "—",
                    "Von": v.get("von", ""),
                    "Nach": v.get("nach", ""),
                    "Begründung": v.get("begruendung", "")
                })
            df_logs = pd.DataFrame(logs_data)
            
            # Statistik anzeigen
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                zu_spam = sum(1 for v in ki_verschiebungen if v.get("nach", "").lower() == "spam")
                st.metric("→ Spam", zu_spam)
            with col_stat2:
                zu_sicher = sum(1 for v in ki_verschiebungen if v.get("nach", "").lower() == "sicher")
                st.metric("→ Sicher", zu_sicher)
            with col_stat3:
                korrekturen = sum(1 for v in ki_verschiebungen if v.get("korrektur"))
                st.metric("Korrekturen", korrekturen)
            
            st.dataframe(
                df_logs,
                width="stretch",
                hide_index=True,
                column_config={
                    "Artikelnummer": st.column_config.TextColumn("Original", width="medium"),
                    "Korrektur": st.column_config.TextColumn("Korrigiert zu", width="medium"),
                    "Von": st.column_config.TextColumn("Von", width="small"),
                    "Nach": st.column_config.TextColumn("Nach", width="small"),
                    "Begründung": st.column_config.TextColumn("Begründung", width="large")
                }
            )
        else:
            st.info("✅ Die KI hat keine Änderungen vorgenommen. Alle Einträge waren korrekt klassifiziert.")
    
    # --- EXPORT ---
    st.divider()
    st.subheader("📥 Excel Export")
    
    # Export mit Display-Spalten und KI-Logs (3 Sheets: Vor_KI, Nach_KI, KI_Logs)
    excel_data = export_to_excel_with_logs(
        prepare_for_display(st.session_state.get("data_sicher_original", display_sicher)),
        prepare_for_display(st.session_state.get("data_unsicher_original", display_unsicher)),
        prepare_for_display(st.session_state.get("data_spam_original", display_spam)),
        display_sicher,
        display_unsicher,
        display_spam,
        st.session_state.get("ki_verschiebungen", []),
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
