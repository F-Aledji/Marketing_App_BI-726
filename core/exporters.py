"""
Export-Funktionen für verschiedene Formate.
"""
import io
import pandas as pd
from core.config import RESULT_COLUMNS


def export_to_excel(
    df_sicher: pd.DataFrame, 
    df_unsicher: pd.DataFrame, 
    df_spam: pd.DataFrame, 
    filename: str
) -> bytes:
    """
    Exportiert alle DataFrames in eine Excel-Datei mit korrektem Text-Format.
    Führende Nullen bleiben erhalten.
    
    Args:
        df_sicher: DataFrame mit sicheren Treffern
        df_unsicher: DataFrame mit unsicheren Treffern
        df_spam: DataFrame mit Spam-Treffern
        filename: Dateiname (ohne Extension)
    
    Returns:
        Excel-Datei als Bytes
    """
    buffer = io.BytesIO()
    
    # Kombiniere alle DataFrames für den Export
    all_data = []
    for status, df in [("Sicher", df_sicher), ("Unsicher", df_unsicher), ("Spam", df_spam)]:
        if not df.empty:
            temp_df = df[RESULT_COLUMNS].copy()
            temp_df["Status"] = status
            all_data.append(temp_df)
    
    if all_data:
        export_df = pd.concat(all_data, ignore_index=True)
    else:
        export_df = pd.DataFrame(columns=RESULT_COLUMNS + ["Status"])
    
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        export_df.to_excel(writer, index=False, sheet_name='Ergebnisse')
        
        # Formatierung für Artikelnummer-Spalte (Text, damit führende Nullen erhalten bleiben)
        workbook = writer.book
        worksheet = writer.sheets['Ergebnisse']
        text_format = workbook.add_format({'num_format': '@'})
        
        # Spalte B (Artikelnummer) als Text formatieren
        worksheet.set_column('B:B', 20, text_format)
    
    return buffer.getvalue()
