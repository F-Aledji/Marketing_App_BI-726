# Exporter-Modul für Excel-Dateien mit korrekter Formatierung
import io
import pandas as pd
<<<<<<< HEAD
from typing import List, Dict, Optional
from core.config import DISPLAY_COLUMNS


# Exportiert alle DataFrames in eine Excel-Datei mit drei Sheets:
# - "Original": Daten vor KI-Anpassungen
# - "KI angepasst": Bereinigte Daten mit farblicher Markierung
# - "Verschiebungen": Tabelle der KI-Änderungen mit Begründung
def export_to_excel(
    df_sicher: pd.DataFrame,            # Tab Sicher (nach KI)
    df_unsicher: pd.DataFrame,          # Tab Unsicher (nach KI)
    df_spam: pd.DataFrame,              # Tab Spam (nach KI)
    filename: str,                       # Dateiname 
    df_original_sicher: Optional[pd.DataFrame] = None,   # Original vor KI
    df_original_unsicher: Optional[pd.DataFrame] = None,
    df_original_spam: Optional[pd.DataFrame] = None,
    verschiebungen: Optional[List[Dict]] = None          # KI-Verschiebungen
) -> bytes:
    buffer = io.BytesIO()
    
    # Hilfsfunktion: Kombiniere DataFrames mit Status-Spalte
    def combine_dataframes(df_s, df_u, df_sp):
        all_data = []
        for status, df in [("Sicher", df_s), ("Unsicher", df_u), ("Spam", df_sp)]:
            if df is not None and not df.empty:
                available_cols = [col for col in DISPLAY_COLUMNS if col in df.columns]
                temp_df = df[available_cols].copy()
                temp_df["Status"] = status
                all_data.append(temp_df)
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        return pd.DataFrame(columns=DISPLAY_COLUMNS + ["Status"])
    
    # Ermittle verschobene Artikelnummern nach Ziel-Kategorie
    verschiebungen = verschiebungen or []
    moved_to_sicher = {v.get("artikelnummer") for v in verschiebungen if v.get("nach", "").lower() == "sicher"}
    moved_to_unsicher = {v.get("artikelnummer") for v in verschiebungen if v.get("nach", "").lower() == "unsicher"}
    moved_to_spam = {v.get("artikelnummer") for v in verschiebungen if v.get("nach", "").lower() == "spam"}
    all_moved = moved_to_sicher | moved_to_unsicher | moved_to_spam
    
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        workbook = writer.book
        text_format = workbook.add_format({'num_format': '@'})
        
        # Farbformate für Highlighting
        format_green = workbook.add_format({'bg_color': '#c6efce', 'num_format': '@'})
        format_yellow = workbook.add_format({'bg_color': '#ffeb9c', 'num_format': '@'})
        format_red = workbook.add_format({'bg_color': '#ffc7ce', 'num_format': '@'})
        
        # === SHEET 1: Original (vor KI-Anpassungen) ===
        if df_original_sicher is not None:
            df_original = combine_dataframes(df_original_sicher, df_original_unsicher, df_original_spam)
        else:
            # Fallback: Aktuelle Daten als "Original" verwenden
            df_original = combine_dataframes(df_sicher, df_unsicher, df_spam)
        
        df_original.to_excel(writer, index=False, sheet_name='Original')
        ws_original = writer.sheets['Original']
        ws_original.set_column('B:B', 20, text_format)
        
        # === SHEET 2: KI angepasst (mit Highlighting) ===
        df_adjusted = combine_dataframes(df_sicher, df_unsicher, df_spam)
        df_adjusted.to_excel(writer, index=False, sheet_name='KI angepasst')
        ws_adjusted = writer.sheets['KI angepasst']
        ws_adjusted.set_column('B:B', 20, text_format)
        
        # Farbliche Markierung der verschobenen Zeilen
        for row_idx, row in df_adjusted.iterrows():
            artikelnummer = row.get("Artikelnummer", "")
            excel_row = row_idx + 1  # +1 wegen Header
            
            if artikelnummer in moved_to_sicher:
                ws_adjusted.set_row(excel_row, cell_format=format_green)
            elif artikelnummer in moved_to_unsicher:
                ws_adjusted.set_row(excel_row, cell_format=format_yellow)
            elif artikelnummer in moved_to_spam:
                ws_adjusted.set_row(excel_row, cell_format=format_red)
        
        # === SHEET 3: Verschiebungen (KI-Protokoll) ===
        if verschiebungen:
            verschiebungen_data = []
            for v in verschiebungen:
                verschiebungen_data.append({
                    "Artikelnummer": v.get("artikelnummer", ""),
                    "Von": v.get("von", ""),
                    "Nach": v.get("nach", ""),
                    "Begründung": v.get("begruendung", "Muster-Anomalie erkannt")
                })
            df_verschiebungen = pd.DataFrame(verschiebungen_data)
        else:
            df_verschiebungen = pd.DataFrame(columns=["Artikelnummer", "Von", "Nach", "Begründung"])
        
        df_verschiebungen.to_excel(writer, index=False, sheet_name='Verschiebungen')
        ws_verschiebungen = writer.sheets['Verschiebungen']
        ws_verschiebungen.set_column('A:A', 20, text_format)
        ws_verschiebungen.set_column('D:D', 50)  # Breite für Begründung
