import streamlit as st
import pdfplumber
import fitz  # PyMuPDF
import re
import pandas as pd
import io
import warnings
import os

# Utils importieren (Verbindung zum "Gehirn")
from utils import render_sidebar, load_blacklist_config

warnings.filterwarnings("ignore", category=UserWarning)

st.set_page_config(page_title="WS Jäger", page_icon="🎯", layout="wide")

# Sidebar laden
render_sidebar()

# --- KONFIGURATION LADEN ---
# Hier laden wir die "Single Source of Truth" beim Start
config = load_blacklist_config()

BAD_PREFIXES = config.get("bad_prefixes", [])
BAD_NUMBERS = config.get("bad_numbers", [])

# Regex Pattern
pattern_alpha = r"(?<![A-Z])([A-Z]{2,4})[\s._\u00A0]+(\d{3})[\s._\u00A0]+(\d{2})(?!\d)"
pattern_numeric = r"(?<!\d)(\d{2})[\s._\u00A0]+(\d{3})[\s._\u00A0]+(\d{2})(?!\d)"
pattern = rf"(?i)(?:{pattern_alpha})|(?:{pattern_numeric})"

# --- HILFSFUNKTIONEN ---

def extract_match_groups(match_tuple):
    if match_tuple[0]: return match_tuple[0], match_tuple[1], match_tuple[2]
    else: return match_tuple[3], match_tuple[4], match_tuple[5]

def normalize(p1, p2, p3): return f"{p1} {p2} {p3}"
def get_clean_string(p1, p2, p3): return f"{p1}{p2}{p3}"

def check_plausibility(match_tuple):
    """
    Prüft gegen Logik UND gegen die geladene JSON-Blacklist.
    """
    p1, p2, p3 = match_tuple
    p1_upper = p1.upper()
    
    # 1. Hard-Checks (Telefon, Jahr)
    if p1.startswith("0"): return False
    if p1 in ["2023", "2024", "2025", "2026"]: return False
    
    # 2. JSON CHECK: Bad Numbers (Exakte Matches)
    clean_num = get_clean_string(p1, p2, p3)
    if clean_num in BAD_NUMBERS: 
        return False
    
    # 3. JSON CHECK: Bad Prefixes (Startet mit...)
    # Löst das "CK21" Problem: Wenn CK gesperrt ist, fliegt CK21 raus.
    for bad_prefix in BAD_PREFIXES:
        if p1_upper.startswith(bad_prefix):
            return False
            
    return True

# --- EXTRAKTOREN ---
@st.cache_data
def analyze_pdf(uploaded_file):
    bytes_data = uploaded_file.getvalue()
    results = []
    
    # 1. PyMuPDF (Fitz)
    try:
        doc = fitz.open(stream=bytes_data, filetype="pdf")
        for i, page in enumerate(doc):
            text = "" 
            text += page.get_text() + " "
            blocks = page.get_text("blocks")
            for block in blocks:
                if len(block) >= 5:
                    if isinstance(block[4], str): text += " " + block[4]
            try:
                text_dict = page.get_text("dict")
                for block in text_dict.get("blocks", []):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text += " " + span.get("text", "")
            except: pass
            
            if text and len(text.strip()) > 5:
                for m in re.findall(pattern, text):
                    p1, p2, p3 = extract_match_groups(m)
                    if check_plausibility((p1, p2, p3)):
                        results.append({
                            "Nummer": normalize(p1, p2, p3),
                            "Clean": get_clean_string(p1, p2, p3),
                            "Seite": i + 1, "Quelle": "PyMuPDF"
                        })
    except Exception as e:
        st.error(f"⚠️ PyMuPDF Fehler: {e}")

    # 2. pdfplumber
    try:
        with pdfplumber.open(io.BytesIO(bytes_data)) as pdf:
            for i, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text() or ""
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            for cell in row:
                                if cell: text += " " + str(cell)
                    
                    if text and len(text.strip()) > 10:
                        for m in re.findall(pattern, text):
                            p1, p2, p3 = extract_match_groups(m)
                            if check_plausibility((p1, p2, p3)):
                                results.append({
                                    "Nummer": normalize(p1, p2, p3),
                                    "Clean": get_clean_string(p1, p2, p3),
                                    "Seite": i + 1, "Quelle": "pdfplumber"
                                })
                except: continue
    except Exception as e:
        if "stroke color" not in str(e).lower():
            st.error(f"⚠️ pdfplumber Fehler: {e}")

    # --- DEDUPLIZIERUNG & STATUS ---
    if not results: return pd.DataFrame()

    seen = set()
    final_data = []
    
    # Zählen für Spam-Erkennung
    all_cleans = [x["Clean"] for x in results]
    from collections import Counter
    counts = Counter(all_cleans)

    # Cross-Match Sets
    plumber_set = {x["Clean"] for x in results if x["Quelle"] == "pdfplumber"}
    fitz_set = {x["Clean"] for x in results if x["Quelle"] == "PyMuPDF"}

    for item in results:
        key = (item["Clean"], item["Seite"])
        if key in seen: continue
        seen.add(key)
        
        status = "Unsicher"
        if counts[item["Clean"]] > 10: status = "Löschkandidat"
        elif item["Clean"] in plumber_set and item["Clean"] in fitz_set: status = "Sicher"
        
        final_data.append({
            "Seite": item["Seite"],
            "Artikelnummer": item["Nummer"],
            "Status": status
        })

    df = pd.DataFrame(final_data)
    if not df.empty:
        df = df.sort_values(by=["Status", "Seite", "Artikelnummer"])
    return df

# --- UI START ---
st.title("WS Bestellnummer Suche")
st.markdown(f"**System Status:** {len(BAD_PREFIXES)} Filter-Regeln | {len(BAD_NUMBERS)} gesperrte Nummern geladen.")

uploaded_file = st.file_uploader("PDF hier reinziehen", type=["pdf"])

if uploaded_file:
    # Button Start
    if st.button("Suche starten"):
        with st.spinner("Suche läuft..."):
            df = analyze_pdf(uploaded_file)
            
            # Session State speichern
            st.session_state["analyse_ergebnis"] = df
            st.session_state["datei_name"] = uploaded_file.name
            
            if df.empty:
                st.warning("Nichts gefunden.")
            else:
                st.success(f"{len(df)} Treffer gefunden!")
                
                # Metrics
                c1, c2, c3 = st.columns(3)
                c1.metric("✅ Sicher", len(df[df['Status']=='Sicher']))
                c2.metric("⚠️ Unsicher", len(df[df['Status']=='Unsicher']))
                c3.metric("❌ Spam", len(df[df['Status'].str.contains("Löschkandidat")]))
                
                st.dataframe(df, width='stretch')
                
                # Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                
                st.download_button("💾 Excel Download", buffer.getvalue(), f"{uploaded_file.name}.xlsx")