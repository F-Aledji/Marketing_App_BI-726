import streamlit as st
import pdfplumber
import fitz  # PyMuPDF
import re
import pandas as pd
from collections import Counter
import io
import warnings

# --- WARNUNGEN ---
warnings.filterwarnings("ignore", category=UserWarning)

# --- STREAMLIT SEITEN-KONFIGURATION ---
st.set_page_config(
    page_title="WS Bestellnummer Analyse",
    page_icon="🎯",
    layout="wide"
)

# --- SIDEBAR ---
with st.sidebar:
    # Logo Platzhalter
    st.image("https://via.placeholder.com/150x50?text=LOGO", use_container_width=True)
    st.markdown("---")
    st.markdown("[🔗 Externer Link (Platzhalter)](https://example.com)")

# --- DEINE LOGIK & KONSTANTEN ---

# -- Suchmuster (REGEX 2.0 - Split Logic) --
pattern_alpha = r"(?<![A-Z])([A-Z]{2,4})[\s._\u00A0]+(\d{3})[\s._\u00A0]+(\d{2})(?!\d)"
pattern_numeric = r"(?<!\d)(\d{2})[\s._\u00A0]+(\d{3})[\s._\u00A0]+(\d{2})(?!\d)"

# Kombiniertes Pattern (Entweder oder)
pattern = rf"(?i)(?:{pattern_alpha})|(?:{pattern_numeric})"

known_bad_numbers = ["4499774433", "9988992211", "9988992299"]

bad_words = [
    "TEL", "FAX", "MOB", "HRB", "UST", "BLZ", "IBAN", "SEITE", "BLAU", "ROT", "GELB", "GRÜN", "GRAU", "WEISS", "SCHWARZ","SET", "STK", "STCK", "PAAR", "BOX", "DOSE", "PACK", 
    "MM", "CM", "M", "KG", "G", "LITER", "WATT", "VOLT", "BAR","EUR", "EURO", "CHF", "USD","JAN", "FEB", "MÄRZ", "APR", "MAI", "JUN", "JUNI", "JUL", "JULI", "AUG", "SEPT", "OKT", "NOV", "DEZ", 
    "VON", "BIS", "MIT", "OHNE", "UND", "ODER", "TYP", "MOD", "ART", "NR","WHITE", "CREME", "MM2", "STÜCK", "ROLLE", "VPE", "AB","CK"
]

# --- Hilfsfunktionen ---

def extract_match_groups(match_tuple):
    """
    Extrahiert die 3 relevanten Gruppen aus dem kombinierten Pattern.
    Da (Gruppe1)|(Gruppe2) genutzt wird, sind immer 3 Felder leer.
    """
    # match_tuple sieht z.B. so aus: ('DAHLE', '123', '45', '', '', '')
    if match_tuple[0]:
        return match_tuple[0], match_tuple[1], match_tuple[2]
    else:
        # oder so: ('', '', '', '62', '070', '97')
        return match_tuple[3], match_tuple[4], match_tuple[5]
    

def normalize(p1, p2, p3):
    return f"{p1} {p2} {p3}"

def get_clean_string(p1, p2, p3):
    return f"{p1}{p2}{p3}"

def check_plausibility(match_tuple):
    p1, p2, p3 = match_tuple
    p1_upper = p1.upper()
    if p1.startswith("0"): return False
    if p1 in ["2023", "2024", "2025", "2026"]: return False
    if p1_upper in bad_words: return False
    clean_num = get_clean_string(p1, p2, p3)
    if clean_num in known_bad_numbers: return False
    return True

# --- EXTRAKTOREN ---

