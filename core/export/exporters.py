# Exporter-Modul für Excel-Dateien mit korrekter Formatierung
import io
import pandas as pd
from typing import List, Dict
from core.config.config import DISPLAY_COLUMNS


def _combine_dataframes(df_sicher: pd.DataFrame, df_unsicher: pd.DataFrame, df_sehr_unsicher: pd.DataFrame) -> pd.DataFrame:
    """Kombiniert alle DataFrames mit Status-Spalte."""
    all_data = []
    for status, df in [("Sicher", df_sicher), ("Unsicher", df_unsicher), ("Sehr Unsicher", df_sehr_unsicher)]:
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
    df_sehr_unsicher_original: pd.DataFrame,
    df_sicher: pd.DataFrame,
    df_unsicher: pd.DataFrame,
    df_sehr_unsicher: pd.DataFrame,
    verschiebungen: List[Dict],
    filename: str
) -> bytes:
    """
    Exportiert alle Daten in eine Excel-Datei mit 3 Sheets:
    - Angepasst: Finale Daten nach der KI-Analyse (Hauptdaten)
    - Original: Ursprüngliche Daten vor der KI-Analyse
    - KI Verschiebungen: Alle Änderungen mit Begründungen
    """
    buffer = io.BytesIO()
    
    # DataFrames kombinieren
    df_original = _combine_dataframes(df_sicher_original, df_unsicher_original, df_sehr_unsicher_original)
    df_angepasst = _combine_dataframes(df_sicher, df_unsicher, df_sehr_unsicher)
    
    # KI-Logs DataFrame erstellen
    if verschiebungen:
        logs_data = []
        for v in verschiebungen:
            logs_data.append({
                "Artikelnummer": v.get("artikelnummer", ""),
                "Korrektur": v.get("korrektur", "") or "",
                "Von": v.get("von", ""),
                "Nach": v.get("nach", ""),
                "Begründung": v.get("begruendung", "")
            })
        df_logs = pd.DataFrame(logs_data)
    else:
        df_logs = pd.DataFrame(columns=["Artikelnummer", "Korrektur", "Von", "Nach", "Begründung"])
    
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        # Sheet 1: Angepasst (finale Daten - wird zuerst angezeigt)
        _format_excel_sheet(writer, 'Angepasst', df_angepasst)
        
        # Sheet 2: Original (Daten vor KI-Analyse)
        _format_excel_sheet(writer, 'Original', df_original)
        
        # Sheet 3: KI Verschiebungen (Logs)
        df_logs.to_excel(writer, index=False, sheet_name='KI Verschiebungen')
        
        # Logs-Sheet formatieren (breitere Spalten für Begründung)
        worksheet = writer.sheets['KI Verschiebungen']
        worksheet.set_column('A:A', 18)  # Artikelnummer
        worksheet.set_column('B:B', 18)  # Korrektur
        worksheet.set_column('C:C', 10)  # Von
        worksheet.set_column('D:D', 10)  # Nach
        worksheet.set_column('E:E', 50)  # Begründung
    
    return buffer.getvalue()
