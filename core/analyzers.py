"""
Analyse-Funktionen für Plausibilitätsprüfung und Kontext-Analyse.
"""
import io
import pdfplumber
from typing import Tuple, List

from core.config import get_config


def get_clean_string(p1: str, p2: str, p3: str) -> str:
    """Gibt die reine Nummer ohne Leerzeichen zurück."""
    return f"{p1}{p2}{p3}"


def check_plausibility(match_tuple: Tuple[str, str, str], config: dict = None) -> bool:
    """
    Prüft gegen Logik UND gegen die geladene JSON-Blacklist.
    
    Args:
        match_tuple: Tuple aus (Teil1, Teil2, Teil3) der Nummer
        config: Optional - Blacklist-Konfiguration
    
    Returns:
        True wenn die Nummer plausibel ist, False wenn sie gefiltert werden soll
    """
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


def analyze_context(text: str, match_start: int, match_end: int, config: dict = None) -> Tuple[str, str]:
    """
    Analysiert den Kontext um einen Match herum und bestimmt den Status.
    
    Args:
        text: Der gesamte Text
        match_start: Start-Position des Matches
        match_end: End-Position des Matches
        config: Optional - Blacklist-Konfiguration
    
    Returns:
        Tuple von (status, context_string)
        - status: "Spam_Candidate" oder "Context_OK"
        - context_string: Der extrahierte Kontext-Text
    """
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


def check_ocr_quality(pdf_bytes: bytes) -> bool:
    """
    Prüft die ersten 3 Seiten auf OCR-Qualität (schneller Check).
    
    Args:
        pdf_bytes: PDF als Bytes
    
    Returns:
        True wenn Warnung angezeigt werden soll (vermutlich gescannt)
    """
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
