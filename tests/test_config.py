"""
Unit Tests für core/config.py
"""
import pytest
import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import PATTERN, INTERNAL_COLUMNS


class TestPatternConstants:
    """Tests für die Regex-Pattern-Konstanten."""
    
    def test_pattern_matches_alpha(self):
        text = "AB 123 45"
        matches = re.findall(PATTERN, text)
        assert len(matches) == 1
    
    def test_pattern_matches_numeric(self):
        text = "12 345 67"
        matches = re.findall(PATTERN, text)
        assert len(matches) == 1
    
    def test_pattern_with_dots(self):
        text = "AB.123.45"
        matches = re.findall(PATTERN, text)
        assert len(matches) == 1
    
    def test_pattern_with_underscores(self):
        text = "AB_123_45"
        matches = re.findall(PATTERN, text)
        assert len(matches) == 1
    
    def test_pattern_no_match_wrong_format(self):
        text = "AB12345"
        matches = re.findall(PATTERN, text)
        assert len(matches) == 0
    
    def test_pattern_multiple_matches(self):
        text = "AB 123 45 und CD 678 90"
        matches = re.findall(PATTERN, text)
        assert len(matches) == 2


class TestResultColumns:
    """Tests für die Spalten-Konstanten."""
    
    def test_result_columns_content(self):
        assert "Seite" in INTERNAL_COLUMNS
        assert "Artikelnummer" in INTERNAL_COLUMNS
        assert "Kontext" in INTERNAL_COLUMNS
    
    def test_result_columns_order(self):
        assert INTERNAL_COLUMNS == ["Seite", "Artikelnummer", "Kontext"]
    
    def test_result_columns_length(self):
        assert len(INTERNAL_COLUMNS) == 3
