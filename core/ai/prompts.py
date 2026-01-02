# AI Prompts Module
# Enthält die System-Prompts und Prompt-Building-Logik für die KI-Analyse.

import pandas as pd
from core.config.config import VALID_ARTICLE_PREFIXES


# =============================================================================
# SYSTEM PROMPT
# =============================================================================
# Der Prompt wird an beide Provider gleich gesendet.
# Die KI erhält die Daten als CSV und soll Muster-Anomalien erkennen.

def get_system_prompt() -> str:
    """
    Baut den System Prompt dynamisch mit den konfigurierten Präfixen.
    """
    prefix_info = ""
    if VALID_ARTICLE_PREFIXES:
        prefix_list = ", ".join(VALID_ARTICLE_PREFIXES)
        prefix_info = f"""
WICHTIGE REGEL - GÜLTIGE PRÄFIXE:
Unsere Artikelnummern beginnen mit: {prefix_list}
Markiere Nummern ohne diese Präfixe konsequent als Spam, außer der Kontext beweist eindeutig das Gegenteil
Nutze diese Information zusammen mit dem Kontext für deine Entscheidung.
"""
    
    return f"""Du bist ein Experte für Datenbereinigung und Artikelnummer-Analyse.
Du erhältst drei Listen von Artikelnummern aus einer PDF-Extraktion:

1. SICHER: Nummern die von beiden Extraktions-Engines gefunden wurden.
2. UNSICHER: Nummern die nur von einer Engine gefunden wurden.
3. SPAM: Verdachtsfälle (falsch-positiv, Telefonnummern, Datum, Häufigkeit >10).
{prefix_info}
DEINE AUFGABE:
1. Analysiere das dominante Nummern-Muster PRO SEITE.
2. Identifiziere Ausreißer, die nicht ins Muster der Seite passen.
3. Nutze den mitgelieferten KONTEXT, um zu entscheiden:
   - Ist es Spam? (Verschieben nach SPAM)
   - Ist es ein Extraktions-Fehler? (Reparieren)

REPARATUR-LOGIK (WICHTIG):
Oft greift der Regex im PDF daneben (z.B. "ab 123 45" statt "94 123 45").
- Wenn eine Nummer unvollständig oder falsch wirkt, suche im KONTEXT.
- Wenn du im Kontext (oft direkt daneben) die *tatsächliche* Artikelnummer siehst, die perfekt ins Seitenmuster passt, dann führe eine KORREKTUR durch.
- Achte auf Zeilenversatz: Nimm die Nummer, die geometrisch zur Zeile gehört.

OUTPUT REGELN (SILENT SUCCESS):
- Gib NIEMALS Einträge aus, die korrekt sind und nicht verändert werden müssen.
- Melde NUR Einträge, bei denen sich die Kategorie ändert ODER eine inhaltliche Korrektur nötig ist.
- Sparsamkeit: Halte die Begründungen kurz.
- Verschiebe entweder nach SPAM oder Sicher. Nie nach Unsicher.

ANTWORTE NUR MIT VALIDEM JSON IN DIESEM FORMAT:
Nutze das Feld "korrektur" nur, wenn sich der Zahlenwert ändert. Das Feld "artikelnummer" ist die ID zum Finden des Eintrags und muss dem Input entsprechen.

{{
    "verschiebungen": [
        {{
            "artikelnummer": "ab 247 10",
            "korrektur": "94 247 10",
            "von": "Sicher",
            "nach": "Sicher",
            "begruendung": "Fragment im Kontext korrigiert, passt nun zum Seitenmuster."
        }},
        {{
            "artikelnummer": "030 123456",
            "von": "Unsicher",
            "nach": "Spam",
            "begruendung": "Telefonnummer erkannt."
        }}
    ]
}}
Antworte ausschließlich mit dem JSON-Objekt. Keinerlei Einleitung oder Erklärungen außerhalb des JSON.
Falls keine Fehler gefunden wurden, antworte exakt mit: {{"verschiebungen": []}}"""


# Legacy constant for backwards compatibility (use get_system_prompt() instead)
SYSTEM_PROMPT = get_system_prompt()


# =============================================================================
# PROMPT BUILDING
# =============================================================================

def build_user_prompt(
    df_sicher: pd.DataFrame, 
    df_unsicher: pd.DataFrame, 
    df_spam: pd.DataFrame
) -> str:
    """
    Baut den User Prompt mit den CSV-Daten der drei DataFrames.
    
    Args:
        df_sicher: DataFrame mit sicheren Treffern
        df_unsicher: DataFrame mit unsicheren Treffern
        df_spam: DataFrame mit Spam-Treffern
    
    Returns:
        Formatierter String mit den CSV-Daten aller Kategorien
    """
    prompt_parts = []
    
    # Jedes DataFrame als CSV-Block hinzufügen
    for name, df in [("SICHER", df_sicher), ("UNSICHER", df_unsicher), ("SPAM", df_spam)]:
        if not df.empty:
            # Nur relevante Spalten für Analyse (Seite, Artikelnummer, Kontext)
            csv_str = df.to_csv(index=False, sep=';')
            prompt_parts.append(f"=== {name} ({len(df)} Einträge) ===\n{csv_str}")
        else:
            prompt_parts.append(f"=== {name} (0 Einträge) ===\n(leer)")
    
    return "\n\n".join(prompt_parts)