@st.cache_data
def analyze_pdf(uploaded_file):
    """
    Führt die komplette Analyse auf dem hochgeladenen File-Objekt aus.
    Gibt ein Pandas DataFrame zurück.
    """
    
    bytes_data = uploaded_file.getvalue()
    results = []
    
    # 1. PyMuPDF (Fitz) Analyse - PRIMÄRE METHODE (Deep Scan)
    try:
        doc = fitz.open(stream=bytes_data, filetype="pdf")
        for i, page in enumerate(doc):
            text = "" # Sammel-Variable für alle Text-Methoden
            
            # Methode A: Normaler Text
            text += page.get_text() + " "
            
            # Methode B: Text aus Blöcken (besser für komplexe Layouts)
            blocks = page.get_text("blocks")
            for block in blocks:
                if len(block) >= 5:
                    block_text = block[4]
                    if isinstance(block_text, str):
                        text += " " + block_text
            
            # Methode C: Text als Dictionary (findet auch versteckten Text)
            try:
                text_dict = page.get_text("dict")
                for block in text_dict.get("blocks", []):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text += " " + span.get("text", "")
            except:
                pass
            
            # Analyse des gesammelten Texts der Seite
            if text and len(text.strip()) > 5:
                for m in re.findall(pattern, text):
                    p1, p2, p3 = extract_match_groups(m)
                    if check_plausibility((p1, p2, p3)):
                        results.append({
                            "Nummer": normalize(p1, p2, p3),
                            "Clean": get_clean_string(p1, p2, p3),
                            "Seite": i + 1,
                            "Quelle": "PyMuPDF"
                        })
    except Exception as e:
        st.error(f"⚠️ PyMuPDF Fehler: {e}")

    # 2. pdfplumber Analyse - BACKUP METHODE
    try:
        with pdfplumber.open(io.BytesIO(bytes_data)) as pdf:
            for i, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text() or ""
                    
                    # Zusätzlich: Tabellen scannen
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            for cell in row:
                                if cell:
                                    text += " " + str(cell)
                    
                    if text and len(text.strip()) > 10:
                        for m in re.findall(pattern, text):
                            p1, p2, p3 = extract_match_groups(m)
                            if check_plausibility((p1, p2, p3)):
                                results.append({
                                    "Nummer": normalize(p1, p2, p3),
                                    "Clean": get_clean_string(p1, p2, p3),
                                    "Seite": i + 1,
                                    "Quelle": "pdfplumber"
                                })
                except: 
                    continue
    except Exception as e:
        # Nur kritische Fehler anzeigen, die keine Stroke-Warnings sind
        if "stroke color" not in str(e).lower():
            st.error(f"⚠️ pdfplumber Fehler: {e}")

    # --- FILTER LOGIK & DEDUPLIZIERUNG ---
    if not results:
        return pd.DataFrame()

    # Spam Filter (zu oft vorkommende Nummern)
    alle_clean = [x["Clean"] for x in results]
    counter = Counter(alle_clean)
    spam_nummern = {num for num, count in counter.items() if count > 10}

    # Cross-Match Check (Wurde es von beiden Engines gefunden?)
    plumber_hits = {x["Clean"] for x in results if x["Quelle"] == "pdfplumber"}
    pymupdf_hits = {x["Clean"] for x in results if x["Quelle"] == "PyMuPDF"}

    final_data = []
    seen_clean_on_page = set()

    for item in results:
        unique_key = (item["Clean"], item["Seite"])
        if unique_key in seen_clean_on_page:
            continue
        seen_clean_on_page.add(unique_key)

        clean = item["Clean"]
        status = "Unsicher"

        if clean in spam_nummern:
            status = "Löschkandidat (Spam/Footer)"
        elif clean in plumber_hits and clean in pymupdf_hits:
            status = "Sicher"
        
        # Quelle wird nicht mehr hinzugefügt
        final_data.append({
            "Seite": item["Seite"],
            "Artikelnummer": item["Nummer"],
            "Status": status
        })

    df = pd.DataFrame(final_data)
    if not df.empty:
        # Sortieren: Erst Status, dann Seite
        df = df.sort_values(by=["Status", "Seite", "Artikelnummer"])
    
    return df

# --- UI (User Interface) ---

st.title("WS Bestellnummer Analyse Tool ")
st.markdown("""
Lade deine PDF-Datei hoch. Es werden Bestellnummern extrahiert und auf Plausibilität geprüft.""")

uploaded_file = st.file_uploader("PDF hier reinziehen", type=["pdf"])

if uploaded_file:
    st.info(f"Datei geladen: {uploaded_file.name}")
    
    if st.button("Analyse starten"):
        with st.spinner("Die Analyse läuft..."):
            
            df_result = analyze_pdf(uploaded_file)
            
            # Ergebnis in Session State speichern
            st.session_state["analyse_ergebnis"] = df_result
            st.session_state["datei_name"] = uploaded_file.name
            
            if df_result.empty:
                st.warning("Keine passenden Nummern gefunden.")
            else:
                st.success(f"Fertig! {len(df_result)} Treffer gefunden.")
                
                # Metrics Row
                col1, col2, col3 = st.columns(3) 
                
                count_sicher = len(df_result[df_result['Status'] == 'Sicher'])
                col1.metric("✅ Sicher", count_sicher)
                
                count_unsicher = len(df_result[df_result['Status'] == 'Unsicher'])
                col2.metric("⚠️ Unsicher", count_unsicher)
                
                count_loesch = len(df_result[df_result['Status'].str.contains("Löschkandidat")])
                col3.metric("❌ Löschkandidaten", count_loesch)

                # Tabelle
                st.dataframe(df_result, use_container_width=True)

                # Excel Export
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    df_result.to_excel(writer, index=False, sheet_name='Daten')
                
                st.download_button(
                    label="💾 Ergebnis als Excel speichern",
                    data=buffer.getvalue(),
                    file_name=f"{uploaded_file.name}_extrahiert.xlsx",
                    mime="application/vnd.ms-excel"
                )

else:
    st.write("waiting for upload...")