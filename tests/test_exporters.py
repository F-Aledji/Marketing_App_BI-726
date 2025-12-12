"""
Unit Tests für core/exporters.py
"""
import pytest
import pandas as pd
from io import BytesIO
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.exporters import export_to_excel
from core.config import RESULT_COLUMNS


class TestExportToExcel:
    """Tests für den Excel-Export."""
    
    @pytest.fixture
    def sample_dataframes(self):
        df_sicher = pd.DataFrame({
            "Seite": [1, 2],
            "Artikelnummer": ["AB 123 45", "CD 678 90"],
            "Kontext": ["Kontext 1", "Kontext 2"]
        })
        
        df_unsicher = pd.DataFrame({
            "Seite": [3],
            "Artikelnummer": ["EF 111 22"],
            "Kontext": ["Kontext 3"]
        })
        
        df_spam = pd.DataFrame({
            "Seite": [4, 5],
            "Artikelnummer": ["TEL 123 45", "FAX 678 90"],
            "Kontext": ["Tel Kontext", "Fax Kontext"]
        })
        
        return df_sicher, df_unsicher, df_spam
    
    def test_returns_bytes(self, sample_dataframes):
        df_sicher, df_unsicher, df_spam = sample_dataframes
        result = export_to_excel(df_sicher, df_unsicher, df_spam, "test")
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_valid_excel_file(self, sample_dataframes):
        df_sicher, df_unsicher, df_spam = sample_dataframes
        result = export_to_excel(df_sicher, df_unsicher, df_spam, "test")
        df_read = pd.read_excel(BytesIO(result))
        assert not df_read.empty
    
    def test_contains_all_data(self, sample_dataframes):
        df_sicher, df_unsicher, df_spam = sample_dataframes
        result = export_to_excel(df_sicher, df_unsicher, df_spam, "test")
        df_read = pd.read_excel(BytesIO(result))
        assert len(df_read) == 5
    
    def test_has_status_column(self, sample_dataframes):
        df_sicher, df_unsicher, df_spam = sample_dataframes
        result = export_to_excel(df_sicher, df_unsicher, df_spam, "test")
        df_read = pd.read_excel(BytesIO(result))
        assert "Status" in df_read.columns
    
    def test_status_values(self, sample_dataframes):
        df_sicher, df_unsicher, df_spam = sample_dataframes
        result = export_to_excel(df_sicher, df_unsicher, df_spam, "test")
        df_read = pd.read_excel(BytesIO(result))
        status_values = df_read["Status"].unique()
        assert "Sicher" in status_values
        assert "Unsicher" in status_values
        assert "Spam" in status_values
    
    def test_empty_dataframes(self):
        empty_df = pd.DataFrame(columns=RESULT_COLUMNS)
        result = export_to_excel(empty_df, empty_df, empty_df, "test")
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_partial_empty(self, sample_dataframes):
        df_sicher, _, _ = sample_dataframes
        empty_df = pd.DataFrame(columns=RESULT_COLUMNS)
        result = export_to_excel(df_sicher, empty_df, empty_df, "test")
        df_read = pd.read_excel(BytesIO(result))
        assert len(df_read) == 2
        assert all(df_read["Status"] == "Sicher")
