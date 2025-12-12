"""
Unit Tests für core/analyzers.py
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.analyzers import check_plausibility, analyze_context, get_clean_string


class TestCheckPlausibility:
    """Tests für die Plausibilitätsprüfung."""
    
    @pytest.fixture
    def mock_config(self):
        return {
            "bad_prefixes": ["TEL", "FAX", "HRB"],
            "bad_numbers": ["1234567", "9999999"],
            "context_bad_words": ["Tel", "Fax"],
            "context_good_words": ["Art", "Best"]
        }
    
    def test_valid_article_number(self, mock_config):
        result = check_plausibility(("AB", "123", "45"), mock_config)
        assert result is True
    
    def test_valid_numeric_number(self, mock_config):
        result = check_plausibility(("12", "345", "89"), mock_config)
        assert result is True
    
    def test_reject_phone_prefix(self, mock_config):
        result = check_plausibility(("TEL", "123", "45"), mock_config)
        assert result is False
    
    def test_reject_fax_prefix(self, mock_config):
        result = check_plausibility(("FAX", "123", "45"), mock_config)
        assert result is False
    
    def test_reject_hrb_prefix(self, mock_config):
        result = check_plausibility(("HRB", "123", "45"), mock_config)
        assert result is False
    
    def test_reject_leading_zero(self, mock_config):
        result = check_plausibility(("01", "234", "56"), mock_config)
        assert result is False
    
    def test_reject_year_2024(self, mock_config):
        result = check_plausibility(("2024", "123", "45"), mock_config)
        assert result is False
    
    def test_reject_year_2025(self, mock_config):
        result = check_plausibility(("2025", "123", "45"), mock_config)
        assert result is False
    
    def test_reject_blacklisted_number(self, mock_config):
        result = check_plausibility(("12", "345", "67"), {
            **mock_config,
            "bad_numbers": ["1234567"]
        })
        assert result is False
    
    def test_case_insensitive_prefix(self, mock_config):
        result = check_plausibility(("tel", "123", "45"), mock_config)
        assert result is False


class TestAnalyzeContext:
    """Tests für die Kontext-Analyse."""
    
    @pytest.fixture
    def mock_config(self):
        return {
            "bad_prefixes": [],
            "bad_numbers": [],
            "context_bad_words": ["Tel", "Fax", "Telefon"],
            "context_good_words": ["Art", "Artikel", "Best"]
        }
    
    def test_context_ok_no_bad_words(self, mock_config):
        text = "Die Bestellung enthält Artikel AB 123 45 in Menge 5"
        status, context = analyze_context(text, 30, 40, mock_config)
        assert status == "Context_OK"
    
    def test_spam_candidate_with_tel(self, mock_config):
        text = "Tel: AB 123 45 ist unsere Hotline"
        status, context = analyze_context(text, 5, 15, mock_config)
        assert status == "Spam_Candidate"
    
    def test_context_at_text_start(self, mock_config):
        text = "AB 123 45 ist die Nummer"
        status, context = analyze_context(text, 0, 9, mock_config)
        assert status == "Context_OK"
        assert len(context) > 0
    
    def test_newlines_removed(self, mock_config):
        text = "Zeile1\nAB 123 45\nZeile3"
        status, context = analyze_context(text, 7, 16, mock_config)
        assert "\n" not in context


class TestGetCleanString:
    """Tests für get_clean_string."""
    
    def test_simple_concat(self):
        result = get_clean_string("AB", "123", "45")
        assert result == "AB12345"
    
    def test_numeric_parts(self):
        result = get_clean_string("12", "345", "67")
        assert result == "1234567"
