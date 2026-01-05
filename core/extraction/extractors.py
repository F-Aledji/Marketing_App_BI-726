# PDF Extraktionen und Analyse der Artikelnummern
import io
import re
import warnings
import fitz  # PyMuPDF
import pdfplumber
import pandas as pd
import streamlit as st
from typing import Tuple, List, Dict
from collections import Counter

# pdfplumber "stroke color" Warnungen unterdrücken (harmlos bei bestimmten PDFs)
warnings.filterwarnings("ignore", message=".*stroke color.*")

from core.config.config import PATTERN, INTERNAL_COLUMNS, get_config, get_clean_string, VALID_ARTICLE_PREFIXES, BAD_PREFIXES
from core.analysis.analyzers import check_plausibility, analyze_context


def _get_prefix_status(artikelnummer: str) -> str:
    """
    Bestimmt den Präfix-Status einer Artikelnummer.
    
    Returns:
        'valid' - Präfix ist in VALID_ARTICLE_PREFIXES
        'invalid' - Präfix ist in BAD_PREFIXES (Tel, Fax, etc.)
        'unknown' - Präfix ist weder valid noch invalid
    """
    # Extrahiere das Präfix (erster Teil vor dem Leerzeichen)
    parts = artikelnummer.split()
    if not parts:
        return 'unknown'
    
    prefix = parts[0].upper()
    
    # Check gegen BAD_PREFIXES (z.B. TEL, FAX, HRB)
    for bad in BAD_PREFIXES:
        if prefix.startswith(bad.upper()):
            return 'invalid'
    
    # Check gegen VALID_ARTICLE_PREFIXES
    if prefix in [p.upper() for p in VALID_ARTICLE_PREFIXES]:
        return 'valid'
    
    # Numerische Präfixe (2-stellig) prüfen
    if prefix.isdigit() and len(prefix) == 2:
        if prefix in VALID_ARTICLE_PREFIXES:
            return 'valid'
    
    return 'unknown'

# Bereinigt den Text von problematischen Whitespace-Zeichen
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
# Output: Drei DataFrames (Sicher, Unsicher, Sehr Unsicher)
def analyze_pdf(uploaded_file) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    config = get_config()
    bytes_data = uploaded_file.getvalue()
    results = []
    
    # Zähler für erfolgreiche Extraktion
    pymupdf_success = False
    pdfplumber_success = False
    
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
            except Exception:
                pass  # Dict-Extraktion optional, Fehler ignorieren
            
            results.extend(extract_matches_from_text(text, i + 1, "PyMuPDF", config))
        pymupdf_success = True
    except Exception as e:
        error_msg = str(e).lower()
        if "eof" in error_msg or "unexpected" in error_msg:
            st.error("⚠️ **PDF-Datei beschädigt oder unvollständig**\n\n"
                    "Mögliche Ursachen:\n"
                    "- Die PDF wurde nicht vollständig heruntergeladen\n"
                    "- Die Datei ist beschädigt\n"
                    "- Die PDF ist passwortgeschützt\n\n"
                    "💡 **Lösung:** Versuche die PDF erneut herunterzuladen oder öffne sie in einem PDF-Reader um sie zu überprüfen.")
        elif "password" in error_msg or "encrypted" in error_msg:
            st.error("🔒 **PDF ist passwortgeschützt**\n\n"
                    "Diese PDF-Datei ist verschlüsselt und kann nicht ohne Passwort gelesen werden.\n\n"
                    "💡 **Lösung:** Öffne die PDF in einem PDF-Reader, entsperre sie und speichere eine ungeschützte Version.")
        else:
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
                except Exception:
                    continue  # Einzelne Seite überspringen bei Fehler
        pdfplumber_success = True
    except Exception as e:
        error_msg = str(e).lower()
        # Nur Fehler anzeigen wenn PyMuPDF auch fehlgeschlagen ist
        if not pymupdf_success:
            if "eof" in error_msg or "unexpected" in error_msg:
                if "⚠️ **PDF-Datei" not in str(st.session_state.get("_last_error", "")):
                    st.error("⚠️ **PDF-Datei kann nicht gelesen werden**\n\n"
                            "Die Datei scheint beschädigt oder unvollständig zu sein.\n\n"
                            "💡 **Lösung:** Versuche die Originaldatei erneut zu öffnen oder lade sie erneut hoch.")
        elif "stroke color" not in error_msg:
            # Nur als Warning wenn PyMuPDF erfolgreich war
            st.warning(f"ℹ️ pdfplumber konnte einige Inhalte nicht lesen (PyMuPDF hat funktioniert): {e}")

    # --- DEDUPLIZIERUNG & STATUS ---
    # Wenn keine Ergebnisse, leere DataFrames zurückgeben
    # Wenn Ergebnisse vorhanden, deduplizieren und Status bestimmen
    if not results:
        empty_df = pd.DataFrame(columns=INTERNAL_COLUMNS)
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
        
        # Präfix-Status ermitteln (Soft-Klassifikation)
        prefix_status = _get_prefix_status(item["Nummer"])
        
        # Check 1: Häufigkeit (Sehr Unsicher wenn >10 Mal gefunden)
        if counts[item["Clean"]] > 10:
            status = "Sehr Unsicher"
        # Check 2: Ungültiger Präfix (BAD_PREFIXES wie TEL, FAX) -> Sehr Unsicher
        elif prefix_status == 'invalid':
            status = "Sehr Unsicher"
        # Check 3: Kontext-basiert (Sehr Unsicher wenn alle Kontexte negativ)
        elif all(s == "Sehr_Unsicher_Candidate" for s in context_status_map.get(item["Clean"], [])):
            status = "Sehr Unsicher"
        # Check 4: Cross-Validation + valider/unbekannter Präfix
        elif item["Clean"] in plumber_set and item["Clean"] in fitz_set:
            # Cross-Match: Sicher nur wenn Präfix valid oder unknown
            if prefix_status == 'valid':
                status = "Sicher"
            else:
                # Cross-Match aber unbekannter Präfix -> bleibt Unsicher
                status = "Unsicher"
        
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
    df_sicher = df[df['Status'] == 'Sicher'][INTERNAL_COLUMNS].reset_index(drop=True)
    df_unsicher = df[df['Status'] == 'Unsicher'][INTERNAL_COLUMNS].reset_index(drop=True)
    df_sehr_unsicher = df[df['Status'] == 'Sehr Unsicher'][INTERNAL_COLUMNS].reset_index(drop=True)
    
    return df_sicher, df_unsicher, df_sehr_unsicher
