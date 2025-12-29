# Developer Dashboard - Standalone App
# Aufruf: streamlit run Dashboard.py
# NICHT für Endnutzer sichtbar (nicht in pages/)

import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Developer Dashboard", page_icon="🔧", layout="wide")

# Import NACH page_config
from core import utils

st.title("🔧 Developer Dashboard")
st.caption("Internes Monitoring für API-Nutzung und Kosten - Nur für Entwickler")

# =============================================================================
# KOSTEN-KONFIGURATION (User-editable)
# =============================================================================

st.sidebar.header("💰 Kosten-Konfiguration")
st.sidebar.caption("Preise pro 1M Tokens (in USD)")

# Standardwerte für gängige Modelle
input_cost_per_million = st.sidebar.number_input(
    "Input Token Preis ($)",
    min_value=0.0,
    max_value=100.0,
    value=2.50,  # GPT-5.1 Standard
    step=0.10,
    help="Kosten pro 1 Million Input-Tokens"
)

output_cost_per_million = st.sidebar.number_input(
    "Output Token Preis ($)",
    min_value=0.0,
    max_value=100.0,
    value=10.00,  # GPT-5.1 Standard
    step=0.10,
    help="Kosten pro 1 Million Output-Tokens"
)

# Umrechnung in Kosten pro Token
input_cost_per_token = input_cost_per_million / 1_000_000
output_cost_per_token = output_cost_per_million / 1_000_000

st.sidebar.divider()
st.sidebar.info(f"💡 Input: ${input_cost_per_token:.8f}/Token\n\nOutput: ${output_cost_per_token:.8f}/Token")

# =============================================================================
# DATEN LADEN
# =============================================================================

stats = utils.get_tracking_stats()

# =============================================================================
# METRIKEN
# =============================================================================

st.subheader("📊 Übersicht")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Gesamte Calls", stats["total_calls"])

with col2:
    st.metric("Erfolgsrate", f"{stats['success_rate']}%")

with col3:
    st.metric("Ø Dauer", f"{stats['avg_duration']}s")

with col4:
    st.metric("Provider", stats["provider"])

st.divider()

# =============================================================================
# TOKEN & KOSTEN
# =============================================================================

st.subheader("💰 Token-Verbrauch & Kosten")

total_input = stats.get("total_input_tokens", 0)
total_output = stats.get("total_output_tokens", 0)

# Kosten berechnen
input_cost = total_input * input_cost_per_token
output_cost = total_output * output_cost_per_token
total_cost = input_cost + output_cost

col_t1, col_t2, col_t3, col_t4 = st.columns(4)

with col_t1:
    st.metric("Input Tokens", f"{total_input:,}")

with col_t2:
    st.metric("Output Tokens", f"{total_output:,}")

with col_t3:
    st.metric("Gesamt Tokens", f"{total_input + total_output:,}")

with col_t4:
    st.metric("💵 Gesamtkosten", f"${total_cost:.4f}")

# Aufschlüsselung
col_c1, col_c2 = st.columns(2)
with col_c1:
    st.caption(f"Input-Kosten: ${input_cost:.4f}")
with col_c2:
    st.caption(f"Output-Kosten: ${output_cost:.4f}")

st.divider()

# =============================================================================
# LOGS TABELLE
# =============================================================================

st.subheader("📋 Letzte 50 API-Calls")

logs = stats.get("logs", [])

if logs:
    df_logs = pd.DataFrame(logs)
    
    # Spalten umbenennen
    column_rename = {
        "timestamp": "Zeit",
        "dateiname": "Datei",
        "provider": "Provider",
        "batch_nummer": "Batch",
        "batch_total": "Total",
        "anzahl_eintraege": "Einträge",
        "dauer_sekunden": "Dauer (s)",
        "status": "Status",
        "input_tokens": "In-Tokens",
        "output_tokens": "Out-Tokens",
        "fehler_msg": "Fehler"
    }
    df_logs = df_logs.rename(columns=column_rename)
    
    # Neueste zuerst
    df_logs = df_logs.iloc[::-1].reset_index(drop=True)
    
    st.dataframe(
        df_logs,
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Noch keine API-Calls geloggt. Führe eine Analyse mit `Suchen.py` durch.")

st.divider()

# =============================================================================
# PERFORMANCE CHART
# =============================================================================

st.subheader("📈 Performance über Zeit")

if logs and len(logs) >= 2:
    df_chart = pd.DataFrame(logs)
    df_chart["dauer_sekunden"] = pd.to_numeric(df_chart["dauer_sekunden"], errors="coerce")
    df_chart["timestamp"] = pd.to_datetime(df_chart["timestamp"], errors="coerce")
    df_chart = df_chart.dropna(subset=["timestamp", "dauer_sekunden"])
    
    if not df_chart.empty:
        df_chart = df_chart.set_index("timestamp")
        st.line_chart(df_chart["dauer_sekunden"], use_container_width=True)
    else:
        st.caption("Keine gültigen Daten für eine Grafik.")
else:
    st.caption("Mindestens 2 Einträge für Grafik nötig.")

# =============================================================================
# FEHLER
# =============================================================================

st.subheader("⚠️ Fehler-Übersicht")

if logs:
    errors = [log for log in logs if log.get("status") == "error"]
    if errors:
        st.warning(f"{len(errors)} Fehler in den letzten 50 Calls")
        for err in errors[-5:]:
            st.error(f"**{err.get('dateiname', '?')}**: {err.get('fehler_msg', 'Unbekannt')}")
    else:
        st.success("✅ Keine Fehler")
else:
    st.caption("Keine Logs vorhanden.")
