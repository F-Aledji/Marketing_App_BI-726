# AI Provider Module
# Enthält die Provider-Klassen für verschiedene KI-Dienste (Gemini, OpenAI)
# und die Konfiguration für API-Keys und Modell-Namen.

import os
import json
from abc import ABC, abstractmethod

# =============================================================================
# KONFIGURATION - API Keys aus Environment-Variablen
# =============================================================================
# Einzusetzen in einer Umgebungsvariable oder in einer .env Datei:
# - GEMINI_API_KEY=dein_gemini_key
# - OPENAI_API_KEY=dein_openai_key

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


# Modell-Namen
GEMINI_MODEL = "gemini-3-flash-preview"
OPENAI_MODEL = "gpt-5.1-2025-11-13"


# =============================================================================
# ABSTRAKTE PROVIDER-KLASSE
# =============================================================================

class AIProvider(ABC):
    """
    Abstrakte Basisklasse für KI-Provider.
    Jedes Modell muss die analyze()-Methode implementieren.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name des Providers für UI-Anzeige."""
        pass
    
    @abstractmethod
    def analyze(self, user_prompt: str, system_prompt: str) -> dict:
        """
        Sendet den prompt an die KI und gibt das Ergebnis zurück.
        
        Args:
            user_prompt: Der User-Prompt mit den zu analysierenden Daten
            system_prompt: Der System-Prompt mit den Anweisungen
        
        Returns:
            Dict mit "verschiebungen" Liste
        
        Raises:
            ImportError: Wenn das Provider-Package nicht installiert ist
            ValueError: Wenn der API-Key nicht gesetzt ist
        """
        pass


# =============================================================================
# GEMINI PROVIDER
# =============================================================================

class GeminiProvider(AIProvider):
    """
    Google Gemini 3 Flash Provider.
    - 1M Token Input Kontext
    - ca. 65.536 Output
    - Günstiger als OpenAI
    """
    
    @property
    def name(self) -> str:
        return "Gemini 3 Flash"
    
    def analyze(self, user_prompt: str, system_prompt: str) -> dict:
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
                system_instruction=system_prompt,
                response_mime_type="application/json",
                
                http_options={'timeout': 60000}  # Timeout in Millisekunden für google-genai
            )
        )
        
        # Response parsen
        return json.loads(response.text)


# =============================================================================
# OPENAI PROVIDER
# =============================================================================

class OpenAIProvider(AIProvider):
    """
    OpenAI GPT-5.1 Provider.
    - 400k Token Input
    - 128k Token Output Kontext
    - Etwas teurer als Gemini, aber oft präziser bei strukturierten Daten
    """
    
    @property
    def name(self) -> str:
        return "GPT-5.1"
    
    def analyze(self, user_prompt: str, system_prompt: str) -> dict:
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
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,  # Niedrige Temperatur für konsistente Ergebnisse
            timeout=60.0      # Timeout in Sekunden für OpenAI
        )
        
        # Response parsen
        return json.loads(response.choices[0].message.content)


# =============================================================================
# PROVIDER AUSWAHL - Hier ändern um Provider zu wechseln!
# =============================================================================
# Kommentiere den gewünschten Provider ein/aus:

# ACTIVE_PROVIDER = GeminiProvider()    # <- Gemini (experimentell, kann hängen)
ACTIVE_PROVIDER = OpenAIProvider()      # <- OpenAI (stabil, schneller)


def get_active_provider_name() -> str:
    """Gibt den Namen des aktiven Providers zurück."""
    return ACTIVE_PROVIDER.name
