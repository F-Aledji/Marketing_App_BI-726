# Exporter-Modul für Excel-Dateien mit korrekter Formatierung
import io
import pandas as pd
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
    
    return buffer.getvalue()
