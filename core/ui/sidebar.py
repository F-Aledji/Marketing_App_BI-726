# Sidebar Module
# Enthält die Sidebar-Komponenten

import streamlit as st


def show_sidebar():
    """Zeigt die Sidebar mit Links."""
    with st.sidebar:
        st.subheader("🔗 Externe Links")
        st.markdown("[Jira-Ticket erstellen](https://ws-support.atlassian.net/servicedesk/customer/portals)")