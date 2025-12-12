"""
Unit Tests für utils.py
"""
import pytest
import os
import json
import tempfile
import pandas as pd
from unittest.mock import patch
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestLoadBlacklistConfig:
    """Tests für das Laden der Blacklist-Konfiguration."""
    
    def test_returns_dict(self):
        from utils import load_blacklist_config
        result = load_blacklist_config()
        assert isinstance(result, dict)
    
    def test_has_required_keys(self):
        from utils import load_blacklist_config
        result = load_blacklist_config()
        assert "bad_prefixes" in result
        assert "bad_numbers" in result
        assert "context_bad_words" in result
        assert "context_good_words" in result
    
    def test_values_are_lists(self):
        from utils import load_blacklist_config
        result = load_blacklist_config()
        assert isinstance(result["bad_prefixes"], list)
        assert isinstance(result["bad_numbers"], list)
        assert isinstance(result["context_bad_words"], list)
        assert isinstance(result["context_good_words"], list)


class TestSaveBlacklistConfig:
    """Tests für das Speichern der Blacklist-Konfiguration."""
    
    def test_creates_file(self, tmp_path):
        import utils
        original_file = utils.DATA_FILE
        original_dir = utils.DATA_DIR
        
        try:
            utils.DATA_DIR = str(tmp_path)
            utils.DATA_FILE = str(tmp_path / "test_blacklist.json")
            
            config = {"bad_prefixes": ["TEST"], "bad_numbers": [], "context_bad_words": [], "context_good_words": []}
            utils.save_blacklist_config(config)
            
            assert os.path.exists(tmp_path / "test_blacklist.json")
        finally:
            utils.DATA_FILE = original_file
            utils.DATA_DIR = original_dir
    
    def test_saves_valid_json(self, tmp_path):
        import utils
        original_file = utils.DATA_FILE
        original_dir = utils.DATA_DIR
        test_file = tmp_path / "test.json"
        
        try:
            utils.DATA_DIR = str(tmp_path)
            utils.DATA_FILE = str(test_file)
            
            config = {"bad_prefixes": ["ABC"], "bad_numbers": ["123"]}
            utils.save_blacklist_config(config)
            
            with open(test_file, "r") as f:
                loaded = json.load(f)
            
            assert loaded == config
        finally:
            utils.DATA_FILE = original_file
            utils.DATA_DIR = original_dir


class TestLogChange:
    """Tests für das Audit-Logging."""
    
    def test_creates_log_entry(self, tmp_path):
        import utils
        original_file = utils.LOG_FILE
        original_dir = utils.DATA_DIR
        test_file = tmp_path / "test_log.csv"
        
        try:
            utils.DATA_DIR = str(tmp_path)
            utils.LOG_FILE = str(test_file)
            
            utils.log_change("TestUser", "Add", "TEST", "Unit Test")
            
            assert os.path.exists(test_file)
        finally:
            utils.LOG_FILE = original_file
            utils.DATA_DIR = original_dir
    
    def test_log_has_correct_columns(self, tmp_path):
        import utils
        original_file = utils.LOG_FILE
        original_dir = utils.DATA_DIR
        test_file = tmp_path / "test_log.csv"
        
        try:
            utils.DATA_DIR = str(tmp_path)
            utils.LOG_FILE = str(test_file)
            
            utils.log_change("TestUser", "Add", "TEST", "Unit Test")
            
            df = pd.read_csv(test_file)
            assert "Timestamp" in df.columns
            assert "User" in df.columns
            assert "Action" in df.columns
            assert "Value" in df.columns
            assert "Reason" in df.columns
        finally:
            utils.LOG_FILE = original_file
            utils.DATA_DIR = original_dir
    
    def test_appends_to_existing(self, tmp_path):
        import utils
        original_file = utils.LOG_FILE
        original_dir = utils.DATA_DIR
        test_file = tmp_path / "test_log.csv"
        
        try:
            utils.DATA_DIR = str(tmp_path)
            utils.LOG_FILE = str(test_file)
            
            utils.log_change("User1", "Add", "A", "First")
            utils.log_change("User2", "Add", "B", "Second")
            
            df = pd.read_csv(test_file)
            assert len(df) == 2
        finally:
            utils.LOG_FILE = original_file
            utils.DATA_DIR = original_dir
