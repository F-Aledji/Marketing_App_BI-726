
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
# =============================================================================

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
# =============================================================================
# Der Prompt wird an beide Provider gleich gesendet.
# Die KI erhält die Daten als CSV und soll Muster-Anomalien erkennen.

SYSTEM_PROMPT = """Du bist ein Experte für Artikelnummer-Analyse. Du erhältst drei Listen von Artikelnummern aus einer PDF-Extraktion:

1. SICHER: Nummern die von beiden Extraktions-Engines PyMuPDF und pdfplumber gefunden wurden
2. UNSICHER: Nummern die nur von einer Engine gefunden wurden
3. SPAM: Womöglich Nummern die als falsch-positiv erkannt wurden (Telefonnummern, etc.) oder mehr als 10 Mal in der PDF vorkommen. Verdacht auf falsche Nummern.

Deine Aufgabe:
- Analysiere die Muster der Artikelnummern PRO SEITE
- Erkenne Ausreißer die nicht ins Muster passen als Hilfestellung erhältst du die Seitenanzahl und den Kontext um die gefundene Nummer herum. Der Kontext ist für dich die Hilfe um zu verstehen ob die Nummer tatsächlich eine Artikelnummer ist.
- Beispiel: Wenn Seite 9 nur "62 2XX XX" Nummern hat, gehört "ab XXX XX" wahrscheinlich dort nicht hin
- Verschiebe falsch klassifizierte Nummern in die richtige Kategorie


WICHTIG: 
- Analysiere NUR basierend auf Nummern-Mustern pro Seite
- Sei konservativ - nur bei klaren Muster-Verletzungen verschieben und keine Vermutungen anstellen
- Gib eine Begründung zu jede Verschiebung an um die Entscheidung nachvollziehbar zu machen

Antworte NUR mit validem JSON in diesem Format:
{
    "verschiebungen": [
        {"artikelnummer": "ab 247 10", "von": "Sicher", "nach": "Spam"},
        {"artikelnummer": "62 001 01", "von": "Spam", "nach": "Sicher"}
    ]

     "verschiebungen": [
        {"artikelnummer": "tel 222 11", "von": "Unsicher", "nach": "Spam"},
        {"artikelnummer": "92 001 01", "von": "Spam", "nach": "Sicher"}
    ]
}

Falls keine Verschiebungen nötig sind musst du in dem Fall nichts tun. Antworte nur mit den Verschiebungen die du vornimmst.
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
                temperature=0.1  # Niedrige Temperatur für konsistente Ergebnisse
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

ACTIVE_PROVIDER = GeminiProvider()    # <- Standard: Gemini 2.5 Flash
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
            
            # Quell-DataFrame bestimmen
            if von == "sicher":
                quell_df = df_sicher_neu
            elif von == "unsicher":
                quell_df = df_unsicher_neu
            elif von == "spam":
                quell_df = df_spam_neu
            else:
                continue  # Ungültige Quelle, überspringen
            
            # Zeile finden und verschieben
            maske = quell_df["Artikelnummer"] == artikelnummer
            if maske.any():
                # Zeile extrahieren
                zeile = quell_df[maske].copy()
                
                # Aus Quelle entfernen
                if von == "sicher":
                    df_sicher_neu = df_sicher_neu[~maske]
                elif von == "unsicher":
                    df_unsicher_neu = df_unsicher_neu[~maske]
                elif von == "spam":
                    df_spam_neu = df_spam_neu[~maske]
                
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
