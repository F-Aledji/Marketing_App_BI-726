"""
Unit Tests für config.py (Blacklist-Konfiguration)
"""
import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestGetConfig:
    """Tests für das Laden der Blacklist-Konfiguration."""
    
    def test_returns_dict(self):
        from core.config.config import get_config
        result = get_config()
        assert isinstance(result, dict)
    
    def test_has_required_keys(self):
        from core.config.config import get_config
        result = get_config()
        assert "bad_prefixes" in result
        assert "bad_numbers" in result
        assert "context_bad_words" in result
        assert "context_good_words" in result
    
    def test_values_are_lists(self):
        from core.config.config import get_config
        result = get_config()
        assert isinstance(result["bad_prefixes"], list)
        assert isinstance(result["bad_numbers"], list)
        assert isinstance(result["context_bad_words"], list)
        assert isinstance(result["context_good_words"], list)
