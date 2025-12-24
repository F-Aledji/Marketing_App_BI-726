# Technische Architektur-Dokumentation

Dieses Dokument bietet einen tiefen Einblick in die technische Funktionsweise, die Datenflüsse und die Design-Entscheidungen der Anwendung.

## 1. Systemübersicht & Datenfluss

Die Anwendung folgt einem linearen **Pipeline-Pattern**, bei dem Daten durch verschiedene Verarbeitungsstufen fließen.

```mermaid
graph TD
    User[Nutzer] -->|Upload PDF| Frontend[Suchen.py]
    Frontend -->|Raw Text| Extractor[Extraction Engine]
    
    subgraph Core Processing
        Extractor -->|Regex Matches| Analyzer[Analyzer Logic]
        Analyzer -->|Kategorisierung| Data{Daten-Pool}
        Data -->|Sicher| D1[DataFrame: Sicher]
        Data -->|Unsicher / Spam| D2[DataFrames: Unsicher/Spam]
        
        D1 & D2 -->|Batching| AI[AI Reviewer]
        AI -->|3-4 Threads| API[External API (OpenAI/Gemini)]
        API -->|JSON Response| AI
    end
    
    AI -->|Korrekturen| Merger[Result Merger]
    Merger -->|Finale Daten| Session[Session State]
    
    subgraph Optional
        Session -->|Vergleich| Verify[Master-List Verification]
        Verify -->|Feedback| Frontend
    end
    
    Frontend -->|Download| Excel[Excel Exporter]
```

---

## 2. Komponenten im Detail

### 2.1 Modulare Struktur (`core/`)
Der Code basiert auf einer "Package-Based Architecture". Jede Hauptfunktion hat ein eigenes Untermodul.

| Modul | Beschreibung | Wichtige Dateien |
|-------|--------------|------------------|
| `core.extraction` | Extrahiert Rohdaten aus PDFs. | `extractors.py`: Nutzt `pymupdf` (fitz) für Text und Regex für Nummern. |
| `core.analysis` | Deterministische Logik zur Vor-Sortierung. | `analyzers.py`: Prüft Plausibilität (keine Telefonnummern, keine Jahreszahlen). |
| `core.ai` | Die Intelligenz der Anwendung. | `reviewer.py` (Manager), `providers.py` (API-Adapter), `prompts.py` (System-Prompts). |
| `core.config` | Zentrale Konfiguration. | `config.py`: Enthält Regex-Pattern (`PATTERN_ALPHA`, `PATTERN_NUMERIC`). |
| `core.utils` | Hilfsdienste. | `tracking.py`: Logging-System für das Dashboard. |

### 2.2 Extraction Engine
Die Extraktion basiert auf **Regular Expressions (Regex)**, die in `core/config/config.py` definiert sind.
- **Strategie**: Wir suchen gezielt nach Mustern ("2-4 Buchstaben + 3 Zahlen + 2 Zahlen" ODER "2 Zahlen + 3 Zahlen + 2 Zahlen").
- **Kontext**: Um jeder Fundstelle werden +/- 50 Zeichen extrahiert, damit die KI später entscheiden kann, ob es sich um eine echte Artikelnummer handelt.

### 2.3 AI Pipeline & Parallelisierung
Um Performance und Stabilität zu gewährleisten, nutzt der `AI Reviewer` ein ausgeklügeltes Batch-System.

1. **Batching**: Daten werden in Pakete à 200 Zeilen geteilt. Dies optimiert die Token-Ausnutzung der LLMs (Context Window).
2. **Parallelisierung (`ThreadPoolExecutor`)**: 
   - Netzwerk-Anfragen (I/O) blockieren den Prozessor kaum.
   - Wir starten bis zu **4 parallele Threads**.
   - Das verkürzt die Wartezeit bei 1000 Zeilen drastisch (von z.B. 60s auf 15s).
3. **Provider-Abstraction**:
   - Die Klasse `AIProvider` (in `providers.py`) ist abstrakt.
   - `OpenAIProvider` und `GeminiProvider` implementieren diese Schnittstelle.
   - **Vorteil**: Man kann den KI-Anbieter wechseln, ohne die Hauptlogik in `reviewer.py` anfassen zu müssen.

### 2.4 Tracking System
Ein "Sidecar"-Prozess für Monitoring.
- Schreibt bei jedem API-Call (Erfolg oder Fehler) eine Zeile in `data/tracking_logs.csv`.
- **Privacy**: Es werden keine Inhalte (Prompts) gespeichert, nur Metadaten (Dauer, Token, Status).
- Das `Dashboard.py` liest diese Datei *read-only*, um Konflikte zu vermeiden.

---

## 3. Fehlerbehandlung & Resilienz

- **Timeouts**: Jeder API-Call hat ein hartes Limit (60 Sekunden). Hängt die API, stürzt die App nicht ab, sondern wirft einen kontrollierten Fehler für diesen Batch.
- **Fail-Safe**: Wenn die KI komplett ausfällt, behält die App die Original-Daten bei. Der Nutzer verliert keine Daten, nur die KI-Verbesserung fällt weg.
- **Dirty Data**: Die Funktion `get_tracking_stats` nutzt `errors='coerce'`, um korrupte Zeilen im Log file zu ignorieren, damit das Dashboard nicht abstürzt.

---

## 4. Erweiterbarkeit

Das System ist für Wachstum ausgelegt:
- **Neue KI-Modelle**: Einfach eine neue Klasse in `providers.py` anlegen, die von `AIProvider` erbt.
- **Andere Dokumenttypen**: Die `extraction`-Logik kann erweitert werden, um Word-Dateien oder Bilder (OCR) zu unterstützen, solange sie Text liefern.
- **Datenbank-Anbindung**: Anstatt in Excel zu exportieren, könnte ein neues Modul `core/export/database.py` die `ReviewResult`-Objekte direkt in eine SQL-Datenbank schreiben.
