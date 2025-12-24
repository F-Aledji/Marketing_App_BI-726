"""
Unit Tests für core/extractors.py
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.extraction.extractors import (
    clean_text,
    extract_match_groups,
    normalize,
    extract_matches_from_text
)
from core.config.config import get_clean_string


class TestCleanText:
    """Tests für die Text-Bereinigung."""
    
    def test_replace_nbsp(self):
        text = "AB\u00A0123\u00A045"
        result = clean_text(text)
        assert result == "AB 123 45"
        assert "\u00A0" not in result
    
    def test_normal_text_unchanged(self):
        text = "Dies ist normaler Text"
        result = clean_text(text)
        assert result == text


class TestExtractMatchGroups:
    """Tests für die Match-Gruppen-Extraktion."""
    
    def test_alpha_pattern(self):
        match_tuple = ("AB", "123", "45", None, None, None)
        p1, p2, p3 = extract_match_groups(match_tuple)
        assert p1 == "AB"
        assert p2 == "123"
        assert p3 == "45"
    
    def test_numeric_pattern(self):
        match_tuple = (None, None, None, "12", "345", "67")
        p1, p2, p3 = extract_match_groups(match_tuple)
        assert p1 == "12"
        assert p2 == "345"
        assert p3 == "67"


class TestNormalize:
    """Tests für die Normalisierung."""
    
    def test_format_with_spaces(self):
        result = normalize("AB", "123", "45")
        assert result == "AB 123 45"
    
    def test_numeric_format(self):
        result = normalize("12", "345", "67")
        assert result == "12 345 67"


class TestGetCleanString:
    """Tests für get_clean_string."""
    
    def test_no_spaces(self):
        result = get_clean_string("AB", "123", "45")
        assert " " not in result
        assert result == "AB12345"


class TestExtractMatchesFromText:
    """Tests für die Match-Extraktion aus Text."""
    
    @pytest.fixture
    def mock_config(self):
        return {
            "bad_prefixes": ["TEL", "FAX"],
            "bad_numbers": [],
            "context_bad_words": ["Tel", "Fax"],
            "context_good_words": ["Art", "Best"]
        }
    
    def test_find_alpha_pattern(self, mock_config):
        text = "Die Artikelnummer ist AB 123 45 bitte bestellen"
        matches = extract_matches_from_text(text, 1, "Test", mock_config)
        assert len(matches) == 1
        assert matches[0]["Nummer"] == "AB 123 45"
        assert matches[0]["Seite"] == 1
    
    def test_find_numeric_pattern(self, mock_config):
        text = "Bestellung 12 345 67 wurde aufgegeben"
        matches = extract_matches_from_text(text, 2, "Test", mock_config)
        assert len(matches) == 1
        assert matches[0]["Nummer"] == "12 345 67"
        assert matches[0]["Seite"] == 2
    
    def test_filter_bad_prefix(self, mock_config):
        text = "Telefonnummer TEL 123 45 anrufen"
        matches = extract_matches_from_text(text, 1, "Test", mock_config)
        assert len(matches) == 0
    
    def test_multiple_matches(self, mock_config):
        text = "Artikel AB 123 45 und CD 678 90 bestellen"
        matches = extract_matches_from_text(text, 1, "Test", mock_config)
        assert len(matches) == 2
    
    def test_empty_text(self, mock_config):
        matches = extract_matches_from_text("", 1, "Test", mock_config)
        assert matches == []
    
    def test_source_preserved(self, mock_config):
        text = "Artikel AB 123 45"
        matches = extract_matches_from_text(text, 1, "PyMuPDF", mock_config)
        assert matches[0]["Quelle"] == "PyMuPDF"
    
    def test_context_included(self, mock_config):
        text = "Die Artikelnummer AB 123 45 ist wichtig"
        matches = extract_matches_from_text(text, 1, "Test", mock_config)
        assert "Kontext" in matches[0]
        assert len(matches[0]["Kontext"]) > 0
