"""
Unit Tests für core/exporters.py
"""
import pytest
import pandas as pd
from io import BytesIO
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.export.exporters import export_to_excel_with_logs
from core.config.config import INTERNAL_COLUMNS


class TestExportToExcelWithLogs:
    """Tests für den Excel-Export mit KI-Logs."""
    
    @pytest.fixture
    def sample_dataframes(self):
        df_sicher = pd.DataFrame({
            "Seite": [1, 2],
            "Artikelnummer": ["AB 123 45", "CD 678 90"],
        })
        
        df_unsicher = pd.DataFrame({
            "Seite": [3],
            "Artikelnummer": ["EF 111 22"],
        })
        
        df_spam = pd.DataFrame({
            "Seite": [4, 5],
            "Artikelnummer": ["TEL 123 45", "FAX 678 90"],
        })
        
        return df_sicher, df_unsicher, df_spam
    
    def test_returns_bytes(self, sample_dataframes):
        df_sicher, df_unsicher, df_spam = sample_dataframes
        result = export_to_excel_with_logs(
            df_sicher, df_unsicher, df_spam,
            df_sicher, df_unsicher, df_spam,
            [], "test"
        )
        assert isinstance(result, bytes)
        assert len(result) > 0
    
    def test_valid_excel_file(self, sample_dataframes):
        df_sicher, df_unsicher, df_spam = sample_dataframes
        result = export_to_excel_with_logs(
            df_sicher, df_unsicher, df_spam,
            df_sicher, df_unsicher, df_spam,
            [], "test"
        )
        df_read = pd.read_excel(BytesIO(result), sheet_name='Angepasst')
        assert not df_read.empty
    
    def test_contains_all_data(self, sample_dataframes):
        df_sicher, df_unsicher, df_spam = sample_dataframes
        result = export_to_excel_with_logs(
            df_sicher, df_unsicher, df_spam,
            df_sicher, df_unsicher, df_spam,
            [], "test"
        )
        df_read = pd.read_excel(BytesIO(result), sheet_name='Angepasst')
        assert len(df_read) == 5
    
    def test_has_status_column(self, sample_dataframes):
        df_sicher, df_unsicher, df_spam = sample_dataframes
        result = export_to_excel_with_logs(
            df_sicher, df_unsicher, df_spam,
            df_sicher, df_unsicher, df_spam,
            [], "test"
        )
        df_read = pd.read_excel(BytesIO(result), sheet_name='Angepasst')
        assert "Status" in df_read.columns
    
    def test_has_three_sheets(self, sample_dataframes):
        df_sicher, df_unsicher, df_spam = sample_dataframes
        result = export_to_excel_with_logs(
            df_sicher, df_unsicher, df_spam,
            df_sicher, df_unsicher, df_spam,
            [], "test"
        )
        excel_file = pd.ExcelFile(BytesIO(result))
        assert 'Original' in excel_file.sheet_names
        assert 'Angepasst' in excel_file.sheet_names
        assert 'KI Verschiebungen' in excel_file.sheet_names
    
    def test_empty_dataframes(self):
        empty_df = pd.DataFrame(columns=["Seite", "Artikelnummer"])
        result = export_to_excel_with_logs(
            empty_df, empty_df, empty_df,
            empty_df, empty_df, empty_df,
            [], "test"
        )
        assert isinstance(result, bytes)
        assert len(result) > 0
