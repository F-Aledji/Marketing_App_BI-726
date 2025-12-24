# WS Bestellnummer Suche App 🚀

Eine intelligente Python-Anwendung zur Extraktion, Analyse und KI-gestützten Überprüfung von Artikelnummern aus PDF-Dokumenten (wie Rechnungen oder Lieferscheinen).

## ✨ Features

- **PDF-Extraktion**: Findet Artikelnummern basierend auf komplexen Regex-Mustern.
- **Plausibilitäts-Check**: Sortiert Treffer automatisch in "Sicher", "Unsicher" und "Spam".
- **AI-Review**: KI (OpenAI GPT-5.1 oder Google Gemini) prüft unsichere Treffer und korrigiert sie bei Bedarf.
- **Master-List Verifizierung**: Abgleich gegen eine hochgeladene "Referenzliste" (Excel/CSV).
- **Excel-Export**: Saubere Ausgabe aller Ergebnisse.
- **Developer Dashboard**: Separates Tool zur Überwachung von API-Kosten, Token-Verbrauch und Performance.

---

## 🛠️ Installation

1. **Repository klonen**
   ```bash
   git clone <repo-url>
   cd Marketing_App_BI-726
   ```

2. **Abhängigkeiten installieren**
   ```bash
   pip install -r requirements.txt
   ```
   *Falls `requirements.txt` fehlt:* `pip install streamlit pandas google-genai openai pymupdf python-dotenv openpyxl`

3. **API-Keys setzen**
   Erstelle eine `.env` Datei im Hauptverzeichnis:
   ```ini
   OPENAI_API_KEY=sk-...
   GEMINI_API_KEY=...
   ```

---

## 🚀 Nutzung

### Für Endnutzer (Die Suche)
Startet die Hauptanwendung im Browser:
```bash
streamlit run Suchen.py
```
1. PDF hochladen.
2. (Optional) Referenzliste in der Sidebar hochladen.
3. Ergebnisse prüfen und exportieren.

### Für Entwickler (Das Dashboard)
Startet das Monitoring-Tool (nicht für Endnutzer gedacht):
```bash
streamlit run Dashboard.py
```
- Zeigt Live-Tracking aller API-Calls.
- Berechnet Kosten basierend auf Token-Verbrauch.
- Ermöglicht Debugging bei Fehlern.

---

## 📂 Projektstruktur

```
.
├── Suchen.py                 # Hauptanwendung (Frontend)
├── Dashboard.py              # Developer Dashboard (Backend-Monitoring)
├── core/                     # Kernlogik (Modularisiert)
│   ├── ai/                   # KI-Logik (Reviewer, Provider, Prompts)
│   ├── analysis/             # Plausibilität & Verifizierung
│   ├── config/               # Einstellungen & Regex
│   ├── extraction/           # PDF-Text-Extraktion
│   ├── export/               # Excel-Export
│   ├── ui/                   # Sidebar & UI-Komponenten
│   └── utils/                # Tracking & Hilfsfunktionen
├── data/                     # Lokale Daten (Logs, Blacklist)
└── tests/                    # Pytest Unit-Tests
```

## 🧪 Tests

Das Projekt verfügt über eine umfassende Test-Suite (48 Tests).
Ausführen mit:
```bash
pytest tests/
```

---

## 📝 Lizenz
Internes Tool. Alle Rechte vorbehalten.
