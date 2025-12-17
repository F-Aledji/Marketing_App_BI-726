# Analyse der PDF-Inhalte nach korrekten Nummern und die extraktion des Kontexts in der nähe der Nummern
# Der Kontext ist wichtig damit eine KI gegenprüfen kann ob die Nummer tatsächlich eine Artikelnummer ist oder z.B. eine Nummer aus verschiedenen Spalten
import io
import pdfplumber
from typing import Tuple, List
from core.config import get_config, get_clean_string


# Prüft gegen die Filter-Logik (PATTERN_ALPHA/NUMERIC) UND gegen die geladene JSON-Blacklist
# Gibt True zurück wenn die Nummer plausibel ist, False wenn sie gefiltert werden soll
def check_plausibility(match_tuple: Tuple[str, str, str], config: dict = None) -> bool:
    if config is None:
        config = get_config()
    
    bad_prefixes = config.get("bad_prefixes", [])
    bad_numbers = config.get("bad_numbers", [])
    
    p1, p2, p3 = match_tuple
    p1_upper = p1.upper()
    
    # 1. Hard-Checks (Telefon, Jahr)
    if p1.startswith("0"): 
        return False
    if p1 in ["2023", "2024", "2025", "2026"]: 
        return False
    
    # 2. JSON CHECK: Bad Numbers (Exakte Matches)
    clean_num = get_clean_string(p1, p2, p3)
    if clean_num in bad_numbers: 
        return False
    
    # 3. JSON CHECK: Bad Prefixes (Startet mit...)
    for bad_prefix in bad_prefixes:
        if p1_upper.startswith(bad_prefix):
            return False
            
    return True

# Das ist die Kontextanalyse um zu prüfen ob die Nummer in einem "guten" oder "schlechten" Kontext steht
# Bedeutet z.B. "Tel", "Fax" in der Nähe der Nummer sind schlechte Indikatoren
# Während "Art", "Best" gute Indikatoren sind
# Der Kontext ist in diesem Fall 35 Zeichen vor und nach der gefundenen Nummer
# Args: text - der gesamte Text, match_start - Start-Position des Matches, match_end - End-Position des Matches
# Returns: Tuple von (status - "Spam_Candidate" oder "Context_OK", context_string - der extrahierte Kontext-Text)
def analyze_context(text: str, match_start: int, match_end: int, config: dict = None) -> Tuple[str, str]:
    if config is None:
        config = get_config()
    
    context_bad_words = config.get("context_bad_words", [])
    context_good_words = config.get("context_good_words", [])
    
    # Kontext extrahieren (35 Zeichen vor und nach)
    context_start = max(0, match_start - 35)
    context_end = min(len(text), match_end + 35)
    context = text[context_start:context_end].replace('\n', ' ').strip()
    
    # Relative Position des Matches im Kontext
    match_pos_in_context = match_start - context_start
    
    # Finde Bad Words und deren Distanz zum Match
    bad_word_distance = float('inf')
    for bad_word in context_bad_words:
        idx = context.lower().find(bad_word.lower())
        if idx != -1:
            distance = abs(idx - match_pos_in_context)
            bad_word_distance = min(bad_word_distance, distance)
    
    # Finde Good Words und deren Distanz zum Match
    good_word_distance = float('inf')
    for good_word in context_good_words:
        idx = context.lower().find(good_word.lower())
        if idx != -1:
            distance = abs(idx - match_pos_in_context)
            good_word_distance = min(good_word_distance, distance)
    
    # Entscheidung: Good Word muss näher sein als Bad Word
    if bad_word_distance < float('inf'):
        if good_word_distance < bad_word_distance:
            return "Context_OK", context
        return "Spam_Candidate", context
    
    return "Context_OK", context


# Prüft die ersten 3 Seiten auf OCR-Qualität/gescannte Dokumente) 
# PDF als Bytes übergeben
def check_ocr_quality(pdf_bytes: bytes) -> bool:

    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            total_chars = 0
            pages_to_check = min(3, len(pdf.pages))
            
            for i in range(pages_to_check):
                text = pdf.pages[i].extract_text() or ""
                total_chars += len(text.strip())
            
            avg_chars = total_chars / pages_to_check if pages_to_check > 0 else 0
            return avg_chars < 50
    except:
        return False
