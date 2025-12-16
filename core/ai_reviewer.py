
# Dieses Modul analysiert die extrahierten Artikelnummern mit KI und erkennt
# Muster-Anomalien (False-Positives/Negatives). Es unterstützt zwei Provider:
# - Gemini 2.5 Flash (Standard, günstiger)
# - GPT-5 mini (Alternative, präziser)
# Provider-Wechsel: Einfach den ACTIVE_PROVIDER unten ändern.

import os
import json
import pandas as pd
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv


load_dotenv()  # Lädt Umgebungsvariablen aus .env Datei
# KONFIGURATION - API Keys aus Environment-Variablen
# Einzusetzen in einer Umgebungsvariable oder in einer .env Datei:
# - GEMINI_API_KEY=dein_gemini_key
# - OPENAI_API_KEY=dein_openai_key

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Modell-Namen
GEMINI_MODEL = "gemini-2.5-flash"
OPENAI_MODEL = "gpt-5-mini-2025-08-07"


# =============================================================================
# DATENSTRUKTUREN


# Ergebnis der KI Analyse mit den bereinigten DataFrames und Verschiebungen
@dataclass
class ReviewResult:
  
    df_sicher: pd.DataFrame
    df_unsicher: pd.DataFrame
    df_spam: pd.DataFrame
    verschiebungen: list  # [{"artikelnummer": "...", "von": "...", "nach": "..."}]
    erfolg: bool = True
    fehler_msg: str = ""


# =============================================================================
# PROMPT TEMPLATE
# Der Prompt wird an beide Provider gleich gesendet.
# Die KI erhält die Daten als CSV und soll Muster-Anomalien erkennen.

SYSTEM_PROMPT = """Du bist ein spezialisierter KI-Analyst zur Bereinigung von PDF-Extraktionsdaten (Artikelnummern).
Deine Aufgabe: Validierung, Kategorisierung und Korrektur basierend auf Seiten-Mustern und Kontext.

INPUT DATEN:
1. SICHER (beide Engines)
2. UNSICHER (eine Engine)
3. SPAM (Verdachtsfälle/Häufige)

ANALYSE-LOGIK PRO SEITE:
1. Identifiziere das dominante Artikelnummern-Schema der Seite (z.B. "94 XXX XX").
2. Prüfe jeden Eintrag gegen dieses Schema.
3. Bei Abweichung: Nutze den KONTEXTString zur Reparatur.

REPARATUR-STRATEGIE (WICHTIG):
Oft extrahieren Engines durch Spaltenversatz Fragmente (z.B. "ab 123 45") statt der Nummer.
Prüfe den Kontext:
- Suche eine Nummer in direkter Nähe (oft rechts/links), die dem Seiten-Schema entspricht.
- ZEILEN-LOGIK: Wenn der Kontext mehrere Nummern zeigt (z.B. Tabelle), wähle diejenige, die geometrisch zur Zeile des falschen Eintrags gehört.
- FRAGMENTE: Oft ist das Ende der falschen Nummer (z.B. "...45") der Anfang der richtigen Nummer. Nutze dies als Indiz.

AKTIONEN:
- Verschiebe ungültige Nummern (Spam/Unsafe).
- Wenn der Kontext eindeutig die *richtige* Nummer zeigt, biete eine KORREKTUR an.

OUTPUT FORMAT (JSON):
Antworte NUR mit validem JSON. 
WICHTIG: Das Feld "artikelnummer" muss EXAKT dem Input entsprechen (als ID). Die korrigierte Fassung kommt in "korrektur".

{
    "verschiebungen": [
        {
            "artikelnummer": "ab 247 10", 
            "korrektur": "94 247 10",
            "von": "Sicher", 
            "nach": "Sicher", 
            "begruendung": "Extrahierter Wert war Fragment. Kontext bestätigt '94 247 10' als korrekte Nummer im Seiten-Muster."
        },
        {
            "artikelnummer": "Tel: 030", 
            "von": "Unsicher", 
            "nach": "Spam", 
            "begruendung": "Keine Artikelnummer, sondern Telefonnummer."
        }
    ]
}
Falls keine Änderungen: {"verschiebungen": []}
"""
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




