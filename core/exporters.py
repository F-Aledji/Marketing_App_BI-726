# Exporter-Modul für Excel-Dateien mit korrekter Formatierung
import io
import pandas as pd
from core.config import DISPLAY_COLUMNS


# Exportiert alle DataFrames (Tabellenstruktur) in eine Excel-Datei mit korrektem Text-Format.
# Die DataFrames sollten bereits mit prepare_for_display() bereinigt sein.
def export_to_excel(
    df_sicher: pd.DataFrame,    # Tab Sicher in der UI (nur Display-Spalten)
    df_unsicher: pd.DataFrame,  # Tab Unsicher in der UI (nur Display-Spalten)
    df_spam: pd.DataFrame,      # Tab Spam in der UI (nur Display-Spalten)
    filename: str               # Dateiname 
) -> bytes:
    buffer = io.BytesIO()
    
    # Kombiniere alle DataFrames für den Export
    all_data = []
    for status, df in [("Sicher", df_sicher), ("Unsicher", df_unsicher), ("Spam", df_spam)]:
        if not df.empty:
            # Nur verfügbare Display-Spalten verwenden
            available_cols = [col for col in DISPLAY_COLUMNS if col in df.columns]
            temp_df = df[available_cols].copy()
            temp_df["Status"] = status
            all_data.append(temp_df)
    
    if all_data:
        export_df = pd.concat(all_data, ignore_index=True)
    else:
        export_df = pd.DataFrame(columns=DISPLAY_COLUMNS + ["Status"])
    
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        export_df.to_excel(writer, index=False, sheet_name='Ergebnisse')
        
        # Formatierung für Artikelnummer-Spalte (Text, damit führende Nullen erhalten bleiben)
        workbook = writer.book
        worksheet = writer.sheets['Ergebnisse']
        text_format = workbook.add_format({'num_format': '@'})
        
        # Spalte B (Artikelnummer) als Text formatieren
        worksheet.set_column('B:B', 20, text_format)
    
    return buffer.getvalue()
