# PDF Extraktionen und Analyse der Artikelnummern
import io
import re
import fitz  # PyMuPDF
import pdfplumber
import pandas as pd
import streamlit as st
from typing import Tuple, List, Dict
from collections import Counter

from core.config import PATTERN, RESULT_COLUMNS, get_config
from core.analyzers import check_plausibility, analyze_context

# Bereinigt de nText von problematischen Whitespace-Zeichen
def clean_text(text: str) -> str:
    return text.replace('\u00A0', ' ').replace('\xa0', ' ')

# Extrahiert die Match-Gruppen aus dem Regex-Ergebnis
def extract_match_groups(match_tuple: Tuple) -> Tuple[str, str, str]:
    if match_tuple[0]: 
        return match_tuple[0], match_tuple[1], match_tuple[2]
    else: 
        return match_tuple[3], match_tuple[4], match_tuple[5]

# Formatiert die Nummer aus den drei Teilen in lesbares Format
# Damit soll gewährleistet werden dass die Nummern in der UI einheitlich dargestellt werden
def normalize(p1: str, p2: str, p3: str) -> str:
    return f"{p1} {p2} {p3}"

# Gibt die reine Nummer ohne Leerzeichen zurück, z.B. "AB12345" oder "1212345"
def get_clean_string(p1: str, p2: str, p3: str) -> str:
    return f"{p1}{p2}{p3}"

# Extrahiert alle gültigen Matches aus einem Text (DRY-Hilfsfunktion).
# Die Funktion wird sowohl von PyMuPDF als auch von pdfplumber genutzt
# Die Ausgabe ist eine Liste von Dictionaries mit den Match-Informationen
def extract_matches_from_text(text: str, page_num: int, source: str, config: dict = None) -> List[Dict]:
    if config is None:
        config = get_config()
    
    matches = []
    text = clean_text(text)
    
    if not text or len(text.strip()) < 5:
        return matches
    
    for m in re.finditer(PATTERN, text):
        match_tuple = m.groups()
        p1, p2, p3 = extract_match_groups(match_tuple)
        if check_plausibility((p1, p2, p3), config):
            context_status, context_str = analyze_context(text, m.start(), m.end(), config)
            matches.append({
                "Nummer": normalize(p1, p2, p3),
                "Clean": get_clean_string(p1, p2, p3),
                "Seite": page_num,
                "Quelle": source,
                "Context_Status": context_status,
                "Kontext": context_str
            })
    
    return matches

# Hauptfunktion zur Analyse eines PDFs und Extraktion der Artikelnummern
# Input: Streamlit UploadedFile Objekt ist eine Funktion die in Streamlit genutzt werden kann
# Output: Drei DataFrames (Sicher, Unsicher, Spam)
def analyze_pdf(uploaded_file) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    config = get_config()
    bytes_data = uploaded_file.getvalue()
    results = []
    
    # 1. PyMuPDF (Fitz) - mit Kontext-Analyse
    try:
        doc = fitz.open(stream=bytes_data, filetype="pdf")
        for i, page in enumerate(doc):
            text = page.get_text() + " "
            blocks = page.get_text("blocks")
            for block in blocks:
                if len(block) >= 5 and isinstance(block[4], str):
                    text += " " + block[4]
            try:
                text_dict = page.get_text("dict")
                for block in text_dict.get("blocks", []):
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text += " " + span.get("text", "")
            except: pass
            
            results.extend(extract_matches_from_text(text, i + 1, "PyMuPDF", config))
    except Exception as e:
        st.error(f"⚠️ PyMuPDF Fehler: {e}")

    # 2. pdfplumber - mit Kontext-Analyse
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
                    
                    results.extend(extract_matches_from_text(text, i + 1, "pdfplumber", config))
                except: continue
    except Exception as e:
        if "stroke color" not in str(e).lower():
            st.error(f"⚠️ pdfplumber Fehler: {e}")

    # --- DEDUPLIZIERUNG & STATUS ---
    # Wenn keine Ergebnisse, leere DataFrames zurückgeben
    # Wenn Ergebnisse vorhanden, deduplizieren und Status bestimmen
    if not results:
        empty_df = pd.DataFrame(columns=RESULT_COLUMNS)
        return empty_df.copy(), empty_df.copy(), empty_df.copy()

    seen = set()
    final_data = []
    
    # Zählen für Spam-Erkennung
    all_cleans = [x["Clean"] for x in results]
    counts = Counter(all_cleans)

    # Cross-Match Sets
    # Cross-match ist wenn eine Nummer von beiden Engines gefunden wurde
    plumber_set = {x["Clean"] for x in results if x["Quelle"] == "pdfplumber"}
    fitz_set = {x["Clean"] for x in results if x["Quelle"] == "PyMuPDF"}
    
    # Sammle Context-Status und Kontext-String pro Clean-Nummer
    # Clean Nummer ist die Nummer ohne Leerzeichen
    context_status_map: Dict[str, List[str]] = {}
    context_string_map: Dict[str, str] = {}
    for item in results:
        if item["Clean"] not in context_status_map:
            context_status_map[item["Clean"]] = []
            context_string_map[item["Clean"]] = item["Kontext"]
        context_status_map[item["Clean"]].append(item["Context_Status"])

    for item in results:
        key = (item["Clean"], item["Seite"])
        if key in seen: continue
        seen.add(key)
        
        # Bestimme Status basierend auf mehreren Faktoren
        status = "Unsicher"
        
        # Check 1: Häufigkeit (Spam wenn >10 Mal gefunden)
        if counts[item["Clean"]] > 10:
            status = "Spam"
        # Check 2: Kontext-basierter Spam
        # also wenn in der Funktion analyze_context als "Spam_Candidate" markiert wurde
        elif all(s == "Spam_Candidate" for s in context_status_map.get(item["Clean"], [])):
            status = "Spam"
        # Check 3: Cross-Validation (Sicher wenn in beiden Engines gefunden)
        elif item["Clean"] in plumber_set and item["Clean"] in fitz_set:
            status = "Sicher"
        
        final_data.append({
            "Seite": item["Seite"],
            "Artikelnummer": item["Nummer"],
            "Kontext": context_string_map.get(item["Clean"], ""),
            "Status": status
        })

    df = pd.DataFrame(final_data)
    if not df.empty:
        df = df.sort_values(by=["Status", "Seite", "Artikelnummer"]).reset_index(drop=True)
    
    # Aufteilen in drei DataFrames für die UI 
    df_sicher = df[df['Status'] == 'Sicher'][RESULT_COLUMNS].reset_index(drop=True)
    df_unsicher = df[df['Status'] == 'Unsicher'][RESULT_COLUMNS].reset_index(drop=True)
    df_spam = df[df['Status'] == 'Spam'][RESULT_COLUMNS].reset_index(drop=True)
    
    return df_sicher, df_unsicher, df_spam
