# WS Bestellnummer Suche App
import streamlit as st
import warnings

# Core-Module importieren
from core.config import get_column_config
from core.extractors import analyze_pdf
from core.analyzers import check_ocr_quality
from core.exporters import export_to_excel

warnings.filterwarnings("ignore", category=UserWarning)

# --- PAGE CONFIG ---
st.set_page_config(page_title="WS PDF Suche", page_icon="🎯", layout="wide")

# --- UI START ---
st.title("Artikelnummer-Suche App")

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
        st.caption("Diese Nummern wurden von beiden Engines gefunden. Vereinzelnte Fehler sind dennoch möglich.")
        
        if not st.session_state["data_sicher"].empty:
            st.dataframe(
                st.session_state["data_sicher"],
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
        
        if not st.session_state["data_unsicher"].empty:
            st.dataframe(
                st.session_state["data_unsicher"],
                width="stretch",
                hide_index=True,
                column_config=column_config
            )
        else:
            st.info("Keine unsicheren Treffer gefunden.")
    
    # --- TAB 3: SPAM ---
    with tab3:
        st.subheader("Spam / Falsch-Positive")
        st.caption("Diese Nummern wurden als Spam erkannt (womöglich falsche Nummern, Telefonnummern, HRB-Nummern, etc.). Bitte überprüfen.")
        
        if not st.session_state["data_spam"].empty:
            st.dataframe(
                st.session_state["data_spam"],
                width="stretch",
                hide_index=True,
                column_config=column_config
            )
        else:
            st.info("Keine Spam-Treffer gefunden.")
    
    # --- EXPORT ---
    st.divider()
    st.subheader("📥 Excel Export")
    
    excel_data = export_to_excel(
        st.session_state["data_sicher"],
        st.session_state["data_unsicher"],
        st.session_state["data_spam"],
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
