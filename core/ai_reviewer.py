
# Dieses Modul analysiert die extrahierten Artikelnummern mit KI und erkennt
# Muster-Anomalien (False-Positives/Negatives). Es unterstützt zwei Provider:
# - Gemini 2.5 Flash (Standard, günstiger)
# - GPT-5 mini (Alternative, präziser)
# 
# Provider-Wechsel: Einfach den ACTIVE_PROVIDER unten ändern.


import os
import json
import pandas as pd
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import dotenv as dotenv

# Load environment variables from .env file
dotenv.load_dotenv()


# KONFIGURATION - API Keys aus Environment-Variablen
# Einzusetzen in einer Umgebungsvariable oder in einer .env Datei:
# - GEMINI_API_KEY=dein_gemini_key
# - OPENAI_API_KEY=dein_openai_key

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Modell-Namen
GEMINI_MODEL = "gemini-3-flash-preview"
OPENAI_MODEL = "gpt-5-mini-2025-08-07"


# =============================================================================
# DATENSTRUKTUREN
# =============================================================================

# Ergebnis der KI Analyse mit den bereinigten DataFrames und Verschiebungen
@dataclass
class ReviewResult:
    # Original-Daten VOR der KI-Analyse (für Excel-Export)
    df_sicher_original: pd.DataFrame
    df_unsicher_original: pd.DataFrame
    df_spam_original: pd.DataFrame
    # Bereinigte Daten NACH der KI-Analyse
    df_sicher: pd.DataFrame
    df_unsicher: pd.DataFrame
    df_spam: pd.DataFrame
    # KI-Aktionen für Logs
    verschiebungen: list  # [{"artikelnummer": "...", "von": "...", "nach": "...", "korrektur": "...", "begruendung": "..."}]
    erfolg: bool = True
    fehler_msg: str = ""


# =============================================================================
# PROMPT TEMPLATE
# =============================================================================
# Der Prompt wird an beide Provider gleich gesendet.
# Die KI erhält die Daten als CSV und soll Muster-Anomalien erkennen.

SYSTEM_PROMPT = """Du bist ein Experte für Datenbereinigung und Artikelnummer-Analyse.
Du erhältst drei Listen von Artikelnummern aus einer PDF-Extraktion:

1. SICHER: Nummern die von beiden Extraktions-Engines gefunden wurden.
2. UNSICHER: Nummern die nur von einer Engine gefunden wurden.
3. SPAM: Verdachtsfälle (falsch-positiv, Telefonnummern, Datum, Häufigkeit >10).

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

ANTWORTE NUR MIT VALIDEM JSON IN DIESEM FORMAT:
Nutze das Feld "korrektur" nur, wenn sich der Zahlenwert ändert. Das Feld "artikelnummer" ist die ID zum Finden des Eintrags und muss dem Input entsprechen.

{
    "verschiebungen": [
        {
            "artikelnummer": "ab 247 10",
            "korrektur": "94 247 10",
            "von": "Sicher",
            "nach": "Sicher",
            "begruendung": "Fragment im Kontext korrigiert, passt nun zum Seitenmuster."
        },
        {
            "artikelnummer": "030 123456",
            "von": "Unsicher",
            "nach": "Spam",
            "begruendung": "Telefonnummer erkannt."
        }
    ]
}

Falls keine Fehler gefunden wurden, antworte exakt mit: {"verschiebungen": []}"""

# Baut den User Prompt mit den CSV-Daten der drei DataFrames
# Input sind die drei DataFrames
# Ausgabe ist ein formatierter String mit den CSV-Daten
def _build_user_prompt(df_sicher: pd.DataFrame, df_unsicher: pd.DataFrame, df_spam: pd.DataFrame) -> str:
  
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


# ABSTRAKTE PROVIDER-KLASSE aus der ein Ki - Provider (Google Gemini, OpenAI GPTs) abgeleitet wird
# Jedes Modell muss die analyze()-Methode implementieren
class AIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        # Name des Providers
        pass
    
    # Sendet den prompt an die KI und gibt das Ergebnis zurück
    # Ausgabe ist ein Dict mit "verschiebungen" Liste
    # Exceptions für API Fehler
    @abstractmethod
    def analyze(self, user_prompt: str) -> dict:
        pass

# GEMINI PROVIDER (Standard) für Google Gemini 2.5 Flash - 1M Token Input Kontext ca 65.536 Output
class GeminiProvider(AIProvider):
    @property
    def name(self) -> str:
        return "Gemini 2.5 Flash"
    
    # Sendet Anfrage an Gemini API mit JSON-Response-Format
    def analyze(self, user_prompt: str) -> dict:
        # Import hier um Fehler zu vermeiden wenn Package nicht installiert
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError("google-genai Package nicht installiert. Führe aus: pip install google-genai")
        
        # API Key prüfen
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY nicht gesetzt. Setze die Environment-Variable.")
        
        # Client initialisieren
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Anfrage senden mit JSON-Response-Format
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                thinking_config=types.ThinkingConfig(thinking_level="high")
                  # Niedrige Temperatur für konsistente Ergebnisse
            )
        )
        
        # Response parsen
        result = json.loads(response.text)
        return result


# =============================================================================
# OPENAI PROVIDER (Alternative)


