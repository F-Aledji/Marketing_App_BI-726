"""
WS Bestellnummer Suche - Hauptanwendung (UI)
Extrahiert und validiert Artikelnummern aus PDF-Dokumenten.
"""
import streamlit as st
import warnings

# Core-Module importieren
from core.config import get_column_config
from core.extractors import analyze_pdf
from core.analyzers import check_ocr_quality
from core.exporters import export_to_excel

warnings.filterwarnings("ignore", category=UserWarning)

# --- PAGE CONFIG ---
st.set_page_config(page_title="WS Jäger", page_icon="🎯", layout="wide")

# --- UI START ---
st.title("🎯 WS Bestellnummer Suche")

uploaded_file = st.file_uploader("PDF hier reinziehen", type=["pdf"])

if uploaded_file:
    # Button Start
    if st.button("🔍 Suche starten", type="primary"):
        with st.spinner("Suche läuft..."):
            bytes_data = uploaded_file.getvalue()
            
            # OCR-Qualitätsprüfung (nur beim Starten, nicht beim Upload)
            if check_ocr_quality(bytes_data):
                st.warning("⚠️ **Achtung:** Diese Datei scheint gescannt zu sein (wenig extrahierbarer Text). Die Ergebnisse könnten unvollständig sein.")
            
            df_sicher, df_unsicher, df_spam = analyze_pdf(uploaded_file)
            
            # Session State speichern (nur nach Analyse!)
            st.session_state["data_sicher"] = df_sicher
            st.session_state["data_unsicher"] = df_unsicher
            st.session_state["data_spam"] = df_spam
            st.session_state["datei_name"] = uploaded_file.name
            st.session_state["analyse_done"] = True
            
            total = len(df_sicher) + len(df_unsicher) + len(df_spam)
            if total == 0:
                st.warning("Nichts gefunden.")
            else:
                st.success(f"✅ {total} Treffer gefunden!")

# --- 3-TAB COCKPIT ---
if st.session_state.get("analyse_done", False):
    st.divider()
    
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
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["🟢 Sicher", "🟡 Unsicher", "🔴 Spam"])
    
    # --- TAB 1: SICHER ---
    with tab1:
        st.subheader("Sichere Treffer")
        st.caption("Diese Nummern wurden von beiden Engines gefunden und haben keinen verdächtigen Kontext.")
        
        if not st.session_state["data_sicher"].empty:
            st.dataframe(
                st.session_state["data_sicher"],
                use_container_width=True,
                hide_index=True,
                column_config=column_config
            )
        else:
            st.info("Keine sicheren Treffer gefunden.")
    
    # --- TAB 2: UNSICHER ---
    with tab2:
        st.subheader("Unsichere Treffer")
        st.caption("Diese Nummern wurden nur von einer Engine gefunden. Bitte manuell prüfen.")
        
        if not st.session_state["data_unsicher"].empty:
            st.dataframe(
                st.session_state["data_unsicher"],
                use_container_width=True,
                hide_index=True,
                column_config=column_config
            )
        else:
            st.info("Keine unsicheren Treffer gefunden.")
    
    # --- TAB 3: SPAM ---
    with tab3:
        st.subheader("Spam / Falsch-Positive")
        st.caption("Diese Nummern wurden als Spam erkannt (Telefonnummern, HRB-Nummern, etc.).")
        
        if not st.session_state["data_spam"].empty:
            st.dataframe(
                st.session_state["data_spam"],
                use_container_width=True,
                hide_index=True,
                column_config=column_config
            )
        else:
            st.info("Keine Spam-Treffer gefunden.")
    
    # --- EXPORT ---
    st.divider()
    st.subheader("📥 Export")
    
    excel_data = export_to_excel(
        st.session_state["data_sicher"],
        st.session_state["data_unsicher"],
        st.session_state["data_spam"],
        st.session_state.get("datei_name", "export")
    )
    
    col_exp1, col_exp2 = st.columns([1, 3])
    with col_exp1:
        st.download_button(
            "💾 Excel Download (Alle)", 
            excel_data, 
            f"{st.session_state.get('datei_name', 'export')}_ergebnisse.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