# =============================================================================
# GEMINI PROVIDER (Standard) für Google Gemini 2.5 Flash - 1M Token Input Kontext ca 65.536 Output
# =============================================================================
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
                temperature=0.1  # Niedrige Temperatur für konsistente Ergebnisse
            )
        )
        
        # Response parsen
        result = json.loads(response.text)
        return result


# =============================================================================
# OPENAI PROVIDER (Alternative)
# =============================================================================
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
            reasoning_effort="high"
        )
        
        # Response parsen
        result = json.loads(response.choices[0].message.content)
        return result


# =============================================================================
# PROVIDER AUSWAHL - Hier ändern um Provider zu wechseln!
# =============================================================================
# Kommentiere den gewünschten Provider ein/aus:

#ACTIVE_PROVIDER = GeminiProvider()    # <- Standard: Gemini 2.5 Flash
ACTIVE_PROVIDER = OpenAIProvider()  # <- Alternative: GPT-5 mini


# =============================================================================
# AB HIER HAUPTFUNKTION
# =============================================================================

# Hauptfunktion zur Überprüfung und Korrektur der DataFrames mit KI
# Konvertiert die DataFrames zu CSV, sendet sie an die KI und wendet die empfohlenen Verschiebungen an
# Gibt die bereinigten DataFrames zurück
def review_dataframes(
    df_sicher: pd.DataFrame,
    df_unsicher: pd.DataFrame,
    df_spam: pd.DataFrame
) -> ReviewResult:
    # Prüfen ob überhaupt Daten vorhanden sind
    total = len(df_sicher) + len(df_unsicher) + len(df_spam)
    if total == 0:
        return ReviewResult(
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
        
        # Kopien der DataFrames erstellen für Modifikation
        df_sicher_neu = df_sicher.copy()
        df_unsicher_neu = df_unsicher.copy()
        df_spam_neu = df_spam.copy()
        
        # Verschiebungen anwenden
        for v in verschiebungen:
            artikelnummer = v.get("artikelnummer", "")
            von = v.get("von", "").lower()
            nach = v.get("nach", "").lower()
            
            # Zeile finden und verschieben - direkt auf den richtigen DataFrames arbeiten
            if von == "sicher":
                maske = df_sicher_neu["Artikelnummer"] == artikelnummer
                if maske.any():
                    zeile = df_sicher_neu[maske].copy()
                    df_sicher_neu = df_sicher_neu[~maske]
                else:
                    continue
            elif von == "unsicher":
                maske = df_unsicher_neu["Artikelnummer"] == artikelnummer
                if maske.any():
                    zeile = df_unsicher_neu[maske].copy()
                    df_unsicher_neu = df_unsicher_neu[~maske]
                else:
                    continue
            elif von == "spam":
                maske = df_spam_neu["Artikelnummer"] == artikelnummer
                if maske.any():
                    zeile = df_spam_neu[maske].copy()
                    df_spam_neu = df_spam_neu[~maske]
                else:
                    continue
            else:
                continue  # Ungültige Quelle, überspringen
            
            # In Ziel einfügen
            if nach == "sicher":
                df_sicher_neu = pd.concat([df_sicher_neu, zeile], ignore_index=True)
            elif nach == "unsicher":
                df_unsicher_neu = pd.concat([df_unsicher_neu, zeile], ignore_index=True)
            elif nach == "spam":
                df_spam_neu = pd.concat([df_spam_neu, zeile], ignore_index=True)
        
        return ReviewResult(
            df_sicher=df_sicher_neu,
            df_unsicher=df_unsicher_neu,
            df_spam=df_spam_neu,
            verschiebungen=verschiebungen,
            erfolg=True
        )
        
    except Exception as e:
        # Bei Fehler: Leere DataFrames zurückgeben und Fehlermeldung setzen
        # Die UI zeigt dann die Fehlermeldung an statt ungeprüfte Daten
        return ReviewResult(
            df_sicher=pd.DataFrame(),
            df_unsicher=pd.DataFrame(),
            df_spam=pd.DataFrame(),
            verschiebungen=[],
            erfolg=False,
            fehler_msg=f"KI-Analyse fehlgeschlagen: {str(e)}"
        )

# Gibt den Nmen des aktiven Providers zurück
def get_active_provider_name() -> str:
    return ACTIVE_PROVIDER.name