# Hier wird GPT 5 mini genutzt - 400k Token Input - 128k Token Output Kontext 
# Etwas teurer als Gemini, aber oft präziser bei strukturierten Daten
class OpenAIProvider(AIProvider):    
    @property
    def name(self) -> str:
        return "GPT-5 mini"
    
    # Sendet Anfrage an OpenAI API mit JSON-Response-Format
    def analyze(self, user_prompt: str) -> dict:

        # Import hier um Fehler zu vermeiden wenn Package nicht installiert
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai Package nicht installiert. Führe aus: pip install openai")
        
        # API Key prüfen
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY nicht gesetzt. Setze die Environment-Variable.")
        
        # Client initialisieren
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Anfrage senden mit JSON-Response-Format
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1  # Niedrige Temperatur für konsistente Ergebnisse
        )
        
        # Response parsen
        result = json.loads(response.choices[0].message.content)
        return result


# =============================================================================
# PROVIDER AUSWAHL - Hier ändern um Provider zu wechseln!
# =============================================================================
# Kommentiere den gewünschten Provider ein/aus:

ACTIVE_PROVIDER = GeminiProvider()    # <- Standard: Gemini 3 Flash Preview
# ACTIVE_PROVIDER = OpenAIProvider()  # <- Alternative: GPT-5 mini


# =============================================================================
# HAUPTFUNKTION
# =============================================================================

# Hauptfunktion zur Überprüfung und Korrektur der DataFrames mit KI
# Konvertiert die DataFrames zu CSV, sendet sie an die KI und wendet die empfohlenen Verschiebungen an
# Gibt die bereinigten DataFrames zurück
def review_dataframes(
    df_sicher: pd.DataFrame,
    df_unsicher: pd.DataFrame,
    df_spam: pd.DataFrame
) -> ReviewResult:
    # Original-Daten sichern für Excel-Export (vor jeder Modifikation)
    df_sicher_original = df_sicher.copy()
    df_unsicher_original = df_unsicher.copy()
    df_spam_original = df_spam.copy()
    
    # Prüfen ob überhaupt Daten vorhanden sind
    total = len(df_sicher) + len(df_unsicher) + len(df_spam)
    if total == 0:
        return ReviewResult(
            df_sicher_original=df_sicher_original,
            df_unsicher_original=df_unsicher_original,
            df_spam_original=df_spam_original,
            df_sicher=df_sicher,
            df_unsicher=df_unsicher,
            df_spam=df_spam,
            verschiebungen=[],
            erfolg=True
        )
    
    try:
        # Prompt bauen
        user_prompt = _build_user_prompt(df_sicher, df_unsicher, df_spam)
        
        # KI-Analyse durchführen
        result = ACTIVE_PROVIDER.analyze(user_prompt)
        verschiebungen = result.get("verschiebungen", [])
        
        # Dictionary-basierter Ansatz für DRY-Code
        dfs = {
            "sicher": df_sicher.copy(),
            "unsicher": df_unsicher.copy(),
            "spam": df_spam.copy()
        }
        
        # Verschiebungen und Korrekturen anwenden
        for v in verschiebungen:
            artikelnummer = v.get("artikelnummer", "")
            korrektur = v.get("korrektur", "")  # NEU: Korrigierte Artikelnummer
            von = v.get("von", "").lower()
            nach = v.get("nach", "").lower()
            
            # Validierung der Kategorie-Namen
            if von not in dfs or nach not in dfs:
                continue  # Ungültige Quelle/Ziel, überspringen
            
            # Zeile finden
            maske = dfs[von]["Artikelnummer"] == artikelnummer
            if maske.any():
                # Zeile extrahieren
                zeile = dfs[von][maske].copy()
                
                # KORREKTUR anwenden: Artikelnummer ersetzen falls vorhanden
                if korrektur:
                    zeile["Artikelnummer"] = korrektur
                
                # Aus Quelle entfernen
                dfs[von] = dfs[von][~maske]
                
                # In Ziel einfügen
                dfs[nach] = pd.concat([dfs[nach], zeile], ignore_index=True)
        
        return ReviewResult(
            df_sicher_original=df_sicher_original,
            df_unsicher_original=df_unsicher_original,
            df_spam_original=df_spam_original,
            df_sicher=dfs["sicher"],
            df_unsicher=dfs["unsicher"],
            df_spam=dfs["spam"],
            verschiebungen=verschiebungen,
            erfolg=True
        )
        
    except Exception as e:
        # Bei Fehler: Original-DataFrames zurückgeben mit Fehlermeldung
        # Die UI kann entscheiden ob sie ungeprüfte Daten anzeigen will
        return ReviewResult(
            df_sicher_original=df_sicher_original,
            df_unsicher_original=df_unsicher_original,
            df_spam_original=df_spam_original,
            df_sicher=df_sicher_original,
            df_unsicher=df_unsicher_original,
            df_spam=df_spam_original,
            verschiebungen=[],
            erfolg=False,
            fehler_msg=f"KI-Analyse fehlgeschlagen: {str(e)}"
        )

# Gibt den Nmen des aktiven Providers zurück
def get_active_provider_name() -> str:
    return ACTIVE_PROVIDER.name
