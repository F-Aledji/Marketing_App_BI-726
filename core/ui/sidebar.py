# Sidebar Module
# Enthält die Sidebar-Komponenten inkl. Referenz-Upload

import streamlit as st
from .. import analysis


def show_sidebar():
    """Zeigt die Sidebar mit Links und Referenz-Upload."""
    with st.sidebar:
        st.subheader("🔗 Externe Links")
        st.markdown("[Jira-Ticket erstellen ↗️](https://ws-support.atlassian.net/servicedesk/customer/portals)")
        
        st.divider()
        
        # --- REFERENZLISTE UPLOAD ---
        st.subheader("📋 Referenzliste")
        st.caption("Lade eine Excel/CSV mit bekannten Artikelnummern hoch, um die Ergebnisse zu verifizieren.")
        
        ref_file = st.file_uploader(
            "Referenz-Datei",
            type=["xlsx", "xls", "csv"],
            key="reference_file_upload",
            label_visibility="collapsed"
        )
        
        if ref_file:
            try:
                reference_set = analysis.load_reference_list(ref_file)
                st.session_state["reference_set"] = reference_set
                st.success(f"✅ {len(reference_set)} Referenz-Nummern geladen")
            except Exception as e:
                st.error(f"❌ Fehler: {e}")
                st.session_state["reference_set"] = None
        
        # Info wenn Referenzliste geladen
        if st.session_state.get("reference_set"):
            if st.button("🗑️ Referenz entfernen", use_container_width=True):
                st.session_state["reference_set"] = None
                st.rerun()