# AI Provider Module
# Enthält die Provider-Klassen für verschiedene KI-Dienste (Gemini, OpenAI)
# und die Konfiguration für API-Keys und Modell-Namen.

import os
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

# =============================================================================
# KONFIGURATION - API Keys aus Environment-Variablen
# =============================================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Modell-Namen
GEMINI_MODEL = "gemini-3-flash-preview"
OPENAI_MODEL = "gpt-5.1-2025-11-13"


# =============================================================================
# DATENSTRUKTUR FÜR API-ANTWORT
# =============================================================================

@dataclass
class AIResponse:
    """Strukturierte Antwort eines AI Providers mit Token-Tracking."""
    data: dict                  # Die geparseten Daten (verschiebungen etc.)
    input_tokens: int = 0       # Verbrauchte Input-Tokens
    output_tokens: int = 0      # Verbrauchte Output-Tokens
    total_tokens: int = 0       # Gesamt-Tokens


# =============================================================================
# ABSTRAKTE PROVIDER-KLASSE
# =============================================================================

class AIProvider(ABC):
    """Abstrakte Basisklasse für KI-Provider."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name des Providers für UI-Anzeige."""
        pass
    
    @abstractmethod
    def analyze(self, user_prompt: str, system_prompt: str) -> AIResponse:
        """
        Sendet den prompt an die KI und gibt das Ergebnis zurück.
        
        Returns:
            AIResponse mit Daten und Token-Verbrauch
        """
        pass


# =============================================================================
# GEMINI PROVIDER
# =============================================================================

class GeminiProvider(AIProvider):
    """Google Gemini 3 Flash Provider. Es ist günstiger als GPT-5.1."""
    
    @property
    def name(self) -> str:
        return "Gemini 3 Flash"
    
    def analyze(self, user_prompt: str, system_prompt: str) -> AIResponse:
        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ImportError("google-genai Package nicht installiert. pip install google-genai")
        
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY nicht gesetzt.")
        
        client = genai.Client(api_key=GEMINI_API_KEY)
        
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                response_mime_type="application/json",
                http_options={'timeout': 60000},
                thinking_config=types.ThinkingConfig(thinking_level="high")
            )
        )
        
        # Token-Daten extrahieren
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) or 0
            output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) or 0
        
        return AIResponse(
            data=json.loads(response.text),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens
        )


# =============================================================================
# OPENAI PROVIDER
# =============================================================================

class OpenAIProvider(AIProvider):
    """OpenAI GPT-5.1 Provider."""
    
    @property
    def name(self) -> str:
        return "GPT-5.1"
    
    def analyze(self, user_prompt: str, system_prompt: str) -> AIResponse:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai Package nicht installiert. pip install openai")
        
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY nicht gesetzt.")
        
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            timeout=60.0
        )
        
        # Token-Daten extrahieren
        input_tokens = 0
        output_tokens = 0
        if response.usage:
            input_tokens = response.usage.prompt_tokens or 0
            output_tokens = response.usage.completion_tokens or 0
        
        return AIResponse(
            data=json.loads(response.choices[0].message.content),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens
        )


# =============================================================================
# PROVIDER AUSWAHL
# =============================================================================

#ACTIVE_PROVIDER = GeminiProvider()
ACTIVE_PROVIDER = OpenAIProvider()


def get_active_provider_name() -> str:
    """Gibt den Namen des aktiven Providers zurück."""
    return ACTIVE_PROVIDER.name