=======
from typing import List, Dict
from core.config import DISPLAY_COLUMNS


def _combine_dataframes(df_sicher: pd.DataFrame, df_unsicher: pd.DataFrame, df_spam: pd.DataFrame) -> pd.DataFrame:
    """Kombiniert alle DataFrames mit Status-Spalte."""
    all_data = []
    for status, df in [("Sicher", df_sicher), ("Unsicher", df_unsicher), ("Spam", df_spam)]:
        if not df.empty:
            available_cols = [col for col in DISPLAY_COLUMNS if col in df.columns]
            temp_df = df[available_cols].copy()
            temp_df["Status"] = status
            all_data.append(temp_df)
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame(columns=DISPLAY_COLUMNS + ["Status"])


def _format_excel_sheet(writer, sheet_name: str, df: pd.DataFrame):
    """Formatiert ein Excel-Sheet mit Text-Format für Artikelnummern."""
    df.to_excel(writer, index=False, sheet_name=sheet_name)
    workbook = writer.book
    worksheet = writer.sheets[sheet_name]
    text_format = workbook.add_format({'num_format': '@'})
    # Artikelnummer-Spalte (B) als Text formatieren
    worksheet.set_column('B:B', 20, text_format)


def export_to_excel_with_logs(
    df_sicher_original: pd.DataFrame,
    df_unsicher_original: pd.DataFrame,
    df_spam_original: pd.DataFrame,
    df_sicher: pd.DataFrame,
    df_unsicher: pd.DataFrame,
    df_spam: pd.DataFrame,
    verschiebungen: List[Dict],
    filename: str
) -> bytes:
    """
    Exportiert alle Daten in eine Excel-Datei mit 3 Sheets:
    - Vor_KI: Original-Daten vor der KI-Analyse
    - Nach_KI: Bereinigte Daten nach der KI-Analyse
    - KI_Logs: Alle Verschiebungen und Korrekturen mit Begründungen
    """
    buffer = io.BytesIO()
    
    # DataFrames kombinieren
    df_vor_ki = _combine_dataframes(df_sicher_original, df_unsicher_original, df_spam_original)
    df_nach_ki = _combine_dataframes(df_sicher, df_unsicher, df_spam)
    
    # KI-Logs DataFrame erstellen
    if verschiebungen:
        logs_data = []
        for v in verschiebungen:
            logs_data.append({
                "Artikelnummer": v.get("artikelnummer", ""),
                "Korrektur": v.get("korrektur", ""),
                "Von": v.get("von", ""),
                "Nach": v.get("nach", ""),
                "Begründung": v.get("begruendung", "")
            })
        df_logs = pd.DataFrame(logs_data)
    else:
        df_logs = pd.DataFrame(columns=["Artikelnummer", "Korrektur", "Von", "Nach", "Begründung"])
    
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        _format_excel_sheet(writer, 'Vor_KI', df_vor_ki)
        _format_excel_sheet(writer, 'Nach_KI', df_nach_ki)
        df_logs.to_excel(writer, index=False, sheet_name='KI_Logs')
        
        # Logs-Sheet formatieren (breitere Spalten für Begründung)
        worksheet = writer.sheets['KI_Logs']
        worksheet.set_column('A:A', 18)  # Artikelnummer
        worksheet.set_column('B:B', 18)  # Korrektur
        worksheet.set_column('C:C', 10)  # Von
        worksheet.set_column('D:D', 10)  # Nach
        worksheet.set_column('E:E', 50)  # Begründung
>>>>>>> 20c20c4ebbafc8485f47815e4b0a657abdd58aed
    
    return buffer.getvalue()


# Legacy-Funktion für Abwärtskompatibilität (nur Nach_KI-Daten)
def export_to_excel(
    df_sicher: pd.DataFrame,
    df_unsicher: pd.DataFrame,
    df_spam: pd.DataFrame,
    filename: str
) -> bytes:
    """Exportiert DataFrames in eine Excel-Datei (Legacy, nur ein Sheet)."""
    buffer = io.BytesIO()
    export_df = _combine_dataframes(df_sicher, df_unsicher, df_spam)
    
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        _format_excel_sheet(writer, 'Ergebnisse', export_df)
    
    return buffer.getvalue()

